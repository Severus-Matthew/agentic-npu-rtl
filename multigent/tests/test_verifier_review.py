from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from multigent.agents.base import AgentRuntimeError, SCHEMA_ROOT
from multigent.agents.verifier_review import VerifierReviewAgent
from multigent.verifier_tool.predefined_assertion.review import assertion_definition_view
from multigent.orchestration import artifacts, verifier_review_node
from multigent.orchestration.routes import route_after_verifier_review, route_start
from multigent.tests.test_verifier import generic_fir_context, verification_ready_result


def approved():
    return {'status': 'APPROVED', 'summary': 'Definitions reviewed, not simulation PASS',
            'findings': []}


def repair():
    return {'status': 'VERIFIER_REPAIR_REQUIRED', 'summary': 'Missing output count check',
            'findings': [{'category': 'MISSING_ASSERTION', 'requirement': 'No extra output',
                          'evidence': 'Sink returns after expected count without a continuing checker',
                          'recommended_change': 'Keep independent output accounting active'}]}


def test_review_schema_is_valid_and_all_outcomes_are_schema_valid():
    schema = json.loads((SCHEMA_ROOT / 'verifier_review.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    for result in (approved(), repair()):
        Draft202012Validator(schema).validate(result)


def test_reviewer_schema_has_no_architect_route():
    schema = json.loads((SCHEMA_ROOT / 'verifier_review.schema.json').read_text())
    result = approved() | {
        'status': 'ARCHITECTURE_CONFLICT',
        'architecture_conflict': {'issue': 'reviewer must not decide this'},
    }
    with pytest.raises(Exception):
        Draft202012Validator(schema).validate(result)


def test_assertion_view_retains_vacuous_guard_snapshot_and_stability_definition():
    source = '''import random
async def cycle(dut):
    pre = {"valid": int(dut.y_valid.value)}
    return pre
async def sink(dut, expected):
    held = None
    previous = None
    a = [[1234567, 7654321]]
    rng = random.Random(7)
    case = rng.randint(0, 500)
    while True:
        dut.y_ready.value = 0
        pre = await cycle(dut)
        payload = int(dut.y_payload.value)
        last = int(dut.y_last.value)
        if previous:
            assert pre["valid"] and (payload, last) == held
        held = (payload, last)
        previous = pre
        assert pre["completion"] == 1 if "completion" in pre else True
        await FallingEdge(dut.clk)
        sample_operation("op", {"row_major": True}, "directed", "STIMULUS_SECRET")
'''
    view = assertion_definition_view(source, filename='tests/test_example.py')
    rendered = json.dumps(view)
    assert 'else True' in rendered
    assert 'pre' in rendered and 'valid' in rendered
    assert '(payload, last)' in rendered
    assert 'FallingEdge' in rendered
    assert 'STIMULUS_SECRET' not in rendered
    assert '1234567' not in rendered
    assert 'randint' not in rendered
    assert 'y_ready' not in rendered
    assert view['functions'][0]['variable_origins'][0]['target'] == 'pre'


def test_review_envelope_excludes_prior_evidence_but_includes_candidate_source():
    context = generic_fir_context()
    context['verification_infrastructure_review'] = {'first_failure_excerpt': 'RTL_EXECUTION_SECRET'}
    context['coverage_closure_review'] = {'bin_hits': {'x': 12}, 'stimulus_summary': 'STIMULUS_SECRET'}
    view = VerifierReviewAgent.build_context(context, verification_ready_result())
    rendered = json.dumps(view)
    assert 'RTL_EXECUTION_SECRET' not in rendered and 'STIMULUS_SECRET' not in rendered
    assert 'actual_bin_hits' not in rendered
    assert view['provenance']['includes_stimulus'] is True
    assert view['provenance']['includes_simulation_evidence'] is False
    assert '_contract_record_checked_stimulus(' in rendered
    assert 'event coverpoints observe signals' in rendered


def test_assertion_view_preserves_accepted_collection_and_counter_update_guards():
    source = '''
async def check_outputs(dut, expected_count):
    received = []
    count = 0
    while True:
        await FallingEdge(dut.clk)
        valid = int(dut.y_valid.value)
        ready = int(dut.y_ready.value)
        payload = int(dut.y_payload.value)
        if valid and ready:
            received.append(payload)
            count += 1
        assert len(received) == count
        assert count <= expected_count
'''
    function = assertion_definition_view(source, filename='tests/test_counts.py')['functions'][0]
    update = function['state_updates'][0]
    assert update['target'] == 'received' and update['operation'] == 'append'
    assert update['arguments'] == ['payload']
    assert update['guards'] == ['while True', 'valid and ready']
    counter = next(item for item in function['variable_origins'] if item['operator'] == 'Add')
    assert counter['target'] == 'count' and counter['expression'] == '1'
    assert counter['guards'] == update['guards']
    assert any(item['target'] == 'payload' and 'dut.y_payload.value' in item['expression']
               for item in function['variable_origins'])


def test_assertion_view_preserves_checker_helper_mutations_and_empty_initial_state():
    source = '''
class Checker:
    def __init__(observer, dut):
        observer.dut = dut
        observer.av, observer.bv = [], []
    def accept_a(observer, value, handshake):
        if handshake:
            observer.av.append(value)
    def check(observer):
        assert len(observer.av) == 4
'''
    functions = assertion_definition_view(source, filename='tests/test_helper.py')['functions']
    helper = next(item for item in functions if item['function'] == 'accept_a')
    assert helper['class'] == 'Checker'
    assert helper['state_updates'][0]['guards'] == ['handshake']
    assert helper['state_updates'][0]['target'] == 'observer.av'
    constructor = next(item for item in functions if item['function'] == '__init__')
    assert any(item['expression'] == '([], [])' for item in constructor['variable_origins'])
    assert any(item['target'] == 'observer.dut' and item['expression'] == 'dut'
               for item in constructor['variable_origins'])  # Keep observation provenance, not a signal drive.


def test_assertion_view_preserves_returned_observations_and_destructive_state_updates():
    source = '''
async def accepted_values(dut):
    received = []
    for unused in range(SECRET_SCHEDULE):
        payload = int(dut.y_payload.value)
        if int(dut.y_valid.value) and int(dut.y_ready.value):
            received.append(payload)
    return received
def trim(received):
    if len(received) > 2:
        received[0] = received[-1]
        received.pop()
        del received[0]
    assert len(received) <= 2
'''
    view = assertion_definition_view(source, filename='tests/test_trim.py')
    assert 'SECRET_SCHEDULE' not in json.dumps(view)
    helper, trim = view['functions']
    assert helper['state_updates'][0]['operation'] == 'append'
    assert {item['operation'] for item in trim['state_updates']} == {'pop', 'delete'}
    assignment = next(item for item in trim['variable_origins'] if item['target'] == 'received[0]')
    assert assignment['guards'] == ['len(received) > 2']


def test_state_update_projection_does_not_reintroduce_rng_payloads_or_driver_writes():
    source = '''
async def sink(dut):
    received = []
    unrelated_jobs = []
    unrelated_jobs.append([1234567, 7654321])
    received.extend([1111111, 2222222])
    received.append(rng.randint(0, 9876543))
    received.append(make_random_matrix(rng.randrange(5555555)))
    dut.y_ready.value, other = 1, 9999999
    dut.y_payload.value.append(8888888)
    assert len(received) >= 0
'''
    function = assertion_definition_view(source, filename='tests/test_redaction.py')['functions'][0]
    rendered = json.dumps(function)
    for secret in ('1234567', '7654321', '1111111', '2222222', '9876543', '5555555', '9999999', '8888888'):
        assert secret not in rendered
    assert 'randint' not in rendered and 'randrange' not in rendered
    assert 'unrelated_jobs' not in rendered
    assert 'dut.y_ready' not in rendered
    assert function['state_updates'][0]['operation'] == 'extend'
    assert function['state_updates'][0]['arguments'] == ['<concrete payload/scenario collection excluded from review>']


def test_review_envelope_contains_checker_state_updates_without_execution_evidence():
    candidate = verification_ready_result()
    candidate['test_files'][0]['content'] += '''
def count_checked_samples(received, payload, accepted):
    if accepted:
        received.append(payload)
    assert len(received) > 0
'''
    envelope = VerifierReviewAgent.build_context(generic_fir_context(), candidate)
    function = next(item for item in envelope['assertion_views'][0]['functions']
                    if item['function'] == 'count_checked_samples')
    assert function['state_updates'][0]['guards'] == ['accepted']
    assert envelope['provenance']['includes_stimulus'] is True
    assert envelope['provenance']['includes_simulation_evidence'] is False


def test_state_update_rng_guards_remain_redacted_without_affecting_handshake_guards():
    source = '''
def check(received, payload, valid, ready):
    rng = random.Random(1234567)
    if rng.randrange(7654321):
        received.append(payload)
    if valid and ready:
        received.append(payload)
    assert len(received) > 0
'''
    function = assertion_definition_view(source, filename='tests/test_rng_guard.py')['functions'][0]
    rendered = json.dumps(function)
    assert '1234567' not in rendered and '7654321' not in rendered
    assert 'randrange' not in rendered and 'random.Random' not in rendered
    assert function['state_updates'][0]['guards'] == ['<stimulus or task setup excluded from review>']
    assert function['state_updates'][1]['guards'] == ['valid and ready']


def test_review_prompt_audits_static_stimulus_intent_without_claiming_hits():
    prompt = VerifierReviewAgent().load_instructions()
    assert 'narrow stimulus-intent audit' in prompt
    assert 'inspect the actual supplied TB construction' in prompt
    assert 'actual hit counts' in prompt
    assert 'including within' in prompt and 'an existing taxonomy class' in prompt
    assert 'always-True fallbacks' in prompt
    assert 'NOT verification PASS' in prompt


@pytest.mark.parametrize('outcome,route', [('APPROVED', 'verification_tools'),
    ('VERIFIER_REPAIR_REQUIRED', 'verification_repair')])
def test_review_routes_use_existing_budgets(outcome, route):
    state = {'verifier_review_status': outcome, 'verifier_revision': 0, 'max_verifier_revisions': 2,
             'rtl_status': 'RTL_GENERATED'}
    assert route_after_verifier_review(state) == route
    if outcome != 'APPROVED':
        state.update(verifier_revision=2)
        assert route_after_verifier_review(state) == 'failed'


def test_saved_unreviewed_tb_resumes_at_review_not_generation_or_simulation():
    state = {'architecture_status': 'READY', 'rtl_status': 'RTL_GENERATED',
             'verifier_status': 'VERIFICATION_READY', 'verification_plan': {'top_module': 'top'}}
    assert route_start(state) == 'verifier_review'
    state['verifier_review_status'] = 'APPROVED'
    assert route_start(state) == 'verification_tools'


def test_definition_repair_feedback_excludes_execution_and_uses_counted_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, 'build_verification_context', lambda **kw: generic_fir_context())
    update = artifacts.verification_repair_node({
        'user_request': 'fir', 'architecture_dir': str(tmp_path),
        'verifier_review_status': 'VERIFIER_REPAIR_REQUIRED', 'verifier_review_result': repair(),
        'verifier_result': verification_ready_result(), 'verifier_revision': 1,
        'verification_evidence': {'stdout': 'RTL_EXECUTION_SECRET'},
    })
    feedback = update['verification_context']['assertion_definition_review']
    assert feedback['findings'] == repair()['findings']
    assert feedback['previous_verifier_output']['test_files']
    assert 'existing valid stimulus' in feedback['instruction']
    assert 'RTL_EXECUTION_SECRET' not in json.dumps(update)
    assert update['verifier_revision'] == 2 and update['verifier_review_status'] == 'PENDING'


def test_approval_does_not_allow_findings_or_stale_definition_hashes(tmp_path, monkeypatch):
    result = approved()
    result['findings'] = repair()['findings']
    with pytest.raises(AgentRuntimeError, match='no findings'):
        VerifierReviewAgent.validate_result(result, generic_fir_context())
    monkeypatch.setattr(artifacts, 'WORKSPACE_ROOT', tmp_path)
    called = []
    state = {'history': [], 'verifier_review_status': 'APPROVED',
             'verifier_review_hashes': {'architecture': {}, 'tests': {}, 'reference': {}}}
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_modified.py').write_text('assert False\n')
    update = artifacts.guarded('verification_tools', lambda state: called.append(True))(state)
    assert 'current definitions' in update['orchestration_error'] and not called


def test_changing_coverage_definition_invalidates_review_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, 'WORKSPACE_ROOT', tmp_path)
    state = {'history': [], 'verifier_review_status': 'APPROVED', 'verifier_result': verification_ready_result()}
    state['verifier_review_hashes'] = artifacts.review_definition_hashes(state)
    state['verifier_result']['operation_coverage'][0]['coverpoints'][0]['bins'][0]['name'] = 'changed_after_review'
    called = []
    update = artifacts.guarded('verification_tools', lambda state: called.append(True))(state)
    assert 'current definitions' in update['orchestration_error'] and not called


