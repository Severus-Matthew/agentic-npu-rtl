# Role Pool

This is one of three Architect-facing metadata pools (the other two are
[`lifecycle_policy_pool/`](../lifecycle_policy_pool/README.md) and
[`operation_metadata/`](../operation_metadata/README.md)). A pool is a
closed, YAML-defined vocabulary plus a Python loader/validator/renderer; it turns
a small set of Architect-declared tags into an unambiguous, code-owned meaning
that `assertion/`, `coverage/`, and `stimulus/` can consume without ever parsing
a signal name or a prose description.

`role_pool` answers three independent questions about every interface signal and
channel, each governed by its own YAML file and Python module:

| Axis | YAML source of truth | Python module | Question it answers |
|---|---|---|---|
| Signal role | `interface_signal_roles.yaml` | `signal_roles.py` | What does this **signal** do (clock, reset, valid, ready, payload, busy, …)? |
| Semantic class | `interface_semantic_classes.yaml` | `interface_semantics.py` | What does a **payload/metadata** signal's value *mean* (data, command, address, opcode, configuration, …)? |
| Protocol profile | `interface_protocol_profiles.yaml` | `interface_semantics.py` | What handshake/bus discipline does a **channel** follow (`ready_valid`, `axi4`, `axi4_lite`, `axi4_stream`, `custom`, …)? |
| Standard protocol fields | `standard_protocols.yaml` | `standard_protocols.py` | For a channel using a **named standard** (AXI4/AXI4-Lite/AXI4-Stream), which exact wire is AWADDR, ARLEN, WSTRB, RRESP, …? |

None of these axes infer anything from a signal's spelling. The Architect must
tag every signal explicitly; an untagged or misspelled tag is a validation error,
never a fallback guess. A contract may carry one complete, contract-local role or
semantic-class candidate through `verification_extensions[].contract_vocabulary`.
That declaration is validated without modifying these global YAML pools.

## `signal_roles.py` — signal roles

`SIGNAL_ROLE_TAXONOMY_PATH` points at `interface_signal_roles.yaml`, whose
`roles` mapping is the single source of truth (roles seen today: `clock`,
`reset`, `clock_enable`, `valid`, `ready`, `payload`, `last`, `keep`,
`transaction_id`, `metadata`, `busy`, `completion`, `error`, and more — read the
YAML directly for the current, authoritative list since it evolves independently
of this prose). Each role entry declares:

- `channel_binding`: `required` / `optional` / `forbidden` — whether the role
  must, may, or must never be attached to a channel.
- `direction_relation`: `fixed`, `same_as_channel`, or `opposite_to_channel` —
  how the signal's `direction` must relate to its channel's declared direction
  (e.g. `ready` is always `opposite_to_channel`, `valid` is always
  `same_as_channel`).
- `allowed_directions`: the subset of `{input, output}` legal for this role,
  regardless of channel.
- `coverage_tags`: labels consumed by `coverage`/`assertion` domain code to find
  "every signal that matters for handshake coverage" etc., without hardcoding
  role names in every domain file.
- `interface_reference` (only on `clock`/`reset`): the exact top-level
  `interface_contract.clock` / `.reset` field must name a signal that actually
  carries this role.

Functions:

- `load_signal_role_taxonomy() -> dict` — parses and structurally validates the
  YAML (`lru_cache`d: loaded once per process). Raises `ValueError` for a
  malformed taxonomy file itself — this is a code-owned data file, not
  Architect input, so a validation failure here is a bug in `verifier_tool`,
  not in a contract.
- `render_signal_role_catalog() -> str` — renders the taxonomy as the
  `SIGNAL ROLE TAXONOMY` block embedded in the Architect prompt (see
  `multigent/agents/architect.py::_build_architecture_task`, and
  [`../../ARCHITECT_INTEGRATION.md`](../../ARCHITECT_INTEGRATION.md)).
- `signals_with_roles(signals, roles) -> set[str]` — exact-role signal-name
  filter; used by domain code that needs "the busy signal" or "all payload
  signals on this channel" without re-deriving the taxonomy.
