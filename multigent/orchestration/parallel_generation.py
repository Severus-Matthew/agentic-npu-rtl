"""LangGraph fan-out with branch-local updates and a single durable join.

Agents are API calls, not shell agents. Each branch exposes only its allowed context
and writes only its owned artifacts. No shared state/checkpoint is written by workers.
"""
import copy
import shutil
from pathlib import Path
from multigent.intake.request_builder import WORKSPACE_ROOT
from multigent.tools.vivado import write_json
from .artifacts import hashes, inputs
from .events import emit

RTL_KEYS = {'run_id','user_request','architecture_dir','architecture_version','repair_iteration',
            'ppa_iteration','rtl_context','rtl_task_type','rtl_feedback','rtl_files','rtl_result',
            'rtl_contract_version','rtl_status'}
TB_KEYS = {'run_id','user_request','architecture_dir','architecture_version','architecture_revision',
           'repair_iteration','verifier_revision','verification_context'}


def generation_start(state):
    architecture = hashes(state.get('architecture_dir',WORKSPACE_ROOT/'architecture'))
    if state.get('contract_review_status') != 'APPROVED' or state.get('contract_review_hashes') != architecture:
        raise ValueError('Generation requires approval of the exact current architecture')
    return {'rtl_branch_update': {}, 'tb_branch_update': {},
            'history': [{'stage':'generation_start','status':'PARALLEL_GENERATION'}]}


def branch(name, node):
    key, allowed, owned = (('rtl_branch_update', RTL_KEYS, ('rtl',)) if name == 'rtl_generator'
                           else ('tb_branch_update', TB_KEYS, ('tests','reference')))
    def run(state):
        emit(WORKSPACE_ROOT, name, 'started')
        snapshot = WORKSPACE_ROOT/'attempts'/f"{len(state.get('history',[])):04d}-{name}"
        snapshot.mkdir(parents=True,exist_ok=True)
        architecture = Path(state.get('architecture_dir',WORKSPACE_ROOT/'architecture'))
        before = hashes(architecture)
        for folder in (*owned, 'architecture'):
            source = architecture if folder == 'architecture' else WORKSPACE_ROOT/folder
            if source.exists():
                shutil.copytree(source,snapshot/folder,dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('__pycache__'))
        try:
            if state.get('contract_review_hashes') != before or state.get('contract_review_status') != 'APPROVED':
                raise ValueError('Parallel generation requires reviewed contracts')
            update = node(copy.deepcopy({k:v for k,v in state.items() if k in allowed}))
            if before != hashes(architecture):
                raise ValueError(f'{name} changed architecture')
        except Exception as exc:
            update = {'orchestration_error':f'{name}: {type(exc).__name__}: {exc}',
                      'errors':[str(exc)], 'history':[{'stage':name,'status':'ERROR','error':str(exc)}]}
        write_json(snapshot/'result.json',update)
        emit(WORKSPACE_ROOT,name,'failed' if update.get('orchestration_error') else 'finished',
             history=update.get('history',[]))
        return {key:update}
    return run


def generation_join(state):
    result = {'history':[], 'errors':[]}
    conflicts = []
    for key in ('rtl_branch_update','tb_branch_update'):
        update = state[key]
        for field,value in update.items():
            if field in {'history','errors'}:
                result[field] += value
            elif field == 'architecture_conflict' and value:
                conflicts.append(value)
            elif field == 'orchestration_error':
                result[field] = result.get(field,'') + value + '\n'
            else:
                result[field] = value
    if result.get('orchestration_error'):
        result['status'] = 'FAILED'
    if conflicts:
        result['architecture_conflict'] = {'source':'independent_generators','findings':conflicts}
    result['frozen_hashes'] = inputs({**state,**result})
    result['history'].append({'stage':'generation_join','status':'JOINED'})
    return result


def route_after_generation(state):
    if state.get('architecture_conflict'):
        from .routes import _architecture_revision_available
        return 'architect' if _architecture_revision_available(state) else 'repair_exhausted'
    if state.get('rtl_status') != 'RTL_GENERATED':
        return 'failed'
    if state.get('verifier_status') == 'SEMANTIC_VALIDATION_FAILED':
        from .routes import _verifier_repair_available, _preflight_exhaustion_route
        return 'verification_repair' if _verifier_repair_available(state) else _preflight_exhaustion_route(state)
    return 'verifier_review'
