from __future__ import annotations

from types import MappingProxyType

import pytest

from multigent.verifier_tool import (
    BEGIN_MARKER,
    ContractSnapshot,
    END_MARKER,
    build_interface_coverage_plan,
    capture_contract_snapshot,
    install_contract_generated_block,
    install_pipeline_generated_annotations,
    render_contract_generated_block,
    validate_contract_generated_block,
    validate_verifier_authored_structure,
)


def plan() -> dict:
    return build_interface_coverage_plan(
        {
            "clock": "clk",
            "reset": "rst",
            "channels": [
                {
                    "name": "out",
                    "direction": "output",
                    "protocol_profile": "ready_valid",
                }
            ],
            "signals": [
                {"name": "clk", "role": "clock", "channel": None},
                {
                    "name": "rst",
                    "role": "reset",
                    "channel": None,
                    "semantic": "active-high reset",
                },
                {"name": "valid", "role": "valid", "channel": "out"},
                {"name": "ready", "role": "ready", "channel": "out"},
                {
                    "name": "data",
                    "role": "payload",
                    "semantic_class": "data",
                    "channel": "out",
                },
            ],
        }
    )


def snapshot(**values: int) -> ContractSnapshot:
    return ContractSnapshot(
        MappingProxyType(dict(values)),
        MappingProxyType({name: 1 for name in values}),
    )


def checker():
    namespace: dict = {}
    exec(render_contract_generated_block(plan()), namespace)
    return namespace, namespace["_check_contract_protocol_assertions"]


def test_snapshot_reads_each_declared_signal_exactly_once() -> None:
    class Signal:
        def __init__(self, value: int) -> None:
            self._value = value
            self.reads = 0

        @property
        def value(self) -> int:
            self.reads += 1
            return self._value

        def __len__(self) -> int:
            return 8

    class Dut:
        pass

    dut = Dut()
    dut.a = Signal(3)
    dut.b = Signal(7)
    observed = capture_contract_snapshot(dut, ("a", "b"))
    assert dict(observed) == {"a": 3, "b": 7}
    assert observed.widths == {"a": 8, "b": 8}
    assert dut.a.reads == dut.b.reads == 1


def test_generated_tb_block_is_visible_final_and_tamper_evident() -> None:
    source = "import cocotb\n"
    installed = install_contract_generated_block(source, plan())
    assert installed.count(BEGIN_MARKER) == 1
    assert installed.rstrip().endswith(END_MARKER)
    assert "from multigent.verifier_tool import (" in installed
    assert "multigent.verifier_tool.orchestration.runtime" not in installed
    assert "# PROTOCOL ASSERTION [channel.out.stall_stability]" in installed
    assert "CONTRACT_SIGNAL_NAMES = ('clk', 'rst', 'valid', 'ready', 'data')" in installed
    validate_contract_generated_block(installed, plan())
    with pytest.raises(ValueError, match="modified"):
        validate_contract_generated_block(
            installed.replace("'valid': 'valid'", "'valid': 'ready'", 1), plan()
        )


def test_catalog_operation_features_are_inserted_by_code() -> None:
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "post_processing",
                ],
                "feature_extensions": ["runtime_shape", "new_fused_mode"],
                "semantics": "GEMM with a custom fused mode and runtime shapes; not code-owned math.",
                "arithmetic": {"classifier_profile": "llm_extension", "reason": "runtime shape and fused mode"},
                "lifecycle_policy": {
                    "job_acceptance": "valid_ready_handshake", "job_overlap": "single_inflight",
                    "busy_behavior": "tracks_active_job", "completion_style": "pulse",
                    "completion_timing": "next_cycle_after_retirement",
                    "illegal_command_behavior": "error_without_start", "error_style": "pulse",
                    "error_timing": "next_cycle_after_error_event", "reset_behavior": "abort_inflight",
                },
            }
        ]
    }
    installed = install_contract_generated_block(
        "import cocotb\n", plan(), architecture
    )
    assert "# CATALOG OPERATION [gemm]" in installed
    assert "# OPERATION ASSERTION [operation.gemm.dimensions]" in installed
    assert "# OPERATION ASSERTION [operation.gemm.runtime_shape]" not in installed
    assert "new_fused_mode" not in installed
    assert "def _contract_record_checked_stimulus" in installed
    assert "assert observed_value == expected_value" in installed
    namespace: dict = {}
    exec(render_contract_generated_block(plan(), architecture), namespace)
    namespace["_contract_runtime_record_stimulus"] = lambda *args, **kwargs: "ok"
    with pytest.raises(AssertionError, match="operation.gemm.dimensions"):
        namespace["_contract_record_checked_stimulus"](
            "directed",
            {"a": [1], "b": [2]},
            {"outputs": [3]},
            {"outputs": [4]},
            operations=("gemm",),
            label="wrong",
        )


def test_one_protocol_state_checks_stability_and_returns_stall_length() -> None:
    namespace, check = checker()
    assert check(snapshot(rst=0, valid=1, ready=0, data=9)) == {}
    assert check(snapshot(rst=0, valid=1, ready=1, data=9)) == {
        "channel.out.stall_stability": 1
    }
    assert namespace["_CONTRACT_PROTOCOL_STATE"] == {}

    check(snapshot(rst=0, valid=1, ready=0, data=10))
    with pytest.raises(AssertionError, match="content changed"):
        check(snapshot(rst=0, valid=1, ready=0, data=11))


def test_reset_clears_pending_protocol_state() -> None:
    namespace, check = checker()
    check(snapshot(rst=0, valid=1, ready=0, data=4))
    assert namespace["_CONTRACT_PROTOCOL_STATE"]
    assert check(snapshot(rst=1)) == {}
    # Reset clears every pending channel/stability record; only the reset-settle
    # sample counter (bookkeeping, not protocol state) survives an active reset.
    assert {
        key: value for key, value in namespace["_CONTRACT_PROTOCOL_STATE"].items()
        if key != "_reset_active_samples"
    } == {}


