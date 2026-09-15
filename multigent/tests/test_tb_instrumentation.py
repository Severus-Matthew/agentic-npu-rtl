from __future__ import annotations

from types import MappingProxyType

import pytest

from multigent.verifier_tool.coverage.protocol.plan import build_interface_coverage_plan
from multigent.verifier_tool.coverage.runtime import ContractSnapshot, capture_contract_snapshot
from multigent.verifier_tool.predefined_assertion.instrumentation import (
    BEGIN_MARKER,
    END_MARKER,
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
    assert "# PROTOCOL ASSERTION [channel.out.stall_stability]" in installed
    assert "CONTRACT_SIGNAL_NAMES = ('clk', 'rst', 'valid', 'ready', 'data')" in installed
    validate_contract_generated_block(installed, plan())
    with pytest.raises(ValueError, match="modified"):
        validate_contract_generated_block(
            installed.replace("snapshot['valid']", "snapshot['ready']", 1), plan()
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
            }
        ]
    }
    installed = install_contract_generated_block(
        "import cocotb\n", plan(), architecture
    )
    assert "# CATALOG OPERATION [gemm]" in installed
    assert "# OPERATION ASSERTION [operation.gemm.dimensions]" in installed
    assert "# OPERATION ASSERTION [operation.gemm.runtime_shape]" in installed
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
    assert namespace["_CONTRACT_PROTOCOL_STATE"] == {}


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
    "directed", {"value": 1}, {"result": 1}, {"result": 1},
    operations=("add",), label="edges",
)
'''
    validate_verifier_authored_structure([valid], required)
    with pytest.raises(ValueError, match="missing=.*feature.b"):
        validate_verifier_authored_structure(
            [valid.replace(', "feature.b"', "")], required
        )


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
        "directed", {"value": 1}, {"result": 1}, {"result": 1},
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
