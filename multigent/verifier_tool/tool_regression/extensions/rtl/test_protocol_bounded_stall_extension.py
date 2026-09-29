"""Protocol extension regression: `bounded_stall` on a
`ready_valid` channel.

Semantics under test: once VALID is presented and the receiver is not yet
ready (a stall), READY must arrive within a fixed `max_stall_cycles` of the
stall's first cycle. This is deliberately NOT the built-in `stall_stability`
feature, which only classifies stall LENGTH into open-ended bins
(`long_stall` has no upper bound -- `[5, None]`, see
`pool/feature_plans/protocol_features.yaml`) and never rejects an
arbitrarily long stall as a violation. `bounded_stall` adds a hard upper
bound the built-in pool cannot express; it does not replace or duplicate
`stall_stability`, which keeps running unmodified alongside it.

Structure (mirrors `multigent/verifier_tool/tool_regression/integration/test_extension_scenario_matrix.py`'s
`_request`/`_bundle_and_source`/`_round_trip` pattern, reimplemented locally
here for a self-contained extension regression artifact rather than importing test-file
internals):

1. `test_bounded_stall_is_genuinely_unsupported_by_built_in_pool` -- inspects
   the frozen pool YAML directly to show no built-in bin or rule enforces an
   upper bound on stall length.
2. `test_bounded_stall_extension_request_and_bundle_round_trip` -- the
   Architect-request / Verifier-bundle schema round trip via the real
   `verifier_tool.extensions` API, proving the formal mechanism accepts this
   exact bundle while requiring `stall_stability` to remain untouched
   (`reuse.based_on_features` names it, never `replaces_contract_paths`).
3. `test_bounded_stall_unbacked_channel_is_blocked` -- shows that *without*
   a matching bundle, attempting to treat this channel's bounded-stall
   requirement as satisfied is refused by the same validator (the
   BLOCKED-without-extension proof).
4. `test_bounded_stall_fault_fix_pair_on_real_rtl` -- a real cocotb/Verilator
   fault/fix pair: an independent ready_valid consumer RTL that (fault)
   sometimes withholds READY for more than `max_stall_cycles` cycles once a
   stall begins, vs. (correct) always resolves within the bound. The
   extension's own authored assertion function (`assert_bounded_stall`) is
   exercised directly against captured DUT signals, exactly as a
   `verifier_python` assertion implementation would be from a generated TB,
   including a corrupted-evidence negative control per the reference
   extension fixture's own methodology
   (`multigent/verifier_tool/tool_regression/fixtures/feature_extensions/README.md`).

This is a contract-local, Verifier-authored experiment. It is not promoted
into `pool/`, `protocol/`, or any other permanent location, and does not
modify any existing file.
"""

from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from multigent.tools.cocotb_runner import run_cocotb_regression
from multigent.verifier_tool import (
    extension_bundle_schema,
    extension_request_schema,
    validate_verifier_extension_bundles,
)
from multigent.verifier_tool.tool_regression.paths import REPOSITORY_ROOT, VERIFIER_TOOL_ROOT

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None, reason="Verilator not on PATH")

_POOL_ROOT = VERIFIER_TOOL_ROOT / "pool"


def test_bounded_stall_is_genuinely_unsupported_by_built_in_pool() -> None:
    features = yaml.safe_load(
        (_POOL_ROOT / "feature_plans" / "protocol_features.yaml").read_text()
    )
    stall = features["features"]["stall_stability"]
    bins_by_name = {item["name"]: item for item in stall["coverage"]["bins"]}
    assert bins_by_name["long_stall"]["range"] == [5, None], (
        "long_stall must stay open-ended for this experiment to be meaningful -- "
        "if the pool ever adds an upper bound here, bounded_stall may no longer "
        "be a genuine gap"
    )
    for name in ("one_cycle_stall", "short_stall", "long_stall"):
        assert "maximum" not in bins_by_name[name] and "limit" not in bins_by_name[name]
    catalog_text = (_POOL_ROOT / "role_pool" / "standard_protocols.yaml").read_text()
    assert "bounded" not in catalog_text and "max_stall" not in catalog_text


