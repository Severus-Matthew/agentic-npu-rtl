# Lifecycle Domain

One of `verifier_tool`'s three verification domains (`protocol`, `lifecycle`,
`operation` — see [`../README.md`](../README.md) for the full architecture
narrative). This folder holds the **complete, independent implementation of
lifecycle-level verification** — job acceptance, busy/completion/error
behavior, reset disposition — split by verification type into its three
subfolders:

- [`assertion/`](assertion/README.md) — lifecycle temporal assertion catalog
  and runtime checkers, including the stateful AXI4-Lite tracker that turns
  register transactions into JOB_START / JOB_COMPLETE events.
- [`coverage/`](coverage/README.md) — lifecycle coverage plan/templates.
- [`stimulus/`](stimulus/README.md) — command-channel driving
  (`drive_accepted_command`), register-mapped job start/completion over an
  AXI4-Lite control bus (`drive_control_plane_sequence`, for operations whose
  lifecycle policy selects `control_plane_sequence`), and lifecycle scenario
  planning. Depends on
  [`../protocol/README.md`](../protocol/README.md)'s generic ready/valid
  primitives (`protocol/stimulus/cocotb.py`) to actually drive the command
  channel's wires — the one deliberate cross-domain dependency in this whole
  three-domain split, documented in `stimulus/README.md`.

None of the three subfolders here depends on either of the other two for
their *own* domain's logic — each independently consumes the Lifecycle
Feature Plan built by `build_lifecycle_feature_plan()` (see
[`../pool/feature_plans/README.md`](../pool/feature_plans/README.md)) and the
policy choices resolved by
[`../pool/lifecycle_policy_pool/README.md`](../pool/lifecycle_policy_pool/README.md).
