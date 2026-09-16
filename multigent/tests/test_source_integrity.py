"""Reject vacuous checks/API drift without rejecting legitimate package files/helpers."""
import pytest
from multigent.agents.base import AgentRuntimeError
from multigent.agents.source_checks import validate_python_integrity, preserve_python_api, sv_port_names
from multigent.agents.verifier import VerifierAgent
from multigent.agents.rtl_generator import RTLGeneratorAgent
from multigent.orchestration.verification_tools_node import simulation_check_summary

@pytest.mark.parametrize('source', [
    'def check():\n    pass\n', 'async def check():\n    "docstring"\n',
    'def check(x):\n    assert True\n', 'def check(x):\n    assert x or True\n',
    'def check(x):\n    assert 2 == 2\n',
])
def test_rejects_empty_or_vacuous(source):
    with pytest.raises(AgentRuntimeError):
        validate_python_integrity('test_design.py', source)

@pytest.mark.parametrize('source', [
    'def check(actual, expected):\n    assert actual == expected\n',
    'def fail():\n    assert False, "unexpected output"\n',
    'async def check(dut):\n    await independent_checker(dut)\n',
])
def test_allows_real_checks_and_delegated_oracle(source):
    validate_python_integrity('test_design.py', source)

def test_empty_package_init_is_allowed():
    VerifierAgent._validate_python_content('__init__.py', '', cocotb_required=False)

def candidate(source, path='test_core.py'):
    return {'test_files':[{'path':path, 'content':source}]}

@pytest.mark.parametrize('replacement', ['def renamed(a): return a', 'def helper(b): return b', 'def helper(*, a): return a'])
def test_preserves_python_function_identity(replacement):
    with pytest.raises(AgentRuntimeError, match='function name and call signature'):
        preserve_python_api(candidate('def helper(a): return a'), candidate(replacement))

def test_allows_new_helpers_and_body_repair():
    preserve_python_api(candidate('def helper(a): return a'),
                        candidate('def helper(a): return a+1\ndef extra(): return 7'))

def test_preserves_filename():
    with pytest.raises(AgentRuntimeError, match='filename'):
        preserve_python_api(candidate('def helper(a): return a'), candidate('def helper(a): return a','renamed.py'))

def test_invalid_initial_python_can_be_repaired():
    preserve_python_api(candidate('def helper('), candidate('def helper(a): return a'))

def test_rtl_function_rename_is_rejected():
    old='module core(output y); function automatic int calc(input int a); return a; endfunction assign y=calc(0); endmodule'
    with pytest.raises(AgentRuntimeError, match='function/task names'):
        RTLGeneratorAgent._validate_module_file('core.sv','core',old.replace('calc','renamed'),'FUNCTIONAL_REPAIR',{'core.sv':old})

def test_port_names_with_parameters_and_inherited_widths():
    assert sv_port_names('module core #(parameter W=8)(input logic [W-1:0] a,b, output logic y); assign y=0; endmodule','core') == {'a','b','y'}

def test_absent_simulation_evidence_cannot_pass():
    checks=simulation_check_summary({'status':'TOOL_UNAVAILABLE'})
    assert checks['protocol_checks']['status']=='INCOMPLETE'
    assert checks['coverage_checks']['status']=='NOT_RUN'

def test_coverage_failure_does_not_relabel_passing_test_cases():
    checks=simulation_check_summary({'status':'COVERAGE_FAILURE','tests':3,'failures':0,
        'functional_coverage':{'status':'FAIL','samples':10,'missing_bins':['edge'],'assertion_failures':[]}})
    assert checks['cocotb_regression']['status']=='PASS'
    assert checks['coverage_checks']['status']=='FAIL'

def test_protocol_failure_reported_separately():
    checks=simulation_check_summary({'status':'SIMULATION_FAILURE','functional_coverage':{
        'status':'FAIL','failure_records':[{'category':'tb.contract_generated_protocol','message':'unstable payload'}]}})
    assert checks['protocol_checks']['status']=='FAIL'

@pytest.mark.parametrize("malformed", [False, True])
def test_default_preflight_has_no_model_call(tmp_path, monkeypatch, malformed):
    from multigent.orchestration import verifier_review_node as node, artifacts
    from multigent.tests.test_verifier import generic_fir_context, verification_ready_result
    monkeypatch.setattr(node, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(artifacts, 'WORKSPACE_ROOT', tmp_path)
    context=generic_fir_context()
    monkeypatch.setattr(node, 'build_verification_context', lambda **kwargs: context)
    monkeypatch.setattr(node.VerifierReviewAgent, '__init__', lambda *a, **kw: pytest.fail('Must not construct reviewer agent'))
    candidate=VerifierAgent._with_contract_generated_blocks(verification_ready_result(), context)
    if malformed: candidate['test_files'][0]['content']='async def broken('
    for field,owner in [('test_files','tests'),('reference_files','reference')]:
        (tmp_path/owner).mkdir()
        for item in candidate[field]:
            (tmp_path/owner/item['path'].split('/')[-1]).write_text(item['content'].rstrip('\n')+'\n')
    state={'user_request':'fir','verifier_status':'VERIFICATION_READY','verifier_result':candidate,
           'architecture_dir':str(tmp_path/'architecture')}
    update=node.make_verifier_review_node()(state)
    assert update['verifier_review_status']==('VERIFIER_REPAIR_REQUIRED' if malformed else 'APPROVED')
    assert update['verification_status']=='PENDING'
    assert (tmp_path/'verification/testbench-checks.json').is_file()

def test_ui_individual_simulator_results_and_path_boundary(tmp_path):
    from multigent.ui.server import simulator_cases
    xml=tmp_path/'results.xml'
    xml.write_text('<testsuites><testsuite><testcase classname="test_core" name="directed"/><testcase name="random"><failure/></testcase><testcase name="reset"><skipped/></testcase></testsuite></testsuites>')
    state={'verification_evidence':{'cocotb':{'results_xml':str(xml)}}}
    assert [x['status'] for x in simulator_cases(tmp_path,state)]==['PASS','FAIL','SKIPPED']
    assert simulator_cases(tmp_path/'other',state)==[]

def test_repair_cannot_turn_registered_test_into_unexecuted_helper():
    with pytest.raises(AgentRuntimeError, match='function name and call signature'):
        preserve_python_api(candidate('@cocotb.test()\nasync def check(dut): await verify(dut)'),
                            candidate('async def check(dut): await verify(dut)'))
