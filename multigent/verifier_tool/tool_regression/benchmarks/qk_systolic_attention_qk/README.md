# Systolic attention-QK qualification

This local benchmark binds a pinned public `Q*K^T` systolic RTL to the
verifier tool's independent `attention_qk` arithmetic pool and then attacks the
frozen testbench with real source mutations.

## Source and arithmetic binding

The two RTL files under `rtl/` are local qualification copies of commit
`3054e9a5324da438a78937049f656abc413c2750` from
[`Abhinav-Avasarala/TRANSFORMER-ATTENTION-ACCELERATOR`](https://github.com/Abhinav-Avasarala/TRANSFORMER-ATTENTION-ACCELERATOR).
They are used only by this local benchmark.

The upstream core ties input and output width together and normally uses Q8.8
truncation.  The raw-QK qualification therefore elaborates it as `N=4`, `D=4`,
`DATA_WIDTH=16`, `ACC_WIDTH=16`, and `FRAC_BITS=0`.  Contract signed-int8 Q/K
elements are sign-extended at the test adapter.  This makes the observed RTL
semantics exactly:

```text
score[q,s] = wrap_s16_after_each_add(sum_d(s8(Q[q,d]) * s8(K[s,d])))
```

This is a raw QK stage.  It does not claim coverage of `/sqrt(d)`, masking,
softmax, or V reduction, and it does not qualify the upstream default Q8.8
format conversion.

## Testbench gates

`qualify.py` uses the production canonical generator/oracle/classifier.  A run
fails unless all 14 QK bins close with no generation exception:

- fixed shape;
- zero, positive, negative, minimum, and maximum operands;
- ordinary, positive/negative boundary, and positive/negative overflow
  accumulation;
- zero, positive, and negative scores.

The same frozen SystemVerilog testbench checks every score coordinate against
the Python-generated independent oracle.  It also checks one-active-edge
synchronous reset abort, no ghost completion, one-cycle `done`, exact declared
latency, result count, and repeated jobs without a reset between them.

Mutation variants are made only in per-run temporary copies.  The campaign has
35 structural faults across arithmetic, signed operand decoding, accumulator,
pipeline, routing, coordinate mapping, lifecycle, and reset.  It can also
sample or exhaustively run 256 output-coordinate bit flips and 128 Q/K
input-row bit flips.  Compile failures are reported as invalid and never
counted as detected semantic bugs.  Contract-equivalent edits are explicitly
excluded with a reason rather than being counted as kills.

Run the default 128-mutant campaign:

```sh
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.qk_systolic_attention_qk.qualify \
  /private/tmp/qk-pool-run --randomized-cases 128 --mutants 128 --seed 0x514B --jobs 4
```

Run every catalogued single-source mutant (419 total):

```sh
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.qk_systolic_attention_qk.qualify \
  /private/tmp/qk-pool-exhaustive --randomized-cases 128 --mutants 419 \
  --seed 0x514B --jobs 4
```

The machine-readable result is `qualification_summary.json` under the selected
output directory.

## Deliberate limits

Passing this benchmark means the RTL survived the declared raw-QK contract and
the catalogued mutation campaign; it is not a proof against every possible RTL
bug.  The current run does not cover the upstream Q8.8 output shift, full-size
`N=64,D=64` exhaustive vectors, synthesis/PPA, gate-level timing, X-propagation,
formal state-space proof, or an illegal `start` while a job is already active.
The upstream interface has no output backpressure.  Scale, mask, softmax, and V
belong to later composed sparse-attention stages and are intentionally outside
this raw-QK benchmark.
