# Operation Metadata

**Naming note:** this folder was renamed from the old
`verifier_tool/operation/` metadata package to
`verifier_tool/pool/operation_metadata/` so it is not confused with the
domain-first [`../../operation/`](../../operation/README.md) folder. The
**three verification domains** are `protocol`, `lifecycle`, and `operation`
(see the top-level
[`../../README.md`](../../README.md)). This folder is a completely different thing:
one of the Architect-facing "pools," alongside
[`../role_pool/`](../role_pool/README.md) (signal roles/semantics/protocols),
[`../lifecycle_policy_pool/`](../lifecycle_policy_pool/README.md)
(lifecycle behaviors), and [`../tag_pool/`](../tag_pool/README.md) (shared
capability tags). Where those pools describe *roles*, *behaviors*, and *tags*,
this pool compiles a frozen Architect contract into **canonical operation I/O
and arithmetic metadata** — the exact mapping of data objects to channels/
signals, and the exact numeric rules for the arithmetic profiles the tool
implements end-to-end (restricted integer GEMM, raw integer QK scores, and
standalone fixed-point score scale, standalone binary-keep attention mask, and
exact unnormalized binary-masked integer sparse attention). If you are looking for "where does
operation classification/coverage-bin logic actually live," it is
`canonical.py` in *this* folder, not `operation/coverage/` or
`operation/assertion/` (those consume this folder's output; they don't
duplicate it).

Architect declares semantics; this pool resolves references, checks
consistency, and executes supported primitives. It must never invent missing
semantics — a missing or ambiguous declaration is a diagnostic (an
`ArchitectMetadataError`/`ArithmeticMetadataError` with a `reason_code`, recorded
per operation in `unrepresentable_operations`), never a legacy default or a
name-based guess.

## Files

| File | Role |
|---|---|
| `architect_metadata_format.yaml` | Human-readable, merge-facing description of the compiled metadata shape (schema_version 2) |
| `architect_metadata.py` | The main compiler: frozen contract → canonical per-operation I/O + lifecycle + arithmetic metadata |
| `arithmetic_metadata.py` | The arithmetic sub-schema, its Architect-schema composer, and the compact-declaration → canonical-arithmetic compiler |
| `arithmetic_metadata.schema.json` | The actual JSON Schema for `operations[].arithmetic` (`anyOf`: `integer_matrix_multiply`, `integer_qk_score`, `fixed_point_attention_scale`, `binary_attention_mask`, `integer_sparse_attention`, or `llm_extension`) |
| `formula.py` | The safe compiler for formula-defined post-op stages. It translates contract syntax into Z3 IR and uses that same IR for golden evaluation; it never uses `eval`/`exec`. |
| `io_metadata.py` | `data_objects[].serialization` schema (`dense_tensor` / `scalar` / `llm_extension` / `packed_encoding`) + validation + the wire-adapter support guard |
| `packed_encoding.py` | The `packed_encoding` serialization kind: declaration validation and the encode-only `pack_words` engine (several logical elements folded into one physical container) |
| `canonical.py` | Canonical job assembly + code-owned GEMM/QK/fixed-point-scale/binary-mask/sparse-attention golden traces, classifiers, and reachable coverage bins |
| `protocol.py` | `ReadyValidCaptureAdapter` — captures accepted logical values off real ready/valid, AXI4-Lite, full-AXI4 (multi-outstanding, ID-correlated), and `custom_mmio` transfers, including register-started (`control_plane_sequence`) jobs |

For a register-started HLS-style job, `protocol.py` reconstructs each data
object's base pointer from **accepted** AXI4-Lite AW/W/B transactions in the
declared `lifecycle.control_plane_sequence.job_start`, rather than requiring
a non-existent ready/valid command channel. It then attributes AXI4 burst
addresses and accepted data bytes to those objects. For a `packed_encoding`
input, the accepted physical words must exactly equal the deterministic
encoding of the planned canonical tensor before that tensor is used for the
golden calculation. This prevents a planned-but-not-accepted tensor from
earning operation correctness or coverage credit. The lifecycle control-bus
tracker independently turns the same declared action sequence into job start
and completion events; the two consumers must agree on the contract action
order. Independent AXI4 memory ports are reassembled separately; only objects
sharing the same address/data/response channels are decoded together. A
generated-TB end-to-end PASS for the HLS golden is still pending.

## `architect_metadata.py` — the compiler

`build_architect_operation_metadata(architecture, interface) -> dict` is the
one function everything else in this pool exists to support. For every
declared operation it attempts one metadata object with
`schema_version: 2, operation_name, family, dimensions, inputs, outputs,
arithmetic, lifecycle`, and validates it with
`validate_architect_operation_metadata` before returning. Two input paths:

One operation failing to compile does not raise and does not lose its siblings'
already-compiled metadata, and it is **not dropped either**. `"operations"` lists
exactly the operations that compiled *whole* (their entries are unchanged, so
every runtime/campaign consumer can trust them); an operation that could not be
compiled is recorded in `"unrepresentable_operations"`:

```python
{
  "name": "gemm", "reason": "<first defect, exactly as the old exception text>",   # legacy keys
  "operation_name": "gemm",
  "reason_code": "ambiguous_transport_binding",   # primary defect, decided at its raise site
  "category": "contract_error",                   # contract_error | extension_required | tool_capability
  "owner": "architect_contract",                  # architect_contract | verifier_extension | verifier_tool
  "affected_domains": ["operation_io"],           # subset of operation_io | arithmetic | lifecycle
  "affected_feature_ids": ["lifecycle.gemm.busy_tracks_active_job", "operation.gemm.accumulation", ...],
  "blocked_by": ["gemm:ambiguous_transport_binding"],   # stable "<operation>:<reason_code>" keys
  "message": "...", "resolution_hint": "...",
  "diagnostics": [ {operation_name, reason_code, category, owner, affected_domains,
                    message, resolution_hint, details, blocked_by}, ... ],   # EVERY defect found
  "shell": {"operation_name", "family", "dimensions", "inputs", "outputs", "lifecycle",
            "arithmetic", "fragments": {"operation_io": ..., "lifecycle": ..., "arithmetic": ...}},
}
```

