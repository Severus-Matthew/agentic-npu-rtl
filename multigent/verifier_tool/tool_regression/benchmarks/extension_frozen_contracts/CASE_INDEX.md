# Frozen extension benchmark case index

## Shared baseline

All 30 cases start from the same frozen `ready_valid_tiny_gemm_a` contract:

- fixed signed GEMM dimensions: M=1, K=4, N=1;
- arithmetic: signed products, wrapping signed accumulation, bias, then ReLU;
- command, A, B, bias, and Y use separate ready/valid channels;
- one job may be active at a time;
- `busy`, one-cycle `done`, one-cycle `err`, and reset-aborts-inflight lifecycle;
- top module: `tiny_gemm_rv_a_top`;
- baseline RTL location: `../ready_valid_tiny_gemm/rtl_a/tiny_gemm_rv_a_top.v`.

Every linked directory contains real, frozen YAML/JSON inputs. The builder is
only for deterministic regeneration; an evaluator may select and run one case
directly from its directory.

## Cases

| Case | Unknown count | Domains | Unknown features |
|---|---:|---|---|
| [`u01_operation_affine`](cases/u01_operation_affine/) | 1 | operation | `operation.affine_triple_plus_one` |
| [`u01_protocol_ready_recovery`](cases/u01_protocol_ready_recovery/) | 1 | protocol | `protocol.bounded_ready_recovery` |
| [`u01_lifecycle_busy_watchdog`](cases/u01_lifecycle_busy_watchdog/) | 1 | lifecycle | `lifecycle.busy_watchdog_observation` |
| [`u01_operation_dead_zone`](cases/u01_operation_dead_zone/) | 1 | operation | `operation.dead_zone` |
| [`u01_protocol_payload_parity`](cases/u01_protocol_payload_parity/) | 1 | protocol | `protocol.payload_parity_observation` |
| [`u02_protocol_pair`](cases/u02_protocol_pair/) | 2 | protocol | `protocol.exact_two_cycle_backpressure`<br>`protocol.minimum_ready_window` |
| [`u02_lifecycle_pair`](cases/u02_lifecycle_pair/) | 2 | lifecycle | `lifecycle.minimum_busy_duration`<br>`lifecycle.maximum_completion_latency` |
| [`u02_operation_pair`](cases/u02_operation_pair/) | 2 | operation | `operation.absolute_value`<br>`operation.negative_shift` |
| [`u02_operation_protocol`](cases/u02_operation_protocol/) | 2 | operation, protocol | `operation.symmetric_clip`<br>`protocol.transfer_gap_limit` |
| [`u02_protocol_lifecycle`](cases/u02_protocol_lifecycle/) | 2 | lifecycle, protocol | `protocol.post_reset_first_transfer_deadline`<br>`lifecycle.reset_recovery_window` |
| [`u03_all_domains`](cases/u03_all_domains/) | 3 | lifecycle, operation, protocol | `operation.relu6`<br>`protocol.backpressure_duty_cycle`<br>`lifecycle.completion_to_idle_deadline` |
| [`u03_protocol_focus`](cases/u03_protocol_focus/) | 3 | protocol | `protocol.bounded_ready_recovery`<br>`protocol.payload_parity_observation`<br>`protocol.transfer_gap_limit` |
| [`u03_lifecycle_focus`](cases/u03_lifecycle_focus/) | 3 | lifecycle | `lifecycle.busy_watchdog_observation`<br>`lifecycle.error_recovery_window`<br>`lifecycle.inter_job_cooldown` |
| [`u03_operation_focus`](cases/u03_operation_focus/) | 3 | operation | `operation.square`<br>`operation.modulo_seven`<br>`operation.floor_scale` |
| [`u03_protocol_lifecycle`](cases/u03_protocol_lifecycle/) | 3 | lifecycle, protocol | `protocol.exact_two_cycle_backpressure`<br>`protocol.minimum_ready_window`<br>`lifecycle.minimum_busy_duration` |
| [`u04_balanced_a`](cases/u04_balanced_a/) | 4 | lifecycle, operation, protocol | `operation.affine_triple_plus_one`<br>`protocol.bounded_ready_recovery`<br>`protocol.payload_parity_observation`<br>`lifecycle.maximum_completion_latency` |
| [`u04_balanced_b`](cases/u04_balanced_b/) | 4 | lifecycle, operation, protocol | `operation.absolute_value`<br>`protocol.transfer_gap_limit`<br>`lifecycle.reset_recovery_window`<br>`lifecycle.inter_job_cooldown` |
| [`u04_operation_heavy`](cases/u04_operation_heavy/) | 4 | operation, protocol | `operation.negative_shift`<br>`operation.symmetric_clip`<br>`operation.sign_dependent_gain`<br>`protocol.minimum_ready_window` |
| [`u04_protocol_heavy`](cases/u04_protocol_heavy/) | 4 | lifecycle, protocol | `protocol.exact_two_cycle_backpressure`<br>`protocol.backpressure_duty_cycle`<br>`protocol.post_reset_first_transfer_deadline`<br>`lifecycle.error_recovery_window` |
| [`u04_lifecycle_heavy`](cases/u04_lifecycle_heavy/) | 4 | lifecycle, operation | `lifecycle.busy_watchdog_observation`<br>`lifecycle.minimum_busy_duration`<br>`lifecycle.completion_to_idle_deadline`<br>`operation.dead_zone` |
| [`u05_mixed_a`](cases/u05_mixed_a/) | 5 | lifecycle, operation, protocol | `operation.relu6`<br>`operation.floor_scale`<br>`protocol.bounded_ready_recovery`<br>`protocol.payload_parity_observation`<br>`lifecycle.reset_recovery_window` |
| [`u05_mixed_b`](cases/u05_mixed_b/) | 5 | lifecycle, operation, protocol | `operation.square`<br>`protocol.exact_two_cycle_backpressure`<br>`protocol.transfer_gap_limit`<br>`lifecycle.maximum_completion_latency`<br>`lifecycle.inter_job_cooldown` |
| [`u05_operation_heavy`](cases/u05_operation_heavy/) | 5 | lifecycle, operation | `operation.affine_triple_plus_one`<br>`operation.absolute_value`<br>`operation.modulo_seven`<br>`operation.dead_zone`<br>`lifecycle.busy_watchdog_observation` |
| [`u05_protocol_heavy`](cases/u05_protocol_heavy/) | 5 | operation, protocol | `protocol.bounded_ready_recovery`<br>`protocol.minimum_ready_window`<br>`protocol.backpressure_duty_cycle`<br>`protocol.post_reset_first_transfer_deadline`<br>`operation.symmetric_clip` |
| [`u05_lifecycle_heavy`](cases/u05_lifecycle_heavy/) | 5 | lifecycle, protocol | `lifecycle.minimum_busy_duration`<br>`lifecycle.maximum_completion_latency`<br>`lifecycle.completion_to_idle_deadline`<br>`lifecycle.error_recovery_window`<br>`protocol.payload_parity_observation` |
| [`u06_mixed_a`](cases/u06_mixed_a/) | 6 | lifecycle, operation, protocol | `operation.affine_triple_plus_one`<br>`operation.negative_shift`<br>`protocol.bounded_ready_recovery`<br>`protocol.transfer_gap_limit`<br>`lifecycle.busy_watchdog_observation`<br>`lifecycle.reset_recovery_window` |
| [`u06_mixed_b`](cases/u06_mixed_b/) | 6 | lifecycle, operation, protocol | `operation.absolute_value`<br>`operation.relu6`<br>`protocol.exact_two_cycle_backpressure`<br>`protocol.payload_parity_observation`<br>`lifecycle.maximum_completion_latency`<br>`lifecycle.error_recovery_window` |
| [`u06_operation_heavy`](cases/u06_operation_heavy/) | 6 | lifecycle, operation, protocol | `operation.square`<br>`operation.modulo_seven`<br>`operation.floor_scale`<br>`operation.sign_dependent_gain`<br>`protocol.minimum_ready_window`<br>`lifecycle.inter_job_cooldown` |
| [`u06_protocol_heavy`](cases/u06_protocol_heavy/) | 6 | lifecycle, operation, protocol | `protocol.bounded_ready_recovery`<br>`protocol.exact_two_cycle_backpressure`<br>`protocol.transfer_gap_limit`<br>`protocol.backpressure_duty_cycle`<br>`operation.dead_zone`<br>`lifecycle.completion_to_idle_deadline` |
| [`u06_lifecycle_heavy`](cases/u06_lifecycle_heavy/) | 6 | lifecycle, operation | `lifecycle.busy_watchdog_observation`<br>`lifecycle.minimum_busy_duration`<br>`lifecycle.maximum_completion_latency`<br>`lifecycle.error_recovery_window`<br>`lifecycle.reset_recovery_window`<br>`operation.symmetric_clip` |
