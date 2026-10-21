# Fixed-point attention-scale RTL qualification

This benchmark binds a standalone signed scale stage to the code-owned
`attention_scale` verification pool.  It is intentionally only

`scaled_score = floor(score * round(2^F / sqrt(D)) / 2^F)`

and contains no mask, softmax, or V multiplication.  The frozen profile uses
`D=64`, `F=8`, so the coefficient is exactly `32` and the effective operation is
a signed arithmetic divide by eight.

## External RTL provenance

The scale equation and fixed-point implementation pattern were extracted from
`src/softmax_unit.sv` in
[Abhinav-Avasarala/TRANSFORMER-ATTENTION-ACCELERATOR](https://github.com/Abhinav-Avasarala/TRANSFORMER-ATTENTION-ACCELERATOR),
commit `3054e9a5324da438a78937049f656abc413c2750`.  That source embeds scaling inside
softmax and applies it to the nonnegative `row_max-score` delta.  The checked-in
RTL isolates the equation and makes the operand signed so it can directly verify
the QK-to-scale boundary.  It is a local qualification fixture, not a claim that
the upstream project shipped a standalone signed scale module.

## Gates

The runner requires all of the following:

1. all 14 code-owned scale coverage bins have solver-generated witnesses;
2. baseline RTL passes directed, qualification, randomized, signed-16 exhaustive,
   backpressure stability, accepted-transfer accounting, and reset-abort checks;
3. every compile-valid mutation in the selected catalog is rejected by the same
   frozen testbench.

Run the baseline and a bounded mutation sample:

```bash
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.attention_scale_fixed.qualify \
  --mutants 24 --workers 4
```

Run the full selected fault catalog:

```bash
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.attention_scale_fixed.qualify \
  --mutants all --workers 4 --json-out /private/tmp/attention-scale-exhaustive.json
```
