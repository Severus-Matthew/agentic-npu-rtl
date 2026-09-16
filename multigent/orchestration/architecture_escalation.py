"""Bounded architecture diagnosis after a complete repair cycle is exhausted."""
import json
from pathlib import Path
from multigent.agents.base import SCHEMA_ROOT
from multigent.agents.contract_reviewer import ContractReviewerAgent
from multigent.agents.debugger import bounded_evidence
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context
from multigent.tools.vivado import write_json


def escalation_start(state):
    count = state.get('architecture_escalation',0) + 1
    if count > state.get('max_architecture_escalations',3):
        raise ValueError('Architecture escalation budget exhausted')
    return {'architecture_escalation': count,
            'history':[{'stage':'architecture_escalation','status':'STARTED','round':count}]}


def make_contract_critique(agent, role):
    def critique(state):
        context = build_verification_context(user_request=state['user_request'],
                         architecture_dir=Path(state['architecture_dir']))
        # Neither generator receives its counterpart's artifacts or diagnosis.
        envelope = {k:context[k] for k in ('user_request','frozen_architecture')}
        result = agent.run_structured(
            task=('Independently inspect this contract from your role perspective. Do not generate source. '
                  'Identify only contradictions or missing executable rules, with exact contract paths. '
                  'APPROVED means no contract defect found, not that hardware passed.\n' + json.dumps(envelope)),
            schema_path=SCHEMA_ROOT/'contract_review.schema.json',
            log_name=f"{role}-contract-critique-{state['run_id']}-e{state['architecture_escalation']}.json")
        ContractReviewerAgent.validate_result(result)
        return {f'{role}_contract_critique':result}
    return critique


def make_architecture_diagnosis(agent):
    def diagnose(state):
        preflight = (state.get('verifier_status') == 'SEMANTIC_VALIDATION_FAILED'
                     or state.get('verifier_review_status') == 'VERIFIER_REPAIR_REQUIRED')
        if preflight:
            contract = build_verification_context(user_request=state['user_request'],
                            architecture_dir=Path(state['architecture_dir']))
            context = {'user_request':state['user_request'],
                       'frozen_architecture':contract['frozen_architecture'],
                       'preflight_evidence':{'validator_errors':state.get('errors',[])[-5:],
                                            'tb_review':state.get('verifier_review_result'),
                                            'simulation_was_run':False},
                       'current_rtl':{p.relative_to(WORKSPACE_ROOT/'rtl').as_posix():p.read_text()
                                      for p in sorted((WORKSPACE_ROOT/'rtl').rglob('*.sv'))},
                       'rejected_tb_draft':state.get('verifier_draft') or state.get('verifier_result')}
        else:
            context = agent.build_context_from_state(state)
        context['independent_contract_critiques'] = {
            'rtl': state['rtl_contract_critique'], 'testbench': state['tb_contract_critique']}
        result = agent.run_structured(
            task=('Architecture escalation after repeated failed repairs. Analyze the contracts, '
                  'deterministic failures, both implementations and independent contract critiques. '
                  'Return REVISION_REQUIRED only for evidenced contract defects, with minimal changes '
                  'and exact paths. Never weaken acceptance to match the RTL. Return APPROVED if the '
                  'contract is sound; the ordinary debugger will then re-localize the implementation defect.\n'
                  + json.dumps(bounded_evidence(context))),
            schema_path=SCHEMA_ROOT/'contract_review.schema.json',
            log_name=f"debugger-contract-{state['run_id']}-e{state['architecture_escalation']}.json")
        ContractReviewerAgent.validate_result(result)
        write_json(WORKSPACE_ROOT/'diagnostics'/f"architecture-escalation-{state['architecture_escalation']}.json",result)
        update = {'escalation_result':result, 'repair_cycle_iteration':0,
                  'contract_review_revision':0, 'diagnostic_iteration':0,
                  'history':[{'stage':'debugger_architecture','status':result['status'],
                              'round':state['architecture_escalation'],'findings':result['findings']}]}
        if result['status'] == 'REVISION_REQUIRED':
            update['architecture_conflict'] = {'source':'debugger_architecture',**result}
        return update
    return diagnose


def route_after_architecture_diagnosis(state):
    if state['escalation_result']['status'] == 'REVISION_REQUIRED':
        return 'architect'
    if (state.get('verifier_status') == 'SEMANTIC_VALIDATION_FAILED'
            or state.get('verifier_review_status') == 'VERIFIER_REPAIR_REQUIRED'):
        return 'verification_repair'
    return 'debugger'