The operation is compiled as **independent fragments** — each input/output
binding, the lifecycle binding + policy, the standard-memory mappings, and the
arithmetic — so one failing fragment no longer hides the others: `diagnostics`
lists every defect the contract has (the first is what the old single exception
reported, in the same order, so `reason` is unchanged), and `shell` keeps
whatever did compile (`fragments` says `compiled` / `partial` / `failed` per
domain; an object that failed to bind is an `{"bound": false}` placeholder).
An interface-level defect that the standard-protocol plan rejects (for example an
incomplete AXI channel set) still surfaces as a `ValueError` when nothing else failed,
exactly as before; once an operation has recorded a failure, a later stage's
unexpected error is never allowed to turn that recorded failure into a raise (the
sequential compile never reached those stages, and a differential test against a
reimplementation of it pins the equivalence).
The shell exists for **planning only**: `build_lifecycle_feature_plan` reads it
to keep the operation's contract-required lifecycle obligations alive (see
[`../feature_plans/README.md`](../feature_plans/README.md)); it is never placed
in `operations`, so no driver, checker or campaign ever sees a half-compiled
operation. For a fully compiled contract the returned dict is byte-identical to
before (`unrepresentable_operations` is `[]`).

Category and reason code are attached **where the defect is detected** (an
exception carries `reason_code`; nothing parses a message), and the vocabulary
lives in [`../diagnostics.py`](../diagnostics.py):

- `contract_error` — the frozen contract is inconsistent; only the Architect can fix
  it. Examples: the same data object on two same-direction channels
  (`ambiguous_transport_binding`), an object only on the opposite-direction channel
  (`data_object_channel_direction_mismatch`), a second `valid`/`ready`/`payload` on
  a data channel (`ambiguous_channel_signal_role`), a `ready_valid` channel missing
  one of those roles (`missing_ready_valid_signal_roles`), a `control_plane_sequence`
  policy with no declaration or a declaration nothing selects, an invalid
  declaration, or a declaration with no AXI4-Lite subordinate group to drive it.
- `tool_capability` — the contract is valid but the tool has no automatic path:
  an operation that consumes/produces an **internal** (non-external) data object
  (`internal_data_object_not_channel_bound`; real Architect runs produce staged
  designs like this) or a repeated sideband role on a data channel
  (`multi_signal_role_on_data_channel`). Never an Architect error.
- `extension_required` — behavior the closed pools do not cover that a
  Verifier-authored extension must supply. No compile diagnostic uses it today
  (extension-backed behavior compiles fine and is tracked through
  `lifecycle_extension_fields` / `llm_extension`); the category and its
  `verifier_extension_required` automation status exist for feature-level records.

Only reason codes flagged `architect_blocking` (`ARCHITECT_BLOCKING_REASON_CODES`)
are ever sent back to the Architect, and only when no earlier validator already
reports the same defect (missing/invalid `lifecycle_policy` and `arithmetic`, unknown
objects/types and serialization stay with `validate_architecture_*` and their
`require_*` tolerance). `validate_operation_compilation(architecture, interface)`
returns those messages (`operation 'x' [reason_code]: message -- hint`);
`ArchitectAgent._validate_contract_references` calls it, and
`review_contract_deterministically` builds the metadata once and applies the same
`blocking_compilation_errors` split, so a defect the compile used to swallow is now
rejected once, precisely, before any Verifier work.
`blocking_compilation_errors(metadata)` / `compilation_capability_notes(metadata)`
split an already-built result the same way.

This is strictly worse than `automatic_campaign_support` marking an operation
unsupported (that still needs valid metadata to run its checks against): an
unrepresentable operation has none, so it cannot even get
`_run_arithmetic_blocked_operation_smoke`'s protocol/lifecycle traffic. It needs
Verifier-authored evidence, an Architect correction (`contract_error`), or
`verifier_tool` support (`tool_capability`) — never the Verifier LLM inventing a
lifecycle policy of its own (see the lifecycle policy pool README for why that
vocabulary is deliberately closed).

- **Compact declaration** (the normal path): resolves each input/output data
  object into a full binding via the internal `_binding(...)` helper — exactly
  one channel of the right direction must carry that data object
  (a diagnostic if zero or more than one; `_channel_count_error` classifies it:
  several channels = `ambiguous_transport_binding`; only an opposite-direction
  carrier = `data_object_channel_direction_mismatch`; no carrier = a contract
  error for an external object but a `tool_capability` limit for an internal one),
  then reads every signal attached to that channel into a `{role: signal_name}`
  map, requiring `valid`/`ready`/`payload` for a `ready_valid` channel. It calls
  `compile_operation_arithmetic` (from `arithmetic_metadata.py`) for the
  arithmetic, `_bind_lifecycle_metadata` + `_attach_lifecycle_policy` for
  lifecycle, and `_attach_standard_memory_mappings` to detect and bind AXI4-
  Lite memory-mapped I/O.
- **Full external `verification_metadata`**: an operation may instead supply
  a complete `operation.verification_metadata` object directly (mutually
  exclusive with `operation.arithmetic` — declaring both is an error). This
  path skips re-deriving bindings from the architecture/interface contracts
  and only attaches/validates the lifecycle policy, then runs the same
  `validate_architect_operation_metadata`. This is the "full external input
  form" the top-level README refers to.

Key internal mechanics worth knowing before touching this file:

- `_bind_lifecycle_metadata(interface)` finds command channels by looking for
  a `payload` signal whose `semantic_class == "command"`, then requires that
  channel to have exactly one `valid`/`ready`/`payload` each. Legal command
  values are parsed **only** from explicit `legal only <literal>` /
  `legal values are <literal>` / `legality is exactly: ... == <literal>`
  clauses in the signal's `semantic` text via `_legal_command_values` — this
  is prose-*parsing* of an explicit machine-oriented clause, not natural-
  language inference; anything not matching one of those three regexes
  contributes no legal values, and `legality_resolution` is reported as
  `"metadata_missing"` rather than silently treating "no clause matched" as
  "no legal values."
- Command **metadata fields** (the fields alongside payload on a command
  channel) can carry base-pointer tags via `_explicit_semantic_tags`:
  `data_object=`, `address_role=`, `byte_order=`, `address_sequence=`,
  `word_stride_bytes=` — the exact same `key=value` tag convention
  `role_pool/standard_protocols.py` uses for protocol fields, just a different
  tag vocabulary, both parsed with the same "explicit tag or nothing" policy.