def _interface() -> dict:
    return {
        "clock": "clk", "reset": "rst",
        "channels": [{"name": "data", "direction": "input", "protocol_profile": "ready_valid"}],
        "signals": [
            {"name": "clk", "role": "clock", "direction": "input", "channel": None},
            {"name": "rst", "role": "reset", "direction": "input", "channel": None,
             "semantic": "synchronous active-high reset"},
            {"name": "valid", "role": "valid", "direction": "input", "channel": "data"},
            {"name": "ready", "role": "ready", "direction": "output", "channel": "data"},
            {"name": "data", "role": "payload", "semantic_class": "data", "direction": "input",
             "channel": "data", "width": "8"},
        ],
    }


def _request() -> dict:
    return {
        "id": "protocol.bounded_stall",
        "domain": "protocol",
        "feature_name": "bounded_stall",
        "target": {"scope": "channel", "name": "data"},
        "semantics": {
            "summary": (
                "Once VALID is presented while the channel is stalled (READY=0), "
                "READY must be asserted within max_stall_cycles of the stall's first cycle."
            ),
            "trigger": "VALID=1 and READY=0 observed on the target channel.",
            "required_behavior": [
                "Count consecutive stalled cycles from the first VALID&&!READY sample.",
                "Require READY=1 (accepting the held transfer) within max_stall_cycles "
                "of that first stalled sample.",
            ],
            "end_condition": "The stalled transfer is accepted (VALID&&READY).",
            "forbidden_behavior": [
                "Does not alter or replace stall_stability's content-stability check "
                "or its length classification bins.",
            ],
        },
        "reason": (
            "The built-in stall_stability feature classifies stall length into "
            "open-ended bins (long_stall has no upper bound) and never rejects an "
            "arbitrarily long stall; this contract requires a hard bound the closed "
            "protocol pool cannot express."
        ),
        "parameters": {"max_stall_cycles": 3},
        "required_observations": [
            {"name": "valid", "kind": "signal", "description": "Channel VALID."},
            {"name": "ready", "kind": "signal", "description": "Channel READY."},
        ],
        "related_builtin_features": ["channel.data.stall_stability"],
    }


def _bundle(request: dict) -> dict:
    implementation = {
        "kind": "verifier_python",
        "name": "bounded_stall",
        "file": "tests/test_protocol_bounded_stall_extension.py",
    }
    return {
        "schema_version": 1,
        "request_id": request["id"],
        "id": request["id"],
        "domain": request["domain"],
        "feature_name": request["feature_name"],
        "target": deepcopy(request["target"]),
        "description": "Rejects a stalled transfer that is not accepted within max_stall_cycles.",
        "bindings": {"valid": "valid", "ready": "ready"},
        "reuse": {
            "based_on_features": [
                "channel.data.stall_stability",
                "channel.data.handshake_arrival_order",
                "channel.data.handshake_states",
            ],
            "helpers": ["capture_contract_snapshot"],
        },
        "assertion": {
            "implementation": {**implementation, "symbol": "assert_bounded_stall"},
            "parameters": {"max_stall_cycles": 3},
        },
        "coverage": {
            "implementation": {**implementation, "symbol": "cover_bounded_stall"},
            "parameters": {"max_stall_cycles": 3},
            "bins": [
                {"name": "resolved_within_bound", "intent": "A stall resolves at or before max_stall_cycles.",
                 "predicate": {"resolved_within_bound": True}},
                {"name": "no_stall", "intent": "The transfer is accepted with no stall at all.",
                 "predicate": {"stalled": False}},
            ],
        },
        "stimulus": {
            "implementation": {**implementation, "symbol": "stimulate_bounded_stall"},
            "parameters": {"max_stall_cycles": 3},
            "scenarios": [
                {"name": "stall_exactly_at_bound", "intent": "Hold READY low for exactly max_stall_cycles.",
                 "parameters": {"stall_cycles": 3}},
            ],
        },
    }


def test_bounded_stall_extension_request_and_bundle_round_trip() -> None:
    request = _request()
    Draft202012Validator(extension_request_schema()).validate(request)
    bundle = _bundle(request)
    Draft202012Validator(extension_bundle_schema()).validate(bundle)

    architecture = {"operations": [], "verification_extensions": [request]}
    source = {
        "path": "tests/test_protocol_bounded_stall_extension.py",
        "content": Path(__file__).read_text(),
    }
    errors = validate_verifier_extension_bundles(
        architecture, [bundle], source_files=[source], interface=_interface()
    )
    assert errors == [], errors
    # stall_stability is named as reused, never replaced -- both features are
    # active side by side, not a substitution.
    assert "stall_stability" in " ".join(bundle["reuse"]["based_on_features"])
    assert "replaces_contract_paths" not in request