def test_static_stimulus_intents_must_cover_every_obligation() -> None:
    required = {"feature.a", "feature.b"}
    valid = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "edges", "targets": ["feature.a", "feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(value):
    # LLM-GENERATED OPERATION ASSERTION [feature.a]
    assert value, "feature=feature.a expected=true observed=false"
# STIMULUS [edges]
_contract_record_checked_stimulus(
    "directed", {"value": 1}, {"result": 1}, {"result": observed_result},
    operations=("add",), label="edges",
)
'''
    validate_verifier_authored_structure([valid], required)
    with pytest.raises(ValueError, match="missing=.*feature.b"):
        validate_verifier_authored_structure(
            [valid.replace(', "feature.b"', "")], required
        )


def test_checked_stimulus_call_must_use_complete_code_owned_signature() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
# STIMULUS [job]
_contract_record_checked_stimulus(
    dut, operations=("add",), label="job", info={"x": 1}
)
'''
    with pytest.raises(ValueError, match="must use exactly.*stimulus_kind"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_kind_is_bounded_to_runtime_values() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
# STIMULUS [job]
_contract_record_checked_stimulus(
    "protocol", {"x": 1}, {"result": 1}, {"result": observed},
    operations=("add",), label="job",
)
'''
    with pytest.raises(ValueError, match="stimulus_kind must be the literal 'directed' or 'randomized'"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_sync_helper_must_not_be_awaited() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise():
    # STIMULUS [job]
    await _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("add",), label="job",
    )
'''
    with pytest.raises(ValueError, match="synchronous code-owned helper and must not be awaited"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_rejects_literal_string_instead_of_mapping() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(observed):
    # STIMULUS [job]
    _contract_record_checked_stimulus(
        "directed", "directed", {"result": 1}, {"result": observed},
        operations=("add",), label="job",
    )
'''
    with pytest.raises(ValueError, match="stimulus must be a mapping"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_code_owned_helper_cannot_be_imported_by_verifier_source() -> None:
    source = '''
from multigent.verifier_tool import _contract_record_checked_stimulus
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = []
# === LLM-GENERATED OPERATION ASSERTIONS ===
'''
    with pytest.raises(ValueError, match="may not define code-owned.*_contract_record_checked_stimulus"):
        install_contract_generated_block(source, {"monitor": {}, "obligations": []})


def test_qualified_checked_stimulus_call_is_rejected_with_exact_fix() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# STIMULUS [job]
contract_coverage._contract_record_checked_stimulus(
    "directed", {"x": 1}, {"result": 1}, {"result": observed},
    operations=("add",), label="job",
)
# === LLM-GENERATED OPERATION ASSERTIONS ===
'''
    with pytest.raises(ValueError) as captured:
        validate_verifier_authored_structure([source], {"feature.a"})
    message = str(captured.value)
    assert "Qualified _contract_record_checked_stimulus calls are invalid" in message
    assert "contract_coverage._contract_record_checked_stimulus" in message
    assert "four positional arguments" in message


def test_output_read_immediately_after_rising_edge_requires_settling() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = []
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def observe(dut):
    dut.y_ready.value = 1
    await RisingEdge(dut.clk)
    completion = int(dut.completion.value)
'''
    interface = {
        "signals": [
            {"name": "rst_n", "direction": "input"},
            {"name": "y_ready", "direction": "input"},
            {"name": "completion", "direction": "output"},
        ]
    }
    with pytest.raises(ValueError) as captured:
        validate_verifier_authored_structure(
            [source], set(), interface_contract=interface
        )
    message = str(captured.value)
    assert "immediately after RisingEdge" in message
    assert "completion" in message
    assert "must await a small Timer" in message
    assert "do not add ReadOnly" in message


def test_output_read_after_timer_is_settled() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def observe(dut):
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    completion = int(dut.completion.value)
    # STIMULUS [job]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"completion": 1}, {"completion": completion},
        operations=("op",), label="job",
    )
'''
    interface = {"signals": [{"name": "completion", "direction": "output"}]}
    validate_verifier_authored_structure(
        [source], {"feature.a"}, interface_contract=interface
    )


def test_nested_output_read_after_timer_is_analyzed_in_body_order() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def observe(dut):
    await RisingEdge(dut.clk)
    if int(dut.rst_n.value):
        await Timer(1, units="ns")
        completion = int(dut.completion.value)
        # STIMULUS [job]
        _contract_record_checked_stimulus(
            "directed", {"x": 1}, {"completion": 1}, {"completion": completion},
            operations=("op",), label="job",
        )
'''
    interface = {
        "signals": [
            {"name": "rst_n", "direction": "input"},
            {"name": "completion", "direction": "output"},
        ]
    }
    validate_verifier_authored_structure(
        [source], {"feature.a"}, interface_contract=interface
    )

    unsafe = source.replace('        await Timer(1, units="ns")\n', '')
    with pytest.raises(ValueError, match="immediately after RisingEdge"):
        validate_verifier_authored_structure(
            [unsafe], {"feature.a"}, interface_contract=interface
        )


def test_input_read_after_rising_edge_is_not_output_race() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def drive(dut):
    await RisingEdge(dut.clk)
    reset_released = int(dut.rst_n.value)
    # STIMULUS [job]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"reset": 1}, {"reset": reset_released},
        operations=("op",), label="job",
    )
'''
    interface = {"signals": [{"name": "rst_n", "direction": "input"}]}
    validate_verifier_authored_structure(
        [source], {"feature.a"}, interface_contract=interface
    )


def test_ready_read_after_rising_edge_requires_pre_edge_snapshot() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = []
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def send(dut):
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    accepted = int(dut.cmd_ready.value)
'''
    interface = {
        "signals": [
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input"},
            {"name": "cmd_ready", "role": "ready", "channel": "cmd", "direction": "output"},
        ]
    }
    with pytest.raises(ValueError) as captured:
        validate_verifier_authored_structure(
            [source], set(), interface_contract=interface
        )
    message = str(captured.value)
    assert "too late to decide whether that edge transferred" in message
    assert "saved pre-edge snapshot" in message
    assert "post-edge Timer or ReadOnly does not repair" in message


def test_structure_validation_reports_all_actionable_errors_together() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "first", "targets": ["feature.a"]},
    {"label": "second", "targets": ["feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(value):
    assert value
'''
    with pytest.raises(ValueError) as captured:
        validate_verifier_authored_structure(
            [source], {"feature.a", "feature.b"}
        )
    message = str(captured.value)
    assert "Stimulus intent 'first'" in message
    assert "Stimulus intent 'second'" in message
    assert "feature comment" in message


def test_channel_coverage_claim_requires_real_dut_input_drive() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "cmd", "targets": ["channel.cmd.handshake_states"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def check(dut, observed):
    dut.cmd_valid.value = 0
    # STIMULUS [cmd]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 1}, {"ok": 1}, {"ok": observed},
        operations=("op",), label="cmd",
    )
'''
    interface = {
        "channels": [{"name": "cmd", "direction": "input"}],
        "signals": [
            {"name": "cmd_valid", "channel": "cmd", "role": "valid", "direction": "input"},
            {"name": "cmd_ready", "channel": "cmd", "role": "ready", "direction": "output"},
        ],
    }
    with pytest.raises(ValueError, match="never drives.*cmd_valid"):
        validate_verifier_authored_structure(
            [source], {"channel.cmd.handshake_states"},
            interface_contract=interface,
        )
    validate_verifier_authored_structure(
        [source.replace("dut.cmd_valid.value = 0", "dut.cmd_valid.value = 1")],
        {"channel.cmd.handshake_states"},
        interface_contract=interface,
    )


def test_channel_drive_through_local_helper_is_recognized() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "cmd", "targets": ["channel.cmd.handshake_states"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def send_one(valid_sig):
    valid_sig.value = 1
async def check(dut, observed):
    await send_one(dut.cmd_valid)
    # STIMULUS [cmd]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 1}, {"ok": 1}, {"ok": observed},
        operations=("op",), label="cmd",
    )
'''
    interface = {
        "channels": [{"name": "cmd", "direction": "input"}],
        "signals": [
            {"name": "cmd_valid", "channel": "cmd", "role": "valid", "direction": "input"},
            {"name": "cmd_ready", "channel": "cmd", "role": "ready", "direction": "output"},
        ],
    }
    validate_verifier_authored_structure(
        [source], {"channel.cmd.handshake_states"}, interface_contract=interface,
    )


def test_channel_drive_through_nested_local_helpers_is_recognized() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "cmd", "targets": ["channel.cmd.handshake_states"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def send_beat(valid_sig):
    valid_sig.value = 1
async def send_vector(values, valid_sig):
    for _ in values:
        await send_beat(valid_sig)
async def check(dut, observed):
    await send_vector([1], dut.cmd_valid)
    # STIMULUS [cmd]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 1}, {"ok": 1}, {"ok": observed},
        operations=("op",), label="cmd",
    )
'''
    interface = {
        "channels": [{"name": "cmd", "direction": "input"}],
        "signals": [
            {"name": "cmd_valid", "channel": "cmd", "role": "valid", "direction": "input"},
            {"name": "cmd_ready", "channel": "cmd", "role": "ready", "direction": "output"},
        ],
    }
    validate_verifier_authored_structure(
        [source], {"channel.cmd.handshake_states"}, interface_contract=interface,
    )


def test_channel_drive_through_bounded_getattr_kwargs_helper_is_recognized() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "cmd", "targets": ["channel.cmd.handshake_states"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def cycle_drive(dut, **values):
    for name, value in values.items():
        getattr(dut, name).value = value
async def send_beat(dut, valid_name, payload_name, value):
    await cycle_drive(dut, **{valid_name: 1, payload_name: value})
async def check(dut, observed):
    await send_beat(dut, "cmd_valid", "cmd_payload", 1)
    # STIMULUS [cmd]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 1}, {"ok": 1}, {"ok": observed},
        operations=("op",), label="cmd",
    )
'''
    interface = {
        "channels": [{"name": "cmd", "direction": "input"}],
        "signals": [
            {"name": "cmd_valid", "channel": "cmd", "role": "valid", "direction": "input"},
            {"name": "cmd_ready", "channel": "cmd", "role": "ready", "direction": "output"},
        ],
    }
    validate_verifier_authored_structure(
        [source], {"channel.cmd.handshake_states"}, interface_contract=interface,
    )


def test_checked_stimulus_expected_and_observed_shapes_must_match() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(observed):
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1},
        {"result": int(observed), "extra": 1},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="identical keys.*unexpected_observed=.*extra"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_rejects_provably_different_value_types() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(observed):
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"error": "pulse"},
        {"error": int(observed)}, operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="types differ.*expected=str, observed=int"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_llm_operation_feature_comments_match_contract_extensions_exactly() -> None:
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": [
                    "dimensions",
                    "operand_values",
                    "accumulation",
                    "post_processing",
                ],
                "feature_extensions": ["novel_epilogue"],
            }
        ]
    }
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "case", "targets": ["feature.a"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(value):
    # LLM-GENERATED OPERATION ASSERTION [operation.gemm.wrong_feature]
    assert value
# STIMULUS [case]
_contract_record_checked_stimulus(
    "directed", {"value": 1}, {"result": 1}, {"result": 1},
    operations=("gemm",), label="case",
)
'''
    with pytest.raises(ValueError) as captured:
        validate_verifier_authored_structure(
            [source], {"feature.a"}, architecture
        )
    message = str(captured.value)
    assert "missing=['operation.gemm.novel_epilogue']" in message
    assert "unknown=['operation.gemm.wrong_feature']" in message


def test_pipeline_normalizes_stimulus_metadata_and_writes_comments() -> None:
    source = '''
COVERAGE_OBLIGATIONS = {"feature.b", "feature.a"}
STIMULUS_COVERAGE_INTENTS = [
    {"label": "edges", "targets": sorted(COVERAGE_OBLIGATIONS)},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def check(value):
    # LLM-GENERATED OPERATION ASSERTION [feature.a]
    assert value, "feature=feature.a expected=true observed=false"
def exercise():
    _contract_record_checked_stimulus(
        "directed", {"value": 1}, {"result": 1}, {"result": observed_result},
        operations=("add",), label="edges",
    )
'''
    installed = install_pipeline_generated_annotations(source)
    assert "STIMULUS_COVERAGE_INTENTS = [{'label': 'edges', 'targets': ['feature.a', 'feature.b']}]" in installed
    assert (
        "    # STIMULUS [edges] targets=('feature.a', 'feature.b')\n"
        "    _contract_record_checked_stimulus"
    ) in installed
    validate_verifier_authored_structure([installed], {"feature.a", "feature.b"})
    assert install_pipeline_generated_annotations(installed) == installed
    with pytest.raises(ValueError, match="feature comment"):
        validate_verifier_authored_structure(
            [installed.replace("    # LLM-GENERATED OPERATION ASSERTION [feature.a]\n", "")],
            {"feature.a", "feature.b"},
        )


def test_consecutive_checked_records_need_new_dut_progress() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "first", "targets": ["feature.a"]},
    {"label": "second", "targets": ["feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    observed = int(dut.result.value)
    # STIMULUS [first]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="first",
    )
    sample_operation("op", {}, "directed", 1)
    # STIMULUS [second]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="second",
    )
'''
    with pytest.raises(ValueError, match="Stimulus 'second'.*no await since stimulus 'first'"):
        validate_verifier_authored_structure([source], {"feature.a", "feature.b"})
    with_progress = source.replace(
        "    # STIMULUS [second]",
        "    dut.start.value = 1\n    await Timer(1, unit='ns')\n"
        "    observed = int(dut.result.value)\n    # STIMULUS [second]",
    )
    validate_verifier_authored_structure([with_progress], {"feature.a", "feature.b"})


def test_checked_record_after_recording_loop_needs_new_dut_progress() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "job", "targets": ["feature.a"]},
    {"label": "summary", "targets": ["feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    for index in range(2):
        await RisingEdge(dut.clk)
        observed = int(dut.result.value)
        # STIMULUS [job]
        _contract_record_checked_stimulus(
            "randomized", {"index": index}, {"result": index}, {"result": observed},
            operations=("op",), label="job",
        )
    # STIMULUS [summary]
    _contract_record_checked_stimulus(
        "directed", {"count": 2}, {"result": 2}, {"result": observed},
        operations=("op",), label="summary",
    )
'''
    with pytest.raises(ValueError, match="Stimulus 'summary'.*no await since stimulus 'job'"):
        validate_verifier_authored_structure([source], {"feature.a", "feature.b"})
    with_progress = source.replace(
        "    # STIMULUS [summary]",
        "    await RisingEdge(dut.clk)\n"
        "    observed = int(dut.result.value)\n"
        "    # STIMULUS [summary]",
    )
    validate_verifier_authored_structure([with_progress], {"feature.a", "feature.b"})


def test_checked_records_separated_by_awaiting_while_true_are_distinct() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "first", "targets": ["feature.a"]},
    {"label": "second", "targets": ["feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    first_observed = int(dut.result.value)
    # STIMULUS [first]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": first_observed},
        operations=("op",), label="first",
    )
    while True:
        await RisingEdge(dut.clk)
        if int(dut.ready.value):
            break
    second_observed = int(dut.result.value)
    # STIMULUS [second]
    _contract_record_checked_stimulus(
        "directed", {"x": 2}, {"result": 2}, {"result": second_observed},
        operations=("op",), label="second",
    )
'''
    validate_verifier_authored_structure([source], {"feature.a", "feature.b"})


def test_checked_records_separated_by_await_in_if_test_are_distinct() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "first", "targets": ["feature.a"]},
    {"label": "second", "targets": ["feature.b"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    first_observed = int(dut.result.value)
    # STIMULUS [first]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": first_observed},
        operations=("op",), label="first",
    )
    while True:
        if await handshake(dut.valid, dut.ready):
            break
    second_observed = int(dut.result.value)
    # STIMULUS [second]
    _contract_record_checked_stimulus(
        "directed", {"x": 2}, {"result": 2}, {"result": second_observed},
        operations=("op",), label="second",
    )
'''
    validate_verifier_authored_structure([source], {"feature.a", "feature.b"})


def test_checked_stimulus_rejects_copied_expected_literal_as_observation() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise():
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": 1},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="identical literal values.*observed must come from a DUT observation"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_rejects_any_literal_observed_field() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(dut):
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"error": 1, "result": 2},
        {"error": 0, "result": int(dut.result.value)},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="literal constants instead of DUT-derived.*error"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_rejects_literal_hidden_behind_aliases() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise():
    empty_outputs = []
    renamed_outputs = empty_outputs
    completion_count = 0
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"outputs": [], "completion": 0},
        {"outputs": renamed_outputs, "completion": completion_count},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="Renaming or aliasing.*constant"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_checked_stimulus_rejects_observed_alias_of_computed_expected() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(dut):
    expected = golden([1, 2, 3])
    observed = expected
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": expected}, {"result": observed},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="observed values alias the expected values"):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_known_operation_requires_tool_owned_logical_io_primitives() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, A, B, expected):
    observed = [int(dut.y_payload.value)]
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"A": A, "B": B}, {"Y": expected}, {"Y": observed},
        operations=("gemm",), label="case",
    )
'''
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions"],
                "feature_extensions": [],
                "inputs": ["A", "B"],
                "outputs": ["Y"],
            }
        ]
    }
    interface = {
        "channels": [
            {"name": "a", "direction": "input", "protocol_profile": "ready_valid", "data_objects": ["A"]},
            {"name": "b", "direction": "input", "protocol_profile": "ready_valid", "data_objects": ["B"]},
            {"name": "y", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["Y"]},
        ],
        "signals": [
            {"name": "a_payload", "channel": "a", "role": "payload"},
            {"name": "b_payload", "channel": "b", "role": "payload"},
            {"name": "y_payload", "channel": "y", "role": "payload"},
        ],
    }
    with pytest.raises(ValueError, match=r"missing_driver_channels=\['a', 'b'\].*missing_collector_channels=\['y'\]"):
        validate_verifier_authored_structure(
            [source],
            {"operation.gemm.dimensions"},
            architecture,
            interface_contract=interface,
        )


