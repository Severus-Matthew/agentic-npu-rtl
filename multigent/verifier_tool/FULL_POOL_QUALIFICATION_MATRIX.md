# Full pool qualification inventory

This is the exhaustive **inventory**, not a pass claim. The HLS benchmark is tracked separately in [`HLS_GOLDEN_BENCHMARK_MATRIX.md`](HLS_GOLDEN_BENCHMARK_MATRIX.md). A strict `✓` requires frozen-contract/generated-TB mutant failure with the intended diagnostic and corrected RTL passing every required bin and ledger check. `S` means an earlier manually assembled smoke TB detected a mutant, which is not strict qualification. `—` means not qualified here. This inventory is intentionally left unqualified while the real HLS benchmark is investigated.

## Verification tags (tag pool)

| Tag | Domains | Strict status |
| --- | --- | --- |
| `4k_boundary` | protocol | — |
| `ack_phase` | protocol | — |
| `address_boundary` | protocol, operation | — |
| `address_range` | protocol, operation | — |
| `alignment` | protocol, operation | — |
| `arbitration` | protocol | — |
| `back_to_back` | protocol, lifecycle | — |
| `backpressure` | protocol | — |
| `burst_length` | protocol | — |
| `burst_type` | protocol | — |
| `busy` | lifecycle | — |
| `byte_enable` | protocol | — |
| `cancel` | lifecycle | — |
| `clocking` | protocol, lifecycle | — |
| `coherence_state` | protocol | — |
| `completion` | lifecycle | — |
| `configuration` | operation, lifecycle | — |
| `contract_defined_protocol` | protocol | — |
| `control` | protocol, lifecycle | — |
| `correlation` | protocol | — |
| `credit_boundary` | protocol | — |
| `credit_empty` | protocol | — |
| `credit_full` | protocol | — |
| `debug_visibility` | protocol, lifecycle | — |
| `denied_access` | protocol | — |
| `destination_partition` | protocol | — |
| `empty_frame` | protocol | — |
| `empty_symbols` | protocol | — |
| `epoch_partition` | protocol, lifecycle | — |
| `error` | protocol, lifecycle | — |
| `error_response` | protocol | — |
| `extrema` | operation, protocol | — |
| `flow_control` | protocol | — |
| `flush` | lifecycle | — |
| `framing` | protocol | — |
| `handshake` | protocol | — |
| `identifier_partition` | protocol | — |
| `illegal_command` | lifecycle | — |
| `illegal_opcode` | protocol, lifecycle | — |
| `illegal_size` | protocol | — |
| `illegal_value` | protocol, lifecycle, operation | — |
| `interrupt` | lifecycle | — |
| `legal_boundary` | protocol, operation | — |
| `legal_command` | lifecycle | — |
| `lifecycle` | lifecycle | — |
| `mask_patterns` | protocol, operation | — |
| `mathematical_correctness` | operation | — |
| `maximum_length` | protocol, operation | — |
| `metadata_values` | protocol | — |
| `minimum_length` | protocol, operation | — |
| `opcode_partition` | protocol, lifecycle | — |
| `operation_feature` | operation | — |
| `ordering` | protocol, lifecycle, operation | — |
| `outstanding_ids` | protocol | — |
| `partial_transfer` | protocol | — |
| `payload_values` | protocol | — |
| `performance_event` | protocol, lifecycle | — |
| `priority_partition` | protocol | — |
| `protection_partition` | protocol | — |
| `recovery` | lifecycle, protocol | — |
| `request_acknowledge` | protocol | — |
| `reset` | lifecycle, protocol | — |
| `response_partition` | protocol | — |
| `serialization` | operation, protocol | — |
| `setup_access_phase` | protocol | — |
| `size_partition` | protocol | — |
| `source_id` | protocol | — |
| `stall_stability` | protocol | — |
| `user_metadata` | protocol | — |
| `value_partition` | protocol, operation | — |
| `wait_state` | protocol | — |

## Selectable protocol profiles

Commented future profiles in the YAML are not selectable and are not counted below.

| Profile | Coverage tags | Strict status |
| --- | --- | --- |
| `custom` | `contract_defined_protocol` | — |
| `ready_valid` | `handshake`, `backpressure`, `stall_stability` | — |
| `axi4` | `handshake`, `backpressure`, `stall_stability`, `alignment`, `burst_length`, `burst_type`, `4k_boundary`, `byte_enable`, `response_partition`, `outstanding_ids`, `ordering` | — |
| `axi4_lite` | `handshake`, `backpressure`, `stall_stability`, `alignment`, `byte_enable`, `response_partition`, `ordering` | — |
| `custom_mmio` | `handshake`, `backpressure`, `stall_stability`, `alignment`, `byte_enable`, `response_partition`, `outstanding_ids`, `ordering` | — |
| `axi4_stream` | `handshake`, `backpressure`, `stall_stability`, `framing`, `partial_transfer`, `ordering`, `identifier_partition`, `destination_partition`, `user_metadata` | — |

