# Verifier tool regression

This package tests the verifier tool itself. It is deliberately separate from
`../tb_validation/`, which is production code invoked for every generated TB.

## Layout

- `unit/`: fast, simulator-free checks of pools, plans, checkers, classifiers,
  and reusable drivers.
- `integration/`: contract compilation, generated-TB instrumentation, extension
  reuse, Architect/Verifier boundary, and ledger-inventory checks.
- `rtl/`: real Verilator/Cocotb fault/fix regressions.
- `extensions/unit/`: simulator-free contract-local and LLM-extension checks.
- `extensions/rtl/`: executable extension bundles and RTL fault/fix checks.
- `extensions/fixtures/`: DUTs and testbench sources used only by extension tests.
- `api_evaluation/`: opt-in real-Verifier challenge catalog, bounded runner, and
  compact paper-facing evidence. Normal regression validates it without calling an API.
- `fixtures/`: reusable small contracts, reference models, and RTL fixtures.
- `benchmarks/`: frozen real/synthetic accelerator benchmarks and mutation
  runners.
- `qualification/`: executable ledger builders and machine-readable qualification state.
- `local_reports/`: ignored local results and historical qualification notes.

## One queue

Run the fast simulator-free regression:

```bash
python -m multigent.verifier_tool.tool_regression.run_all --quick
```

Run everything, including the non-HLS RTL fault/fix fixtures, a fresh HLS
baseline, every registered HLS RTL mutant, and every registered HLS driver
fault:

```bash
python -m multigent.verifier_tool.tool_regression.run_all --jobs 4
```

The full runner writes generated RTL and reports to a temporary directory by
default. Use `--output-dir PATH` to retain them locally. It never calls an LLM
or an external API. Batch qualification is resumable: an existing qualified
case is reused only when its saved generated-TB hash still matches the current
positive baseline. Non-qualified case workspaces are overwritten on retry.
Successful cases retain the compact
`qualification.json` evidence while reproducible copied RTL, raw simulation
reports, and compiler build trees are removed.

## Opt-in Verifier API evaluation

The normal regression never calls an LLM. The dedicated
[`api_evaluation/`](api_evaluation/) catalog contains operation, protocol,
lifecycle, and mixed frozen-contract challenges. An opt-in case calls only the
Verifier, validates the generated artifacts, and stops before RTL generation or
simulation:

```bash
set -a
source .env
set +a
RUN_VERIFIER_API_EVALUATION=1 \
VERIFIER_API_SCENARIO_ID=mixed.affine_and_busy_watchdog \
VERIFIER_API_OUTPUT_DIR=/tmp/verifier-api-evaluation \
PYTHONPATH=. .venv/bin/pytest -q -s \
  multigent/verifier_tool/tool_regression/api_evaluation/test_api_evaluation.py \
  -k selected_verifier_api
```

Each selected scenario permits one structured API attempt. The expected
ownership split, solver witnesses, generated entry-point reachability, and exact
extension bundle IDs are checked deterministically. Raw artifacts remain
ignored; only compact reviewed evidence is retained for paper analysis.
