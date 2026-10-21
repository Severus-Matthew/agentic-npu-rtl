# u04_lifecycle_heavy

## Baseline

This case starts from the checked-in `ready_valid_tiny_gemm_a` frozen
contract: a fixed M=1, K=4, N=1 signed-integer GEMM, followed by bias addition
and ReLU. It uses separate ready/valid channels for command, A, B, bias, and Y;
single-inflight job control; a busy signal; one-cycle completion and error
pulses; and reset-aborts-inflight behavior.

The baseline RTL is intentionally not copied into this contract-input folder.
`module_manifest.json` names `tiny_gemm_rv_a_top`; its benchmark RTL is
[`tiny_gemm_rv_a_top.v`](../../../ready_valid_tiny_gemm/rtl_a/tiny_gemm_rv_a_top.v).
This corpus evaluates frozen contract inputs first; a later RTL campaign
must explicitly choose a compatible baseline or mutant.

## Unknown features (4)

- `lifecycle.busy_watchdog_observation` (lifecycle): Observe whether an accepted job remains busy for twelve sampled cycles.  Representation: Verifier extension request `lifecycle.busy_watchdog_observation`.
- `lifecycle.minimum_busy_duration` (lifecycle): Every accepted job remains busy for at least four sampled cycles.  Representation: Verifier extension request `lifecycle.minimum_busy_duration`.
- `lifecycle.completion_to_idle_deadline` (lifecycle): Busy deasserts within two cycles after completion.  Representation: Verifier extension request `lifecycle.completion_to_idle_deadline`.
- `operation.dead_zone` (operation): Piecewise dead-zone transform.  Representation: solver DAG stage `dead_zone`.

## Direct inputs

The files below are fully materialized and may be passed to one Verifier run
without regenerating this case:

- `architecture_contract.yaml`
- `interface_contract.yaml`
- `module_manifest.json`
- `acceptance_criteria.yaml`
- `benchmark_manifest.yaml`

`benchmark_manifest.yaml` is evaluation metadata, not part of the frozen
Architect contract. No Verifier output, generated TB, or model response is
stored in this directory.