## Standard protocol rules by profile

| Profile | Rule | Strict status |
| --- | --- | --- |
| `axi4` | `standard_signal_widths` | — |
| `axi4` | `ready_valid_stability` | — |
| `axi4` | `valid_low_during_reset` | — |
| `axi4` | `legal_burst_encoding` | — |
| `axi4` | `legal_burst_length` | — |
| `axi4` | `transfer_size_within_data_bus` | — |
| `axi4` | `wrap_length_and_alignment` | — |
| `axi4` | `no_4k_boundary_crossing` | — |
| `axi4` | `write_last_matches_length` | — |
| `axi4` | `read_last_matches_length` | — |
| `axi4` | `write_strobe_within_active_lanes` | — |
| `axi4` | `response_after_request` | — |
| `axi4` | `response_id_matches_request` | — |
| `axi4` | `response_order_preserved_per_id` | — |
| `axi4` | `write_address_and_data_are_independent` | — |
| `axi4` | `legal_response_encoding` | — |
| `axi4` | `exclusive_access_restrictions` | — |
| `axi4` | `exclusive_response_consistency` | — |
| `axi4_lite` | `standard_signal_widths` | — |
| `axi4_lite` | `ready_valid_stability` | — |
| `axi4_lite` | `valid_low_during_reset` | — |
| `axi4_lite` | `write_response_after_address_and_data` | — |
| `axi4_lite` | `read_response_after_address` | — |
| `axi4_lite` | `write_address_and_data_are_independent` | — |
| `axi4_lite` | `legal_lite_response_encoding` | — |
| `axi4_lite` | `data_width_is_32_or_64` | — |
| `axi4_lite` | `strobe_width_matches_data_bytes` | — |
| `axi4_lite` | `optional_id_return_and_in_order_completion` | — |
| `axi4_stream` | `standard_signal_widths` | — |
| `axi4_stream` | `ready_valid_stability` | — |
| `axi4_stream` | `valid_low_during_reset` | — |
| `axi4_stream` | `keep_and_strobe_width_match_data_bytes` | — |
| `axi4_stream` | `strobe_is_subset_of_keep` | — |
| `axi4_stream` | `packet_state_is_tracked_per_stream_key` | — |
| `axi4_stream` | `continuous_packet_constraints_when_declared` | — |
| `custom_mmio` | `ready_valid_stability` | — |
| `custom_mmio` | `valid_low_during_reset` | — |
| `ready_valid` | `ready_valid_stability` | — |
| `ready_valid` | `valid_low_during_reset` | — |

## Protocol feature catalog and bins

