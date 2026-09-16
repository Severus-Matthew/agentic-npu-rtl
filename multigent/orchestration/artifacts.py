"""Artifact provenance, immutable attempt snapshots and durable graph reports."""
import ast
import hashlib
import json
import re
import shutil
from pathlib import Path
from multigent.intake.request_builder import WORKSPACE_ROOT, build_verification_context
from multigent.verifier_tool.coverage.stimulus import (
    HISTORY_FILE,
    rebuild_stimulus_history,
    verifier_stimulus_history_view,
)
from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.operation.plan import (
    merge_coverage_plans,
    operation_plan_for_tests,
)
from multigent.tools.vivado import digest, write_json
from .events import emit


def hashes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.sv','.py','.yaml','.json'}}


def inputs(state):
    return {'architecture':hashes(state.get('architecture_dir',WORKSPACE_ROOT/'architecture')),
            'rtl':hashes(WORKSPACE_ROOT/'rtl'), 'tests':hashes(WORKSPACE_ROOT/'tests'),
            'reference':hashes(WORKSPACE_ROOT/'reference')}


def review_definition_hashes(state, artifact_hashes=None):
    """Bind approval to the actual check/coverage definitions, not just TB files."""
    artifacts = artifact_hashes if artifact_hashes is not None else inputs(state)
    result = {name: artifacts[name] for name in ('architecture', 'tests', 'reference')}
    coverage = (state.get('verifier_result') or {}).get('operation_coverage', [])
    result['operation_coverage'] = hashlib.sha256(json.dumps(coverage, sort_keys=True).encode()).hexdigest()
    code_root = Path(__file__).resolve().parents[1]
    verifier_tool = code_root / 'verifier_tool'
    sources = [
        *sorted(verifier_tool.rglob('*.yaml')),
        verifier_tool / 'coverage/runtime.py',
        verifier_tool / 'coverage/cocotb_model.py',
        verifier_tool / 'coverage/operation/plan.py',
        verifier_tool / 'coverage/operation/sampling.py',
        verifier_tool / 'predefined_assertion/protocol/generator.py',
        verifier_tool / 'predefined_assertion/operation/generator.py',
        verifier_tool / 'predefined_assertion/instrumentation.py',
    ]
    result['taxonomy_and_monitor'] = {path.relative_to(code_root).as_posix(): digest(path) for path in sources}
    return result


def guarded(name, node):
    def run(state):
        emit(WORKSPACE_ROOT, name, 'started')
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
            if name in {'rtl_generator', 'verifier', 'verification_tools'}:
                if (state.get('contract_review_status') != 'APPROVED'
                        or state.get('contract_review_hashes') != before['architecture']):
                    raise ValueError('Current architecture requires Contract Reviewer approval')
            if name in {'rtl_generator','verification_tools','synthesis','ppa_optimizer'}:
                frozen = state.get('frozen_hashes')
                if frozen and before['architecture'] != frozen['architecture']:
                    raise ValueError('Frozen architecture changed outside Architect')
                if name != 'rtl_generator' and state.get('verifier_status') == 'VERIFICATION_READY' and frozen:
                    for owned in ('tests','reference'):
                        if before[owned] != frozen[owned]:
                            raise ValueError(f'Frozen {owned} changed outside independent Verifier')
            if name == 'verification_tools':
                definitions = review_definition_hashes(state, before)
                if state.get('verifier_review_status') != 'APPROVED' or state.get('verifier_review_hashes') != definitions:
                    raise ValueError('Coverage/assertion review must approve the current definitions before simulation')
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
        emit(WORKSPACE_ROOT, name, 'failed' if update.get('orchestration_error') else 'finished',
             status=update.get('status'), history=update.get('history', []))
        return update
    return run


