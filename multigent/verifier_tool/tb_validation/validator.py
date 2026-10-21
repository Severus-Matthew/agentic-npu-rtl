"""Stable, deterministic replacement for the LLM-based TB review stage.

Keep orchestration integration pointed at :func:`review_verifier_artifacts`.  The
facade intentionally lives under ``verifier_tool`` so it can be copied or merged as
one self-contained feature while the underlying validators continue to evolve.

This module performs no model call, network access, simulation, or filesystem write.
It trusts Verifier-owned ``llm_extension`` semantics and enforces only the existing
code-owned artifact, interface, taxonomy, coverage, and assertion rules.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any


PreparedValidator = Callable[[Mapping[str, Any], Mapping[str, Any]], None]


class DeterministicArtifactError(ValueError):
    """A generated artifact violated a code-owned validation rule."""


def _canonical_validator(
    candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    """Reuse the canonical deterministic checks without duplicating their policy."""

    # Imported lazily to keep this facade out of VerifierAgent's import graph.  The
    # validator is code-only despite currently living on the agent class.
    from multigent.agents.verifier import VerifierAgent

    try:
        VerifierAgent._validate_context(context)
        VerifierAgent._validate_prepared_result(result=candidate, context=context)
    except Exception as exc:
        if type(exc).__name__ != "AgentRuntimeError":
            raise
        raise DeterministicArtifactError(str(exc)) from exc


_FINDING_BOUNDARY = re.compile(
    r"; (?=(?:test source \d+|Test source|A new capture_protocol_event_trace|"
    r"cycle_trace record|transaction_trace record|Ready/valid handshake output|"
    r"component |"
    r"Every _contract_|Stimulus intent|"
    r"Stimulus |Every Verifier-authored|Verifier must|Stimulus coverage intent|"
    r"STIMULUS_COVERAGE_INTENTS|Verifier-authored operation|Missing |Unknown |"
    r"Operation |Coverage |feature_extensions\[\d+\]))"
)


def _finding_for(evidence: str) -> dict[str, str]:
    evidence = evidence.strip() or "unknown deterministic validation error"
    lowered = evidence.lower()
    if (
        "resolves multiple runtime bindings" in lowered
        and "capture_protocol_event_traces" in lowered
    ):
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Cross-domain evidence observes one shared transaction window",
            "evidence": evidence,
            "recommended_change": (
                "Import capture_protocol_event_traces, resolve every exact binding "
                "named in the finding, and pass them together with one shared unawaited "
                "stimulus coroutine. Consume the returned evidence for every binding. "
                "Do not replay the stimulus through sequential single-binding captures"
            ),
        }
    if any(
        phrase in lowered
        for phrase in (
            "protocol.monitor.contract_event_trace' bindings must be a dict",
            "must be indexed by one of its literal string binding keys",
            "evidence binding use is incomplete",
            "never consumed by an assertion or coverage classifier",
        )
    ):
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "Every concurrently captured protocol binding supplies consumed evidence",
            "evidence": evidence,
            "recommended_change": (
                "Pass bindings as a literal dict whose nonempty string keys map to "
                "(profile, transaction) tuples. Index the returned mapping with those "
                "same literal string keys and feed every binding's trace into a "
                "reachable assertion or coverage classifier; do not create an unused "
                "destination-domain trace"
            ),
        }
    if "test source is missing # === llm-generated operation assertions ===" in lowered:
        return {
            "category": "MISSING_ASSERTION",
            "requirement": "Generated tests retain the canonical assertion-section marker",
            "evidence": evidence,
            "recommended_change": (
                "Restore the exact line '# === LLM-GENERATED OPERATION ASSERTIONS ===' "
                "once in the generated test source. Keep all existing executable "
                "assertions and place their verifier-authored assertion block after it"
            ),
        }
    if (
        "a new capture_protocol_event_trace stimulus is started immediately" in lowered
        and "readonly phase" in lowered
    ):
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Each trace capture starts from a Cocotb writable scheduling phase",
            "evidence": evidence,
            "recommended_change": (
                "Before starting the named next capture, await a writable boundary such "
                "as FallingEdge on that capture's contract-declared clock or Timer(...). "
                "Do not merely add ReadOnly. If two clock-domain traces must observe the "
                "same transaction, start both monitors before the one shared stimulus "
                "instead of replaying that stimulus sequentially"
            ),
        }
    if (
        "ready/valid handshake output is read after risingedge" in lowered
        and "too late to decide" in lowered
    ):
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Handshake acceptance is decided from the values presented at the active edge",
            "evidence": evidence,
            "recommended_change": (
                "Drive inputs on the inactive edge, allow them to settle, and snapshot "
                "the request/ready values before RisingEdge. Cross RisingEdge and use "
                "only that saved pre-edge snapshot to decide whether the transfer was "
                "accepted. A post-edge Timer or ReadOnly cannot recover the old values"
            ),
        }
    if "stimulus coverage intent must target every exact coverage obligation" in lowered:
        return {
            "category": "COVERAGE_DEFINITION",
            "requirement": "Stimulus intent names every exact required coverage obligation",
            "evidence": evidence,
            "recommended_change": (
                "Add each exact ID listed under missing to a reachable "
                "STIMULUS_COVERAGE_INTENTS target list and to the matching STIMULUS "
                "record. Preserve existing targets. The corresponding scenario must "
                "actually create the named condition; do not add a target only to "
                "silence validation"
            ),
        }
    if (
        "stimulus_coverage_intents must be a non-empty list" in lowered
        or "every test file needs exactly one literal stimulus_coverage_intents declaration"
        in lowered
    ):
        return {
            "category": "COVERAGE_DEFINITION",
            "requirement": "Stimulus-to-coverage intent metadata has one canonical literal form",
            "evidence": evidence,
            "recommended_change": (
                "Restore exactly one non-empty literal list: "
                "STIMULUS_COVERAGE_INTENTS = [{\"label\": \"case_id\", "
                "\"targets\": [\"exact.obligation.id\", ...]}]. Preserve each "
                "existing label and target unless the finding explicitly changes it. "
                "Do not use a dict keyed by label, an empty list, or omit the declaration"
            ),
        }
    if "no await since stimulus" in lowered:
        stall_targets = "stall_stability" in lowered
        return {
            "category": "MISSING_STIMULUS",
            "requirement": "Each checked stimulus must correspond to a distinct DUT observation",
            "evidence": evidence,
            "recommended_change": (
                "Keep the existing passing scenario. For the named later stimulus, "
                "drive a genuinely new DUT transaction, await its observed result, "
                "and record those new values under its existing label; do not "
                "reuse the prior checked result or claim a coverage hit"
                + (
                    ". For the listed stall_stability targets, present valid and "
                    "payload before ready, hold them stable while stalled, and "
                    "measure the actual ready/valid cycles on each input channel"
                    if stall_targets else ""
                )
            ),
        }
    if "identical literal values" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "Checked observed values must be measured from the DUT",
            "evidence": evidence,
            "recommended_change": (
                "Replace the copied observed constant with a value actually sampled "
                "from the DUT after stimulus; preserve the independent expected value"
            ),
        }
    if "never reads passed keyword" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "A claimed stimulus-control option must affect real DUT traffic",
            "evidence": evidence,
            "recommended_change": (
                "Make the named helper use this keyword to drive the intended "
                "DUT-input scenario and measure its observed effect. For an input "
                "stall claim, present valid/payload before ready, hold both stable "
                "during the stall, and count actual ready/valid cycles. Preserve "
                "the existing legal jobs and checks; do not merely add a flag "
                "to a stimulus record"
            ),
        }
    if "cocotb time unit" in lowered and "invalid" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "The generated TB must use time units accepted by installed cocotb",
            "evidence": evidence,
            "recommended_change": (
                "Patch only the named cocotb.test or Timer unit literal to an "
                "accepted unit; for seconds use 'sec', not 's'. Preserve all "
                "stimulus, oracle checks, coverage bindings, and RTL"
            ),
        }
    if "may transfer a beat before replay" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Directed stalls must not duplicate an accepted beat",
            "evidence": evidence,
            "recommended_change": (
                "The valid=1 pre-stall loop can handshake whenever ready is high. "
                "Observe ready at every rising edge, count an accepted beat exactly "
                "once, and do not call the normal sender again for that beat. "
                "Create stalls by presenting future-channel valid/payload before "
                "its ready phase and holding both stable until the real handshake; "
                "let measured coverage hits determine which stall lengths occurred"
            ),
        }
    if "not called with simulator-derived evidence" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": (
                "Extension assertions and coverage must consume observations "
                "captured from the running DUT"
            ),
            "evidence": evidence,
            "recommended_change": (
                "Start the reusable capture_protocol_event_trace monitor before "
                "the extension stimulus, then pass evidence['cycle_trace'] and "
                "evidence['transaction_trace'] directly to the named assertion "
                "and coverage functions. Do not reconstruct either trace from "
                "planned inputs, scenario labels, constants, or returned markers"
            ),
        }
    if "capture_protocol_event_trace must receive the unawaited stimulus" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Runtime observation must start before extension stimulus",
            "evidence": evidence,
            "recommended_change": (
                "Pass the stimulus coroutine object directly as the fourth "
                "capture_protocol_event_trace argument, without awaiting it there. "
                "Await capture_protocol_event_trace itself; it starts the observer "
                "and then awaits the stimulus internally"
            ),
        }
    if "record has no top-level field" in lowered and "record['signals']" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "Extension checkers must consume the reusable trace schema exactly",
            "evidence": evidence,
            "recommended_change": (
                "Use transaction records' top-level event/cycle/outstanding fields "
                "and read sampled DUT values from record['signals']. Use cycle "
                "record['events'] for compiled protocol predicates. Do not invent "
                "top-level kind or signal fields; derive residual cross-protocol "
                "events from the real nested signals and event timeline"
            ),
        }
    if "omits exact contract runtime binding(s)" in lowered:
        return {
            "category": "MISSING_ASSERTION",
            "requirement": (
                "Every resolved protocol clock domain must be observed on its "
                "own contract-declared clock"
            ),
            "evidence": evidence,
            "recommended_change": (
                "Use each exact profile/transaction accessor named in the finding. "
                "Run a separate capture_protocol_event_trace for each binding and "
                "combine the observed traces only after capture. Do not infer a "
                "destination-clock event by sampling its signal level on the source clock"
            ),
        }
    if "has no reachable responder that can assert completion input(s)" in lowered:
        return {
            "category": "MISSING_STIMULUS",
            "requirement": (
                "A monitored DUT-output request path needs a reachable testbench "
                "responder capable of completing it"
            ),
            "evidence": evidence,
            "recommended_change": (
                "Start a responder concurrently with the source stimulus. Observe "
                "the destination request on its declared clock, apply any requested "
                "stall schedule, and assert exactly one declared completion input "
                "such as ACK or ERR with the corresponding response payload. "
                "Initializing all completion inputs to zero is not a responder"
            ),
        }
    if "ignores declared parameter(s)" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": (
                "Every branch parameter must shape that branch's executable behavior"
            ),
            "evidence": evidence,
            "recommended_change": (
                "For the named assertion, coverage, or stimulus branch, either "
                "consume each listed parameter in the actual checker, classifier, "
                "or driver behavior, or remove it from that branch's parameters. "
                "Request-level parameters are not copied into every branch"
            ),
        }
    if "never executes declared scenario(s)" in lowered:
        return {
            "category": "MISSING_STIMULUS",
            "requirement": "Every declared extension scenario must execute real DUT traffic",
            "evidence": evidence,
            "recommended_change": (
                "Invoke each named scenario from a reachable cocotb test with its "
                "exact declared parameter values and check the resulting DUT "
                "evidence. If a scenario is not required by the residual feature, "
                "remove it from the bundle instead of leaving an unexecuted claim"
            ),
        }
    if "claims channel" in lowered and "never drives its dut-input" in lowered:
        return {
            "category": "MISSING_STIMULUS",
            "requirement": "Claimed channel coverage must execute that channel direction",
            "evidence": evidence,
            "recommended_change": (
                "Exercise the named channel before its checked-stimulus record. "
                "When a required reusable protocol responder is already selected, "
                "keep that responder call and give its literal request_counts a "
                "nonzero read or write count for the missing direction; do not "
                "replace it with a duplicate manual valid loop. Otherwise drive "
                "the listed DUT-input valid and await the observed handshake. "
                "If this label does not execute that direction, move the target "
                "to a separate label that does instead of overclaiming it"
            ),
        }
    if "does not use a declared cycle/window parameter" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "Temporal stimulus must contain a real parameterized schedule",
            "evidence": evidence,
            "recommended_change": (
                "Declare one real cycle/window parameter and use it to control a "
                "driver stall, repeated clock-edge wait, or other observable "
                "multi-cycle DUT schedule. Do not add an unused timing parameter "
                "only to satisfy metadata"
            ),
        }
    if "only waits; it must drive a dut signal or await a reusable driver" in lowered:
        return {
            "category": "INVALID_STIMULUS_MAPPING",
            "requirement": "The declared extension stimulus function must execute the scenario",
            "evidence": evidence,
            "recommended_change": (
                "Inside the named stimulus function itself, drive the required DUT "
                "input or await an exact required reusable component from the supplied "
                "extension_worklist call_contract. A driver call made only by the parent "
                "test does not make a passive declared stimulus implementation executable"
            ),
        }
    if "returns a decision that no generated test asserts" in lowered:
        return {
            "category": "INVALID_ASSERTION",
            "requirement": "Every extension checker decision must be enforced",
            "evidence": evidence,
            "recommended_change": (
                "At the reachable cocotb call site, assert the named checker result "
                "directly (for example `assert checker(observed_trace) is True`), or "
                "make the checker raise/assert internally. Assigning or ignoring the "
                "returned decision is not enforcement"
            ),
        }
    if (
        "can earn a temporal bin without a reachable assertion" in lowered
        or "can earn declared temporal bin(s)" in lowered
    ):
        return {
            "category": "COVERAGE_DEFINITION",
            "requirement": "Temporal coverage requires explicit observed-trigger evidence",
            "evidence": evidence,
            "recommended_change": (
                "Return trigger evidence derived from the simulator trace and, at the "
                "reachable test call site, assert that the trigger/event count is nonzero "
                "before asserting an exact declared bin. Empty or idle traces must fail"
            ),
        }
    category = (
        "MISSING_STIMULUS"
        if any(word in lowered for word in ("never drives", "missing implementation", "no _contract_record"))
        else "INVALID_STIMULUS_MAPPING"
        if "stimulus" in lowered and any(word in lowered for word in ("mapping", "target", "label"))
        else "MISSING_ASSERTION"
        if "missing" in lowered and any(word in lowered for word in ("assert", "feature comment"))
        else
        "COVERAGE_DEFINITION"
        if any(word in lowered for word in ("coverage", "sampling", "coverpoint", "bin"))
        else "INVALID_ASSERTION"
    )
    return {
        "category": category,
        "requirement": "Generated verification artifacts must satisfy the code-owned deterministic contract",
        "evidence": evidence,
        "recommended_change": "Correct only the artifact named by the deterministic validation error, then rerun validation",
    }


def findings_from_validation_error(error: object) -> list[dict[str, str]]:
    """Turn one aggregated validator error into independently patchable findings.

    The structural validator intentionally reports every defect it can prove in one
    pass.  Preserve that batching here so one Verifier patch can address all defects
    and a partial patch retry can retain the findings it already fixed.
    """

    evidence = str(error).strip() or type(error).__name__
    prefix = "Generated test file "
    # Keep the useful filename wrapper on the first item, but split the validator's
    # semicolon-joined findings only at known finding starts, not at prose clauses.
    parts = [part.strip() for part in _FINDING_BOUNDARY.split(evidence) if part.strip()]
    return [_finding_for(part) for part in parts]


def findings_from_coverage(coverage: Mapping[str, Any]) -> list[dict[str, str]]:
    """Create concrete local findings, grouped by coverage obligation.

    A large interface can have dozens of bins.  Grouping sibling bins keeps one
    conceptual defect together and stays within the bounded patch schema while
    retaining every exact missing bin as evidence.
    """

    findings = []
    grouped: dict[str, list[str]] = {}
    for bin_id in map(str, coverage.get("missing_bins", [])):
        if bin_id in {"runtime_report_missing", "invalid_runtime_report"}:
            findings.append(
                {
                    "category": "COVERAGE_DEFINITION",
                    "requirement": "The full regression must emit a valid measured functional-coverage hit report",
                    "evidence": f"coverage hit report unavailable: {bin_id}; {coverage.get('error', '')}",
                    "recommended_change": (
                        "Repair verifier-owned coverage instrumentation or report emission; "
                        "do not infer missing stimulus or claim any bin hits without a report"
                    ),
                }
            )
            continue
        obligation = bin_id.rsplit(".", 1)[0] if "." in bin_id else bin_id
        grouped.setdefault(obligation, []).append(bin_id)
    for obligation, bins in grouped.items():
        findings.append(
            {
                "category": "MISSING_STIMULUS",
                "requirement": f"Runtime coverage obligation {obligation} must close",
                "evidence": f"functional coverage hit count is 0 for bins={bins}",
                "recommended_change": (
                    "Preserve all existing tests and add the smallest legal DUT stimulus/check "
                    "needed to exercise this exact bin; do not synthesize a hit"
                ),
            }
        )
    for failure in map(str, coverage.get("assertion_failures", [])):
        findings.append(
            {
                "category": "INVALID_ASSERTION",
                "requirement": "All deterministic runtime assertions must pass",
                "evidence": failure,
                "recommended_change": "Repair only the verifier-owned stimulus or checker implicated by this failure",
            }
        )
    if not findings:
        findings.append(
            {
                "category": "COVERAGE_DEFINITION",
                "requirement": "Functional coverage must be exactly 100 percent",
                "evidence": f"coverage status={coverage.get('status')!r}, percent={coverage.get('coverage_percent')!r}",
                "recommended_change": "Repair the smallest verifier-owned coverage or stimulus defect and rerun",
            }
        )
    return findings


def _validate_basic_shape(candidate: Mapping[str, Any]) -> None:
    if candidate.get("status") != "VERIFICATION_READY":
        raise DeterministicArtifactError(
            "Deterministic TB review requires VERIFICATION_READY artifacts"
        )
    for field in ("reference_files", "test_files"):
        items = candidate.get(field)
        if not isinstance(items, list) or not items:
            raise DeterministicArtifactError(f"{field} must be a non-empty list")
        for item in items:
            if not isinstance(item, Mapping) or not str(item.get("content", "")).strip():
                path = item.get("path", "<unknown>") if isinstance(item, Mapping) else "<unknown>"
                raise DeterministicArtifactError(
                    f"Generated {field} artifact {path} is empty"
                )


def coverage_obligation_mapping_diff(
    artifact_obligations: Iterable[str], source_obligations: Iterable[str]
) -> dict[str, list[str]]:
    """Return the exact auditable difference between JSON and source claims."""

    artifact = set(map(str, artifact_obligations))
    source = set(map(str, source_obligations))
    return {
        "missing_in_source_constant": sorted(artifact - source),
        "unexpected_in_source_constant": sorted(source - artifact),
    }


def extract_literal_coverage_obligations(
    filename: str, content: str
) -> set[str]:
    """Read one inert module-level COVERAGE_OBLIGATIONS declaration."""

    tree = ast.parse(content, filename=filename, mode="exec")
    declarations: list[ast.AST] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(
            isinstance(target, ast.Name)
            and target.id == "COVERAGE_OBLIGATIONS"
            for target in targets
        ):
            declarations.append(node.value)
    if len(declarations) != 1:
        raise ValueError(
            f"Generated test file {filename} must define exactly one module-level "
            "COVERAGE_OBLIGATIONS literal"
        )
    try:
        value = ast.literal_eval(declarations[0])
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS must be literal"
        ) from exc
    if not isinstance(value, (list, tuple, set)) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS must contain strings"
        )
    if len(value) != len(set(value)):
        raise ValueError(
            f"Generated test file {filename} COVERAGE_OBLIGATIONS contains duplicates"
        )
    return set(value)


def synchronize_test_coverage_metadata(
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild redundant test-artifact obligation metadata from Python source.

    ``coverage_obligations`` is a structured copy of the inert module-level
    ``COVERAGE_OBLIGATIONS`` declaration, not an independent semantic input. A
    local Verifier source patch can therefore make only this duplicate stale.
    Rebuilding the JSON copy is deterministic and leaves the authored Python TB
    byte-for-byte unchanged. The canonical validator still compares the source
    claims with the frozen coverage plan, so this cannot invent or hide a hit.
    """

    prepared = copy.deepcopy(dict(candidate))
    if prepared.get("status") != "VERIFICATION_READY":
        return prepared
    tests = prepared.get("test_files")
    if not isinstance(tests, list):
        return prepared
    for item in tests:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("path", "<unknown>"))
        item["coverage_obligations"] = sorted(
            extract_literal_coverage_obligations(
                filename, str(item.get("content", ""))
            )
        )
    return prepared