| Feature | Bin / assertion-only | Strict status |
| --- | --- | --- |
| `features.handshake_states` | `idle` | — |
| `features.handshake_states` | `receiver_ready` | — |
| `features.handshake_states` | `backpressured` | — |
| `features.handshake_states` | `transfer` | — |
| `features.handshake_arrival_order` | `simultaneous` | — |
| `features.handshake_arrival_order` | `valid_before_ready` | — |
| `features.handshake_arrival_order` | `ready_before_valid` | — |
| `features.stall_stability` | `one_cycle_stall` | — |
| `features.stall_stability` | `short_stall` | — |
| `features.stall_stability` | `long_stall` | — |
| `features.address_alignment` | `minimum` | — |
| `features.address_alignment` | `aligned_interior` | — |
| `features.address_alignment` | `maximum` | — |
| `features.address_alignment` | `boundary_neighbor` | — |
| `features.axi4_4k_boundary` | `ends_before_boundary` | — |
| `features.axi4_4k_boundary` | `ends_at_boundary` | — |
| `features.axi4_4k_boundary` | `would_cross_boundary` (diagnostic) | — |
| `features.axi4_burst_type` | `fixed` | — |
| `features.axi4_burst_type` | `incrementing` | — |
| `features.axi4_burst_type` | `wrapping` | — |
| `features.axi4_burst_length` | `single` | — |
| `features.axi4_burst_length` | `two_to_sixteen` | — |
| `features.axi4_burst_length` | `seventeen_to_256` | — |
| `features.axi4_transfer_size` | `one_byte` | — |
| `features.axi4_transfer_size` | `narrow` | — |
| `features.axi4_transfer_size` | `full_width` | — |
| `features.axi4_alignment` | `aligned` | — |
| `features.axi4_alignment` | `unaligned` | — |
| `features.axi4_write_strobe` | `all_zero` | — |
| `features.axi4_write_strobe` | `sparse` | — |
| `features.axi4_write_strobe` | `full` | — |
| `features.axi4_write_channel_order` | `address_first` | — |
| `features.axi4_write_channel_order` | `data_first` | — |
| `features.axi4_write_channel_order` | `same_cycle` | — |
| `features.axi4_response_code` | `okay` | — |
| `features.axi4_response_code` | `exokay` (diagnostic) | — |
| `features.axi4_response_code` | `slverr` (diagnostic) | — |
| `features.axi4_response_code` | `decerr` (diagnostic) | — |
| `features.axi4_outstanding_depth` | `one` | — |
| `features.axi4_outstanding_depth` | `multiple_same_id` | — |
| `features.axi4_outstanding_depth` | `multiple_ids` (diagnostic) | — |
| `features.axi4_sideband_partition` | `zero` | — |
| `features.axi4_sideband_partition` | `nonzero` | — |
| `features.axi_lite_write_channel_order` | `address_first` | — |
| `features.axi_lite_write_channel_order` | `data_first` | — |
| `features.axi_lite_write_channel_order` | `same_cycle` | — |
| `features.axi_lite_write_strobe` | `all_zero` | — |
| `features.axi_lite_write_strobe` | `sparse` | — |
| `features.axi_lite_write_strobe` | `full` | — |
| `features.axi_lite_response_code` | `okay` | — |
| `features.axi_lite_response_code` | `slverr` (diagnostic) | — |
| `features.axi_lite_response_code` | `decerr` (diagnostic) | — |
| `features.axi_lite_read_write_concurrency` | `write_only_cycle` | — |
| `features.axi_lite_read_write_concurrency` | `read_only_cycle` | — |
| `features.axi_lite_read_write_concurrency` | `simultaneous` | — |
| `features.axi_lite_address_partition` | `zero` | — |
| `features.axi_lite_address_partition` | `aligned` | — |
| `features.axi_lite_address_partition` | `unaligned` | — |
| `features.axi_lite_address_partition` | `page_edge` | — |
| `features.axi_lite_protection_partition` | `zero` | — |
| `features.axi_lite_protection_partition` | `nonzero` | — |
| `features.axi_lite_outstanding_depth` | `one` | — |
| `features.axi_lite_outstanding_depth` | `multiple` | — |
| `features.axis_packet_length` | `single_beat` | — |
| `features.axis_packet_length` | `multi_beat` | — |
| `features.axis_keep_pattern` | `full` | — |
| `features.axis_keep_pattern` | `partial` | — |
| `features.axis_keep_pattern` | `empty_last` (diagnostic) | — |
| `features.axis_stall_position` | `first_beat` | — |
| `features.axis_stall_position` | `middle_beat` | — |
| `features.axis_stall_position` | `last_beat` | — |
| `features.axis_back_to_back_packets` | `no_gap` | — |
| `features.axis_back_to_back_packets` | `with_gap` | — |
| `features.axis_sideband_partition` | `zero` | — |
| `features.axis_sideband_partition` | `nonzero` | — |
| `derived_features.valid_low_during_reset` | assertion-only | — |
| `derived_features.standard_protocol_rule` | assertion-only | — |

## Lifecycle policy choices

| Policy field | Choice | Strict status |
| --- | --- | --- |
| `job_acceptance` | `valid_ready_handshake` | — |
| `job_acceptance` | `control_plane_sequence` | — |
| `job_overlap` | `single_inflight` | — |
| `busy_behavior` | `tracks_active_job` | — |
| `completion_style` | `pulse` | — |
| `completion_style` | `control_plane_sequence` | — |
| `completion_timing` | `next_cycle_after_retirement` | — |
| `completion_timing` | `observed_via_poll` | — |
| `illegal_command_behavior` | `error_without_start` | — |
| `error_style` | `pulse` | — |
| `error_style` | `sticky_until_reset` | — |
| `error_timing` | `next_cycle_after_error_event` | — |
| `reset_behavior` | `abort_inflight` | — |

## Lifecycle features and bins

