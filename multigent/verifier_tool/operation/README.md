# Operation Domain

One of `verifier_tool`'s three verification domains (`protocol`, `lifecycle`,
`operation` — see [`../README.md`](../README.md) for the full architecture
narrative). This folder holds the **complete, independent implementation of
operation-level verification** — the actual arithmetic/data-movement
semantics of a declared operation (today: `integer_matrix_multiply`, the raw
`integer_qk_score` stage, standalone `fixed_point_attention_scale`, standalone
`binary_attention_mask`, indexed `integer_block_matmul`, standalone
`fixed_point_softmax`, and the restricted exact `integer_sparse_attention`
profile) — split
by verification type into its three subfolders:

- [`assertion/`](assertion/README.md) — operation feature assertion catalog
  and code-owned generator.
- [`coverage/`](coverage/README.md) — operation coverage families/plan
  (`plan.py`) and canonical-job sampling bindings (`sampling.py`).
- [`stimulus/`](stimulus/README.md) — canonical GEMM/QK/sparse-attention stimulus generators
  and golden-model evaluator (`evaluate_canonical_operation`) — the one
  place in this domain that computes expected results, shared by every
  design rather than generated per-design.

The QK profile is deliberately an independently verifiable stage:

```text
score[q,s] = sum_d Q[q,d] * K[s,d]
```

It accepts only Q and K and emits the row-major raw score matrix. Score
scaling, masking, softmax, block selection, and multiplication by V are not
silently fused into this profile; each requires its own declared stage.

The standalone mask profile consumes aligned scaled scores and unsigned
one-bit mask elements. `binary_keep` means one preserves the score and zero
emits zero. It intentionally preserves the mask boundary used by the current
unnormalized sparse composition. The separate softmax profile excludes masked
elements from both the row maximum and denominator: zeroing a score is not
equivalent to excluding it from softmax.

## Indexed blocks and normalized rows

`integer_block_matmul` is reusable for GEMM and QK, selected by an explicit
`right_transposed` field, not by signal names. It consumes complete logical
operands and a fixed work list of output-block coordinates. Column/key blocks
identify different outputs; reduction chunks contribute to the same output.
The oracle computes a full dot product independently of the DUT's chunk loop.
It checks selected block mapping, inactive slots, row/column/reduction tails,
and the declared exact or per-add wrap conversion. Its 21 catalog bins describe
external behavior, not internal scheduler activity.

`fixed_point_softmax` is a separate full-row stage with 22 catalog bins.
Scores, optional keep bits, LUT values, delta scaling, clipping, denominator
conversion, division/reciprocal algorithm, rounding, output scale and saturation
must be explicit. It supports direct integer division and a specified
Newton-reciprocal profile. A distinct high-precision natural-exp model reports
approximation error; it never silently replaces the bit-accurate oracle.
Independently normalizing each key block is not full-row softmax.

Both use the ordinary generated campaign, accepted-transfer accounting, protocol
stalls and lifecycle/reset checks. Directed constructors are reclassified before
use; seeded random cases are also included. A bounded constructor miss is
`generation_inconclusive`, not proof of unreachability. See the
[contract details](../pool/operation_metadata/README.md#structured-operation-contracts)
and [local/external RTL evaluation](../tool_regression/benchmarks/block_softmax_external/README.md).

The source-history audit adds explicit reduction-cancellation/last-term cases,
mask sign/zero crosses, discriminating block results and nonzero depth tails,
masked-max/zero softmax cases, distinct rows, and positive-weight underflow.
Six attention-related families now total 115 catalog bins. Twenty supplemental
external tensor invariants execute on accepted DUT I/O; their IDs are recorded
in the stimulus ledger. These are neither internal stage monitors nor claims
that selection, BFP arithmetic, or online weighted normalization is implemented.
See [the source audit](../tool_regression/benchmarks/attention_source_audit/README.md).

These additions do not change `integer_sparse_attention` into a full normalized
attention profile. Online softmax state across streamed tiles, arbitrary sparse
encodings, and an end-to-end normalized QK→softmax→PV contract still require
their own explicit composition/extension. No internal monitor signals are assumed.

The sparse-attention base is deliberately narrow, exact, and composed:

```text
score[q,s] = sum_d Q[q,d] * K[s,d]
Y[q,v] = sum_s(mask[q,s] ? score[q,s] * V[s,v] : 0)
```

Its shared golden trace is assembled as `integer_qk_score -> scale -> mask ->
normalization -> value reduction`. The restricted profile requires explicit
`scaling: none`, a one-bit `binary_keep` mask, and `normalization: none`; those
two bypass stages remain visible in the trace instead of being silently fused.
Non-identity scaling, softmax, top-k, or approximation need another supported
stage/profile or an explicit operation extension.

Not to be confused with [`../pool/operation_metadata/`](../pool/operation_metadata/README.md)
(a "pool," not a domain implementation) — that folder is the Architect-facing
canonical operation/arithmetic metadata *compiler* (turns a frozen contract
into machine-readable operation metadata, including the protocol capture
adapter); this folder is what *consumes* that compiled metadata to generate
assertions, coverage, and stimulus. Confusing these two was the exact
motivation for renaming the old `operation/` (now `pool/operation_metadata/`)
early in this reorg's history, and remains the one naming collision worth
double-checking if you get lost.

The three subfolders select their features independently from the Operation
Feature Plan built by `build_operation_feature_plan()` (see
[`../pool/feature_plans/README.md`](../pool/feature_plans/README.md)); no branch
uses another branch's output to decide applicability. Their implementations do
deliberately share pure, code-owned arithmetic: the assertion wrapper and the
coverage classifier both rely on the canonical golden trace evaluated through
`operation/stimulus/` and `pool/operation_metadata/canonical.py`, while
coverage may query the stimulus generator to prove that a required bin has a
constructible witness. This reuse keeps expected values, trace classification,
and directed witnesses consistent without coupling feature selection.
