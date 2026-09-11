"""Offline adapter fixtures are synthetic test data, never reported as real PPA."""
import json
from pathlib import Path
import pytest
from multigent.tools import vivado
from multigent.agents.ppa_optimizer import PPAOptimizerAgent
from multigent.agents.rtl_generator import RTLGeneratorAgent
from multigent.agents.base import AgentRuntimeError
from multigent.orchestration import ppa_node, artifacts
from multigent.orchestration.graph import build_workflow_graph
from multigent.orchestration.routes import route_after_rtl, route_after_debugger
from multigent.tools.cocotb_runner import xunit_complete


def bundle(tmp_path):
    rtl = tmp_path/'source'; rtl.mkdir()
    (rtl/'top.sv').write_text('module top(input logic clk); endmodule\n')
    out = tmp_path/'bundle'
    vivado.prepare_bundle(rtl,out,'top',{'part':'fixture-part','clock_port':'clk','period_ns':10}, {'status':'PASS'})
    return out


def reports(out, slack='0.3'):
    (out/'timing.tsv').write_text(f'vivado_version\tfixture\nclock_count\t1\nrouted_fully\t1\nrouting_errors\t0\ncritical_drc_count\t0\nwns_ns\t{slack}\nwhs_ns\t0.1\ncritical_path_delay_ns\t9.2\n')
    (out/'utilization.rpt').write_text('| CLB LUTs | 100 | 0 | 10000 | 1 |\n| CLB Registers | 40 | 0 | 1000 | 4 |\n| DSPs | 4 | 0 | 100 | 4 |\n| Block RAM Tile | 0.5 | 0 | 100 | .5 |\n')
    (out/'power.rpt').write_text('| Total On-Chip Power (W) | 0.8 |\n')
    for name in ('timing_summary.rpt','critical_paths.rpt','drc.rpt'):
        (out/name).write_text('fixture report\n')
    (out/'route_status.rpt').write_text('# of unrouted nets : 0\n')
    (out/'completed.marker').write_text('VIVADO_OOC_COMPLETE\n')


def test_missing_tool_has_no_ppa(tmp_path,monkeypatch):
    out=bundle(tmp_path)
    monkeypatch.setattr(vivado.shutil,'which',lambda _:None)
    result=vivado.run_bundle(out)
    assert result['status']=='TOOL_UNAVAILABLE' and result['metrics'] is None
    assert (out/'run.tcl').exists()


def test_source_tamper_refuses_tool(tmp_path,monkeypatch):
    out=bundle(tmp_path); (out/'rtl/top.sv').write_text('changed')
    monkeypatch.setattr(vivado.shutil,'which',lambda _:pytest.fail('must check provenance first'))
    assert vivado.run_bundle(out)['status']=='PROVENANCE_MISMATCH'


def test_requires_functional_pass(tmp_path):
    with pytest.raises(ValueError,match='PASS'):
        vivado.prepare_bundle(tmp_path,tmp_path/'out','top',{}, {'status':'FAIL'})


def test_parser_extracts_without_inventing_fmax(tmp_path):
    reports(tmp_path)
    metrics=vivado.parse_reports(tmp_path)
    assert metrics['lut']==100 and metrics['bram_tiles']==0.5
    assert metrics['fmax_mhz'] is None


@pytest.mark.parametrize('slack',['NaN','inf','missing'])
def test_parser_rejects_invalid_numbers(tmp_path,slack):
    reports(tmp_path,slack)
    with pytest.raises(ValueError): vivado.parse_reports(tmp_path)


def test_parser_missing_power_is_not_zero(tmp_path):
    reports(tmp_path); (tmp_path/'power.rpt').write_text('unsupported layout')
    with pytest.raises(ValueError,match='power'): vivado.parse_reports(tmp_path)


@pytest.mark.parametrize('slack,expected',[('0.3','PASS'),('-0.1','TIMING_FAILED')])
def test_process_result_and_report_gate(tmp_path,monkeypatch,slack,expected):
    from subprocess import CompletedProcess
    out=bundle(tmp_path)
    monkeypatch.setattr(vivado.shutil,'which',lambda _:'/fixture/vivado')
    def execute(*args,**kwargs):
        reports(out,slack)
        return CompletedProcess([],0,'','')
    monkeypatch.setattr(vivado,'run_process',execute)
    result=vivado.run_bundle(out)
    assert result['status']==expected
    assert 'critical_paths.rpt' in result['reports']
    assert vivado.run_bundle(out)['status']=='STALE_OUTPUT'


def test_ppa_scope_enforced():
    with pytest.raises(AgentRuntimeError,match='outside'):
        RTLGeneratorAgent._validate_authorized_change_scope(changed_modules={'other'},task_type='PPA_OPTIMIZATION',feedback={'optimization_plan':{'affected_modules':['top']},'frozen_verifier':True})


def test_optimization_reuses_verifier_and_full_tools():
    assert route_after_rtl({'rtl_status':'RTL_GENERATED','rtl_task_type':'PPA_OPTIMIZATION','verifier_status':'VERIFICATION_READY','verification_plan':{'full':['test_top']}})=='verification_tools'


