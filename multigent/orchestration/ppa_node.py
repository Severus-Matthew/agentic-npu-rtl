"""Vivado/optimizer nodes and deterministic selection, all routed by LangGraph."""
import json
from pathlib import Path
from multigent.agents.ppa_optimizer import PPAOptimizerAgent
from multigent.intake.request_builder import WORKSPACE_ROOT, load_frozen_architecture
from multigent.tools.vivado import prepare_bundle, run_bundle, write_json, import_result, digest


def synthesis_node(state):
    if state.get('verification_status') != 'PASS' or state.get('needs_regression'):
        raise ValueError('Vivado requires fresh full functional regression')
    if state.get('external_vivado_bundle') and state.get('ppa_iteration',0)==0:
        result = import_result(Path(state['external_vivado_bundle']), WORKSPACE_ROOT/'rtl', state.get('vivado_config',{}))
        return {'synthesis_result':result,'status':'VIVADO_'+result['status'],
                'history':[{'stage':'vivado','status':result['status'],'external':True}]}
    tag = f"av{state.get('architecture_version',0)}-r{state.get('repair_iteration',0)}-p{state.get('ppa_iteration',0)}-v{state.get('verifier_revision',0)}"
    bundle = WORKSPACE_ROOT/'synthesis'/(tag+f"-attempt{len(state.get('history',[]))}")
    prepare_bundle(WORKSPACE_ROOT/'rtl', bundle, state['verification_plan']['top_module'],
                   state.get('vivado_config', {}), state['verification_evidence'])
    result = run_bundle(bundle, state.get('vivado_executable','vivado'), state.get('vivado_timeout',3600))
    return {'synthesis_result': result, 'status': 'VIVADO_'+result['status'],
            'history': [{'stage':'vivado', 'status':result['status'], 'bundle':str(bundle)}]}


def route_after_synthesis(state):
    return 'ppa_optimizer' if (state.get('synthesis_result') or {}).get('status') in {'PASS','TIMING_FAILED'} else 'final_report'


def make_ppa_node(agent=None):
    runtime = agent or PPAOptimizerAgent()
    def node(state):
        current = state['synthesis_result']
        if current['status'] not in {'PASS','TIMING_FAILED'} or state['verification_status'] != 'PASS':
            raise ValueError('Optimizer gate requires verified deterministic Vivado evidence')
        best = state.get('best_candidate')
        objective = state.get('ppa_objective','lut')
        candidate = {'synthesis_result': current, 'verification_evidence':state['verification_evidence'],
                     'objective':objective, 'architecture_version':state.get('architecture_version')}
        if current['status'] == 'PASS':
            if best and best['architecture_version'] == candidate['architecture_version'] and current['metrics'][objective] >= best['synthesis_result']['metrics'][objective]:
                return {'ppa_status':'NO_IMPROVEMENT', 'status':'SUCCESS', 'best_candidate':best}
            best = candidate
        if state.get('ppa_iteration',0) >= state.get('max_ppa_iterations',0):
            return {'ppa_status':'BUDGET_EXHAUSTED', 'best_candidate':best,
                    'status':'SUCCESS' if best else 'PPA_TARGET_UNMET'}
        excerpts = {}
        for name in ('critical_paths.rpt','utilization.rpt','timing_summary.rpt','power.rpt'):
            expected_hash = current.get('reports',{}).get(name)
            if expected_hash:
                report_path = Path(current['bundle'])/name
                if digest(report_path) != expected_hash:
                    raise ValueError('Vivado report changed before optimizer handoff')
                raw = report_path.read_text()
                excerpts[name] = {'text':raw[:24000],'truncated':len(raw)>24000}
        context = {'report_excerpts':excerpts, 'frozen_architecture' :load_frozen_architecture(Path(state['architecture_dir'])),
                   'synthesis_result':current, 'objective':objective,
                   'prior_plan':state.get('optimization_plan')}
        plan = runtime.run(context, run_id=f"{state['run_id']}-p{state.get('ppa_iteration',0)}")
        # Validate injected agents too, before authorizing RTL mutation.
        PPAOptimizerAgent.validate(plan, context)
        write_json(WORKSPACE_ROOT/'optimization'/f"plan-p{state.get('ppa_iteration',0)}.json",plan)
        if plan['action'] == 'STOP':
            return {'ppa_status':'STOP', 'optimization_plan':plan, 'best_candidate':best,
                    'status':'SUCCESS' if best else 'PPA_TARGET_UNMET'}
        return {'ppa_status':'OPTIMIZE', 'optimization_plan':plan, 'best_candidate':best,
                'ppa_iteration':state.get('ppa_iteration',0)+1,
                'rtl_task_type':'PPA_OPTIMIZATION',
                'rtl_feedback':{'source':'ppa_optimizer','optimization_plan':plan,
                                'synthesis_result':current,'frozen_verifier':True},
                'verification_status':'PENDING','needs_regression':True,
                'history':[{'stage':'ppa_optimizer','status':'OPTIMIZE'}]}
    return node


def route_after_ppa(state):
    return 'rtl_generator' if state.get('ppa_status') == 'OPTIMIZE' else 'final_report'