def verification_repair_node(state):
    # Do not transmit Debugger prose/logs/source-derived facts to independent Verifier.
    context = build_verification_context(user_request=state['user_request'],
                                         architecture_dir=Path(state['architecture_dir']))
    if state.get('verifier_review_status') == 'VERIFIER_REPAIR_REQUIRED':
        review = state['verifier_review_result']
        context['assertion_definition_review'] = {
            'findings': review['findings'],
            'previous_verifier_output': state['verifier_result'],
            'instruction': (
                'Repair only the concrete coverage/assertion definition findings. '
                'Start from previous_verifier_output and return exact local source '
                'patches only. Preserve frozen external semantics, valid existing '
                'coverage/checks, and existing valid stimulus. Change stimulus only '
                'for a concrete MISSING_STIMULUS or INVALID_STIMULUS_MAPPING finding, '
                'or when a small wiring change is essential to install a checker. Do not optimize '
                'stimulus distributions or claim bins were hit; simulation follows '
                'the review. Add contract-relevant points even inside an existing '
                'taxonomy class; retain required source for existing baseline/Architect '
                'concepts and use llm_extension only for additional concepts. '
                'Do not edit code-owned interface IDs, taxonomy or runtime. Do not '
                'downgrade required concepts. The Reviewer never contacts Architect; '
                'if a unique executable expectation still cannot be derived, the '
                'Verifier alone may submit a precise question to Architect. '
                'A metadata_edit can never change a coverpoint or bin identity field '
                '(operation_name, family, id, concept, source, name) even to correct '
                'its meaning; that request is always rejected. When a finding says a '
                "bin's meaning is wrong (e.g. a bin is unreachable or mislabeled for "
                'the contract), keep its name and id exactly as declared and correct '
                'only its predicate/intent/fields, or the sampling binding, so the '
                'existing identity now matches the corrected behavior.'
            ),
        }
        return {'verification_context': context,
                'verifier_revision': state.get('verifier_revision', 0) + 1,
                'verifier_status': 'PENDING', 'verification_status': 'PENDING',
                'verifier_review_status': 'PENDING', 'verifier_review_result': None,
                'verifier_review_hashes': {}, 'needs_regression': True,
                'history': [{'stage': 'verification_repair', 'status': 'ASSERTION_DEFINITION_CORRECTION',
                             'findings': review['findings']}]}
    if state.get('verifier_status') == 'SEMANTIC_VALIDATION_FAILED':
        errors = state.get('errors', [])
        validator_error = str(errors[-1]) if errors else 'unknown semantic validation error'
        missing_concepts = _extract_missing_concepts(validator_error)
        previous_draft = state.get('verifier_draft')
        previous_context = state.get('verification_context')
        previous_assertion_review = (
            previous_context.get('assertion_definition_review')
            if isinstance(previous_context, dict)
            else None
        )
        if isinstance(previous_assertion_review, dict):
            # A malformed or incomplete local patch remains owned by Verifier. Keep
            # the same concrete review findings and retry against the most recent
            # reconstructed draft instead of falling back to a full-file rewrite.
            # That draft may already carry genuinely-applied edits from a prior
            # attempt in this same round (see ReviewPatchPartialFailure); only
            # the findings still outstanding need to be resubmitted.
            already_addressed = sorted(
                set(state.get('verifier_addressed_findings', []))
                | set(previous_assertion_review.get('already_addressed_findings', []))
            )
            total_findings = len(previous_assertion_review.get('findings', []))
            remaining = sorted(set(range(total_findings)) - set(already_addressed))
            context['assertion_definition_review'] = {
                **previous_assertion_review,
                'previous_verifier_output': (
                    previous_draft
                    if isinstance(previous_draft, dict)
                    else previous_assertion_review.get('previous_verifier_output')
                ),
                'patch_validation_error': validator_error,
                'already_addressed_findings': already_addressed,
                'instruction': (
                    'Correct the local source patch using this exact validation error. '
                    'Do not regenerate complete files and do not escalate a patch, '
                    'Python, coverage, or output-size problem to Architect. '
                    f'Findings at indices {already_addressed} are already correctly '
                    'applied in previous_verifier_output by a prior retry in this same '
                    f'review round; do not resubmit edits for them. Only findings at '
                    f'indices {remaining} still need a patch or metadata edit now.'
                    if already_addressed else
                    'Correct the local source patch using this exact validation error. '
                    'Do not regenerate complete files and do not escalate a patch, '
                    'Python, coverage, or output-size problem to Architect.'
                ),
            }
            return {
                'verification_context': context,
                'verifier_revision': state.get('verifier_revision', 0) + 1,
                'verifier_status': 'PENDING',
                'verification_status': 'PENDING',
                'needs_regression': True,
                'history': [{
                    'stage': 'verification_repair',
                    'status': 'SOURCE_PATCH_CORRECTION',
                    'validator_error': validator_error,
                    'already_addressed_findings': already_addressed,
                }],
            }
        context['semantic_validation_review'] = {
            'validator_error': validator_error,
            'missing_concepts': missing_concepts,
            'instruction': (
                'This is a defect in the verifier-owned output, not an architecture '
                'conflict. Start from previous_verifier_output when it is present and '
                'resolve validator_error below. While you are there, also check '
                'previous_verifier_output against every other structural rule you were '
                'given for verifier-authored output (required section markers, a '
                '# STIMULUS [label] comment for every declared stimulus intent and a '
                'feature comment immediately above every assert, an OPERATION_SAMPLING_BINDINGS '
                'entry for every declared operation coverage point, a coverage intent '
                'for every declared coverage_obligation, references to every required '
                'role-tagged completion/error signal, and real executable cocotb test '
                'bodies rather than descriptions) and fix any of those you can identify '
                'as still violated in the same response, not only validator_error. '
                'Reproduce every other line of previous_verifier_output byte-for-byte: '
                'working oracle/test code, comments, coverage points, checks, and '
                'stimulus that are not implicated by validator_error or one of the '
                'rules above must not change. The response '
                'schema still requires complete file content, but only the regions '
                'implicated by validator_error or a rule above may differ from '
                'previous_verifier_output. If there is no previous '
                'output, generate a fresh complete oracle and test suite from the '
                'frozen contract; prior sources are not required. Coverage field '
                'names, bins and test schedules are your decisions, not missing '
                'Architect decisions. For '
                'every missing concept, add an operation coverpoint whose concept ID '
                'matches byte-for-byte, whose source is baseline or architect_extension '
                'as required by the frozen contract, and whose field, reachable bins, '
                'predicates, test stimulus, and reusable/custom DUT observer are mutually '
                'consistent, without touching unrelated existing coverpoints. Preserve all '
                'already-required features and checks. Do not '
                'return ARCHITECTURE_CONFLICT to evade this validator error. Response '
                'length, token budget, delivery format, and missing prior source are '
                'process concerns and are never architecture conflicts; emit the '
                'corrected artifact now.'
            ),
        }
        if isinstance(previous_draft, dict):
            context['semantic_validation_review']['previous_verifier_output'] = previous_draft
        return {
            'verification_context': context,
            'verifier_revision': state.get('verifier_revision', 0) + 1,
            'verifier_status': 'PENDING',
            'verification_status': 'PENDING',
            'needs_regression': True,
            'history': [
                {
                    'stage': 'verification_repair',
                    'status': 'SEMANTIC_CORRECTION',
                    'missing_concepts': missing_concepts,
                }
            ],
        }
    cocotb_evidence = (
        (state.get('verification_evidence') or {}).get('cocotb') or {}
    )
    context['verification_infrastructure_review'] = {
        'category':'TESTBENCH_ERROR',
        'instruction':(
            'Independently revalidate your own Python imports, timing phases, handshake '
            'sampling, signed conversions, oracle arithmetic and task lifetimes against '
            'the frozen contract. The failure excerpt is evidence from your own generated '
            'test, not RTL source or a new expected behavior. Fix test infrastructure '
            'only; preserve all coverage and assertions. Do not adapt expectations to '
            'implementation behavior.'
        ),
        'previous_own_artifacts':{name:{p.name:p.read_text() for p in sorted((WORKSPACE_ROOT/name).glob('*.py'))}
                                 for name in ('reference','tests')}}
    failure_excerpt = _first_cocotb_failure_excerpt(cocotb_evidence.get('stdout'))
    if failure_excerpt:
        context['verification_infrastructure_review']['first_failure_excerpt'] = failure_excerpt
    functional_coverage = (
        (state.get('verification_evidence') or {}).get('cocotb') or {}
    ).get('functional_coverage')
    if isinstance(functional_coverage, dict) and functional_coverage.get('status') != 'PASS':
        history = rebuild_stimulus_history(WORKSPACE_ROOT / 'verification')
        history_view = verifier_stimulus_history_view(
            history,
            history_path=WORKSPACE_ROOT / 'verification' / HISTORY_FILE,
        )
        missing_bins = list(functional_coverage.get('missing_bins', []))
        context['coverage_closure_review'] = {
            'missing_bins': missing_bins,
            'covered_bins': list(functional_coverage.get('covered_bins', [])),
            'bin_hits': dict(functional_coverage.get('bin_hits', {})),
            'missing_bin_definitions': _missing_bin_definitions(
                context, state, missing_bins
            ),
            'stimulus_summary': history_view,
            'instruction': (
                'These missing bins came from your previous verifier-owned coverage '
                'plan; they are diagnostic evidence, not a frozen Architect contract. '
                'Preserve every frozen interface obligation and valid check. For '
                'operation coverage, independently re-derive reachable fields and '
                'bins from the frozen operation semantics: keep valid prior bins and '
                'add specification-derived stimulus for them, but replace any '
                'impossible, inapplicable, placeholder, or malformed prior operation '
                'bin instead of requesting an architecture change. Operation field '
                'names are verifier-owned and must be chosen consistently between the '
                'coverage plan and DUT observation bindings. For all '
                'points, preserve valid OPERATION_SAMPLING_BINDINGS and use the supplied '
                'effective bin definitions; only the trusted observer feeds those points. '
                'Do not replace a missing actual observation with a planned field value. '
                'Catalog starter-bin '
                'names are suggestions, not mandatory bins. Use the previous test source, '
                'missing_bin_definitions, and stimulus_summary field distributions to '
                'preserve useful prior scenarios, avoid blind repetition, and add new '
                'legal stimulus aimed at missing_bins. Exact prior input/output payloads '
                'are deliberately excluded from this LLM context and remain only in the '
                'on-disk audit ledger. '
                'Never declare a bin hit '
                'manually, and do not return ARCHITECTURE_CONFLICT solely because a '
                'previous verifier-owned operation ID, field, or bin was defective.'
            ),
        }
    return {'verification_context':context, 'verifier_revision':state.get('verifier_revision',0)+1,
            'verifier_status':'PENDING','verification_status':'PENDING','needs_regression':True,
            'history':[{'stage':'verification_repair','status':'INDEPENDENT_REVIEW'}]}