def review_verifier_artifacts(
    context: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    validator: PreparedValidator | None = None,
) -> dict[str, Any]:
    """Validate one Verifier candidate and return the legacy review-shaped result.

    The return shape deliberately remains compatible with the existing orchestration
    state and routing.  This lets callers replace the old reviewer with one function
    call without renaming graph nodes or migrating saved state.
    """

    validate = validator or _canonical_validator
    prepared = copy.deepcopy(dict(candidate))
    try:
        _validate_basic_shape(prepared)
        validate(prepared, context)
    except (SyntaxError, TypeError, ValueError) as exc:
        return {
            "status": "VERIFIER_REPAIR_REQUIRED",
            "summary": "Deterministic TB validation rejected the generated artifacts",
            "findings": findings_from_validation_error(exc),
        }
    return {
        "status": "APPROVED",
        "summary": (
            "Code-owned interface, taxonomy, coverage, sampling, and base assertion "
            "checks passed; Verifier-owned llm_extension semantics were trusted"
        ),
        "findings": [],
    }


__all__ = [
    "coverage_obligation_mapping_diff",
    "extract_literal_coverage_obligations",
    "findings_from_coverage",
    "findings_from_validation_error",
    "review_verifier_artifacts",
    "synchronize_test_coverage_metadata",
]