- `_attach_standard_memory_mappings(bindings, lifecycle, interface)` handles
  an operation whose data-object binding is `axi4_lite`, `axi4`, or
  `custom_mmio` and which has either exactly one command channel or **no**
  command channel. With one command channel the pointer metadata comes from
  that command's metadata fields; with none, it is synthesized from
  `lifecycle.control_plane_sequence.job_start.actions[].value_from`
  (`_control_plane_sequence_pointer_fields`: `byte_order: little`,
  `address_sequence: contiguous`, `word_stride_bytes` left to be filled from
  the bus width). With more than one command channel nothing is attached. It
  requires exactly one pointer tagged
  `address_role=base` for that data object, requires `byte_order`/
  `address_sequence` to be present (and `word_stride_bytes`, unless it is
  derived from the bus width as above), resolves the
  matching address/data/response channels from
  `role_pool.standard_protocols.compile_standard_protocol_plan`, checks the
  data channel `kind` matches the binding's direction (AXI
  `read_data`↔input / `write_data`↔output, or the corresponding custom-MMIO
  request/data group), and requires the bus data width to
  be an exact multiple of the element width before attaching
  `binding["memory_mapping"]` (`elements_per_word`, `word_stride_bytes`,
  `bus_width_bits`, `address_channel`, `data_channel`, `response_channel`,
  `protocol_capabilities`, and the group's machine-readable `protocol_fields`
  by channel kind). `elements_per_word` is `bus_width // element_width` for
  `dense_tensor`/`scalar` objects, but for a `packed_encoding` object it is
  `packed_encoding.group_size * traversal.containers_per_word` (the
  declaration's own answer to how many logical elements one physical word
  carries — e.g. 32 for a 512-bit word whose sixteen 32-bit containers each
  hold two INT8 fields, not the naive 64). `word_stride_bytes` defaults to one
  full bus word (`bus_width // 8`) when the pointer does not supply it. The AXI4 automatic
  campaign uses these resolved fields to require AWID/ARID/BID/RID before it
  selects the ID-correlated driver; a full-AXI4 contract without them can
  still be structurally legal but needs a different Verifier adapter. Any of those
  checks failing just means memory mapping isn't attached (not an error) —
  *except* a duplicate `address_role=base` tag on the same object
  (`ambiguous_base_pointer`) and an object bound to the wrong kind of memory
  channel (`memory_channel_kind_mismatch`), both Architect-blocking diagnostics.
- `render_architect_metadata_format() -> str` is what actually appears in the
  Architect prompt: the static `architect_metadata_format.yaml` text plus the
  rendered lifecycle policy pool (`lifecycle_policies.yaml` text, which lists
  the `control_plane_sequence` / `observed_via_poll` choices), arithmetic schema,
  and serialization schema (which includes `packed_encoding`) appended live, so
  the prompt reflects the current enums even though the static YAML's own
  serialization/lifecycle prose has not been updated for those kinds. The
  `control_plane_sequence` declaration schema itself is **not** rendered into
  the prompt. The prompt always reflects the current schema even if this
  YAML file goes stale. See
  `multigent/agents/architect.py::_build_architecture_task`'s
  `VERIFIER_TOOL ARCHITECT METADATA FORMAT` section, and
  [`../../ARCHITECT_INTEGRATION.md`](../../ARCHITECT_INTEGRATION.md) for what the
  Architect must be required to emit.
- `validate_architect_operation_metadata(metadata)` is the structural gate:
  required top-level keys, `schema_version == 2`, a valid lifecycle policy
  (delegates to `lifecycle_policy_pool.resolve_lifecycle_policy`), every
  input/output binding has all nine required keys and a valid
  `serialization`, arithmetic has a `classifier_profile`, and — specifically
  for `integer_matrix_multiply` — ten additional exact fields must be present
  (`accumulator_data_type`, `product_data_type`, `accumulator_initialization`,
  `reduction_order`, `reduction_conversion`, `bias_conversion`,
  `result_data_type`, `stage_order`, `resolved_stage_order`, `support_status`).

## `arithmetic_metadata.py` — the arithmetic sub-schema and compiler

This is where the *compact* declaration Architect writes under
`operations[].arithmetic` gets validated against
`arithmetic_metadata.schema.json` and turned into the *canonical* arithmetic
metadata `architect_metadata.py` embeds.

- `operation_arithmetic_schema()` / `with_operation_arithmetic_schema(schema,
  *, required=True)` — the latter is what `ArchitectAgent.load_output_schema`
  calls (chained with `with_lifecycle_policy_schema`) to compose the *effective*
  Architect response schema actually sent to the model: it injects the
  arithmetic schema at
  `architecture_contract.operations.items.properties.arithmetic` and the
  serialization schema at
  `architecture_contract.data_objects.items.properties.serialization`, adding
  both to `required` unless `required=False` (used for a **revision** schema
  that must still accept old contracts predating this field, per
  `architect.py::load_output_schema`'s call site — check that call site before
  assuming this is always `True`).
- `compile_operation_arithmetic(operation, architecture) -> dict` — the actual
  compiler. `operation["arithmetic"]` is JSON-schema-validated against the full
  `anyOf` schema first; on failure it re-validates against just the matching
  `classifier_profile` branch so the error message is the specific branch's
  complaint, not an unreadable `anyOf` dump. Two branches:
  - `classifier_profile == "llm_extension"`: requires non-empty
    `operation["semantics"]`, and returns a metadata object with
    `support_status: "llm_extension_required"` and empty
    accumulator/reduction/post-op fields — this is a capability report, not
    executable arithmetic, and callers must check `support_status` before
    assuming the code-owned campaign or oracle can run. New contracts should
    also provide the optional `extension_request` field. The extension boundary
    validates that it names an operation-domain request targeting this exact
    operation, so unsupported arithmetic is traceable without disabling known
    protocol/lifecycle behavior. The field remains optional only for older
    coarse `llm_extension` contracts.
  - `classifier_profile == "integer_sparse_attention"`: requires
    `coverage_family == "sparse_attention"`, fixed rank-2 objects with roles
    `query_matrix`, `key_matrix`, `value_matrix`, `attention_mask`, and
    `attention_result`, and shape agreement `Q[Q,D]`, `K[S,D]`, `V[S,DV]`,
    `mask[Q,S]`, `Y[Q,DV]`. The mask is unsigned one-bit `binary_keep`, and
    scaling and normalization are explicitly `none`. The compiler validates exact Q×K and
    score×V product types, both declared reduction axes/conversions, and the
    result conversion. It returns
    `support_status: "supported_composed_restricted_integer_sparse_attention"`
    plus a machine-readable QK/scale/mask/normalization/value composition. This is
    deliberately not a claim of softmax, score scaling, top-k, or approximate
    attention support.
  - `classifier_profile == "fixed_point_attention_scale"`: requires
    `coverage_family == "attention_scale"`, one signed rank-2
    `attention_score_matrix` input, and one matching
    `scaled_attention_score_matrix` output. `head_dimension` must resolve to a
    positive fixed D, and `scale_multiplier` must equal the exact
    `round(2^scale_shift/sqrt(D))` derivation. The compiler proves the declared
    signed product type covers every score×multiplier product and records the
    exact stage order: signed decode, exact multiply, arithmetic-floor shift,
    result conversion. This is scaling only; mask, softmax, and V are separate.
  - `classifier_profile == "integer_matrix_multiply"`: requires
    `coverage_family == "matrix_multiply"`; resolves `left_operand_matrix` /
    `right_operand_matrix` / `result_matrix` object roles and checks
    `A[M,K] · B[K,N] = Y[M,N]` shape agreement; requires every M/K/N dimension
    to be fixed (either literally `minimum==maximum`, or resolvable through
    exactly one `bound_parameter`'s integer `default_value` — a
    `runtime_configurable` dimension is rejected outright, since this profile
    assumes a fixed elaborated shape); requires `product_data_type` to
    losslessly represent *every* possible `A*B` product given the two operand
    types' bit ranges; resolves `post_operations` — a **DAG of named stages,
    not a fixed-order list** — by calling `_resolve_post_operation_order`,
    which walks each stage's `depends_on` reference back from `post_output`
    to the literal `"accumulator"` sentinel, rejecting cycles, dangling
    references, and any declared stage left unreferenced by that chain; at
    most one `bias_add`, one `wrap`, one `relu`, and one
    `affine_quantize` may appear, **in any
    order the `depends_on` edges express** — cross-checks that a declared
    `bias`/`activation`/`quantization` *feature* exists if and only if the
    matching `bias_add`/`relu`/`affine_quantize` stage exists; and requires every input/output object to
    be "modeled" (referenced by the left/right/bias/output roles) or the
    whole operation must use `llm_extension`. The returned dict adds
    `integer_evaluation: "unbounded_between_explicit_conversions"`, fully
    resolved `accumulator_type`/`product_data_type`/`result_data_type`
    objects, `resolved_stage_order` (the stage *names* in dependency order,
    e.g. `["bias", "wrapped", "activated"]` for a bias→wrap→relu chain —
    every other consumer of a compiled operation, `canonical.py` and
    `operation/stimulus/stimulus_generator.py` included, walks stages via
    this field rather than recomputing the DAG), a `stage_order` list of
    internal execution-stage *labels* built from that same order (e.g.
    `["operand_decode", "exact_product",
    "ordered_reduction_with_explicit_conversion", "bias_add_with_explicit_conversion",
    "wrap_accumulator", "relu_threshold_zero",
    "per_tensor_affine_quantize_nearest_even_saturate", "result_conversion"]` when all
    three optional stages are present, in whatever order they were declared),
    and `support_status: "supported_restricted_integer_gemm"`.
