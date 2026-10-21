# Operation Domain

One of `verifier_tool`'s three verification domains (`protocol`, `lifecycle`,
`operation` — see [`../README.md`](../README.md) for the full architecture
narrative). This folder holds the **complete, independent implementation of
operation-level verification** — the actual arithmetic/data-movement
semantics of a declared operation (today: `integer_matrix_multiply`, the raw
`integer_qk_score` stage, standalone `fixed_point_attention_scale`, standalone
`binary_attention_mask`, and the restricted exact
`integer_sparse_attention` profile) — split
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
unnormalized sparse composition; a future softmax profile must separately
declare how inactive positions are excluded from normalization.

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
