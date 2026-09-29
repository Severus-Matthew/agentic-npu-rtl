# Verifier API evaluation

This directory is the dedicated, opt-in evaluation surface for asking the real
Verifier model to handle behavior absent from the built-in pools. It is
separate from ordinary regression because API calls cost tokens and can vary;
the normal `tool_regression` queue validates the catalog and harness locally but
does not call a model.

## What is measured

Each case begins with a frozen, deterministically validated Architect contract.
Only the Verifier is called, and execution stops after validated reference/TB
generation. Architect, RTL Generator, simulation, Debugger, commit, and push
are outside this evaluation.

The evaluation asks whether the Verifier:

1. preserves all tool-owned protocol, lifecycle, operation, golden, and
   stimulus behavior;
2. implements only the requested residual feature;
3. reuses resolved helpers and real DUT bindings;
4. produces reachable stimulus and coverage (every formula bin needs a solver
   witness before the TB is accepted);
5. emits assertion/coverage/stimulus functions that are reachable from the
   generated test; and
6. avoids inventing an operation extension when a formula compiles into the
   tool-owned solver DAG.

`scenario_catalog.yaml` currently contains 27 cases: 10 operation formulas,
7 protocol extensions, 7 lifecycle extensions, and 3 mixed cases. It is meant
to grow toward a larger paper evaluation without changing the runner.

## Run locally without an API

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  multigent/verifier_tool/tool_regression/api_evaluation
```

This validates every frozen contract and formula but skips the one opt-in API
test.

## Run selected API cases

List cases:

```bash
PYTHONPATH=. .venv/bin/python -m \
  multigent.verifier_tool.tool_regression.api_evaluation.runner --list
```

Run exactly one case (the default cap is one, even when filtering a domain):

```bash
set -a
source .env
set +a
RUN_VERIFIER_API_EVALUATION=1 PYTHONPATH=. .venv/bin/python -m \
  multigent.verifier_tool.tool_regression.api_evaluation.runner \
  --scenario operation.absolute_value --max-cases 1
```

Run a bounded domain batch by increasing the cap explicitly:

```bash
RUN_VERIFIER_API_EVALUATION=1 PYTHONPATH=. .venv/bin/python -m \
  multigent.verifier_tool.tool_regression.api_evaluation.runner \
  --domain lifecycle --max-cases 3
```

Raw generated files and `attempt_summary.json` go to ignored
`local_results/<scenario>/`. They must not be committed. After human review,
copy only compact, factual fields into `evidence/evaluation_ledger.json` and add
one concise failure row to `evidence/VERIFIER_BUGGY_ATTEMPTS.md` when needed.

## Evidence policy

- Source-controlled: frozen scenario definitions, harness, compact reviewed
  ledger, concise failure taxonomy, and reusable tests.
- Ignored: prompts expanded at runtime, raw API responses, generated TBs,
  coverage plans, simulator logs, build products, and screenshots/slides.
- A model response is not a PASS merely because structured output parsed. It
  must pass every deterministic gate and meet the scenario's ownership split.
- A rejected bad response is useful evidence about the model, but it is never
  counted as successful feature generation.

The compact ledger supports paper tables such as success rate by domain,
first-attempt success, deterministic rejection rate, failure category, helper
reuse, and whether the Verifier changed only the missing delta.