- `validate_resolved_arithmetic(metadata)` — re-derives a *synthetic* compact
  declaration + minimal architecture from an already-canonical
  `arithmetic`/`inputs`/`outputs`/`dimensions` blob (used for the **full
  external `verification_metadata`** input path, where there is no original
  compact declaration to re-validate against) and calls
  `compile_operation_arithmetic` on that synthetic input, then asserts the
  recomputed `stage_order`/`resolved_stage_order`/`integer_evaluation`/
  `support_status`/`metadata_origin` agree with what was supplied. This
  guarantees the "full metadata" input path cannot smuggle in numerically
  different behavior than the compact-declaration path would have produced
  for equivalent facts — it is not a separate, weaker validation path.
- `validate_architecture_operation_arithmetic(architecture, *,
  require_arithmetic=True, previous_architecture=None) -> list[str]` — the
  reference-check-style function `ArchitectAgent._validate_contract_references`
  calls; also forbids a **revision** from deleting a previously-declared
  `arithmetic` field even when `require_arithmetic=False` (checked via
  `previous_architecture`), matching the top-level README's "explicit
  selections... cannot be removed to fall back to legacy defaults" rule
  applied to arithmetic specifically.

### Example compact declaration

For declared `s8`/`s16`/`s32` types and `A[M,K]`, `B[K,N]`, `bias[N]`, `Y[M,N]`
objects:

```yaml
arithmetic:
  classifier_profile: integer_matrix_multiply
  product_data_type: s16
  accumulator_data_type: s32
  accumulator_initialization: 0
  reduction_dimensions: [K]
  reduction_order: increasing_declared_reduction_coordinate
  reduction_conversion: wrap_twos_complement_after_each_add
  post_operations:
    bias: {kind: bias_add, depends_on: [accumulator], data_object: bias, broadcast_dimensions: [N]}
    activated: {kind: relu, depends_on: [bias]}
  post_output: activated
  bias_conversion: wrap_twos_complement_after_add
  result_data_type: s32
  result_conversion: wrap_twos_complement
```

`post_operations` is a **DAG, not a fixed-order array**: each stage is a named
entry keyed by an Architect-chosen stage name, and names its own predecessor
via `depends_on` — either the literal string `"accumulator"` or another
stage's key. Execution order is derived by following `depends_on` back from
`post_output`, not by dict-declaration order. Because every currently
supported stage kind (`bias_add`, `wrap`, `relu`, `affine_quantize`) is unary, a valid graph is
always a simple chain, but that chain may run in **any** order the Architect
declares — `wrap` before `bias_add`, `relu` before `wrap`, or any other
combination — not only the `bias_add → wrap → relu` order shown above. For
example, declaring the two stages above in the opposite dependency direction
(`bias: {..., depends_on: [activated]}`, `activated: {kind: relu,
depends_on: [accumulator]}`, `post_output: bias`) compiles to `relu` running
*before* `bias_add`, and `evaluate_canonical_operation` will compute a
correspondingly different numeric result — the declared graph is genuinely
authoritative, not decoration on top of a hardcoded order.

No selected post-processing feature means `post_operations: {}` and
`post_output: accumulator` (no corresponding feature leaf, and
`bias_conversion: exact`). Declaring
`activation` never implies ReLU automatically — the post-operation stage is
the only thing that selects it. Unsupported math must say so honestly instead
of being coerced:

The built-in quantization feature is the common deterministic hardware form of
per-tensor affine requantization:

```text
q = clamp(round_to_nearest_even(value * scale_multiplier / 2^scale_shift)
          + zero_point, dtype_min, dtype_max)
```

It is declared as `kind: affine_quantize` with explicit `scale_multiplier`,
`scale_shift`, `zero_point`, output `data_type`,
`rounding: nearest_ties_to_even`, `saturation: clamp`, and
`granularity: per_tensor`. Per-axis, stochastic, floating-scale, and other
quantizers remain contract-local extensions rather than being silently treated as
this profile.

```yaml
arithmetic:
  classifier_profile: llm_extension
  reason: This operation uses GELU, which the integer GEMM backend does not implement.
  extension_request: operation.gelu_arithmetic
semantics: <exact equation, types, rounding, overflow, stages, and input/output meaning>
```

### `llm_defined` post-op stages — a new stage kind without `llm_extension`'s all-or-nothing cost

`classifier_profile: llm_extension` above blocks **the entire operation**:
`stimulus_generator.py::_gemm_model` raises `unsupported_known_feature` for
*every* concept the moment `post_operations` contains a `kind` it does not
recognize, even a concept like `accumulation` that never looks past the
reduction step — because `_case()` always needs a correct **end-to-end**
golden value (through every post-op) to check any generated stimulus
against, regardless of which concept it targets, and an unrecognized stage
anywhere in the chain makes that end-to-end value uncomputable.

