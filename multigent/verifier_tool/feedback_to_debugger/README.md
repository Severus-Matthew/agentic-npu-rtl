# Feedback to Debugger

This folder owns only the Verifier-provided portion of a Debugger handoff. It has
no dependency on LangGraph, API agents, workspace paths, Architect, RTL Generator,
or Debugger internals.

Pipeline adapters perform only three operations:

1. Load the failed run's coverage plan, coverage report, and stimulus ledger.
2. Call `build_failed_run_artifacts(...)` to select bounded diagnostic evidence.
3. Call `build_verifier_debugger_feedback(...)` with frozen Verifier artifacts.

The returned mapping is not a complete Debugger input: a pipeline may combine it
with Architect-owned contracts and RTL-Generator-owned RTL separately. Call
`validate_verifier_debugger_feedback(...)` again at a process or queue boundary
if this Verifier payload was serialized. `format.yaml` documents the stable
machine-readable field contract and explicitly lists forbidden foreign fields.

This package never decides the root cause and never edits RTL or verifier files.
Those remain Debugger and downstream pipeline responsibilities.
