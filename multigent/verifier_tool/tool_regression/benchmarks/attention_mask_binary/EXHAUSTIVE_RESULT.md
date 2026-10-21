# Attention-mask exhaustive result

Status: **STRICT PASS**

- Contract: standalone signed `s16` scaled-score mask, unsigned `u1` mask,
  `binary_keep` polarity (`1=keep`, `0=zero`).
- Functional coverage: **17/17** required bins.
- Exhaustive arithmetic: **131,072/131,072** signed-score/mask pairs.
- Pool traffic: 20 directed/qualification cases, 128 fixed-seed randomized
  cases, and 888 canonical pool elements.
- Total RTL comparisons: **131,960**.
- Temporal stimulus: independently randomized score-valid and mask-valid gaps,
  randomized output backpressure, skewed-channel directed pairing, stalled
  output stability, score-only reset abort, mask-only reset abort, and
  post-completion no-extra-output checks.
- Mutation campaign: **59/59** compile-valid mutations killed, zero survivors,
  zero compile-invalid mutations.
- Deterministic seed: `0xA55A`.
- RTL SHA-256:
  `6c6495a09c5e7a6affc885fd3771c6fa385f66d1e8473ce79da8604bbb1f38cc`.

The full machine-readable result is reproducible at
`/private/tmp/attention-mask-full/qualification_summary.json` using the command
in `README.md`.
