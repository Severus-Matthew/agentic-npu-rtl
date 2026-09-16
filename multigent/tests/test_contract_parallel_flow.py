"""Behavior tests for independent review, concurrency, repair budgets and escalation."""
import copy
import json
from pathlib import Path
from threading import Barrier
import pytest
from multigent.agents.base import AgentRuntimeError
from multigent.agents.contract_reviewer import ContractReviewerAgent
from multigent.orchestration import artifacts, parallel_generation as parallel
from multigent.orchestration import graph as workflow
from multigent.orchestration import contract_review_node as contracts
from multigent.orchestration import architecture_escalation as escalation
from multigent.orchestration.routes import route_after_verification
from multigent.orchestration.contract_review_node import route_after_contract_review
from multigent.tests.test_verifier import generic_fir_context

APPROVED = {'status':'APPROVED','summary':'Consistent','findings':[]}
REVISE = {'status':'REVISION_REQUIRED','summary':'Ambiguous reset','findings':[
    {'contract_path':'/interface_contract/reset','issue':'Missing interrupted-work behavior',
     'requested_change':'Specify whether reset discards a pending transaction'}]}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    for module in (artifacts, parallel, contracts, escalation):
        monkeypatch.setattr(module,'WORKSPACE_ROOT',tmp_path)
    (tmp_path/'architecture').mkdir()
    (tmp_path/'architecture/architecture_contract.yaml').write_text('design: test\n')
    context = generic_fir_context()
    for module in (contracts, escalation):
        monkeypatch.setattr(module,'build_verification_context',lambda **kw:copy.deepcopy(context))
    return tmp_path


def initial(root):
    return {'run_id':'fixture','user_request':'generic fir','architecture_dir':str(root/'architecture'),
            'architecture_status':'READY','architecture_version':1,'rtl_task_type':'INITIAL_GENERATION',
            'contract_review_status':'APPROVED','contract_review_hashes':artifacts.hashes(root/'architecture'),
            'history':[],'errors':[],'verification_only':True}


def test_real_graph_executes_generators_concurrently_without_cross_context(workspace,monkeypatch):
    rendezvous = Barrier(2,timeout=5)
    calls=[]
    class RTL:
        def run_from_state(self,state):
            assert 'verifier_result' not in state and 'verification_context' not in state
            rendezvous.wait()
            calls.append('rtl')
            (workspace/'rtl').mkdir()
            (workspace/'rtl/top.sv').write_text('module top; endmodule\n')
            return {'rtl_status':'RTL_GENERATED','rtl_files':['top.sv']}
    class TB:
        def run_from_state(self,state):
            assert 'rtl_context' not in state and 'rtl_result' not in state and 'rtl_files' not in state
            rendezvous.wait()
            calls.append('tb')
            (workspace/'tests').mkdir()
            (workspace/'tests/test_top.py').write_text('assert True\n')
            return {'verifier_status':'VERIFICATION_READY','verification_plan':{'top_module':'top'}}
    def review(state):
        assert set(calls)=={'rtl','tb'}
        return {'verifier_review_status':'APPROVED',
                'verifier_review_hashes':artifacts.review_definition_hashes(state)}
    monkeypatch.setattr(workflow,'make_verifier_review_node',lambda _:review)
    monkeypatch.setattr(workflow,'verification_tools_node',lambda state:{'verification_status':'PASS',
                         'needs_regression':False,'verification_evidence':{'status':'PASS'}})
    state=initial(workspace)
    state.update(rtl_context={'own':'rtl'},verification_context={'own':'tb'},verifier_result={'private':'tb'},rtl_result={'private':'rtl'})
    result=workflow.build_workflow_graph(rtl_agent=RTL(),verifier_agent=TB()).invoke(state)
    assert result['status']=='SUCCESS', result
    assert result['verified_hashes']==artifacts.inputs(result)
    saved=json.loads((workspace/'state/latest.json').read_text())
    assert saved['rtl_status']=='RTL_GENERATED' and saved['verifier_status']=='VERIFICATION_READY'
    assert len(list((workspace/'attempts').glob('*-rtl_generator')))==1
    assert len(list((workspace/'attempts').glob('*-verifier')))==1


def test_branch_failure_joins_without_running_verification(workspace,monkeypatch):
    class RTL:
        def run_from_state(self,state): raise RuntimeError('provider unavailable')
    class TB:
        def run_from_state(self,state): return {'verifier_status':'VERIFICATION_READY'}
    monkeypatch.setattr(workflow,'verification_tools_node',lambda state:pytest.fail('cannot simulate failed generation'))
    result=workflow.build_workflow_graph(rtl_agent=RTL(),verifier_agent=TB()).invoke(initial(workspace))
    assert 'provider unavailable' in result['orchestration_error']
    assert result['status']=='FAILED'