def test_debugger_testbench_route_is_bounded():
    assert route_after_debugger({'debugger_status':'VERIFICATION_REPAIR_REQUIRED'})=='verification_repair'
    assert route_after_debugger({'debugger_status':'VERIFICATION_REPAIR_REQUIRED','verifier_revision':2})=='failed'


@pytest.mark.parametrize('xml,ok',[
    ('<testsuites><testsuite/></testsuites>',False),
    ('<testsuites><testsuite><testcase name="a"/></testsuite></testsuites>',True),
    ('<testsuites><testsuite><testcase><skipped/></testcase></testsuite></testsuites>',False),
    ('<testsuites><testsuite><testcase><error/></testcase></testsuite></testsuites>',False),
    ('broken',False)])
def test_xunit_never_vacuously_passes(tmp_path,xml,ok):
    path=tmp_path/'results.xml';path.write_text(xml)
    assert xunit_complete(path)==ok


def test_verifier_receives_no_rtl_state():
    from multigent.orchestration.verifier_node import make_verifier_node
    class Spy:
        def run_from_state(self,state):
            assert 'rtl_result' not in state and 'verification_evidence' not in state
            return {'verifier_status':'VERIFICATION_READY'}
    make_verifier_node(Spy())({'run_id':'test','rtl_result':{'secret':'source'},'verification_evidence':{'stdout':'RTL source line'}})


def test_mutating_protected_artifacts_stops_graph(tmp_path,monkeypatch):
    monkeypatch.setattr(artifacts,'WORKSPACE_ROOT',tmp_path)
    (tmp_path/'tests').mkdir(); (tmp_path/'tests/test_top.py').write_text('assert True')
    def malicious(state):
        (tmp_path/'tests/test_top.py').write_text('pass')
        return {'rtl_status':'RTL_GENERATED'}
    update=artifacts.guarded('rtl_generator',malicious)({'history':[]})
    assert 'protected tests' in update['orchestration_error']
    assert (tmp_path/'attempts/0000-rtl_generator/tests/test_top.py').read_text()=='assert True'


def test_synthesis_rejects_stale_verification(tmp_path,monkeypatch):
    monkeypatch.setattr(artifacts,'WORKSPACE_ROOT',tmp_path)
    called=[]
    update=artifacts.guarded('synthesis',lambda s:called.append(True))({'verified_hashes':{},'history':[]})
    assert 'since deterministic verification' in update['orchestration_error'] and not called


def test_graph_optimization_runs_full_regression_again(tmp_path,monkeypatch):
    import multigent.orchestration.graph as module
    monkeypatch.setattr(artifacts,'WORKSPACE_ROOT',tmp_path)
    monkeypatch.setattr(ppa_node,'WORKSPACE_ROOT',tmp_path)
    contract={'module_manifest':{'modules':[{'name':'top'}]}}
    monkeypatch.setattr(ppa_node,'load_frozen_architecture',lambda _:contract)
    calls=[]
    class RTL:
        def run_from_state(self,state):
            calls.append('rtl:'+state['rtl_task_type'])
            return {'rtl_status':'RTL_GENERATED','rtl_files':['top.sv'],'needs_regression':True}
    class Verifier:
        def run_from_state(self,state):
            calls.append('verifier')
            return {'verifier_status':'VERIFICATION_READY','verification_plan':{'top_module':'top'}}
    def verify(state):
        calls.append('regression')
        return {'verification_status':'PASS','verification_evidence':{'status':'PASS'},'needs_regression':False}
    def synthesize(state):
        calls.append('vivado')
        return {'synthesis_result':{'status':'PASS','manifest_sha256':'hash','metrics':{'lut':100-state.get('ppa_iteration',0)},'bundle':str(tmp_path/'bundle')}}
    class Optimizer:
        def run(self,context,run_id):
            calls.append('optimizer')
            return {'action':'OPTIMIZE','affected_modules':['top'],'protected_modules':[],
                    'regression_required':'FULL','preserve_contract':True,
                    'evidence_manifest_sha256':'hash','recommended_change':'Simplify redundant mux',
                    'summary':'fixture','do_not_change':['contracts']}
    monkeypatch.setattr(module,'verification_tools_node',verify)
    monkeypatch.setattr(module,'synthesis_node',synthesize)
    graph=build_workflow_graph(rtl_agent=RTL(),verifier_agent=Verifier(),ppa_agent=Optimizer())
    result=graph.invoke({'run_id':'fixture','user_request':'streaming block','architecture_dir':str(tmp_path/'architecture'),
                         'architecture_status':'READY','rtl_context':{'frozen_architecture':contract},
                         'rtl_task_type':'INITIAL_GENERATION','ppa_iteration':0,'max_ppa_iterations':1,'history':[]})
    assert result['status']=='SUCCESS',result
    assert calls==['rtl:INITIAL_GENERATION','verifier','regression','vivado','optimizer','rtl:PPA_OPTIMIZATION','regression','vivado']
    assert (tmp_path/'reports/final.json').is_file()


