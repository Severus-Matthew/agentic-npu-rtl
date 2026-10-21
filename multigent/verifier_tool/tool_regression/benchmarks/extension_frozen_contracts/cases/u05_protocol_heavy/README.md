# u05_protocol_heavy

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

## Unknown features (5)

- `protocol.bounded_ready_recovery` (protocol): DUT-owned operand-A READY must recover within seven cycles after A VALID is presented and a legal command opens the input channel.  Representation: Verifier extension request `protocol.bounded_ready_recovery`.
- `protocol.minimum_ready_window` (protocol): Once READY rises it remains asserted for at least three sampled cycles.  Representation: Verifier extension request `protocol.minimum_ready_window`.
- `protocol.backpressure_duty_cycle` (protocol): Measure the fraction of valid cycles spent under backpressure.  Representation: Verifier extension request `protocol.backpressure_duty_cycle`.
- `protocol.post_reset_first_transfer_deadline` (protocol): The first legal output transfer after reset must occur within a declared window.  Representation: Verifier extension request `protocol.post_reset_first_transfer_deadline`.
- `operation.symmetric_clip` (operation): Bounded saturating scalar transform.  Representation: solver DAG stage `symmetric_clip`.

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