def test_contract_review_filters_all_downstream_artifacts(monkeypatch):
    agent=ContractReviewerAgent()
    captured={}
    def generate(**kw): captured.update(kw); return copy.deepcopy(APPROVED)
    monkeypatch.setattr(agent,'run_structured',generate)
    agent.review({**generic_fir_context(),'rtl':'RTL_SECRET','testbench':'TB_SECRET'},run_id='fixture')
    assert 'RTL_SECRET' not in captured['task'] and 'TB_SECRET' not in captured['task']
    assert 'frozen_architecture' in captured['task']


def test_contract_review_hashes_bind_approval(workspace):
    class Reviewer:
        def review(self,*args,**kwargs): return copy.deepcopy(APPROVED)
    state=initial(workspace)
    state.update(contracts.make_contract_review_node(Reviewer())(state))
    parallel.generation_start(state)
    (workspace/'architecture/architecture_contract.yaml').write_text('design: changed\n')
    with pytest.raises(ValueError,match='exact current architecture'):
        parallel.generation_start(state)


def test_rejected_contract_routes_back_and_is_bounded(workspace):
    class Reviewer:
        def review(self,*args,**kwargs): return copy.deepcopy(REVISE)
    state=initial(workspace)
    update=contracts.make_contract_review_node(Reviewer())(state)
    assert update['architecture_conflict']['findings']==REVISE['findings']
    assert update['contract_review_hashes']=={}
    assert route_after_contract_review(update)=='architect'
    assert route_after_contract_review({**update,'contract_review_revision':4})=='repair_exhausted'


@pytest.mark.parametrize('status',['COMPILE_FAILURE','SIMULATION_FAILURE','SIMULATION_TIMEOUT','COVERAGE_FAILURE'])
def test_seven_repairs_then_three_escalations(status):
    state={'verification_status':status,'max_repair_iterations':7}
    for round_number in range(4):
        state['architecture_escalation']=round_number
        for attempt in range(7):
            state['repair_cycle_iteration']=attempt
            assert route_after_verification(state)=='debugger'
        state['repair_cycle_iteration']=7
        assert route_after_verification(state)==('architecture_escalation' if round_number<3 else 'repair_exhausted')


def test_escalation_critiques_are_contract_only(workspace):
    class Agent:
        def run_structured(self,**kw):
            assert 'RTL_SECRET' not in kw['task'] and 'TB_SECRET' not in kw['task']
            return copy.deepcopy(APPROVED)
    state={**initial(workspace),'architecture_escalation':1,'rtl_result':'RTL_SECRET','verifier_result':'TB_SECRET'}
    for role in ('rtl','tb'):
        update=escalation.make_contract_critique(Agent(),role)(state)
        assert update[f'{role}_contract_critique']['status']=='APPROVED'


def test_debugger_escalation_requests_architect_and_resets_cycle(workspace):
    class Debugger:
        def build_context_from_state(self,state): return {'verification_evidence':{'status':'FAIL'}}
        def run_structured(self,**kw): return copy.deepcopy(REVISE)
    state={**initial(workspace),'architecture_escalation':1,'repair_cycle_iteration':7,
           'rtl_contract_critique':APPROVED,'tb_contract_critique':REVISE}
    update=escalation.make_architecture_diagnosis(Debugger())(state)
    assert update['repair_cycle_iteration']==0
    assert update['architecture_conflict']['source']=='debugger_architecture'
    assert escalation.route_after_architecture_diagnosis(update)=='architect'


def test_approval_cannot_hide_findings():
    with pytest.raises(AgentRuntimeError):
        ContractReviewerAgent.validate_result({**APPROVED,'findings':REVISE['findings']})


