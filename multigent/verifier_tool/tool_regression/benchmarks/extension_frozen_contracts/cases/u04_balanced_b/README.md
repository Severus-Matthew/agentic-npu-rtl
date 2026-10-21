# u04_balanced_b

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

- `operation.absolute_value` (operation): Nonnegative piecewise scalar transform.  Representation: solver DAG stage `absolute_value`.
- `protocol.transfer_gap_limit` (protocol): Consecutive output transfers must be separated by at most five cycles.  Representation: Verifier extension request `protocol.transfer_gap_limit`.
- `lifecycle.reset_recovery_window` (lifecycle): A clean legal job can start within five cycles after reset release.  Representation: Verifier extension request `lifecycle.reset_recovery_window`.
- `lifecycle.inter_job_cooldown` (lifecycle): Two completed jobs are separated by at least two idle cycles.  Representation: Verifier extension request `lifecycle.inter_job_cooldown`.

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
