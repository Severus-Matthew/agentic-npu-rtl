# Operation Domain

One of `verifier_tool`'s three verification domains (`protocol`, `lifecycle`,
`operation` — see [`../README.md`](../README.md) for the full architecture
narrative). This folder holds the **complete, independent implementation of
operation-level verification** — the actual arithmetic/data-movement
semantics of a declared operation (today: `integer_matrix_multiply`) — split
by verification type into its three subfolders:

- [`assertion/`](assertion/README.md) — operation feature assertion catalog
  and code-owned generator.
- [`coverage/`](coverage/README.md) — operation coverage families/plan
  (`plan.py`) and canonical-job sampling bindings (`sampling.py`).
- [`stimulus/`](stimulus/README.md) — the canonical GEMM stimulus generator
  and golden-model evaluator (`evaluate_canonical_operation`) — the one
  place in this domain that computes expected results, shared by every
  design rather than generated per-design.

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