| Catalog section | Feature | Bin / assertion-only | Strict status |
| --- | --- | --- | --- |
| `features` | `reset_behavior` | `asserted` | — |
| `features` | `reset_behavior` | `deasserted` | — |
| `features` | `reset_behavior` | `release` | — |
| `features` | `busy_behavior` | `idle` | — |
| `features` | `busy_behavior` | `active` | — |
| `features` | `busy_behavior` | `retired` | — |
| `features` | `completion_behavior` | `observed` | — |
| `features` | `completion_behavior` | `back_to_back` | — |
| `features` | `error_behavior` | `inactive` | — |
| `features` | `error_behavior` | `asserted` | — |
| `features` | `error_behavior` | `recovered` | — |
| `features` | `command_legality` | `legal` | — |
| `features` | `command_legality` | `illegal` | — |
| `operation_features` | `legal_command_starts_one_job` | assertion-only or dynamic obligation | — |
| `operation_features` | `illegal_command_errors_without_start` | assertion-only or dynamic obligation | — |
| `operation_features` | `response_error_follows_nonokay` | assertion-only or dynamic obligation | — |
| `operation_features` | `no_output_without_active_job` | assertion-only or dynamic obligation | — |
| `operation_features` | `busy_tracks_active_job` | assertion-only or dynamic obligation | — |
| `operation_features` | `completion_matches_final_output` | assertion-only or dynamic obligation | — |
| `operation_features` | `reset_aborts_pending_job` | assertion-only or dynamic obligation | — |
| `operation_features` | `status_pulses_are_one_cycle` | assertion-only or dynamic obligation | — |
| `operation_coverage` | `job_lifecycle` | `accepted` | — |
| `operation_coverage` | `job_lifecycle` | `active` | — |
| `operation_coverage` | `job_lifecycle` | `retired` | — |
| `operation_coverage` | `job_lifecycle` | `aborted` | — |
| `operation_coverage` | `reset_abort_phase` | `idle` | — |
| `operation_coverage` | `reset_abort_phase` | `compute` | — |
| `operation_coverage` | `reset_abort_phase` | `output` | — |
| `operation_coverage` | `post_reset_purity` | `no_ghost_completion` | — |
| `operation_coverage` | `post_reset_purity` | `no_ghost_output` | — |
| `operation_coverage` | `post_reset_purity` | `clean_recovery_job` | — |

## Operation families, concepts, and bins

| Family | Concept | Bin | Strict status |
| --- | --- | --- | --- |
| `matrix_multiply` | `dimensions` | `fixed_shape` | — |
| `matrix_multiply` | `operand_values` | `zero` | — |
| `matrix_multiply` | `operand_values` | `positive` | — |
| `matrix_multiply` | `operand_values` | `negative` | — |
| `matrix_multiply` | `operand_values` | `minimum` | — |
| `matrix_multiply` | `operand_values` | `maximum` | — |
| `matrix_multiply` | `accumulation` | `ordinary` | — |
| `matrix_multiply` | `accumulation` | `positive_boundary` | — |
| `matrix_multiply` | `accumulation` | `negative_boundary` | — |
| `matrix_multiply` | `accumulation` | `positive_overflow` | — |
| `matrix_multiply` | `accumulation` | `negative_overflow` | — |
| `matrix_multiply` | `post_processing.bias` | `zero_bias` | — |
| `matrix_multiply` | `post_processing.bias` | `positive_bias` | — |
| `matrix_multiply` | `post_processing.bias` | `negative_bias` | — |
| `matrix_multiply` | `post_processing.bias` | `minimum_bias` | — |
| `matrix_multiply` | `post_processing.bias` | `maximum_bias` | — |
| `matrix_multiply` | `post_processing.activation` | `negative_region` | — |
| `matrix_multiply` | `post_processing.activation` | `zero_region` | — |
| `matrix_multiply` | `post_processing.activation` | `positive_region` | — |
| `matrix_multiply` | `post_processing.quantization` | `exact` | — |
| `matrix_multiply` | `post_processing.quantization` | `rounded` | — |
| `matrix_multiply` | `post_processing.quantization` | `nonzero_zero_point` | — |
| `matrix_multiply` | `post_processing.quantization` | `negative_saturation` | — |
| `matrix_multiply` | `post_processing.quantization` | `positive_saturation` | — |

Source files: `pool/tag_pool/verification_tags.yaml`, `pool/role_pool/interface_protocol_profiles.yaml`, `pool/role_pool/standard_protocols.yaml`, `pool/feature_plans/{protocol,lifecycle,operation}_features.yaml`, and `pool/lifecycle_policy_pool/lifecycle_policies.yaml`.
