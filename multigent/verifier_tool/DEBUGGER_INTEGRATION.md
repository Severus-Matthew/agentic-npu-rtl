# Debugger-side evidence: what `verifier_tool` provides

This document describes the one piece of `verifier_tool` that produces
evidence for a failure-diagnosis consumer: the
[`feedback_to_debugger/`](feedback_to_debugger/README.md) package. It states
what the package requires, what it returns, how it is currently used, and where
the details are. It does not describe or prescribe how any pipeline is
structured; whatever consumes the payload owns that.

## What to require of a Debugger-side consumer

These follow from how the tool defines its evidence and its ownership:

1. **Treat the payload as measured, frozen evidence.** The tool stamps
   `provenance` with `deterministic_evidence_authoritative`,
   `verifier_artifacts_frozen`, and `coverage_hits_are_measured`. Coverage hits,
   assertion failures, and ledger rows come from the simulation, not from what a
   scenario label planned.
2. **Keep non-Verifier state out of the Verifier payload.** The tool's validator
   rejects `current_rtl`, `frozen_architecture`, `root_cause_policy`,
   `prior_diagnosis`, `prior_repair_plan`, `repair_iteration`, and `rtl_feedback`
   inside it. Whatever else the consumer needs travels beside it, not in it.
3. **Do not ask for edits to tool-owned artifacts.** The generated testbench
   block, golden-model evaluator, canonical classifiers, and protocol/lifecycle
   checkers are `verifier_tool` code; the tool provides no LLM-editable path for
   them (`validate_contract_generated_block` rejects a modified block). A
   diagnosis that names one of them is a defect report against `verifier_tool`.
4. **Supply already-parsed plain data** to the builder (mappings, strings,
   lists); the package does no file loading.

## What the tool provides

Four public functions, all importable from `multigent.verifier_tool`:

| Function | Purpose |
|---|---|
| `build_failed_run_artifacts(verification_evidence, *, coverage_plan=None, coverage_report=None, stimulus_ledger=None)` | Selects the root-cause-relevant rows of the measured artifacts (no file loading — the caller passes already-parsed mappings). |
| `build_verifier_debugger_feedback(*, verification_status, failure_class, verification_evidence, failed_run_artifacts, frozen_reference, frozen_tests, verification_plan, operation_coverage, evidence_limit=6000)` | Assembles the complete, exclusive Verifier-owned payload and validates it before returning. |
| `validate_verifier_debugger_feedback(payload)` | Re-validates a payload (for example after it crossed a process or queue boundary). Raises `DebuggerFeedbackError`. |
| `bound_debugger_evidence(value, limit=6000)` | The truncation policy used by the builder; also usable on its own. |

`feedback_to_debugger/format.yaml` documents the same contract in machine-readable
form, including the explicitly excluded fields.

## Payload shape

```python
{
  "schema_version": 1,
  "source": "verifier_tool",
  "verification_status": "COMPILE_FAILURE" | "SIMULATION_FAILURE" | "SIMULATION_TIMEOUT" | "COVERAGE_FAILURE",
  "failure_class": "...",                # non-empty
  "verification_evidence": {...},        # bounded copy of the raw evidence mapping
  "failed_run_artifacts": {              # exactly these three keys
    "coverage_plan": {...} | None,
    "coverage_report": {...} | None,     # path, status, coverage_percent, assertion_failures, failure_records, last_observed_snapshot, operation_sampling
    "stimulus_ledger": {...} | None,     # path, status, most_recent_checked_stimuli (last 8 records)
  },
  "frozen_verifier": {                   # exactly these four keys
    "reference": {"<file>.py": "<source>"},   # non-empty, .py names
    "tests": {"<file>.py": "<source>"},        # non-empty, .py names
    "verification_plan": {...},
    "operation_coverage": [...],
  },
  "provenance": {                        # must match exactly
    "deterministic_evidence_authoritative": True,
    "verifier_artifacts_frozen": True,
    "coverage_hits_are_measured": True,
  },
}
```

## What the tool requires

- Inputs are plain data (mappings, strings, lists). The package has no
  dependency on LangGraph, agents, workspace paths, or any RTL/Architect/Debugger
  code.
- `build_failed_run_artifacts` reads two optional locators from
  `verification_evidence`: `cocotb.functional_coverage.report_path` and
  `cocotb.stimulus_ledger.path` (recorded as `path` in the selected rows), and
  takes the coverage plan/report and ledger as separate arguments.
- The validator rejects a payload that is missing any required key, whose
  `failed_run_artifacts` / `frozen_verifier` key sets differ from the two lists
  above, whose `verification_status` is not one of the four failure statuses,
  or that carries any of these foreign fields: `current_rtl`,
  `frozen_architecture`, `root_cause_policy`, `prior_diagnosis`,
  `prior_repair_plan`, `repair_iteration`, `rtl_feedback`.

## Truncation behavior

`bound_debugger_evidence` returns a bounded deep copy. `limit` must be an
integer >= 300. A string longer than `limit` keeps its first `limit // 3` and
last `2 * limit // 3` characters around a
`[TRUNCATED: full evidence retained in run artifacts]` marker. Lists and tuples
keep their last 128 entries (tuples come back as lists); mappings are bounded
recursively. It only bounds the returned copy; it does not read or write files.

## How it is currently used

Nothing in `multigent/` other than
[`multigent/tests/test_debugger_feedback_builder.py`](../tests/test_debugger_feedback_builder.py)
calls these four functions today (checked by grep), and
`multigent/agents/debugger.py` imports nothing from `verifier_tool`. The package
is an available surface, not a wired dependency. The same statement holds in the
other direction: `verifier_tool` never calls a Debugger.

## Where details are

- [`feedback_to_debugger/README.md`](feedback_to_debugger/README.md) and
  `format.yaml` — the package contract.
- [`orchestration/README.md`](orchestration/README.md) — the coverage report and
  stimulus-ledger artifacts these functions select from, and how they are
  produced.
- [`operation/coverage/README.md`](operation/coverage/README.md) — the
  `operation_sampling` rows carried in the coverage report.
- [`VERIFIER_INTEGRATION.md`](VERIFIER_INTEGRATION.md) — the frozen Verifier
  artifacts (`reference`, `tests`, `verification_plan`, `operation_coverage`)
  the payload embeds.