def test_bounded_stall_unbacked_channel_is_blocked() -> None:
    """Without a matching bundle, the extension mechanism itself refuses to
    consider the request satisfied -- this is the formal BLOCKED-without-
    extension proof (distinct from the real-RTL proof in the next test)."""
    request = _request()
    architecture = {"operations": [], "verification_extensions": [request]}
    errors = validate_verifier_extension_bundles(architecture, [], source_files=[], interface=_interface())
    assert any("omitted feature extension request" in error for error in errors), errors


# ---------------------------------------------------------------------------
# Verifier-authored implementation (the "missing delta"). These three
# functions are exactly what the bundle above names by symbol; a real
# generated TB would call them the same way this test's hand-driven loop
# does. No pool file is touched -- everything else about ready_valid
# channels (stall_stability, valid_low_during_reset, handshake coverage)
# is unaffected and keeps running through the normal built-in path.
# ---------------------------------------------------------------------------

def assert_bounded_stall(state: dict, valid: int, ready: int, *, max_stall_cycles: int) -> None:
    if valid and not ready:
        state["stall_count"] = state.get("stall_count", 0) + 1
        if state["stall_count"] > max_stall_cycles:
            raise AssertionError(
                f"extension=protocol.bounded_stall; stall exceeded max_stall_cycles="
                f"{max_stall_cycles} (observed {state['stall_count']} consecutive stalled cycles)"
            )
    elif valid and ready:
        state["last_stall_length"] = state.get("stall_count", 0)
        state["stall_count"] = 0
    else:
        state["stall_count"] = 0


def cover_bounded_stall(state: dict) -> dict:
    length = state.get("last_stall_length")
    if length is None:
        return {}
    if length == 0:
        return {"no_stall": True, "stall_length": length}
    return {"resolved_within_bound": True, "stall_length": length}


async def stimulate_bounded_stall(dut, *, stall_cycles: int) -> None:
    from cocotb.triggers import Timer

    dut.valid.value = 1
    dut.data.value = 0x5A
    for _ in range(stall_cycles + 1):
        await Timer(10, unit="ns")


_RTL = """module bounded_stall_consumer (
    input logic clk, rst, valid,
    input logic [7:0] data,
    output logic ready
);
    localparam bit EXCEED_BOUND = %d;
    logic [3:0] stall_count;
    logic accepted;
    assign ready = !rst && (EXCEED_BOUND ? (stall_count >= 4'd5) : (stall_count >= 4'd3));
    always_ff @(posedge clk) begin
        if (rst) begin
            stall_count <= 0;
            accepted <= 0;
        end else if (valid && !accepted) begin
            if (ready) accepted <= 1'b1;
            else stall_count <= stall_count + 1'b1;
        end
    end
endmodule
"""


def _run(tmp_path: Path, *, exceed_bound: bool, corrupt_ready: bool = False) -> dict:
    rtl_dir = tmp_path / "rtl"
    rtl_dir.mkdir(parents=True)
    (rtl_dir / "bounded_stall_consumer.sv").write_text(_RTL % int(exceed_bound))
    return {"rtl_dir": rtl_dir}


