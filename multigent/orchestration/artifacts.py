"""Artifact provenance, immutable attempt snapshots and durable graph reports."""
import json
import shutil
from pathlib import Path
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context
from multigent.tools.vivado import digest, write_json


def hashes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.sv','.py','.yaml','.json'}}


def inputs(state):
    return {'architecture':hashes(state.get('architecture_dir',WORKSPACE_ROOT/'architecture')),
            'rtl':hashes(WORKSPACE_ROOT/'rtl'), 'tests':hashes(WORKSPACE_ROOT/'tests'),
            'reference':hashes(WORKSPACE_ROOT/'reference')}


def guarded(name, node):
    def run(state):
        before = inputs(state)
        sequence = len(state.get('history',[]))
        snapshot = WORKSPACE_ROOT/'attempts'/f'{sequence:04d}-{name}'
        snapshot.mkdir(parents=True, exist_ok=True)
        for owned in ('rtl','reference','tests','diagnostics'):
            if (WORKSPACE_ROOT/owned).exists():
                shutil.copytree(WORKSPACE_ROOT/owned, snapshot/owned, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns('__pycache__'))
        architecture = Path(state.get('architecture_dir',WORKSPACE_ROOT/'architecture'))
        if architecture.exists():
            shutil.copytree(architecture,snapshot/'architecture',dirs_exist_ok=True)
        write_json(snapshot/'inputs.json',before)
        try:
            if name in {'rtl_generator','verification_tools','synthesis','ppa_optimizer'}:
                frozen = state.get('frozen_hashes')
                if frozen and before['architecture'] != frozen['architecture']:
                    raise ValueError('Frozen architecture changed outside Architect')
                if name != 'rtl_generator' and state.get('verifier_status') == 'VERIFICATION_READY' and frozen:
                    for owned in ('tests','reference'):
                        if before[owned] != frozen[owned]:
                            raise ValueError(f'Frozen {owned} changed outside independent Verifier')
            if name == 'synthesis' and before != state.get('verified_hashes'):
                raise ValueError('Candidate artifacts changed since deterministic verification')
            update = node(state)
            after = inputs({**state,**update})
            permitted = {'architect':{'architecture'},'rtl_generator':{'rtl'},'verifier':{'tests','reference'}}.get(name,set())
            for owned in before:
                if owned not in permitted and before[owned] != after[owned]:
                    raise ValueError(f'{name} changed protected {owned} artifacts')
            if name in {'architect','verifier'}:
                update['frozen_hashes'] = after
            if name == 'verification_tools' and update.get('verification_status') == 'PASS':
                update['verified_hashes'] = after
            update['history'] = update.get('history',[]) or [{'stage':name,'status':update.get('status',update.get('ppa_status','DONE'))}]
        except Exception as exc:
            update = {'orchestration_error':f'{name}: {type(exc).__name__}: {exc}',
                      'status':'FAILED', 'errors':[f'{type(exc).__name__}: {exc}'],
                      'history':[{'stage':name,'status':'ERROR','error':str(exc)}]}
        combined = {**state,**update,'history':state.get('history',[])+update.get('history',[]),
                    'errors':state.get('errors',[])+update.get('errors',[])}
        write_json(WORKSPACE_ROOT/'state'/'latest.json',combined)
        write_json(snapshot/'result.json',update)
        return update
    return run


def verification_repair_node(state):
    # Do not transmit Debugger prose/logs/source-derived facts to independent Verifier.
    context = build_verification_context(user_request=state['user_request'],
                                         architecture_dir=Path(state['architecture_dir']))
    context['verification_infrastructure_review'] = {
        'category':'TESTBENCH_ERROR',
        'instruction':'Independently revalidate your own Python imports, timing phases, handshake sampling, signed conversions, oracle arithmetic and task lifetimes against the frozen contract. Fix test infrastructure only; preserve all coverage and assertions. Do not adapt expectations to implementation behavior.',
        'previous_own_artifacts':{name:{p.name:p.read_text() for p in sorted((WORKSPACE_ROOT/name).glob('*.py'))}
                                 for name in ('reference','tests')}}
    return {'verification_context':context, 'verifier_revision':state.get('verifier_revision',0)+1,
            'verifier_status':'PENDING','verification_status':'PENDING','needs_regression':True,
            'history':[{'stage':'verification_repair','status':'INDEPENDENT_REVIEW'}]}


def final_report_node(state):
    root = WORKSPACE_ROOT/'reports'
    root.mkdir(parents=True,exist_ok=True)
    report = dict(state)
    report['workspace'] = str(WORKSPACE_ROOT)
    report['artifact_hashes'] = inputs(state)
    report['limitations'] = [
        'Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.',
        'Vivado adapter requires validation against the installed Vivado version and FPGA target.',
        'Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.']
    best = state.get('best_candidate')
    if best:
        report['selected_rtl'] = str(Path(best['synthesis_result']['bundle'])/'rtl')
    elif state.get('verification_status') == 'PASS' and state.get('verified_hashes') == report['artifact_hashes'] and not state.get('needs_regression'):
        report['selected_rtl'] = str(WORKSPACE_ROOT/'rtl')
    else:
        report['selected_rtl'] = None
    write_json(root/'final.json',report)
    lines = [f"# Hardware generation: {state.get('status','UNKNOWN')}", '',
             f"Request: {state.get('user_request','')}", '',
             f"Functional verification: {state.get('verification_status','NOT_RUN')}",
             f"Vivado: {(state.get('synthesis_result') or {}).get('status','NOT_RUN')}",
             f"RTL repair iterations: {state.get('repair_iteration',0)}",
             f"Verifier revisions: {state.get('verifier_revision',0)}",
             f"PPA iterations: {state.get('ppa_iteration',0)}", '',
             f"Selected RTL: {report['selected_rtl']}", '', '## Errors']
    lines.extend(state.get('errors',[]) or ['None'])
    lines += ['', '## Limitations', *report['limitations']]
    (root/'final.md').write_text('\n'.join(lines)+'\n')
    return {'final_report':str(root/'final.json')}


def diagnostic_node(state):
    from multigent.tools.diagnostic import collect_diagnostics
    count=state.get('diagnostic_iteration',0)+1
    result=collect_diagnostics(WORKSPACE_ROOT,state['verification_plan'],
        WORKSPACE_ROOT/'diagnostics'/f"probe-{count}-attempt{len(state.get('history',[]))}")
    evidence=dict(state['verification_evidence'])
    evidence['additional_diagnostics']=result
    return {'verification_evidence':evidence,'diagnostic_iteration':count,
            'history':[{'stage':'diagnostic_probe','status':'EVIDENCE_COLLECTED'}]}