def test_awaited_tool_owned_driver_counts_as_real_claimed_channel_drive() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["channel.a.handshake_states", "operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, A, expected):
    a_channel = _contract_protocol_channel("contract_ready_valid", "a")
    y_channel = _contract_protocol_channel("contract_ready_valid", "y")
    await _contract_drive_protocol_field_values(
        dut, "clk", a_channel, field="payload", values=A
    )
    observed = await _contract_collect_protocol_field_values(
        dut, "clk", y_channel, field="payload", count=len(expected)
    )
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "randomized", {"A": A}, {"Y": expected}, {"Y": observed},
        operations=("gemm",), label="case",
    )
'''
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions"],
                "feature_extensions": [],
                "inputs": ["A"],
                "outputs": ["Y"],
            }
        ]
    }
    interface = {
        "channels": [
            {"name": "a", "direction": "input", "protocol_profile": "ready_valid", "data_objects": ["A"]},
            {"name": "y", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["Y"]},
        ],
        "signals": [
            {"name": "a_valid", "direction": "input", "channel": "a", "role": "valid"},
            {"name": "a_ready", "direction": "output", "channel": "a", "role": "ready"},
            {"name": "a_payload", "direction": "input", "channel": "a", "role": "payload"},
            {"name": "y_valid", "direction": "output", "channel": "y", "role": "valid"},
            {"name": "y_ready", "direction": "input", "channel": "y", "role": "ready"},
            {"name": "y_payload", "direction": "output", "channel": "y", "role": "payload"},
        ],
    }
    validate_verifier_authored_structure(
        [source],
        {"channel.a.handshake_states", "operation.gemm.dimensions"},
        architecture,
        interface_contract=interface,
    )


def test_tool_owned_transfer_call_requires_exact_signature_and_await() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, values):
    channel = _contract_protocol_channel("contract_ready_valid", "a")
    _contract_drive_protocol_transfers(dut, channel, values, clock=dut.clk)
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": values}, {"y": values}, {"y": observed},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(
        ValueError,
        match="must be awaited and use the exact exported signature",
    ):
        validate_verifier_authored_structure([source], {"feature.a"})


def test_each_looped_operation_record_requires_its_own_complete_transfers() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [
    {"label": "directed", "targets": ["operation.gemm.dimensions"]},
    {"label": "random", "targets": ["operation.gemm.operand_values"]},
]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, A, expected):
    a_channel = _contract_protocol_channel("contract_ready_valid", "a")
    y_channel = _contract_protocol_channel("contract_ready_valid", "y")
    await _contract_drive_protocol_field_values(
        dut, "clk", a_channel, "payload", A
    )
    directed_observed = await _contract_collect_protocol_field_values(
        dut, "clk", y_channel, "payload", count=len(expected)
    )
    # STIMULUS [directed]
    _contract_record_checked_stimulus(
        "directed", {"A": A}, {"Y": expected}, {"Y": directed_observed},
        operations=("gemm",), label="directed",
    )
    for _ in range(2):
        random_observed = await _contract_collect_protocol_field_values(
            dut, "clk", y_channel, "payload", count=len(expected)
        )
        # STIMULUS [random]
        _contract_record_checked_stimulus(
            "randomized", {"A": A}, {"Y": expected}, {"Y": random_observed},
            operations=("gemm",), label="random",
        )
'''
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions", "operand_values"],
                "feature_extensions": [],
                "inputs": ["A"],
                "outputs": ["Y"],
            }
        ]
    }
    interface = {
        "channels": [
            {"name": "a", "direction": "input", "protocol_profile": "ready_valid", "data_objects": ["A"]},
            {"name": "y", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["Y"]},
        ],
        "signals": [
            {"name": "a_payload", "direction": "input", "channel": "a", "role": "payload"},
            {"name": "y_payload", "direction": "output", "channel": "y", "role": "payload"},
        ],
    }
    with pytest.raises(
        ValueError,
        match=r"Checked stimulus 'random'.*missing_driver_channels=\['a'\]",
    ):
        validate_verifier_authored_structure(
            [source],
            {"operation.gemm.dimensions", "operation.gemm.operand_values"},
            architecture,
            interface_contract=interface,
        )


