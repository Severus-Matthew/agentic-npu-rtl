# Deterministic Review and Patch

**Naming note:** this folder consolidates two files that used to sit loose
directly under `verifier_tool/` (`deterministic_review.py` and
`deterministic_patch.py`) into one package, purely for filesystem
consistency with every other concern in this tool (`role_pool/`,
`feature_plans/`, `operation_metadata/`, …). Nothing about the public API
changed: both modules are still reached only through the
`multigent.verifier_tool` facade, which now points at
`multigent.verifier_tool.deterministic.review` and
`multigent.verifier_tool.deterministic.patch` instead of the old top-level
module names.

Both modules replace what used to be LLM-driven pipeline stages
(a TB *review* stage, and a metadata *patch* stage) with pure, deterministic
Python. Neither makes a model call, a network request, a simulator call, or a
filesystem write — that is a hard design invariant stated in both files'
module docstrings, not an implementation detail that happens to be true today.

## `review.py` — deterministic TB review

`review_verifier_artifacts(context, candidate, *, validator=None) -> dict` is
the single integration point (also documented at the very end of the
top-level [`../README.md`](../README.md): "the single integration point for
the pre-simulation gate"). It is a drop-in, same-shaped replacement for the
old LLM review stage:

```python
{
  "status": "APPROVED" | "VERIFIER_REPAIR_REQUIRED",
  "summary": "...",
  "findings": [ { "category": ..., "requirement": ..., "evidence": ..., "recommended_change": ... }, ... ],
}
```

Internally it: (1) `_validate_basic_shape` — candidate status must be
`VERIFICATION_READY` and its `reference_files`/`test_files` must be non-empty
with non-blank content; (2) calls a `validator` (by default
`_canonical_validator`, which lazily imports `multigent.agents.verifier.
VerifierAgent` and reuses its existing `_validate_context` +
`_validate_prepared_result` — this facade deliberately does not duplicate that
policy, it just gives it a stable, LLM-free entry point); (3) on any
`SyntaxError`/`TypeError`/`ValueError` from either step, converts the
exception into one or more structured `findings` via
`findings_from_validation_error`, instead of propagating the raw exception.

`findings_from_validation_error(error) -> list[dict]` deliberately preserves
the underlying validator's batching: the validator reports every defect it can
prove in one pass as one semicolon-joined string, and this function splits
that string back into independent findings using `_FINDING_BOUNDARY` — a
regex tuned to split only at known finding-start phrases (`"test source N"`,
`"Every _contract_"`, `"Stimulus intent"`, `"Missing "`, `"Unknown "`, `"Operation "`,
`"Coverage "`, …), not at arbitrary sentence punctuation, so one long
validator message becomes exactly one finding per real defect rather than
being shredded mid-sentence. `_finding_for(evidence)` then pattern-matches
known validator phrasings (`"no await since stimulus"`, `"identical literal
values"`, `"never reads passed keyword"`, `"cocotb time unit ... invalid"`,
`"may transfer a beat before replay"`) into specific `category` +
`recommended_change` pairs with concrete guidance, falling back to a generic
category inferred from keywords (`MISSING_STIMULUS`, `INVALID_STIMULUS_MAPPING`,
`MISSING_ASSERTION`, `COVERAGE_DEFINITION`, `INVALID_ASSERTION`) for anything
unrecognized. If you add a new deterministic validation error message
elsewhere in `verifier_tool` and want it to produce sharp remediation
guidance instead of the generic fallback, add a matching clause here.

`findings_from_coverage(coverage) -> list[dict]` is the other finding
producer, used when the candidate passed structural review but a full
regression's coverage report shows unmet obligations: groups `missing_bins`
by their obligation prefix (bin id minus its final `.segment`) into one
`MISSING_STIMULUS` finding per obligation rather than one per bin (bounded
patch schema, one conceptual defect per finding), reports a report-loading
failure as its own `COVERAGE_DEFINITION` finding, reports every
`assertion_failures` entry as its own `INVALID_ASSERTION` finding, and falls
back to one generic "coverage must be exactly 100 percent" finding if nothing
else could be extracted.

Three more exports exist for coverage-obligation bookkeeping rather than
top-level review:

- `coverage_obligation_mapping_diff(artifact_obligations, source_obligations)`
  — pure set difference in both directions; used to prove a JSON-declared
  obligation list and a Python-source `COVERAGE_OBLIGATIONS` literal actually
  agree.
- `extract_literal_coverage_obligations(filename, content) -> set[str]` —
  parses `content` with `ast` (never `exec`/`eval`s it) to find exactly one
  module-level `COVERAGE_OBLIGATIONS = {...}` assignment and
  `ast.literal_eval`s only that one node; raises if there isn't exactly one,
  if it isn't a literal, if it isn't a collection of strings, or if it has
  duplicates.
- `synchronize_test_coverage_metadata(candidate) -> dict` — for a
  `VERIFICATION_READY` candidate, rebuilds each test file's JSON-side
  `coverage_obligations` field by re-extracting the literal from that same
  file's `content`. The docstring is explicit about why this is safe: the JSON
  field is a *derived copy* of the inert Python literal, not an independent
  semantic input, so recomputing it can only fix staleness (e.g. after a local
  source patch), never invent or hide a real obligation — the canonical
  validator still separately compares the source's claims against the frozen
  coverage plan.

## `patch.py` — bounded local metadata patches

This module implements **one** patch primitive,
`apply_operation_coverage_metadata_edits(operation_coverage, edits) -> None`
(mutates its first argument in place, after building the result on a private
deep copy so a batch either fully succeeds or leaves the input untouched) —
plus the supporting `finding_scope(review)` helper and two exception types.
It exists in `verifier_tool` rather than an LLM-reviewer module specifically
so that "what counts as a safe local edit" is defined exactly once and reused
by semantic validation, coverage-closure patches, and runtime-testbench-failure
patches alike, per its module docstring.

- `finding_scope(review) -> (findings, already_addressed, still_required)` —
  reads `review["findings"]` and `review["already_addressed_findings"]`
  (indices), raising `AgentRuntimeError` if any "already addressed" index is
  out of range, and returns the three sets a caller needs to decide what a
  patch still has to fix.
- `apply_operation_coverage_metadata_edits(operation_coverage, edits)` accepts
  a list of `{"path": "/operation_coverage/...", "op": "add"|"replace"|"remove",
  "value_json": "..."}` edits and enforces, per edit:
  - `path` must start with `/operation_coverage/` and resolve to at least four
    segments deep (an operation → a coverpoint/bin list → a selector → a leaf
    — you cannot patch a whole coverpoint or a whole `operation_coverage`
    entry at once).
  - List traversal uses **selector syntax**, never a numeric index:
    `operation_name=<value>` to pick an operation, `id=<value>` to pick a
    coverpoint, `name=<value>` to pick a bin (`_SELECTORS`). Numeric indices
    are only accepted for a genuinely positional scalar list leaf.
  - A path may be edited at most once per batch — except a repeated `.../-`
    append, which is allowed (multiple new bins/coverpoints in one batch).
  - The leaf segment may never be an identity field
    (`operation_name`/`family`/`id`/`concept`/`source`/`name` —
    `_IDENTITY_FIELDS`): a coverpoint or bin's name/id is permanently frozen
    once created, even to "fix" its meaning — the error message explicitly
    tells the caller to instead edit the sibling `predicate`/`intent` field
    under the same unchanged name.
  - `remove` may only delete one whole `coverpoints`/`bins` list *entry* by
    its selector (never a field beneath one), and is refused if it would leave
    that list empty (a coverpoint always needs ≥1 bin; an operation always
    needs ≥1 coverpoint) unless a replacement was already added earlier in the
    same or an earlier batch.
  - `add .../-` on a `coverpoints`/`bins` list requires the appended object's
    identity field to be **new** — appending a second bin with an
    already-used `name` is rejected (use `replace` on the existing one's
    non-identity fields instead).
  - `replace` may only target an existing scalar leaf (never a `dict`/`list`
    on either side), and is rejected as a no-op if the new value equals the
    old one.

## Who calls this package

- `review_verifier_artifacts` is the pre-simulation gate every generated
  Verifier candidate passes through; see the top-level
  [`../README.md`](../README.md) and
  [`../VERIFIER_INTEGRATION.md`](../VERIFIER_INTEGRATION.md) for the checks it
  runs and what a Verifier-side generator must satisfy
  (`multigent/orchestration/verifier_review_node.py` imports
  `review_verifier_artifacts` directly from the facade).
- `apply_operation_coverage_metadata_edits` is called wherever a Verifier
  local-revision patch touches `operation_coverage` — the same bounded-edit
  discipline the top-level README's "Verifier may change its executable
  coverpoint definitions without returning a new complete coverage catalog"
  sentence refers to.
- Both modules are exercised directly by
  `multigent/tests/test_deterministic_review.py` (imports from
  `multigent.verifier_tool.deterministic.review` after this reorg) and other
  verifier-patch tests.