def test_external_result_cannot_describe_other_rtl(tmp_path,monkeypatch):
    from subprocess import CompletedProcess
    out=bundle(tmp_path)
    monkeypatch.setattr(vivado.shutil,'which',lambda _:'/fixture/vivado')
    def execute(*args,**kwargs):
        reports(out)
        return CompletedProcess([],0,'','')
    monkeypatch.setattr(vivado,'run_process',execute)
    vivado.run_bundle(out)
    config={'part':'fixture-part','clock_port':'clk','period_ns':10}
    assert vivado.import_result(out,tmp_path/'source',config)['status']=='PASS'
    (tmp_path/'source/top.sv').write_text('other rtl')
    with pytest.raises(ValueError,match='different RTL'):
        vivado.import_result(out,tmp_path/'source',config)


def test_optimizer_cannot_use_report_from_another_candidate():
    context={'synthesis_result':{'manifest_sha256':'a'},'frozen_architecture':{'module_manifest':{'modules':[{'name':'top'}]}}}
    plan={'action':'OPTIMIZE','affected_modules':['top'],'protected_modules':[],
          'regression_required':'FULL','preserve_contract':True,'evidence_manifest_sha256':'b'}
    with pytest.raises(AgentRuntimeError,match='different candidate'):
        PPAOptimizerAgent.validate(plan,context)


def test_missing_vivado_never_calls_optimizer(tmp_path,monkeypatch):
    assert ppa_node.route_after_synthesis({'synthesis_result':{'status':'TOOL_UNAVAILABLE'}})=='final_report'


def test_verification_repair_does_not_forward_debugger_prose(tmp_path,monkeypatch):
    monkeypatch.setattr(artifacts,'WORKSPACE_ROOT',tmp_path)
    monkeypatch.setattr(artifacts,'build_verification_context',lambda **kwargs:{'user_request':'identity'})
    update=artifacts.verification_repair_node({'user_request':'identity','architecture_dir':str(tmp_path),
                                             'diagnosis':{'root_cause':'RTL_SOURCE_SECRET'},
                                             'verification_evidence':{'stdout':'RTL_SOURCE_SECRET'}})
    assert 'RTL_SOURCE_SECRET' not in json.dumps(update)


def test_optimizer_keeps_better_baseline(tmp_path,monkeypatch):
    baseline={'architecture_version':1,'synthesis_result':{'status':'PASS','metrics':{'lut':50}}}
    state={'architecture_version':1,'verification_status':'PASS','synthesis_result':{'status':'PASS','metrics':{'lut':70}},
           'verification_evidence':{'status':'PASS'},'best_candidate':baseline,'ppa_objective':'lut'}
    update=ppa_node.make_ppa_node(object())(state)
    assert update['best_candidate']==baseline and update['ppa_status']=='NO_IMPROVEMENT'


def test_incomplete_routing_fails_even_with_positive_slack(tmp_path):
    reports(tmp_path)
    path=tmp_path/'timing.tsv';path.write_text(path.read_text().replace('routed_fully\t1','routed_fully\t0'))
    with pytest.raises(ValueError,match='routing'):
        vivado.parse_reports(tmp_path)


def test_diagnostic_probe_preserves_original_test_and_is_not_acceptance(tmp_path,monkeypatch):
    from multigent.tools import diagnostic
    (tmp_path/'tests').mkdir()
    original='import cocotb\n@cocotb.test()\nasync def check(dut):\n    assert 1 == 1\n'
    (tmp_path/'tests/test_top.py').write_text(original)
    monkeypatch.setattr(diagnostic,'run_cocotb_regression',lambda **kwargs:{'status':'PASS'})
    result=diagnostic.collect_diagnostics(tmp_path,{'top_module':'top','regression_groups':{'full':['test_top']},'seed':1},tmp_path/'probe')
    assert result['purpose']=='DIAGNOSTIC_ONLY_NOT_ACCEPTANCE'
    assert (tmp_path/'tests/test_top.py').read_text()==original
    assert '@diagnostic' in (tmp_path/'probe/tests/test_top.py').read_text()


def test_diagnostic_route_is_bounded():
    assert route_after_debugger({'debugger_status':'EVIDENCE_INSUFFICIENT','max_diagnostic_iterations':2})=='diagnostic_probe'
    assert route_after_debugger({'debugger_status':'EVIDENCE_INSUFFICIENT','max_diagnostic_iterations':2,'diagnostic_iteration':2})=='failed'


def test_resume_refuses_wrong_workspace_before_any_agent_call(tmp_path):
    import os,subprocess,sys
    state=tmp_path/'saved'/'state'/'latest.json';state.parent.mkdir(parents=True)
    state.write_text(json.dumps({'run_id':'test','user_request':'identity'}))
    completed=subprocess.run([sys.executable,'-m','multigent.orchestration.graph','--resume-state',str(state)],
        env={**os.environ,'NPU_WORKSPACE_ROOT':str(tmp_path/'wrong')},capture_output=True,text=True)
    assert completed.returncode==2 and 'refusing to mix workspaces' in completed.stderr
    assert not (tmp_path/'wrong').exists()