def test_empty_tool_owned_transfers_receive_no_operation_credit() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "empty", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, A, expected):
    a_channel = _contract_protocol_channel("contract_ready_valid", "a")
    y_channel = _contract_protocol_channel("contract_ready_valid", "y")
    await _contract_drive_protocol_field_values(
        dut, "clk", a_channel, field="payload", values=[]
    )
    observed = await _contract_collect_protocol_field_values(
        dut, "clk", y_channel, field="payload", count=0
    )
    # STIMULUS [empty]
    _contract_record_checked_stimulus(
        "randomized", {"A": A}, {"Y": expected}, {"Y": observed},
        operations=("gemm",), label="empty",
    )
'''
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions"],
                "feature_extensions": [],
                "inputs": ["A"],
                "outputs": ["Y"],
            }
        ]
    }
    interface = {
        "channels": [
            {"name": "a", "direction": "input", "protocol_profile": "ready_valid", "data_objects": ["A"]},
            {"name": "y", "direction": "output", "protocol_profile": "ready_valid", "data_objects": ["Y"]},
        ],
        "signals": [
            {"name": "a_payload", "direction": "input", "channel": "a", "role": "payload"},
            {"name": "y_payload", "direction": "output", "channel": "y", "role": "payload"},
        ],
    }
    with pytest.raises(
        ValueError,
        match=r"missing_driver_channels=\['a'\].*missing_collector_channels=\['y'\]",
    ):
        validate_verifier_authored_structure(
            [source], {"operation.gemm.dimensions"}, architecture,
            interface_contract=interface,
        )


def test_completed_operation_record_requires_declared_job_start_channel() -> None:
    from multigent.tests.test_canonical_operation import contracts

    architecture, interface = contracts()
    interface["channels"].append(
        {
            "name": "cmd",
            "direction": "input",
            "protocol_profile": "ready_valid",
            "data_objects": [],
        }
    )
    interface["signals"].extend(
        [
            {"name": "cmd_valid", "direction": "input", "channel": "cmd", "role": "valid"},
            {"name": "cmd_ready", "direction": "output", "channel": "cmd", "role": "ready"},
            {"name": "cmd_payload", "direction": "input", "channel": "cmd", "role": "payload", "semantic_class": "command"},
        ]
    )
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["operation.gemm_core.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut, A, B, bias, expected):
    a_channel = _contract_protocol_channel("contract_ready_valid", "a")
    b_channel = _contract_protocol_channel("contract_ready_valid", "b")
    bias_channel = _contract_protocol_channel("contract_ready_valid", "bias")
    y_channel = _contract_protocol_channel("contract_ready_valid", "y")
    await _contract_drive_protocol_field_values(dut, "clk", a_channel, "payload", A)
    await _contract_drive_protocol_field_values(dut, "clk", b_channel, "payload", B)
    await _contract_drive_protocol_field_values(dut, "clk", bias_channel, "payload", bias)
    observed = await _contract_collect_protocol_field_values(
        dut, "clk", y_channel, "payload", count=len(expected)
    )
    # STIMULUS [job]
    _contract_record_checked_stimulus(
        "randomized",
        {"A_matrix": A, "B_matrix": B, "bias_vector": bias},
        {"Y_matrix": expected}, {"Y_matrix": observed},
        operations=("gemm_core",), label="job",
    )
'''
    with pytest.raises(
        ValueError,
        match=r"missing_job_start_channels=\['cmd'\]",
    ):
        validate_verifier_authored_structure(
            [source], {"operation.gemm_core.dimensions"}, architecture,
            interface_contract=interface,
        )