def _first_cocotb_failure_excerpt(stdout, *, max_chars=6000):
    """Return one verifier-owned failure block without compiler/debugger output."""

    if not isinstance(stdout, str) or not stdout:
        return None
    lines = stdout.splitlines()
    start = next((index for index, line in enumerate(lines)
                  if 'cocotb.regression' in line and ' failed' in line), None)
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if 'cocotb.regression' in line and (' running ' in line or '*****' in line):
            end = index
            break
    return '\n'.join(lines[start:end])[:max_chars]


def _extract_missing_concepts(message: str) -> list[str]:
    """Extract exact IDs from deterministic validator set-difference errors."""

    concepts: set[str] = set()
    for literal in re.findall(r"missing=(\[[^\]]*\])", message):
        try:
            values = ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            continue
        if isinstance(values, list):
            concepts.update(value for value in values if isinstance(value, str))
    return sorted(concepts)


def _missing_bin_definitions(context, state, missing_bins):
    """Return only the active plan rows needed to understand failed coverage."""

    architecture = context.get('frozen_architecture', {})
    interface = architecture.get('interface_contract')
    if not isinstance(interface, dict):
        return []
    verifier_result = state.get('verifier_result') or {}
    operation_coverage = verifier_result.get('operation_coverage', [])
    try:
        plan = merge_coverage_plans(
            build_interface_coverage_plan(interface),
            operation_plan_for_tests(
                list(operation_coverage),
                [item['content'] for item in verifier_result.get('test_files', [])],
                architecture.get('architecture_contract', {}), interface,
            ),
        )
    except (KeyError, TypeError, ValueError):
        return []
    missing = set(map(str, missing_bins))
    definitions = []
    for obligation in plan.get('obligations', []):
        obligation_id = str(obligation.get('id', ''))
        selected_bins = []
        for bin_spec in obligation.get('bins', []):
            bin_id = f"{obligation_id}.{bin_spec.get('name', '')}"
            if bin_id in missing:
                selected_bins.append(dict(bin_spec))
        if selected_bins:
            definitions.append({
                'id': obligation_id,
                'template': obligation.get('template'),
                'bindings': obligation.get('bindings', {}),
                'bins': selected_bins,
            })
    return definitions


