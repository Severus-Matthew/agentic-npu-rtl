# Local exhaustive result — 2026-10-20

Command:

```sh
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.qk_systolic_attention_qk.qualify \
  /private/tmp/qk-pool-exhaustive-419 --randomized-cases 128 \
  --mutants 419 --seed 0x514B --jobs 4
```

Result: **PASS**

- QK coverage: 14/14 required bins, no missing bins.
- Frozen stimulus: 148 jobs and 2,368 score-coordinate comparisons per RTL
  variant, plus a one-edge reset-abort sequence.
- Mutation campaign: 419 selected, 419 compile-valid, 419 killed, 0 survived,
  0 invalid.
- Structural faults: 35/35 killed.
- Q/K input-row bit faults: 128/128 killed.
- Score-coordinate output bit faults: 256/256 killed.
- Detection reasons: 411 output mismatches, 2 over-wide completion pulses,
  3 incorrect completion latencies, and 3 completion timeouts.
- Two contract-equivalent edits were excluded from the kill-rate denominator
  with explicit mathematical/control rationales in the JSON report.

Baseline source hashes:

```text
mac_pe.sv       a26d3a5331232538bcd89aee2dd284dba63439f1e2cc2409a73f0ca4e19916e3
qk_systolic.sv  bfd2e58a39432e3ce418cacfa67396dfb171b4d4e3d36c7a869f3b9c915aa3d1
```

The complete local report was written to
`/private/tmp/qk-pool-exhaustive-419/qualification_summary.json`.