def test_protocol_only_intent_cannot_enter_known_operation_ledger() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "illegal", "targets": ["signal.error.error_behavior"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    observed_error = int(dut.error.value)
    # STIMULUS [illegal]
    _contract_record_checked_stimulus(
        "randomized", {"opcode": 2}, {"error": 1}, {"error": observed_error},
        operations=("gemm",), label="illegal",
    )
'''
    architecture = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": [],
                "feature_extensions": [],
                "inputs": [],
                "outputs": [],
            }
        ]
    }
    with pytest.raises(
        ValueError,
        match=r"unexpected_record_operations=\['gemm'\].*protocol/error/reset-only",
    ):
        validate_verifier_authored_structure(
            [source], {"signal.error.error_behavior"}, architecture,
        )


def test_checked_stimulus_accepts_list_updated_by_dut_observation() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    outputs = []
    await RisingEdge(dut.clk)
    outputs.append(int(dut.result.value))
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"outputs": [1]}, {"outputs": outputs},
        operations=("op",), label="case",
    )
'''
    validate_verifier_authored_structure([source], {"feature.a"})


def test_passed_stimulus_control_must_be_used_by_local_helper() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "stall", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def run_job(dut, directed_input_stalls=False):
    await Timer(1, unit="ns")
    return int(dut.result.value)
async def exercise(dut):
    observed = await run_job(dut, directed_input_stalls=True)
    # STIMULUS [stall]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="stall",
    )