def test_review_node_is_read_only_and_saves_non_pass_report(tmp_path, monkeypatch):
    monkeypatch.setattr(artifacts, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(verifier_review_node, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(verifier_review_node, 'build_verification_context', lambda **kw: generic_fir_context())
    candidate = verification_ready_result()
    for field, owner in [('test_files', 'tests'), ('reference_files', 'reference')]:
        (tmp_path / owner).mkdir()
        for item in candidate[field]:
            content = item['content'] if item['content'].endswith('\n') else item['content'] + '\n'
            (tmp_path / owner / Path(item['path']).name).write_text(content)
    class Reviewer:
        def review(self, context, output, **kwargs):
            assert output == candidate
            assert 'verification_evidence' not in context
            return approved()
    state = {'user_request': 'fir', 'verifier_status': 'VERIFICATION_READY', 'verifier_result': candidate,
             'history': [], 'architecture_dir': str(tmp_path / 'architecture')}
    before = artifacts.inputs(state)
    update = artifacts.guarded('verifier_review', verifier_review_node.make_verifier_review_node(Reviewer()))(state)
    assert 'orchestration_error' not in update
    assert artifacts.inputs(state) == before
    assert update['verification_status'] == 'PENDING'
    report = json.loads(next((tmp_path / 'verification').glob('verifier-review-*.json')).read_text())
    assert report['stimulus_reviewed'] is True and report['simulation_pass'] is False


@pytest.mark.parametrize('approve_second', [True, False])
def test_graph_reviews_repairs_and_reviews_again_with_existing_budget(tmp_path, monkeypatch, approve_second):
    import multigent.orchestration.graph as graph_module
    monkeypatch.setattr(artifacts, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(verifier_review_node, 'WORKSPACE_ROOT', tmp_path)
    monkeypatch.setattr(verifier_review_node, 'build_verification_context', lambda **kw: generic_fir_context())
    monkeypatch.setattr(artifacts, 'build_verification_context', lambda **kw: generic_fir_context())
    calls = []
    class Verifier:
        def run_from_state(self, state):
            calls.append('generate')
            if calls.count('generate') == 2:
                assert state['verification_context']['assertion_definition_review']['findings'] == repair()['findings']
            candidate = verification_ready_result()
            for field, owner in [('test_files', 'tests'), ('reference_files', 'reference')]:
                (tmp_path / owner).mkdir(exist_ok=True)
                for item in candidate[field]:
                    content = item['content'] if item['content'].endswith('\n') else item['content'] + '\n'
                    (tmp_path / owner / Path(item['path']).name).write_text(content)
            return {'verifier_status': 'VERIFICATION_READY', 'verifier_result': candidate,
                    'verification_plan': candidate['verification_plan'], 'verification_context': generic_fir_context(),
                    'architecture_conflict': None}
    class Reviewer:
        def review(self, context, candidate, **kwargs):
            calls.append('review')
            return approved() if approve_second and calls.count('review') == 2 else repair()
    def simulate(state):
        calls.append('simulate')
        assert state['verifier_review_status'] == 'APPROVED'
        return {'verification_status': 'PASS', 'status': 'VERIFIED_RTL', 'needs_regression': False}
    monkeypatch.setattr(graph_module, 'verification_tools_node', simulate)
    graph = graph_module.build_workflow_graph(verifier_agent=Verifier(), verifier_review_agent=Reviewer())
    result = graph.invoke({'user_request': 'fir', 'run_id': 'offline',
                           'architecture_dir': str(tmp_path / 'architecture'), 'architecture_status': 'READY',
                           'rtl_status': 'RTL_GENERATED', 'verification_only': True,
                           'max_verifier_revisions': 1, 'verifier_revision': 0,
                           'history': [], 'errors': []})
    assert calls[:4] == ['generate', 'review', 'generate', 'review']
    assert result['verifier_revision'] == 1
    assert any(event.get('status') == 'ASSERTION_DEFINITION_CORRECTION' for event in result['history'])
    if approve_second:
        assert calls == ['generate', 'review', 'generate', 'review', 'simulate']
        assert result['status'] == 'VERIFIED_RTL'
    else:
        assert 'simulate' not in calls and result['status'] == 'FAILED'