If the new post-op is expressible as a small arithmetic formula, declare it
as `kind: llm_defined` instead of reaching for `llm_extension`:

```yaml
post_operations:
  bias: {kind: bias_add, depends_on: [accumulator], data_object: bias, broadcast_dimensions: [N]}
  activated: {kind: relu, depends_on: [bias]}
  clipped: {kind: llm_defined, depends_on: [activated], formula: "clip(value, 0, 100)"}
post_output: clipped
```

`formula.py` attempts to compile `formula` into an integer Z3 expression. The
contract schema deliberately does not publish a fixed list of accepted
operators. The Contract Reviewer runs the compiler: a successful compilation
becomes the single semantic source for symbolic solving and concrete golden
evaluation; a failed compilation is returned to the Architect for revision.
The compiler translates syntax node by node and never uses `eval` or `exec`.
If the Architect determines that the behavior cannot be represented by this
solver-backed scalar model, it explicitly selects `classifier_profile:
llm_extension` and links an operation-domain extension request.

`canonical.py::integer_matrix_multiply_events` evaluates the compiled formula
inside the golden-model walk, so once the formula compiles,
`accumulation`/`bias`/`activation`/`dimensions`/`operand_values` — none of
which have anything to do with the new stage — go back to being fully
automatic, exactly as if the stage were
`bias_add`/`wrap`/`relu`/`affine_quantize`. Unlike those built-in stages (each
singular by construction), a contract may declare several
distinct `llm_defined` stages chained together; they are disambiguated by
stage name and formula, not by `kind`.

The Architect declares only the formula and its DAG dependency here. It does
not declare coverage bins. After successful compilation, the Verifier owns the
feature's bins and predicates and may use the compiled formula for targeted
stimulus. Full `llm_extension` remains the explicit path for behavior that the
compiler cannot represent, such as stateful, temporal, or externally defined
semantics.

## `io_metadata.py` — explicit serialization, never inferred from shape

- `serialization_schema()` — the JSON Schema for
  `data_objects[].serialization`: `kind` (`dense_tensor`/`scalar`/
  `llm_extension`/`packed_encoding`), `index_order` (outermost→innermost axis
  names), and a required free-text `description`. `derived_axes`, `traversal`,
  and `packed_encoding` blocks apply to `kind: packed_encoding` only (see the
  next section). For `kind: llm_extension`, new contracts
  should also provide optional `extension_request`; validation requires that ID
  to name an operation-domain request targeting the exact data object. It is
  rejected on supported serialization kinds. Omission remains accepted only
  for older coarse extension contracts.
- `declared_serialization(obj, *, dimension_extents=None, element_width_bits=None) -> dict` —
  validates one object's `serialization` against that schema, then
  semantically requires `scalar` ⟺ no dimensions and empty `index_order`, and
  `dense_tensor` ⟺ `index_order` is a permutation of exactly the object's
  declared `dimensions` (no missing axis, no duplicate, no invented axis). A
  `packed_encoding` declaration is instead validated by
  `packed_encoding.validate_packed_encoding_declaration`, which needs the
  object's resolved `dimension_extents` and `element_width_bits`; omitting them
  for that kind raises. Called from `architect_metadata.py::_binding`,
  `validate_architect_operation_metadata`, and
  `arithmetic_metadata.validate_architecture_operation_arithmetic`, each of
  which passes the computed extents/width.
- `require_supported_serialization(binding) -> None` — the *executable* wire-
  adapter guard: the automatic capture/drive path implements
  one-element-per-transfer, canonical-declared-order streams (i.e.
  `serialization.index_order == binding["dimensions"]` exactly) and the generic
  `packed_encoding` engine (which returns immediately here — its own validation
  already ran). A different declared order, or
  `serialization.kind == "llm_extension"`, is legal
  *metadata* but is explicitly rejected here — callers
  (`orchestration/campaign.py`, `pool/operation_metadata/protocol.py`) call this before
  trusting the automatic adapter, and its failure is a capability boundary
  (`llm_extension_required`-style), not a contract error.

## `packed_encoding.py` — several logical elements folded into one physical container

`dense_tensor` can only express "one element per `width`-bit lane, lanes in
order." `kind: packed_encoding` covers layouts where a container is narrower or
wider than that, holds padding, or is an arithmetic combination of more than
one logical element (e.g. the DSP48 SIMD trick some Vitis HLS INT8 GEMM kernels
use). Only the **encode** direction exists: a stimulus generator only ever
constructs the memory image an accelerator reads.

Declaration blocks (all in `serialization`; schema in `io_metadata.py`):

- `derived_axes[]` — `{real_axis, order, sub_axes[{name, extent}]}`: decomposes
  one declared dimension into an ordered (outermost→innermost) chain of
  pseudo-axes (mixed radix); the sub-axis extents must multiply to the real
  axis's fixed extent.
- `traversal` — `word_axes` (outermost→innermost, one iteration = one physical
  word), `containers_per_word`, `container_axis` (a non-null axis whose extent
  equals `containers_per_word` when it is > 1; must be null when it is 1), and
  `field_axis`.
- `packed_encoding` — `physical_container_width`, `used_width`,
  `used_bit_range` (must be exactly `[0, used_width - 1]`),
  `padding_value` (`zero`/`dont_care`), `container_bit_layout`
  (`contiguous_ascending` only), `group_size`, and `fields[]` of
  `{logical_offset, source_width, interpretation (signed|unsigned), shift}`.

The engine computes each container as
`P = (Σ extend(field_i) << shift_i) mod 2^used_width`, where `extend` is
two's-complement sign extension of `source_width` bits for a `signed` field or
a plain bit mask for an `unsigned` one (arbitrary-precision integers, so no
separate extend width is needed), and places container `c` of a word at bit
`c * physical_container_width`. Bits above `used_width` are always emitted as
zero (the `padding_value` enum is validated but does not change the encoder).

`validate_packed_encoding_declaration(...)` requires: fixed extents for every
dimension; sub-axis names that do not collide with existing axes and whose
extents multiply to the real axis; traversal axes that do not repeat, are all
known, and account for every dimension (a decomposed dimension must be fully
placed via its sub-axes); the `containers_per_word` / `container_axis` rule
above; `field_axis` extent == `group_size` == `len(fields)`; `logical_offset`s
exactly `0..group_size-1`; `0 < used_width <= physical_container_width`;
every field's `source_width` equal to the object's own element width; and
`unsigned` fields whose bit ranges do not overlap. Public functions:
`pack_words(declaration, dimensions, dimension_extents, values)`,
`packed_encoding_word_count`, `packed_encoding_word_bits`.