'''
    with pytest.raises(ValueError, match="never reads passed keyword 'directed_input_stalls'"):
        validate_verifier_authored_structure([source], {"feature.a"})
    using_control = source.replace(
        '    await Timer(1, unit="ns")',
        '    if directed_input_stalls:\n        dut.input_valid.value = 1\n'
        '    await Timer(1, unit="ns")',
    )
    validate_verifier_authored_structure([using_control], {"feature.a"})


def test_invalid_cocotb_timeout_unit_is_rejected_before_simulation() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
@cocotb.test(timeout_time=2, timeout_unit="s")
async def exercise(dut):
    await Timer(1, units="ns")
    observed = int(dut.result.value)
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="case",
    )
'''
    with pytest.raises(ValueError, match="Cocotb time unit 's' is invalid.*Use 'sec'"):
        validate_verifier_authored_structure([source], {"feature.a"})
    validate_verifier_authored_structure(
        [source.replace('timeout_unit="s"', 'timeout_unit="sec"')],
        {"feature.a"},
    )


def test_stall_helper_cannot_replay_beat_after_unchecked_ready_edge() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "stall", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def send_one(valid_sig, ready_sig, payload_sig, value):
    await RisingEdge(clk)
async def send_one_with_stall(valid_sig, ready_sig, payload_sig, value, cycles):
    for _ in range(cycles):
        valid_sig.value = 1
        payload_sig.value = value
        await RisingEdge(clk)
    await send_one(valid_sig, ready_sig, payload_sig, value)
async def exercise(dut):
    await send_one_with_stall(dut.input_valid, dut.input_ready, dut.input_payload, 1, 3)
    observed = int(dut.result.value)
    # STIMULUS [stall]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="stall",
    )
'''
    with pytest.raises(ValueError, match="may transfer a beat before replay"):
        validate_verifier_authored_structure([source], {"feature.a"})
    checked = source.replace(
        '        await RisingEdge(clk)\n    await send_one',
        '        await RisingEdge(clk)\n'
        '        if int(ready_sig.value):\n            return\n'
        '    await send_one',
    )
    validate_verifier_authored_structure([checked], {"feature.a"})


def test_output_ready_cannot_remain_low_in_unbounded_handshake_wait() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def exercise(dut):
    for beat in range(4):
        dut.y_ready.value = 0 if beat % 2 == 0 else 1
        while True:
            await FallingEdge(dut.clk)
            valid = int(dut.y_valid.value)
            ready = int(dut.y_ready.value)
            await RisingEdge(dut.clk)
            if valid and ready:
                break
    observed = int(dut.result.value)
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="case",
    )
'''
    interface_contract = {
        "channels": [{"name": "y", "signals": {"ready": "y_ready"}}],
        "signals": [{"name": "y_ready", "direction": "input"}],
    }
    with pytest.raises(ValueError, match="permanent backpressure"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )
    progressing = source.replace(
        "            await FallingEdge(dut.clk)",
        "            dut.y_ready.value = 1\n            await FallingEdge(dut.clk)",
    )
    validate_verifier_authored_structure(
        [progressing], {"feature.a"}, interface_contract=interface_contract
    )


def test_catalog_operation_requires_randomized_record_kind() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(observed):
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"A": [1], "B": [1]}, {"Y": [1]}, {"Y": observed},
        operations=("gemm",), label="case",
    )