- `signals_with_coverage_tags(signals, coverage_tags) -> set[str]` — same
  idea, indexed by `coverage_tags` instead of role name, so a new role that
  carries an existing tag (e.g. a second "handshake-like" role) is picked up by
  every consumer automatically.
- `validate_interface_signal_roles(interface, *, role_extensions=None) -> list[str]`
  — the deterministic
  gate called from `ArchitectAgent._validate_contract_references` (via the
  `multigent.verifier_tool` facade) on every Architect READY output, and also run
  by the contract preflight `review_contract_deterministically` (see
  [`../../CONTRACT_REVIEWER_INTEGRATION.md`](../../CONTRACT_REVIEWER_INTEGRATION.md)).
  It checks: unique signal names, known role, direction legality for that role,
  channel-binding legality (required/forbidden), the channel/role direction
  relation, and — for `reset` — that `semantic` declares exactly one of
  `active-high`/`active-low`. `role_extensions` contains only definitions already
  validated from the frozen contract-local extension requests. Returns a list of human-readable error strings
  (empty = valid); it never raises for a bad *contract* (only for a malformed
  *taxonomy file*, inside `load_signal_role_taxonomy`).

## `interface_semantics.py` — semantic classes and protocol profiles

Two independent taxonomies share this module because both describe "the
*meaning* layered on top of a role," as opposed to `signal_roles.py`'s "what a
signal *is* electrically."

- `load_interface_semantic_taxonomy()` loads `interface_semantic_classes.yaml`.
  Its `role_binding` section (`required`/`optional`/`forbidden`) partitions
  *every* signal role from `signal_roles.py` into exactly one of the three sets
  — this function raises if a new role is added to the role pool without also
  classifying it here, which is what keeps the two YAML files from drifting
  apart. Each semantic class (`data`, `command`, `configuration`, `opcode`,
  `address`, …) declares `allowed_roles` (must be a subset of the roles that
  are `required`/`optional` for a semantic class at all — i.e. `payload` and
  `metadata`) and `coverage_tags`.
- `load_interface_protocol_taxonomy()` loads `interface_protocol_profiles.yaml`
  — the currently selectable `channel.protocol_profile` values are `custom`,
  `ready_valid`, `axi4`, `axi4_lite`, `axi4_stream`, and `custom_mmio`.
  Profiles without a qualified tool-owned implementation are commented out
  in the YAML, so the Architect cannot select one as if it were supported.
  (see the YAML for exact
  `coverage_tags` per profile — this is what lets, for example,
  `feature_plans/protocol.py::build_protocol_feature_plan` decide "does this
  channel need a `stall_stability` feature" purely from
  `stall_match.coverage_tag in tags`, with zero knowledge of AXI vs.
  ready-valid vs. a fully custom profile).
- `render_interface_semantic_catalog() -> str` — renders both taxonomies for
  the Architect prompt (the `INTERFACE SEMANTICS AND PROTOCOL PROFILES` block in
  `architect.py::_build_architecture_task`).
- `validate_interface_semantics(interface, *, role_extensions=None,
  semantic_class_extensions=None) -> list[str]` — the other half of
  the Architect reference-validation gate (called alongside
  `validate_interface_signal_roles`): every channel's `protocol_profile` must
  be a known profile; every signal whose role is in `role_binding.required`
  must carry a `semantic_class`, every signal whose role is
  `role_binding.forbidden` must *not*; and a declared `semantic_class` must
  list this signal's role in its own `allowed_roles`. Contract-local definitions
  are merged only for this validation call; the cached built-in taxonomy remains
  unchanged.
- `derive_interface_coverage_seed(interface) -> dict` — combines role
  `coverage_tags` and semantic-class `coverage_tags` per signal, and profile
  `coverage_tags` per channel, into one `{"channels": {...}, "signals": {...}}`
  structure. This is the name-independent seed several coverage/assertion
  matchers use instead of re-reading all three taxonomies themselves.