def test_full_graph_repair_cycles_stop_after_three_escalations(workspace, monkeypatch):
    counts={'rtl':0,'debugger':0,'escalations':0,'critiques':0,'simulations':0}
    class RTL:
        def run_from_state(self,state):
            counts['rtl']+=1
            return {'rtl_status':'RTL_GENERATED','rtl_files':['top.sv']}
        def run_structured(self,**kw):
            counts['critiques']+=1
            return copy.deepcopy(APPROVED)
    class TB:
        def run_structured(self,**kw):
            counts['critiques']+=1
            return copy.deepcopy(APPROVED)
    class Debugger:
        def run_from_state(self,state):
            counts['debugger']+=1
            return {'debugger_status':'REPAIR_PLAN_READY','repair_iteration':state.get('repair_iteration',0)+1,
                    'rtl_task_type':'FUNCTIONAL_REPAIR'}
        def build_context_from_state(self,state):
            return {'verification_evidence':state['verification_evidence']}
        def run_structured(self,**kw):
            counts['escalations']+=1
            return copy.deepcopy(APPROVED)
    def verify(state):
        counts['simulations']+=1
        return {'verification_status':'SIMULATION_FAILURE','failure_class':'UNKNOWN',
                'verification_evidence':{'status':'FAIL'},'needs_regression':True}
    monkeypatch.setattr(workflow,'verification_tools_node',verify)
    state={**initial(workspace),'rtl_status':'RTL_GENERATED','verifier_status':'VERIFICATION_READY',
           'verification_plan':{'top_module':'top'},'verifier_review_status':'APPROVED',
           'max_repair_iterations':7,'max_architecture_escalations':3}
    state['verifier_review_hashes']=artifacts.review_definition_hashes(state)
    result=workflow.build_workflow_graph(rtl_agent=RTL(),verifier_agent=TB(),debugger_agent=Debugger()).invoke(state,{'recursion_limit':250})
    assert result['status']=='REPAIR_BUDGET_EXHAUSTED',result
    assert counts=={'rtl':28,'debugger':28,'escalations':3,'critiques':6,'simulations':29}
    assert result['repair_iteration']==28 and result['architecture_escalation']==3


def test_review_revision_round_trip_precedes_generation(workspace,monkeypatch):
    reviews=[]
    def architect(state):
        assert state['architecture_conflict']['source']=='contract_reviewer'
        reviews.append('architect_fix')
        return {'architecture_status':'READY','architecture_revision':1,'architecture_conflict':None}
    class Reviewer:
        def review(self,*args,**kwargs):
            reviews.append('review')
            return copy.deepcopy(REVISE if reviews.count('review')==1 else APPROVED)
    monkeypatch.setattr(workflow,'make_architect_node',lambda _:architect)
    # Stop at fan-out preparation: this test isolates review routing and feedback.
    def ready(state):
        assert state['contract_review_status']=='APPROVED'
        raise RuntimeError('review-flow-test-stop')
    monkeypatch.setattr(workflow,'generation_start',ready)
    state=initial(workspace)
    state['contract_review_status']='PENDING'
    result=workflow.build_workflow_graph(contract_review_agent=Reviewer()).invoke(state)
    assert reviews==['review','architect_fix','review']
    assert 'review-flow-test-stop' in result['orchestration_error']


def test_selected_model_applies_to_new_reviewer(monkeypatch):
    monkeypatch.setenv('NPU_AGENT_MODEL','gpt-6-astra')
    assert ContractReviewerAgent().config.model=='gpt-6-astra'


def test_approved_review_resets_its_episode_budget(workspace):
    class Reviewer:
        def review(self,context,**kwargs):
            assert context['previous_contract_review']==REVISE
            assert context['architect_revision_patch']=={'status':'PATCH_READY'}
            return copy.deepcopy(APPROVED)
    state={**initial(workspace),'contract_review_revision':3,
           'contract_review_result':REVISE,'architecture_revision_patch':{'status':'PATCH_READY'}}
    update=contracts.make_contract_review_node(Reviewer())(state)
    assert update['contract_review_revision']==0


def test_static_tb_failure_also_escalates_without_fabricating_simulation(workspace):
    from multigent.orchestration.routes import route_after_verifier
    class Debugger:
        def run_structured(self,**kw):
            assert '"simulation_was_run": false' in kw['task']
            assert 'missing feature comment' in kw['task']
            return copy.deepcopy(APPROVED)
    state={**initial(workspace),'rtl_status':'RTL_GENERATED',
           'verifier_status':'SEMANTIC_VALIDATION_FAILED','verifier_revision':7,
           'architecture_escalation':1,'errors':['missing feature comment'],
           'rtl_contract_critique':APPROVED,'tb_contract_critique':APPROVED}
    assert route_after_verifier(state)=='architecture_escalation'
    update=escalation.make_architecture_diagnosis(Debugger())(state)
    assert escalation.route_after_architecture_diagnosis({**state,**update})=='verification_repair'
    state['architecture_escalation']=3
    assert route_after_verifier(state)=='repair_exhausted'
