# Qualification status

The old matrix mixed isolated local fixtures, hand-assembled HLS smoke tests,
and full generated-TB evidence under the same check mark. It has been replaced
with two separate matrices:

- [`FULL_POOL_QUALIFICATION_MATRIX.md`](FULL_POOL_QUALIFICATION_MATRIX.md):
  exhaustive inventory of the active tag, protocol, lifecycle, and operation
  pools. It is an unqualified checklist, not a support claim.
- [`HLS_GOLDEN_BENCHMARK_MATRIX.md`](HLS_GOLDEN_BENCHMARK_MATRIX.md): concrete
  features and bins resolved from the frozen real-HLS GEMM contract. Earlier
  manually assembled mutant tests are marked `S` (smoke), deterministic driver
  rejections `D`, and timeout-only detections `T`; none is a strict `✓`.

Strict qualification requires a frozen contract, a normally generated TB, a
single-feature RTL mutant rejected for the intended reason, and original or
corrected RTL passing all required coverage bins, assertions, and the stimulus
ledger with that same TB. We are prioritizing previously untested HLS benchmark
features. No entry has a strict `✓` yet.