'''
    architecture_contract = {
        "operations": [
            {
                "name": "gemm",
                "kind": "matrix_multiply",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions"],
                "feature_extensions": [],
                "inputs": ["A", "B"],
                "outputs": ["Y"],
            }
        ]
    }
    with pytest.raises(ValueError, match="no literal 'randomized'"):
        validate_verifier_authored_structure(
            [source], {"operation.gemm.dimensions"}, architecture_contract
        )
    randomized = source.replace('"directed", {"A": [1]', '"randomized", {"A": [1]')
    validate_verifier_authored_structure(
        [randomized], {"operation.gemm.dimensions"}, architecture_contract
    )


def test_operation_claim_requires_complete_architect_data_object_mapping() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "job", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(accepted):
    # STIMULUS [job]
    _contract_record_checked_stimulus(
        "randomized", {"cmd": 1}, {"accepted": 1}, {"accepted": accepted},
        operations=("gemm",), label="job",
    )
'''
    architecture_contract = {
        "operations": [
            {
                "name": "gemm",
                "coverage_family": "matrix_multiply",
                "coverage_family_source": "catalog",
                "features": ["dimensions"],
                "feature_extensions": [],
                "inputs": ["A_matrix", "B_matrix", "bias_vector"],
                "outputs": ["Y_matrix"],
            }
        ]
    }
    with pytest.raises(ValueError, match="does not isolate canonical data objects"):
        validate_verifier_authored_structure(
            [source], {"operation.gemm.dimensions"}, architecture_contract
        )
    complete = source.replace(
        '{"cmd": 1}, {"accepted": 1}, {"accepted": accepted}',
        '{"A_matrix": A, "B_matrix": B, "bias_vector": bias}, '
        '{"Y_matrix": expected}, {"Y_matrix": observed}',
    )
    validate_verifier_authored_structure(
        [complete], {"operation.gemm.dimensions"}, architecture_contract
    )
    mixed_status = complete.replace(
        '{"Y_matrix": expected}, {"Y_matrix": observed}',
        '{"Y_matrix": expected, "completion": 1}, '
        '{"Y_matrix": observed, "completion": completion}',
    )
    with pytest.raises(ValueError, match=r"extra_expected_fields=\['completion'\]"):
        validate_verifier_authored_structure(
            [mixed_status], {"operation.gemm.dimensions"}, architecture_contract
        )


def test_each_cocotb_test_initializes_all_monitored_contract_inputs() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
@cocotb.test(timeout_time=1, timeout_unit="us")
async def test_case(dut):
    dut.rst_n.value = 0
    dut.a_valid.value = 0
    observed = int(dut.result.value)
    await RisingEdge(dut.clk)
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": 1}, {"result": observed},
        operations=("op",), label="case",
    )
'''
    interface_contract = {
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "a_valid", "role": "valid", "direction": "input", "reset_value": "0"},
            {"name": "a_payload", "role": "payload", "direction": "input", "reset_value": "0"},
        ]
    }
    with pytest.raises(ValueError, match=r"missing=\['a_payload'\]"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )
    initialized = source.replace(
        "    dut.a_valid.value = 0", "    dut.a_valid.value = 0\n    dut.a_payload.value = 0"
    )
    validate_verifier_authored_structure(
        [initialized], {"feature.a"}, interface_contract=interface_contract
    )


def test_randomized_minimum_requires_unconditional_literal_loop_records() -> None:
    source = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "rand", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(A, B, Y, Y_observed):
    _contract_record_checked_stimulus(
        "randomized", {"A": A, "B": B}, {"Y": Y}, {"Y": Y_observed},
        operations=("gemm",), label="rand",
    )
'''
    architecture_contract = {
        "operations": [{
            "name": "gemm", "coverage_family": "matrix_multiply",
            "coverage_family_source": "catalog", "features": ["dimensions"],
            "feature_extensions": [], "inputs": ["A", "B"], "outputs": ["Y"],
        }]
    }
    with pytest.raises(ValueError, match="proven_maximum=1"):
        validate_verifier_authored_structure(
            [source], {"operation.gemm.dimensions"}, architecture_contract,
            randomized_transactions_minimum=100,
        )
    looped = '''
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "rand", "targets": ["operation.gemm.dimensions"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
def exercise(A, B, Y, Y_observed):
    for _ in range(100):
        # STIMULUS [rand]
        _contract_record_checked_stimulus(
            "randomized", {"A": A, "B": B}, {"Y": Y}, {"Y": Y_observed},
            operations=("gemm",), label="rand",
        )
'''
    validate_verifier_authored_structure(
        [looped], {"operation.gemm.dimensions"}, architecture_contract,
        randomized_transactions_minimum=100,
    )
    conditional = looped.replace(
        "        _contract_record_checked_stimulus(",
        "        if A:\n            _contract_record_checked_stimulus(",
    ).replace(
        '            "randomized",', '                "randomized",'
    ).replace(
        '            operations=', '                operations='
    ).replace('        )\n', '            )\n')
    with pytest.raises(ValueError, match="conditional_or_dynamic_calls"):
        validate_verifier_authored_structure(
            [conditional], {"operation.gemm.dimensions"}, architecture_contract,
            randomized_transactions_minimum=100,
        )


def test_no_queue_command_cannot_be_restarted_by_full_job_helper() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def full_job(dut):
    dut.cmd_valid.value = 1
    await FallingEdge(dut.clk)
    await Timer(1, unit="ns")
    observed = [int(dut.y_payload.value)]
    return observed

@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_case(dut):
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_payload.value = 0
    dut.y_ready.value = 0
    await RisingEdge(dut.clk)
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)
    observed = await full_job(dut)
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"x": 1}, {"result": [1]}, {"result": observed},
        operations=("op",), label="case",
    )
'''
    interface_contract = {
        "channels": [
            {
                "name": "cmd",
                "direction": "input",
                "ordering": "Only accepted in IDLE; no queueing",
                "data_objects": [],
            },
            {
                "name": "y",
                "direction": "output",
                "data_objects": ["result"],
            },
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_payload", "role": "payload", "semantic_class": "command", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "y_valid", "role": "valid", "channel": "y", "direction": "output", "reset_value": "0"},
            {"name": "y_payload", "role": "payload", "channel": "y", "direction": "output", "reset_value": "0"},
            {"name": "y_ready", "role": "ready", "channel": "y", "direction": "input", "reset_value": "0"},
        ],
    }
    with pytest.raises(ValueError, match="IDLE-only/no-queue"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )

    fixed = source.replace(
        "    dut.cmd_valid.value = 1\n    await RisingEdge(dut.clk)\n    observed = await full_job(dut)",
        "    observed = await full_job(dut)",
    )
    validate_verifier_authored_structure(
        [fixed], {"feature.a"}, interface_contract=interface_contract
    )


def test_full_operation_loop_records_every_completed_iteration() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def full_job(dut):
    dut.cmd_valid.value = 1
    await FallingEdge(dut.clk)
    await Timer(1, unit="ns")
    observed = [int(dut.y_payload.value)]
    return observed

@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_case(dut):
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_payload.value = 0
    dut.y_ready.value = 0
    await RisingEdge(dut.clk)
    for iteration in range(2):
        observed = await full_job(dut)
        if iteration == 0:
            # STIMULUS [case]
            _contract_record_checked_stimulus(
                "directed", {"x": iteration}, {"result": [1]}, {"result": observed},
                operations=("op",), label="case",
            )
'''
    interface_contract = {
        "channels": [
            {"name": "cmd", "direction": "input", "data_objects": []},
            {"name": "y", "direction": "output", "data_objects": ["result"]},
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_payload", "role": "payload", "semantic_class": "command", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "y_payload", "role": "payload", "channel": "y", "direction": "output", "reset_value": "0"},
            {"name": "y_ready", "role": "ready", "channel": "y", "direction": "input", "reset_value": "0"},
        ],
    }
    with pytest.raises(ValueError, match="Every completed DUT job"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )

    fixed = source.replace(
        "        if iteration == 0:\n            # STIMULUS [case]\n            _contract_record_checked_stimulus(\n                \"directed\", {\"x\": iteration}, {\"result\": [1]}, {\"result\": observed},\n                operations=(\"op\",), label=\"case\",\n            )",
        "        # STIMULUS [case]\n        _contract_record_checked_stimulus(\n            \"directed\", {\"x\": iteration}, {\"result\": [1]}, {\"result\": observed},\n            operations=(\"op\",), label=\"case\",\n        )",
    )
    validate_verifier_authored_structure(
        [fixed], {"feature.a"}, interface_contract=interface_contract
    )