Where it is used (verified in code): the shared memory adapter
`protocol/stimulus/adapter/operation_memory_adapter.py::pack_words` dispatches
to this engine when a binding's serialization is `packed_encoding` (its
`unpack_words` raises for that kind, so a packed **output** cannot be read back
by the code-owned drivers); `ReadyValidCaptureAdapter._consume_memory_objects`
requires the *accepted* physical words of a packed input to equal
`pack_words(...)` of the planned canonical tensor before that tensor is used for
the golden calculation; and `architect_metadata.py` derives
`memory_mapping.elements_per_word` from `group_size * containers_per_word`. The
real worked example is `benchmark/int8_gemm_hls_golden/build_contract.py`
(A: one 512-bit container per word, 32 unsigned INT8 fields at `m*8`, upper 256
bits zero; B: `N` decomposed into `N_tile x N_lane x N_offset`, sixteen 32-bit
containers per word, each `(B[n1] << 18) + B[n0]` over signed fields, 27 bits
used; word index is `K*4 + N_tile`, 256 words). Unit tests:
`multigent/verifier_tool/tool_regression/unit/test_packed_encoding.py` (reference-encoder equality incl. the
sign-extension-carry edge case, and each rejection rule above). Do not confuse
this with `test_packed_memory_output.py`, which covers ordinary sub-word
`dense_tensor` outputs (several narrow elements per bus word).

## `canonical.py` — canonical jobs and GEMM classification

This is the only place that actually *evaluates* observed DUT behavior against
the compiled arithmetic metadata to produce semantic coverage classes. Its
`_classify_integer_matrix_multiply` and
`operation/stimulus/stimulus_generator.py`'s `evaluate_canonical_operation`
(which computes the *golden/expected* result for stimulus generation) both
call the same `integer_matrix_multiply_events` (below) rather than each
carrying its own copy of the product/reduction/DAG-walk arithmetic — so those
two can no longer silently disagree with each other. The remaining, still
load-bearing cross-check is DUT-vs-golden: the *observed* hardware output
compared against what `integer_matrix_multiply_events` says it should be, and
disagreeing there is exactly the kind of RTL-vs-golden discrepancy a failing
run surfaces; [`../../DEBUGGER_INTEGRATION.md`](../../DEBUGGER_INTEGRATION.md)
describes the evidence payload the tool can build for such a failure.

- `supported_code_owned_concepts(metadata) -> {operation_name: {concepts}}` —
  for every `integer_matrix_multiply` operation, always includes `dimensions`,
  `operand_values`, `accumulation`, plus `bias`/`activation`/`quantization` if
  the corresponding post-operation stage is present. For
  `integer_sparse_attention`, it includes `dimensions`, `operand_values`,
  `sparsity_patterns`, `attention_scores`, `stage_handoffs`, and `output_values`. Anything else the Architect
  declared as a feature is, by construction, **not** in this set — that
  difference (`declared - supported`) is exactly what
  `orchestration/campaign.py`'s `automatic_campaign_support` reports as
  `llm_extension_features`.
- `assemble_canonical_job(operation_metadata, stimulus, expected, observed) ->
  CanonicalOperationJob | None` — looks up each declared input's *accepted*
  stimulus value by exact `data_object` name, falling back to a small fixed
  alias table keyed by `object_role` (e.g. `left_operand_matrix` also accepts
  `"a"`/`"A"` — a compatibility shim for existing Verifier-authored test code,
  not a general name-guessing mechanism), flattens nested lists to a flat
  integer tuple via `_flatten` (raising `CanonicalOperationError` on any
  non-integer element), and checks the flattened length against the shape
  implied by `operation_metadata["dimensions"]`. Returns `None` (not an error)
  if *none* of the declared inputs were found in `stimulus` at all — that
  means this is a protocol-only transaction with nothing to classify, which is
  a normal, expected case, not a bug.
- `classify_operation_job(job)` / `classify_checked_operations(metadata,
  operations, stimulus, expected, observed)` — dispatches on
  `job.metadata["arithmetic"]["classifier_profile"]`; the code-owned
  classifiers are `_classify_integer_matrix_multiply` and
  `_classify_integer_sparse_attention`. Unsupported profiles return `{}`.
