# Extension retrieval

This directory implements deterministic, structure-aware retrieval-augmented
generation for unsupported verification features. The corpus is built from the
checked-in protocol, lifecycle, operation, and lifecycle-policy pools. Retrieval
never changes the frozen contract and never promotes a candidate into a pool.

Ranking first filters by domain, then scores compatible scope, temporal behavior
(handshake, stall, phase, pulse, delay, ordering, reset, error, lifecycle, or
mathematics), request terminology, required evidence shape, and explicit Architect
references. The Verifier receives the top analogues as reusable assertion,
coverage, and stimulus shapes. Exact deterministic feature matching remains the
authoritative first path; retrieval assists only the residual LLM extension.

This feature-level retrieval is complementary to
[`components/`](../../components/README.md). Feature retrieval answers “which
known verification behavior is analogous?” Component resolution answers “which
existing executable building blocks are structurally safe to call?” Exact
component matches are required reuse; incompatible high-ranked components remain
reference-only.
