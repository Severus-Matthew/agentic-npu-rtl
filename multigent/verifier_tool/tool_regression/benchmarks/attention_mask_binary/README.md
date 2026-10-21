# Standalone binary attention-mask qualification

This benchmark isolates the mask boundary in the composed sparse-attention
pipeline:

```text
masked_score[q,s] = mask[q,s] ? scaled_score[q,s] : 0
```

The frozen profile is `binary_attention_mask` with `mask_mode=binary_keep`:
one means keep and zero means drop. It is deliberately a mask-only stage. It
does not implement softmax, a negative-infinity softmax sentinel, normalization,
or the V reduction.

The RTL exposes independent ready/valid score and mask inputs. The
qualification harness inserts deterministic, different valid gaps on those two
channels and random output backpressure. That makes coordinate alignment,
accepted-input accounting, output stability, and reset abort observable without
internal monitor signals.

Run the complete qualification with:

```bash
.venv/bin/python -m multigent.verifier_tool.tool_regression.benchmarks.attention_mask_binary.qualify \
  --random-cases 128 --all-mutants --workers 4 \
  --work-root /private/tmp/attention-mask-full \
  --json /private/tmp/attention-mask-full/qualification_summary.json
```

The exhaustive domain contains every signed 16-bit score under both legal mask
values: 131,072 score/mask pairs. Mutations are applied only to temporary RTL
copies.
