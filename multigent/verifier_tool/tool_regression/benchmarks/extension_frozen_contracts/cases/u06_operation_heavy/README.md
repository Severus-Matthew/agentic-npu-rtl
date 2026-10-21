# u06_operation_heavy

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

## Unknown features (6)

- `operation.square` (operation): Nonlinear but bounded integer expression.  Representation: solver DAG stage `square`.
- `operation.modulo_seven` (operation): Integer remainder classes.  Representation: solver DAG stage `modulo_seven`.
- `operation.floor_scale` (operation): Integer scale-down with explicit floor semantics.  Representation: solver DAG stage `floor_scale`.
- `operation.sign_dependent_gain` (operation): Conditional gain selected by sign.  Representation: solver DAG stage `sign_dependent_gain`.
- `protocol.minimum_ready_window` (protocol): Once READY rises it remains asserted for at least three sampled cycles.  Representation: Verifier extension request `protocol.minimum_ready_window`.
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