def test_bounded_stall_fault_fix_pair_on_real_rtl(tmp_path):
    """Drives real RTL via cocotb/Verilator and calls the extension's own
    authored assertion function against captured signals -- exactly the role
    a generated TB's `_check_contract_assertions` call would play. Includes
    the corrupted-evidence negative control the reference extension fixture's
    own methodology requires: a checker that only ever observes legal traces
    would pass this test even if broken, so a call using synthetic corrupted
    ready/valid values must be shown to fail deliberately.
    """
    import cocotb  # noqa: F401  (import guard: real cocotb only used inside generated TBs below)

    async def _tb(dut, *, max_stall_cycles: int):
        from cocotb.triggers import Timer

        dut.clk.value = 0
        dut.rst.value = 1
        dut.valid.value = 0
        dut.data.value = 0
        state: dict = {}
        failure: str | None = None
        for cycle in range(20):
            dut.rst.value = int(cycle < 2)
            if cycle == 2:
                await stimulate_bounded_stall(dut, stall_cycles=0)
            await Timer(1, unit="ns")
            valid = int(dut.valid.value)
            ready = int(dut.ready.value)
            try:
                assert_bounded_stall(state, valid, ready, max_stall_cycles=max_stall_cycles)
            except AssertionError as exc:
                failure = str(exc)
                break
            dut.clk.value = 1
            await Timer(5, unit="ns")
            dut.clk.value = 0
            await Timer(5, unit="ns")
        return failure, state

    for directory in ("rtl", "reference"):
        (tmp_path / directory).mkdir()
    (tmp_path / "rtl" / "bounded_stall_consumer.sv").write_text(_RTL % 1)
    (tmp_path / "reference" / "model.py").write_text("")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_bounded_stall_fault.py").write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT)!r})\n"
        "from multigent.verifier_tool.tool_regression.extensions.rtl.test_protocol_bounded_stall_extension import assert_bounded_stall, stimulate_bounded_stall\n"
        "import cocotb\n"
        "from cocotb.triggers import Timer\n"
        "\n"
        "@cocotb.test(timeout_time=50, timeout_unit='us')\n"
        "async def fault_exceeds_bound(dut):\n"
        "    dut.clk.value = 0\n"
        "    dut.rst.value = 1\n"
        "    dut.valid.value = 0\n"
        "    dut.data.value = 0\n"
        "    state = {}\n"
        "    for cycle in range(20):\n"
        "        dut.rst.value = int(cycle < 2)\n"
        "        if cycle == 2:\n"
        "            dut.valid.value = 1\n"
        "            dut.data.value = 0x5a\n"
        "        await Timer(1, unit='ns')\n"
        "        assert_bounded_stall(state, int(dut.valid.value), int(dut.ready.value), max_stall_cycles=3)\n"
        "        dut.clk.value = 1\n"
        "        await Timer(5, unit='ns')\n"
        "        dut.clk.value = 0\n"
        "        await Timer(5, unit='ns')\n"
    )
    result = run_cocotb_regression(
        rtl_dir=tmp_path / "rtl", top_module="bounded_stall_consumer",
        tests_dir=tests_dir, reference_dir=tmp_path / "reference",
        test_modules=["test_bounded_stall_fault"], seed=97,
        build_dir=tmp_path / "build_fault", report_path=tmp_path / "fault_report.json",
        timeout_seconds=120,
    )
    assert result["status"] == "SIMULATION_FAILURE", result
    assert "extension=protocol.bounded_stall" in result["stdout"], result["stdout"][-3000:]

    tmp_path2 = tmp_path / "correct"
    for directory in ("rtl", "reference", "tests"):
        (tmp_path2 / directory).mkdir(parents=True)
    (tmp_path2 / "rtl" / "bounded_stall_consumer.sv").write_text(_RTL % 0)
    (tmp_path2 / "reference" / "model.py").write_text("")
    (tmp_path2 / "tests" / "test_bounded_stall_fault.py").write_text(
        (tests_dir / "test_bounded_stall_fault.py").read_text().replace(
            "fault_exceeds_bound", "correct_within_bound"
        )
    )
    good = run_cocotb_regression(
        rtl_dir=tmp_path2 / "rtl", top_module="bounded_stall_consumer",
        tests_dir=tmp_path2 / "tests", reference_dir=tmp_path2 / "reference",
        test_modules=["test_bounded_stall_fault"], seed=97,
        build_dir=tmp_path2 / "build_correct", report_path=tmp_path2 / "correct_report.json",
        timeout_seconds=120,
    )
    assert good["status"] == "PASS", good


def test_bounded_stall_negative_control_rejects_corrupted_evidence() -> None:
    """Per the reference extension fixture's methodology: a checker that
    merely allows its stimulus to run is not evidence. Feeding the assertion
    a synthetic, corrupted (valid=1, ready=0) trace held past the bound must
    raise -- proving the checker rejects a false-good result rather than
    passing regardless of input."""
    state: dict = {}
    with pytest.raises(AssertionError, match="protocol.bounded_stall"):
        for _ in range(5):
            assert_bounded_stall(state, 1, 0, max_stall_cycles=3)


def test_cover_bounded_stall_classifies_observed_evidence() -> None:
    """Reachability anchor for the coverage symbol (a generated TB would call
    this the same way after each sampled cycle) and a direct check that it
    classifies from observed state rather than declaring a bin hit because a
    scenario was merely planned."""
    resolved_bin = cover_bounded_stall({"last_stall_length": 2})
    assert resolved_bin == {"resolved_within_bound": True, "stall_length": 2}
    assert cover_bounded_stall({"last_stall_length": 0}) == {"no_stall": True, "stall_length": 0}
    assert cover_bounded_stall({}) == {}