def test_one_cycle_command_error_is_not_sampled_after_next_active_edge() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
async def send_cmd(dut):
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0

@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_case(dut):
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_payload.value = 0
    await send_cmd(dut)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    observed_error = int(dut.error.value)
    # LLM-GENERATED PROTOCOL ASSERTION [error_pulse]
    assert observed_error == 1
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 2}, {"error": 1}, {"error": observed_error},
        operations=("op",), label="case",
    )
'''
    interface_contract = {
        "channels": [{"name": "cmd", "direction": "input", "data_objects": []}],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_payload", "role": "payload", "semantic_class": "command", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "error", "role": "error", "direction": "output", "width": "1", "reset_value": "0", "semantic": "One-cycle pulse on illegal command acceptance"},
        ],
    }
    with pytest.raises(ValueError, match="already clear the pulse"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )

    fixed = source.replace("    await RisingEdge(dut.clk)\n    await Timer", "    await Timer", 1)
    validate_verifier_authored_structure(
        [fixed], {"feature.a"}, interface_contract=interface_contract
    )

    direct_record = source.replace(
        "    observed_error = int(dut.error.value)\n    # LLM-GENERATED PROTOCOL ASSERTION [error_pulse]\n    assert observed_error == 1",
        "    # LLM-GENERATED PROTOCOL ASSERTION [error_pulse]\n    assert int(dut.rst_n.value) == 1",
    ).replace(
        '{"error": observed_error}', '{"error": int(dut.error.value)}'
    )
    with pytest.raises(ValueError, match="already clear the pulse"):
        validate_verifier_authored_structure(
            [direct_record], {"feature.a"}, interface_contract=interface_contract
        )

    vacuous = fixed.replace(
        "assert observed_error == 1", "assert int(dut.error.value) in (0, 1)"
    )
    with pytest.raises(ValueError, match="complete binary domain"):
        validate_verifier_authored_structure(
            [vacuous], {"feature.a"}, interface_contract=interface_contract
        )


def test_inline_command_pulse_monitor_starts_before_next_active_edge() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "case", "targets": ["feature.a"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_case(dut):
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_payload.value = 0
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 1
    while True:
        await Timer(1, unit="ns")
        ready = int(dut.cmd_ready.value)
        await RisingEdge(dut.clk)
        if ready:
            break
        await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0
    saw_error = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        if int(dut.error.value) == 1:
            saw_error = 1
    # LLM-GENERATED PROTOCOL ASSERTION [error_pulse]
    assert saw_error == 1
    # STIMULUS [case]
    _contract_record_checked_stimulus(
        "directed", {"cmd": 2}, {"status": {"error": 1}},
        {"status": {"error": saw_error}}, operations=("op",), label="case",
    )
'''
    interface_contract = {
        "channels": [{"name": "cmd", "direction": "input", "data_objects": []}],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_payload", "role": "payload", "semantic_class": "command", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_ready", "role": "ready", "channel": "cmd", "direction": "output", "reset_value": "0"},
            {"name": "error", "role": "error", "direction": "output", "width": "1", "reset_value": "0", "semantic": "One-cycle pulse on illegal command acceptance"},
        ],
    }
    with pytest.raises(ValueError, match="Start the pulse monitor before"):
        validate_verifier_authored_structure(
            [source], {"feature.a"}, interface_contract=interface_contract
        )


def test_reset_abort_operation_record_requires_post_reset_relaunch() -> None:
    source = '''
import cocotb
# === STIMULUS AND COVERAGE INTENT ===
STIMULUS_COVERAGE_INTENTS = [{"label": "abort", "targets": ["signal.rst_n.reset_behavior", "operation.op.activation"]}]
# === LLM-GENERATED OPERATION ASSERTIONS ===
@cocotb.test(timeout_time=1, timeout_unit="us")
@contract_coverage()
async def test_case(dut):
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_payload.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    observed_y = [int(dut.y_payload.value)]
    # STIMULUS [abort]
    _contract_record_checked_stimulus(
        "directed", {"A": [1]}, {"Y": [0]}, {"Y": observed_y},
        operations=("op",), label="abort",
    )
'''
    interface_contract = {
        "channels": [
            {"name": "cmd", "direction": "input", "data_objects": []},
            {"name": "y", "direction": "output", "data_objects": ["Y"]},
        ],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "reset_value": "0"},
            {"name": "rst_n", "role": "reset", "direction": "input", "reset_value": "0"},
            {"name": "cmd_valid", "role": "valid", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "cmd_payload", "role": "payload", "semantic_class": "command", "channel": "cmd", "direction": "input", "reset_value": "0"},
            {"name": "y_payload", "role": "payload", "channel": "y", "direction": "output", "reset_value": "0"},
        ],
        "global_handshake_rules": {
            "stall_behavior": "Reset aborts in-flight work using non-attributable discard"
        },
    }
    with pytest.raises(ValueError, match="non-attributable discard"):
        validate_verifier_authored_structure(
            [source],
            {"signal.rst_n.reset_behavior", "operation.op.activation"},
            interface_contract=interface_contract,
        )