- `_classify_integer_matrix_multiply(job)` calls `integer_matrix_multiply_events`
  (this file) for the exact same product/reduction/bias/wrap/ReLU pipeline
  `arithmetic_metadata.py` validated the *shape* of — the same walk
  `operation/stimulus/stimulus_generator.py::evaluate_canonical_operation`
  calls for golden values, so classification evidence and the golden result
  come from one computation, not two independently-maintained copies — then
  classifies each intermediate: `accumulation` bins
  (`ordinary`/`positive_boundary`/`negative_boundary`/`positive_overflow`/
  `negative_overflow`, from `_reduction_trace`'s **mathematical** — i.e.
  unwrapped — prefix sums compared against the accumulator's representable
  range), `bias` values, and `activation` region
  (`negative`/`zero`/`positive`, from the pre-activation value's sign). It
  also returns a `numeric_stage_events` list with one entry per output
  coordinate carrying the full product terms, both mathematical and converted
  reduction-prefix traces, and every intermediate flag — this is the
  structured evidence a Debugger diagnosis or a coverage failure report can
  cite precisely (`coordinate`, `reduction_excursion`, `bias_excursion`, …)
  instead of a bare pass/fail.
- `_classify_integer_sparse_attention(job)` calls the shared
  `integer_sparse_attention_events` trace. It classifies mask rows as
  `empty_row`/`singleton_row`/`partial_row`/`dense_row`, active score signs,
  stage handoffs, and result signs while retaining score products, reduction
  prefixes, weighted terms, and output prefixes as debugger evidence. The
  trace calls the standalone QK evaluator and then composes scale, mask,
  normalization, and value stages; the same trace is used by the end-to-end
  sparse-attention golden evaluator.
- `canonical_bins_for_concept(operation_metadata, concept) -> list[dict] |
  None` — returns the **reachable** coverage bins for a supported
  supported concepts, computed from actual declared type bit-widths (e.g.
  `operand_values` only emits a `negative` bin if the operand type's range
  actually includes a negative value). This is what makes bins
  "mathematically impossible... exposed as unreachable... instead of being
  silently credited" (per the top-level README) — bin *existence* itself
  already accounts for the concrete metadata, rather than emitting a fixed
  bin list and hoping stimulus can hit it.

## `protocol.py` — `ReadyValidCaptureAdapter`

Not to be confused with `role_pool/standard_protocols.py` (which *compiles
field bindings*) or `feature_plans/protocol.py` (which *matches assertion/
coverage/stimulus features*) — this `protocol.py` *captures runtime values*.
It is instantiated once per cocotb test (see
[`../../orchestration/README.md`](../../orchestration/README.md) for exactly where) from the
interface contract, and on every sampled snapshot where a channel's bound
`valid` and `ready` are both true, records the decoded payload/field values.

- `__init__(interface)` builds `self.channels`: one entry per `ready_valid`-
  profile channel (from raw role bindings — `valid`, `ready`, at most one
  `payload`, plus `last`/`keep`/`strb`/`transaction_id`/`metadata` fields) and
  one entry per compiled standard-protocol channel (from
  `role_pool.standard_protocols.compile_standard_protocol_plan`, keyed by its
  `fields` mapping) — raising `ProtocolAdapterError` if a channel name were
  ever compiled by both paths (should be structurally impossible given
  `protocol_profile` is exclusive, but it's checked).
- `observe(snapshot, *, event_sequence=0, reset_epoch=0)` — for every channel
  whose `valid`+`ready` are both `1` in this snapshot, decodes every mapped
  field (`_decode` applies width masking and two's-complement sign extension
  from the signal's declared `width`/`signed`), appends the primary field's
  value to `self.values[channel]` (used by the simple ready/valid path), and
  appends a full event dict (all field values plus `signal_values`,
  `acceptance_event_sequence`, `reset_epoch`) to `self.events[channel]` (used
  by the memory-mapped path, which needs the full address/data/response
  correlation, not just a value list).
- `consume_operation_inputs(operation_metadata, planned_inputs=None)` /
  `consume_operation_outputs(operation_metadata)`
  — the two functions `canonical.py::assemble_canonical_job` ultimately
  receives data from. Each first calls `_validate_serialization` (i.e.
  `io_metadata.require_supported_serialization`) for every binding, then
  either delegates entirely to `_consume_memory_objects` (if any binding is
  `axi4_lite`, `axi4`, or `custom_mmio`) or reads straight from
  `self.values[channel]` for a plain ready/valid object. `planned_inputs` (the
  TB's planned canonical tensors) is used only to verify `packed_encoding`
  inputs, below.
- `_consume_memory_objects(operation, direction, planned_inputs=None)` splits
  bindings by `protocol_profile` and dispatches each group to its own
  algorithm — AXI4-
  Lite needs a genuinely different reconstruction strategy from the other
  two, not just different field names. Two additions specific to register-
  started (`control_plane_sequence`) jobs and packed inputs:
  - **Base pointers from accepted register writes.** When
    `lifecycle.policy.job_acceptance == "control_plane_sequence"` there is no
    command event to read a base pointer from, so
    `_control_plane_object_bases` recovers each object's base address from the
    *accepted* AXI4-Lite AW/W/B transactions of the declared `job_start` action
    list: exactly one AXI4-Lite subordinate group must exist; the accepted
    AW/W/B counts must each equal the number of declared start actions; each AW
    address must equal the declared register address; each B must be OKAY; a
    `write_field` start bit must have been accepted with the declared value;
    every pointer needs both a `low` and a `high` half; the base is
    `low | (high << 32)`. Planned values are never used.
  - **Per-bus grouping.** AXI4/custom_mmio bindings are grouped by their
    (address, data, response) channel triple and each group is reassembled
    independently, because one operation may use several independent AXI4
    manager ports (the HLS GEMM has separate `gmem_a` and `gmem_b` reads).
  - **Packed inputs.** For an input with `serialization.kind ==
    "packed_encoding"`, the AXI4 path returns the accepted physical words, which
    must equal `packed_encoding.pack_words(...)` of the planned canonical
    tensor; otherwise `ProtocolAdapterError`. The planned tensor is then what
    flows into golden evaluation, so a planned-but-not-accepted tensor cannot
    earn correctness or coverage credit.
  - `_consume_axi4_lite_objects` — AXI4-Lite has no ID and no burst `LAST`,
    so this reconstructs the **expected** address sequence purely from the
    accepted command's base-pointer value (captured off the *command*
    channel's event) and the binding's `word_stride_bytes`/`elements_per_word`,
    then asserts the **observed** address-channel events match that sequence
    **exactly, in that order** (`ProtocolAdapterError` if not — this is what
    proves the RTL issued the addresses the metadata promised, rather than
    merely "some addresses"). This only works because AXI4-Lite is
    single-outstanding by construction: request order and response order are
    the same thing.
  - `_consume_burst_memory_objects` — shared by full AXI4 (`axi4`) and any
    LLM-declared custom memory-like protocol (`custom_mmio`, see below).
    Full AXI4 permits several simultaneously outstanding requests whose
    responses may complete in a **different order** than they were issued,
    and same-ID requests are only guaranteed in-order *relative to each
    other* (not relative to other IDs). Read data is paired by RID with the
    oldest matching AR request. AXI4 write data has no WID, so accepted W
    bursts pair with AW requests in issue order; each B response is then
    matched to its AW request by BID. The adapter uses the paired request's
    captured address, never response position, to attribute the burst to a
    bound data object's `[base, base+word_count*stride)` window. For AXI4,
    `_decode_axi4_bursts` resolves actual per-beat addresses and AxSIZE-selected
    byte lanes, then rejects duplicated or missing object bytes before
    reconstructing canonical words. This works for aligned byte/halfword/full
    transfers and aligned FIXED/INCR/WRAP bursts. Custom-MMIO retains the
    next-expected-word sequence check. A custom-MMIO
    data channel that declares its own ID retains the per-ID matching path.
    The response-channel queue must yield one `OKAY` response per
    completed write burst before its write-strobe is checked — *unless*
    the binding's `memory_mapping.response_channel` is `None` (only possible
    for `custom_mmio`, see below), in which case acceptance onto the data
    channel itself, plus that beat's own optional `resp` field, is the
    completion signal.
  Both paths funnel into the same `_decode_words`, which unpacks multiple
  elements per bus word using declared `elements_per_word`, `width_bits`, and
  `signed`, truncating to the binding's expected element count.

  **Update**: driving BFMs now exist for both full AXI4 and `custom_mmio` —
  `protocol/stimulus/drivers/axi4_outstanding.py::execute_axi4_memory_job`,
  built on the `cocotbext-axi` dependency's low-level channel primitives plus
  a seeded-random completion scheduler
  (`protocol/stimulus/drivers/_completion_scheduler.py::RandomCompletionScheduler`), proven
  against a real Verilator simulation in
  `multigent/verifier_tool/tool_regression/rtl/test_axi4_outstanding_drive.py` (a request issued second
  is driven to complete *before* one issued first, deterministically from a
  fixed seed). `orchestration/campaign.py::automatic_campaign_support` now
  reports `axi4` bindings as automatable only when the required
  `protocol_capabilities` and physical AWID/ARID/BID/RID fields are bound.
  `_run_axi4_operation_campaign` drives every generated case through it for
  a single shared AXI4 manager group with a ready/valid command, and
  `_run_axi4_control_plane_operation_campaign` does the same for
  register-started (`control_plane_sequence`) jobs over several independent
  AXI4 manager groups. See
  [`protocol/stimulus/README.md`](../../protocol/stimulus/README.md) for the
  exact mechanism, including legal unaligned INCR starts and byte-lane
  reconstruction. Coverage/qualification status is tracked in the executable
  [`../../tool_regression/qualification/ledger.json`](../../tool_regression/qualification/ledger.json):
  an entry is only
  strictly qualified when a frozen-contract/generated-TB mutant fails for the
  intended reason and the corrected RTL passes every required bin; earlier
  smoke-level runs are not counted, and rows are marked one at a time (see the
  matrices for the current state).
  `custom_mmio` bindings are automatable too — see
  the section immediately below for the exact reusable-`RandomCompletionScheduler`
  mechanism and where `orchestration/campaign.py` drives it.

### `custom_mmio` — the same engine for a non-AXI custom protocol

An Architect describing a genuinely custom protocol is not limited to the
opaque `custom` profile (which gets no field-level binding at all, only
generic handshake/stall coverage). If that custom protocol is *structurally
memory-like* — an address-bearing request accepted on one ready/valid
channel, completed by a data-bearing response accepted on another — it can
declare `protocol_profile: custom_mmio` on those channels and reuse the
exact same `protocol_group=`/`protocol_channel=`/`protocol_field=` tag
vocabulary as `axi4`/`axi4_lite` (`role_pool/standard_protocols.yaml`), with
only three generic channel kinds instead of AXI4's five:

| kind | required fields | optional fields |
|---|---|---|
| `request` | `addr` | `id` |
| `data` | `data` | `id`, `last`, `resp`, `strb` |
| `response` | `resp` | `id` |

A group is one direction only (a `request`+`data` pair) — unlike AXI4, a
`custom_mmio` group has no distinct kind names for read vs. write, so a
design wanting both directions on what is conceptually "one port" declares
two `custom_mmio` groups (see `multigent/verifier_tool/tool_regression/unit/test_custom_mmio_protocol.py`
for a worked example using channel/signal names — `req_out`, `dat_in`,
`wreq_out`, `wdat_out`, `ack_in` — that look nothing like AXI, proving the
binding is matched purely by tag, never by spelling). The `response` channel
is **optional on writes**: a custom protocol that signals write completion by
simply accepting onto the `data` channel (no separate ack channel at all)
declares no `response` kind, and `_attach_standard_memory_mappings` records
`memory_mapping["response_channel"] = None`, which `_consume_burst_memory_objects`
treats as described above. For reads, completion is always the `data`
channel itself (there is nothing to declare — same as AXI4's `RDATA` being
its own read response).

Everything downstream of the tag vocabulary is reused unmodified:
`_attach_standard_memory_mappings` (`architect_metadata.py`) recognizes the
pattern the same way it recognizes AXI4/AXI4-Lite; `automatic_campaign_support`
(`orchestration/campaign.py`) reports it executable once `memory_mapping` is
resolved on every bound object — unlike `axi4`/`axi4_lite`, it does not also
require `protocol_capabilities` (`max_outstanding`, `address_bins`, …), since
custom_mmio's channel vocabulary has no AxPROT/WSTRB-style signals to bin that
coverage on. The actual drive is
`protocol/stimulus/drivers/custom_mmio.py::execute_custom_mmio_read_job`/
`execute_custom_mmio_write_job` — both directions, multi-beat reads via an
optional `len` field, reusing the protocol-neutral
`drivers/_completion_scheduler.py::RandomCompletionScheduler` and
`OperationMemoryAdapter` unmodified — orchestrated per job by
`orchestration/campaign.py::run_code_owned_custom_mmio_operation_case`
(resolves the read group from the operation's inputs and the write group from
its outputs, runs both concurrently). `protocol/coverage/plan.py` generates
the same generic `handshake_states`/`handshake_arrival_order`/`stall_stability`
coverage per channel plus the generic `address_alignment` partition on the
`addr` field (custom_mmio is deliberately excluded from the
STANDARD_PROFILES skip that suppresses that partition for AXI, since AXI has
richer dedicated address coverage of its own that `custom_mmio` does not).

## Who calls this pool

- **Architect** (`multigent/agents/architect.py`) renders
  `render_architect_metadata_format()` into its prompt and calls
  `with_operation_arithmetic_schema` (chained with
  `with_lifecycle_policy_schema`) to build its effective response schema; its
  reference validation calls `validate_architecture_operation_arithmetic`.
- **`orchestration/instrumentation.py`**, **`orchestration/runtime.py`**,
  **`operation/coverage/plan.py`**, **`orchestration/campaign.py`**, and
  **`operation/stimulus/stimulus_generator.py`** all import from this package
  (via `multigent.verifier_tool.pool.operation_metadata`, or the relative
  `...operation_metadata` form from three levels down) to get
  `build_architect_operation_metadata`, `supported_code_owned_concepts`,
  `assemble_canonical_job`/`classify_checked_operations`,
  `ReadyValidCaptureAdapter`, and `require_supported_serialization`.
- See [`../../ARCHITECT_INTEGRATION.md`](../../ARCHITECT_INTEGRATION.md) for what
  a contract producer must be required to declare, and
  [`../../CONTRACT_REVIEWER_INTEGRATION.md`](../../CONTRACT_REVIEWER_INTEGRATION.md)
  for the deterministic contract-review surface
  (`review_contract_deterministically` builds this metadata, reports the
  Architect-blocking compile defects as `operation_compilation` findings, and lists
  every other diagnostic as a non-blocking `capability_notes` entry).

## Validation and integration notes

`with_operation_arithmetic_schema()` composes the arithmetic and
object-serialization fields into the effective Architect schema; initial and
revision validation reject missing declarations. There is no automatic
migration for old frozen contracts — a pre-existing contract missing
`arithmetic` or `serialization` must be revised explicitly, never defaulted.
Full external `verification_metadata` must be explicit and may not be supplied
alongside compact `arithmetic` on the same operation.

Test fixtures explicitly state their intended semantics; production code never
borrows fixture defaults. The test suite
(`multigent/verifier_tool/tool_regression/unit/test_operation_arithmetic_metadata.py`,
`test_canonical_operation.py`, `test_lifecycle_policy_pool.py`) covers missing
fields, invalid references, unsupported math, extension delegation,
serialization, accumulator/result width differences, conversion order, and
revision preservation — these are local unit tests, not evidence of a
successful live Architect/Verifier API trial.
