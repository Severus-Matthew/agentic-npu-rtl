# Bounded external Verifier API generation result

Date: 2026-10-14

P01, P02, and P03 were run independently with a hard limit of ten Verifier API
requests per case. Architect, RTL Generator, Debugger, and FPGA stages were not
invoked. The frozen contracts and pinned upstream RTL were audited before each
run; model-declared conflicts were checked against those sources rather than
accepted automatically.

| Case | API requests | Generation result | Post-generation validation | Local simulation |
|---|---:|---|---|---|
| P01 Wishbone pipelined to AXI4 | 10 | `REJECTED` | No artifact passed the deterministic gate | Not run |
| P02 Wishbone cross-clock | 10 | `REJECTED` | Repeated incomplete assertion/coverage call graphs; one repair omitted both bundles | Not run |
| P03 APB cross-clock | 10 | Artifact review reached `APPROVED` on attempt 10 | Rejected after direct inspection exposed shell-quoted dict keys and the validator was strengthened | `SIMULATION_FAILURE` in reference self-check at 0 ns |

No case is qualified. P03 demonstrates useful convergence—the Verifier repaired
missing files, runtime-evidence bindings, exact bin consumption, checked-record
mapping, assertion comments, and three separate cocotb drive/`ReadOnly` phase
violations—but the final executable evidence is still negative.

## P03 execution failure

The generated reference self-check intended to prove that a two-cycle
`S_APB_PREADY` pulse is rejected. It appended a new high sample after a low
sample, which creates a second one-cycle pulse rather than a two-cycle pulse.
Consequently the checker correctly saw two legal one-cycle runs and the
self-check failed before DUT traffic began.

Direct source inspection also found shell quote-splicing fragments such as
`result['"'"'expected'"'"']`. They are valid Python syntax but produce a key that
contains quote characters and would fail at runtime. The deterministic source
validator now rejects this pattern before simulation. The generated TB was not
hand-edited; P03 stopped because its ten-call budget was exhausted.

## General tool defects found and fixed

- `AgentConfig.timeout_seconds` previously bounded individual socket reads, not
  total API request wall time. API calls now have a real POSIX wall-clock
  deadline and a machine-readable timeout trace.
- TB validation assumed `global_handshake_rules` was always a mapping. It now
  accepts both structured mappings and the schema-compatible descriptive string.
- Extension clock validation previously inspected only a direct caller and
  falsely rejected clocks started through reachable helpers. It now follows the
  local call graph.
- Extension authoring/repair guidance now explicitly requires a free-running
  clock for every independently driven clock domain, exact-bin assertions, and
  explicit trigger/nonempty evidence.
- Generated Python containing shell quote-splicing in subscript keys is now
  rejected statically.

The source RTL for P01–P03 still passes the separately recorded Verilator lint
check in `source_lint_summary.yaml`. That is source evidence only and is not
reported as generated-TB success.
