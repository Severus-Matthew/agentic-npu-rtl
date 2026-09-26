# Protocol Domain

One of `verifier_tool`'s three verification domains (`protocol`, `lifecycle`,
`operation` — see [`../README.md`](../README.md) for the full architecture
narrative). This folder holds the **complete, independent implementation of
protocol-level verification** — generic ready/valid handshakes plus the
standard AXI4, AXI4-Lite, and AXI4-Stream profiles — split by verification
type into its three subfolders:

- [`assertion/`](assertion/README.md) — protocol-level runtime checkers
  (`check_axi4`/`check_axi4_lite`/`check_axi4_stream`, stall stability,
  generic handshake invariants) and the code that renders them into the
  generated testbench.
- [`coverage/`](coverage/README.md) — protocol coverage obligation templates
  and the runtime monitor that samples them.
- [`stimulus/`](stimulus/README.md) — scenario planning plus the actual
  cocotb-executing drivers, split into `drivers/` (protocol-specific BFMs:
  `axi_lite.py`, `axi4_outstanding.py`, `custom_mmio.py`, plus
  `axi_lite_control.py` for non-destructive control-bus probes and the shared
  `_bus_binding.py` / `_completion_scheduler.py`), `adapter/` (the
  operation-contract-aware address-window and value-packing layer,
  `OperationMemoryAdapter`), and `memory/` (the raw byte store, a re-export of
  `cocotbext.axi.memory.Memory`) — see `stimulus/README.md` for why that
  three-layer split exists.

Each subfolder independently consumes the Protocol Feature Plan built by
`build_protocol_feature_plan()` (see
[`../pool/feature_plans/README.md`](../pool/feature_plans/README.md)) and the
role/protocol-profile bindings compiled by
[`../pool/role_pool/README.md`](../pool/role_pool/README.md).
Feature selection never flows from assertion to coverage or stimulus. The one
deliberate implementation-level reuse is pure AXI transfer geometry from
`assertion/axi.py`, which the coverage runtime imports so assertions and
coverage classify byte windows identically.

## Why domain-first

This folder (and its `operation`/`lifecycle` siblings) replaced an earlier
layout where `assertion/`, `coverage/`, and `stimulus/` were the top-level
folders, each with its own `protocol`/`lifecycle`/`operation` subfolder. That
made "everything about AXI" span three different top-level folders. The
orchestrators that genuinely cut across all three domains at once
(`render_contract_generated_block`, `get_coverage_tracker`,
`run_code_owned_verification_campaign`) do **not** live under `protocol/`,
`operation/`, or `lifecycle/` — they live in
[`../orchestration/README.md`](../orchestration/README.md), since they belong
to none of the three individually.
