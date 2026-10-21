# Frozen extension benchmark corpus

This directory contains 30 hand-selected, locally materialized frozen-contract
inputs for evaluating Verifier behavior that is absent from the closed pools.
It does not contain generated Verifier answers and does not call an API.

The corpus has five distinct cases at each unknown-feature count from one
through six.  It includes isolated protocol, lifecycle, and operation cases;
same-domain compositions; and cross-domain compositions.  Operation formulas
are expressed as solver-compilable `llm_defined` DAG stages.  Protocol and
lifecycle gaps are expressed as normalized `verification_extensions` requests
that require the Verifier to supply only assertion, coverage, and stimulus for
the missing behavior.

Each case directory contains:

- `architecture_contract.yaml`
- `interface_contract.yaml`
- `module_manifest.json`
- `acceptance_criteria.yaml`
- `benchmark_manifest.yaml`, which records the unknown features and whether
  each one is a solver formula or a Verifier extension request
- `README.md`, which explains the shared baseline and each unknown feature in
  that specific case

[`CASE_INDEX.md`](CASE_INDEX.md) lists all 30 cases and their unknown features.
The YAML/JSON contracts are checked in as real files under `cases/`; running the
builder is not required to select and evaluate an individual case.

Regenerate deterministically, without an API:

```bash
PYTHONPATH=. .venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.extension_frozen_contracts.build_contracts
```

Validate all 30 frozen inputs:

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  multigent/verifier_tool/tool_regression/benchmarks/extension_frozen_contracts/test_frozen_contracts.py
```

A future API run must write raw Verifier output under the ignored API results
directory, not into these frozen inputs.  A case counts as successful only
after deterministic approval and, when the evaluation includes RTL, a real
fault/fix simulation using the generated extension code.