## `standard_protocols.py` — exact AXI4 / AXI4-Lite / AXI4-Stream / custom-memory field binding

This is the largest and most load-bearing file in `role_pool` (~27 KB). The
Architect's current JSON-schema output has no native `protocol_group` /
`protocol_channel` / `protocol_field` properties yet (that schema merge is
future work — the docstring says so explicitly), so until then this module
reads those three keys as literal `key=value` tags smuggled into existing
`channel.metadata` / `signal.semantic` string fields:

```text
channel.metadata:    protocol_group=<value> protocol_channel=<write_address|write_data|write_response|read_address|read_data|stream|request|data|response>
signal.semantic:     protocol_field=<addr|len|size|burst|data|strb|last|id|dest|resp|lock|cache|prot|qos|region|user|keep>
channel.metadata:    protocol_capability.<key>=<value>     (sets use a|b|c, booleans true|false, else integer literal)
```

(`request`/`data`/`response` are `custom_mmio`'s three generic kinds; every
other kind listed belongs to `axi4`/`axi4_lite`/`axi4_stream`.)

- `load_standard_protocol_catalog()` loads `standard_protocols.yaml`, which
  defines, per profile (`axi4`, `axi4_lite`, `axi4_stream`, `custom_mmio`)
  and per channel kind (`write_address`, `write_data`, `write_response`,
  `read_address`, `read_data`, `stream`, or — for `custom_mmio` — the three
  generic kinds `request`/`data`/`response`), the `required_fields`/
  `optional_fields` and the applicable `rules`/`coverage` tags consumed later
  by `protocol/assertion/assertion_checkers.py`. `custom_mmio` exists so an
  LLM-declared protocol that isn't AXI at all, but is structurally
  memory-like, can reuse this exact same compiler and the multi-outstanding
  capture engine in `operation_metadata/protocol.py` — see
  [`../operation_metadata/README.md`](../operation_metadata/README.md#custom_mmio--the-same-engine-for-a-non-axi-custom-protocol).
  It must also be listed in `interface_protocol_profiles.yaml` (below) or
  basic interface validation rejects the profile before this compiler ever
  runs.
- `render_standard_protocol_metadata_format() -> str` — renders the exact tag
  format plus every profile's required/optional field list. The function is
  available through the facade, but the current Architect prompt does not call it
  directly; its surrounding prompt prose describes the native/tag fields instead.
- `enrich_standard_protocol_metadata(interface) -> dict` — parses the
  `key=value` tags out of `metadata`/`semantic` strings via the module-level
  `_TAG_VALUE`/`_CAPABILITY_TAG` regexes and promotes them onto
  `channel["protocol_group"]`, `channel["protocol_channel"]`,
  `channel["protocol_capabilities"]`, and `signal["protocol_field"]` on a
  **detached copy** of the interface. Raises `ValueError` if a native field and
  a tag both exist and disagree. Nearly everything downstream
  (`compile_standard_protocol_plan`, `operation_metadata.protocol.
  ReadyValidCaptureAdapter`, `operation_metadata.architect_metadata.
  _attach_standard_memory_mappings`) calls this first so the rest of the
  pipeline never has to know tags exist.
- `compile_standard_protocol_plan(interface, *, require_complete=True) -> dict`
  — the main compiler. Groups channels by `protocol_group`, checks the group is
  single-profile, binds each channel's `valid`/`ready`/named fields by walking
  every signal whose `channel` matches and whose `protocol_field` is legal for
  that channel kind, verifies AXI/AXI4-Lite `channel_sets` (e.g. a `write`
  capability needs `write_address`+`write_data`+`write_response` all present or
  all absent), infers `endpoint_role` (`manager`/`subordinate` for
  AXI/AXI4-Lite, `source`/`sink` for AXI4-Stream) from directions, validates
  widths (`_validate_widths`: data width is a power-of-two byte count 8–1024
  for AXI4/AXI4-Lite, `strb`/`keep` width matches data bytes, AXI4-Lite data
  width is exactly 32 or 64, fixed field widths like `resp`=2 bits/`last`=1 bit
  per `_FIXED_FIELD_WIDTHS`), and cross-checks AWID/BID, ARID/RID, and
  AWADDR/ARADDR width pairing for AXI4/AXI4-Lite. With
  `require_complete=True` (the default) it raises `ValueError` joining every
  collected error; with `False` it returns them in `result["errors"]` instead
  (used by `validate_standard_protocol_bindings`, which is the pure "give me
  errors, don't raise" form the Contract Reviewer preflight and tests call).
- The returned `groups[]` entries are what `role_pool`'s consumers actually
  read: each has `name`, `profile`, `endpoint_role`, `capabilities`, and
  `channels: {kind: {valid, ready, fields: {field: signal_name}, widths,
  effective_defaults, capabilities}}`. This exact shape is what
  `operation_metadata/protocol.py::ReadyValidCaptureAdapter.__init__` iterates
  to build its own per-channel capture table, and what
  `operation_metadata/architect_metadata.py::_attach_standard_memory_mappings`
  reads to compute a memory-mapped operation's address/data/response channel
  triple.

## Who calls this pool

- **Architect** (`multigent/agents/architect.py`): renders
  `render_signal_role_catalog()` and `render_interface_semantic_catalog()`
  straight into the prompt, and its `_validate_contract_references` calls
  `validate_interface_signal_roles` + `validate_interface_semantics` on every
  candidate READY output (required fields — a missing/invalid role or semantic
  class is `ContractValidationError`, not a warning). Before these calls it
  validates `verification_extensions[]` and extracts any contract-local role or
  semantic-class definitions passed to the two validators.
- **Feature planners** (`../feature_plans/README.md`): `feature_plans/common.py
  ::interface_parts` calls `compile_standard_protocol_plan` whenever a raw
  interface (not an already-compiled plan) is passed in; `feature_plans/
  protocol.py` reads `load_interface_protocol_taxonomy()` directly for
  `stall_stability` applicability.
- **`operation_metadata`** (`../operation_metadata/README.md`):
  `architect_metadata.py` and `protocol.py` both call
  `compile_standard_protocol_plan`/`enrich_standard_protocol_metadata` to bind
  memory-mapped I/O and to capture accepted AXI4-Lite, AXI4, and custom-MMIO
  transfers.
- **Contract preflight**
  ([`../../CONTRACT_REVIEWER_INTEGRATION.md`](../../CONTRACT_REVIEWER_INTEGRATION.md)):
  `review_contract_deterministically` runs `validate_interface_signal_roles`,
  `validate_interface_semantics`, and `validate_standard_protocol_bindings`
  among its checks (as `signal_roles`, `interface_semantics`, and
  `standard_protocol_bindings`).

## Extending the pool

Adding a role, semantic class, or protocol profile is a two-step YAML+cross-
reference change, not a one-line enum edit: a new signal role must also be
classified into exactly one of `interface_semantic_classes.yaml`'s
`role_binding` buckets (required/optional/forbidden) or
`load_interface_semantic_taxonomy()` raises at import time; a new standard
protocol profile needs both a `interface_protocol_profiles.yaml` entry (for
coverage tags) and, if it should get exact field binding like AXI, a
`standard_protocols.yaml` profile plus the corresponding runtime work in
`protocol/assertion/`, `protocol/coverage/`, and `protocol/stimulus/` — adding
the vocabulary here does not by itself implement checkers, samplers, or
drivers for it.

For one contract, do not edit this pool. Architect can use `custom` for a
contract-local protocol and declare its observable semantics in a
protocol-domain extension request. Verifier supplies that request's assertion,
coverage, and stimulus bundle. Reused role-based checks remain tool-owned.
The local definition is not promoted automatically. Future pool promotion can
consume the saved request/implementation manifest after independent
qualification, then uncomment the named profile once its implementation is
complete.