def final_report_node(state):
    emit(WORKSPACE_ROOT, 'final_report', 'started')
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
    vivado_status = (
        'SKIPPED (verification-only)'
        if state.get('verification_only') and state.get('verification_status') == 'PASS'
        else (state.get('synthesis_result') or {}).get('status','NOT_RUN')
    )
    lines = [f"# Hardware generation: {state.get('status','UNKNOWN')}", '',
             f"Request: {state.get('user_request','')}", '',
             f"Functional verification: {state.get('verification_status','NOT_RUN')}",
             f"Vivado: {vivado_status}",
             f"RTL repair iterations: {state.get('repair_iteration',0)}",
             f"Verifier revisions: {state.get('verifier_revision',0)}",
             f"Coverage/assertion review: {state.get('verifier_review_status','NOT_RUN')} (not simulation PASS)",
             f"PPA iterations: {state.get('ppa_iteration',0)}", '',
             f"Selected RTL: {report['selected_rtl']}", '', '## Errors']
    lines.extend(state.get('errors',[]) or ['None'])
    functional_coverage = (
        (state.get('verification_evidence') or {}).get('cocotb') or {}
    ).get('functional_coverage')
    if isinstance(functional_coverage, dict):
        lines += ['', '## Functional coverage',
                  f"Status: {functional_coverage.get('status', 'UNKNOWN')}",
                  f"Coverage: {functional_coverage.get('coverage_percent', 0.0):.2f}%", '',
                  '### Covered bins']
        bin_hits = functional_coverage.get('bin_hits', {})
        covered_bins = list(functional_coverage.get('covered_bins', []))
        lines.extend(
            [f"- {bin_id} (hits: {bin_hits.get(bin_id, 0)})" for bin_id in covered_bins]
            or ['None']
        )
        lines += ['', '### Missing bins']
        lines.extend(
            [f"- {bin_id}" for bin_id in functional_coverage.get('missing_bins', [])]
            or ['None']
        )
    stimulus_history = (
        (state.get('verification_evidence') or {}).get('stimulus_history')
        or ((state.get('verification_evidence') or {}).get('cocotb') or {}).get(
            'stimulus_history'
        )
    )
    if isinstance(stimulus_history, dict):
        lines += [
            '',
            '## Stimulus history',
            f"Path: {stimulus_history.get('path', '')}",
            f"Executed records: {stimulus_history.get('stimulus_count', 0)}",
            f"Unique stimuli: {stimulus_history.get('unique_stimulus_count', 0)}",
            f"Repeated executions: {stimulus_history.get('duplicate_execution_count', 0)}",
        ]
    lines += ['', '## Limitations', *report['limitations']]
    (root/'final.md').write_text('\n'.join(lines)+'\n')
    emit(WORKSPACE_ROOT, 'final_report', 'finished', status=state.get('status'))
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
