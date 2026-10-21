from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
import multigent.verifier_tool.components.registry as component_registry

from multigent.verifier_tool import (
    build_interface_coverage_plan,
    build_contract_local_component_manifests,
    load_component_catalog,
    load_component_entrypoint,
    render_requested_extension_worklist,
    render_contract_generated_block,
    resolve_extension_components,
    validate_verifier_extension_bundles,
)
from multigent.verifier_tool.tool_regression.extensions.rtl.test_feature_extensions import (
    _protocol_bundle,
    _protocol_request,
    _protocol_source,
)
from multigent.verifier_tool.tool_regression.unit.test_canonical_operation import (
    axi_lite_contracts,
)
from multigent.verifier_tool.extensions.authoring import (
    _component_invocation_errors,
    _protocol_completion_drive_errors,
)


CASE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "tool_regression"
    / "benchmarks"
    / "external_feature_benchmarks"
    / "cases"
    / "p04_obi_to_apb_bridge"
)
P01_ROOT = CASE_ROOT.parent / "p01_wishbone_pipelined_to_axi4"
P02_ROOT = CASE_ROOT.parent / "p02_wishbone_cross_clock"


def _contracts() -> tuple[dict, dict]:
    architecture = yaml.safe_load(
        (CASE_ROOT / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (CASE_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    return architecture, interface


def test_all_checked_in_component_entrypoints_are_importable() -> None:
    catalog = load_component_catalog()
    assert len(catalog) >= 20
    assert len({item.id for item in catalog}) == len(catalog)
    for component in catalog:
        assert callable(load_component_entrypoint(component)), component.id


def test_partial_protocol_resolution_reuses_only_compatible_mechanics() -> None:
    architecture, interface = _contracts()
    resolved = resolve_extension_components(architecture, interface)
    by_request = {item["request_id"]: item for item in resolved["entries"]}
    split = by_request["protocol.p04_obi_req_gnt_split_response"]

    selected = set(split["required_reuse_component_ids"])
    assert "protocol.driver.role_bound_source" in selected
    assert "protocol.monitor.interface_runtime" not in selected
    assert "memory.model.byte_addressable" not in selected
    assert "protocol.assertion.event_correlation" not in set(
        split["pipeline_managed_reuse_component_ids"]
    )
    assert "obi_req_gnt_split_response" in split["residual_capabilities"]
    assert all(
        item["compatibility"] == "compatible"
        for item in split["automatic_reuse"]
    )


def test_compiled_wishbone_semantics_select_exact_driver_and_accounting() -> None:
    architecture = yaml.safe_load(
        (P01_ROOT / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (P01_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    entry = resolve_extension_components(architecture, interface)["entries"][0]
    assert set(entry["required_reuse_component_ids"]) == {
        "protocol.assertion.transaction_completion_payload",
        "protocol.driver.axi4_protocol_responder",
        "protocol.driver.contract_event_source",
        "protocol.monitor.contract_event_trace",
    }
    assert set(entry["pipeline_managed_reuse_component_ids"]) == {
        "protocol.assertion.event_correlation",
        "protocol.assertion.standard_runtime",
    }
    responder = next(
        item
        for item in entry["automatic_reuse"]
        if item["id"] == "protocol.driver.axi4_protocol_responder"
    )
    assert responder["runtime_bindings"] == [
        {
            "protocol_group": "axi",
            "protocol_profile": "axi4",
            "generated_accessor": (
                "_contract_standard_protocol_group('axi', 'axi4')"
            ),
        }
    ]
    driver = next(
        item
        for item in entry["automatic_reuse"]
        if item["id"] == "protocol.driver.contract_event_source"
    )
    assert driver["runtime_bindings"] == [
        {
            "profile_name": "wishbone_b4_pipelined",
            "transaction_name": "wishbone_request",
            "generated_accessor": (
                "_contract_protocol_event_transaction("
                "'wishbone_b4_pipelined', 'wishbone_request')"
            ),
        }
    ]
    monitor = next(
        item
        for item in entry["automatic_reuse"]
        if item["id"] == "protocol.monitor.contract_event_trace"
    )
    assert monitor["runtime_bindings"] == driver["runtime_bindings"]
    assert set(entry["residual_capabilities"]) == {
        "little_endian",
        "reset_abort",
        "wishbone_axi_translation_residuals",
    }


def test_cross_clock_monitor_exposes_input_and_output_transactions() -> None:
    architecture = yaml.safe_load(
        (P02_ROOT / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (P02_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    entries = resolve_extension_components(architecture, interface)["entries"]
    outstanding = next(
        item
        for item in entries
        if item["request_id"] == "protocol.p02_wishbone_outstanding_cdc"
    )
    automatic = {item["id"]: item for item in outstanding["automatic_reuse"]}
    driver_bindings = automatic[
        "protocol.driver.contract_event_source"
    ]["runtime_bindings"]
    monitor_bindings = automatic[
        "protocol.monitor.contract_event_trace"
    ]["runtime_bindings"]

    assert [item["profile_name"] for item in driver_bindings] == [
        "wishbone_source_domain"
    ]
    assert {item["profile_name"] for item in monitor_bindings} == {
        "wishbone_source_domain",
        "wishbone_destination_domain",
    }

    source_only = {
        "tests/test_extension.py": """
import cocotb
from multigent.verifier_tool.protocol.evidence import capture_protocol_event_trace

async def run_stimulus(dut):
    return None

@cocotb.test()
async def test_extension(dut):
    profile, transaction = _contract_protocol_event_transaction(
        "wishbone_source_domain", "source_request"
    )
    await capture_protocol_event_trace(
        dut, profile, transaction, run_stimulus(dut)
    )
"""
    }
    errors = _component_invocation_errors(
        source_only,
        automatic["protocol.monitor.contract_event_trace"],
    )
    assert any("wishbone_destination_domain" in item for item in errors)
    assert any("capture_protocol_event_traces" in item for item in errors)
    completion_errors = _protocol_completion_drive_errors(
        source_only,
        interface,
        automatic["protocol.monitor.contract_event_trace"],
    )
    assert any("i_xclk_ack" in item and "i_xclk_err" in item for item in completion_errors)

    with_responder = {
        "tests/test_extension.py": source_only["tests/test_extension.py"].replace(
            "async def run_stimulus(dut):\n    return None",
            "async def run_stimulus(dut):\n"
            "    dut.i_xclk_ack.value = 1\n"
            "    return None",
        )
    }
    assert _protocol_completion_drive_errors(
        with_responder,
        interface,
        automatic["protocol.monitor.contract_event_trace"],
    ) == []

    concurrent = {
        "tests/test_extension.py": """
import cocotb
from multigent.verifier_tool.protocol.evidence import capture_protocol_event_traces

async def run_stimulus(dut):
    dut.i_xclk_ack.value = 1

@cocotb.test()
async def test_extension(dut):
    source_profile, source_transaction = _contract_protocol_event_transaction(
        "wishbone_source_domain", "source_request"
    )
    destination_profile, destination_transaction = _contract_protocol_event_transaction(
        "wishbone_destination_domain", "destination_request"
    )
    evidence = await capture_protocol_event_traces(
        dut,
        {
            "source": (source_profile, source_transaction),
            "destination": (destination_profile, destination_transaction),
        },
        run_stimulus(dut),
    )
    assert evidence["source"]["cycle_trace"]
    assert evidence["destination"]["cycle_trace"]
"""
    }
    assert _component_invocation_errors(
        concurrent,
        automatic["protocol.monitor.contract_event_trace"],
    ) == []


def test_completion_payload_component_rejects_vacuous_invocation() -> None:
    architecture = yaml.safe_load(
        (P01_ROOT / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (P01_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    entry = resolve_extension_components(architecture, interface)["entries"][0]
    component = next(
        item
        for item in entry["automatic_reuse"]
        if item["id"] == "protocol.assertion.transaction_completion_payload"
    )
    source = """
async def test_extension(dut):
    result = check_transaction_completion_payloads(
        transaction_trace=trace,
        expected_payloads=[],
        payload_signal="o_data",
        require_activity=False,
        require_all_completed=False,
    )
"""
    errors = _component_invocation_errors({"tests/test_extension.py": source}, component)
    assert any("expected_payloads" in item and "empty" in item for item in errors)
    assert any("require_activity" in item and "False" in item for item in errors)
    assert any("require_all_completed" in item and "False" in item for item in errors)
    assert any("result field 'passed' is not asserted" in item for item in errors)


def test_completion_payload_component_accepts_enforced_runtime_evidence() -> None:
    architecture = yaml.safe_load(
        (P01_ROOT / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (P01_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    entry = resolve_extension_components(architecture, interface)["entries"][0]
    component = next(
        item
        for item in entry["automatic_reuse"]
        if item["id"] == "protocol.assertion.transaction_completion_payload"
    )
    source = """
async def test_extension(dut):
    expected_payloads = build_expected_payloads(reference_model)
    result = check_transaction_completion_payloads(
        transaction_trace=trace,
        expected_payloads=expected_payloads,
        payload_signal="o_data",
    )
    assert result["passed"], result["errors"]
"""
    assert _component_invocation_errors(
        {"tests/test_extension.py": source}, component
    ) == []


def test_p01_generated_block_exposes_exact_axi_participant_group() -> None:
    interface = yaml.safe_load(
        (P01_ROOT / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    namespace: dict = {}
    exec(
        render_contract_generated_block(build_interface_coverage_plan(interface)),
        namespace,
    )
    group = namespace["_contract_standard_protocol_group"]("axi", "axi4")
    assert group["endpoint_role"] == "manager"
    assert set(group["channels"]) == {
        "write_address",
        "write_data",
        "write_response",
        "read_address",
        "read_data",
    }


def test_profile_binding_selects_axi4_driver_without_core_code_changes() -> None:
    architecture, interface = _contracts()
    architecture = deepcopy(architecture)
    interface = deepcopy(interface)
    architecture["operations"] = [{"name": "dummy_memory_read"}]
    architecture["verification_extensions"] = [
        deepcopy(architecture["verification_extensions"][0])
    ]
    request = architecture["verification_extensions"][0]
    request["id"] = "protocol.axi4_unknown_read_rule"
    request["feature_name"] = "axi4_unknown_read_rule"
    request["semantics"]["summary"] = "Check an unknown AXI4 memory read rule."
    request["semantics"]["required_behavior"] = [
        "Complete a memory read and preserve the frozen unknown rule."
    ]
    for channel in interface["channels"]:
        channel["protocol_profile"] = "axi4"

    entry = resolve_extension_components(architecture, interface)["entries"][0]
    selected = set(entry["required_reuse_component_ids"])
    assert "protocol.driver.axi4_memory" in selected
    assert "protocol.driver.axi4_lite_memory" not in selected
    assert "protocol.driver.custom_mmio_read" not in selected


def test_new_manifest_component_is_selected_without_resolver_edit(
    tmp_path: Path, monkeypatch
) -> None:
    architecture, interface = _contracts()
    (tmp_path / "new_driver.yaml").write_text(
        """schema_version: 1
components:
  - id: protocol.driver.obi_role_bound_source
    component_type: protocol_source_driver
    abi: role_bound_channel_source_v1
    entrypoint: multigent.verifier_tool.protocol.stimulus.cocotb:drive_protocol_transfers
    domains: [protocol]
    description: OBI role-bound source using the stable channel ABI.
    supported_profiles: [custom]
    required_roles: [valid, ready]
    supported_directions: [input]
    capabilities: [request_grant]
    tags: [obi]
    match_terms: [obi request grant]
    auto_reuse: true
""",
        encoding="utf-8",
    )
    component_registry.load_component_catalog.cache_clear()
    monkeypatch.setattr(component_registry, "CATALOG_ROOT", tmp_path)
    try:
        entry = resolve_extension_components(architecture, interface)["entries"][0]
        assert entry["required_reuse_component_ids"] == [
            "protocol.driver.obi_role_bound_source"
        ]
    finally:
        component_registry.load_component_catalog.cache_clear()


def test_worklist_exposes_exact_reuse_and_residual_boundaries() -> None:
    architecture, interface = _contracts()
    work = yaml.safe_load(render_requested_extension_worklist(architecture, interface))
    split = next(
        item
        for item in work
        if item["request_id"] == "protocol.p04_obi_req_gnt_split_response"
    )
    resolution = split["component_resolution"]
    assert resolution["required_reuse_component_ids"]
    assert resolution["residual_capabilities"]
    assert resolution["rag_component_references"]
    assert "normative call_contract" in resolution["llm_rule"]
    for item in resolution["automatic_reuse"]:
        assert item["call_contract"]["authority"] == (
            "normative_verifier_tool_api_for_this_run"
        )


def test_contract_local_component_manifests_are_derived_not_promoted() -> None:
    architecture, interface = _contracts()
    request = architecture["verification_extensions"][0]
    bundles = [
        {
            "request_id": request["id"],
            "domain": request["domain"],
            "reuse": {"helpers": ["protocol.driver.role_bound_source"]},
        }
    ]
    for branch in ("assertion", "coverage", "stimulus"):
        bundles[0][branch] = {
            "implementation": {
                "file": "tests/test_extension.py",
                "symbol": f"extension_{branch}",
            }
        }

    manifests = build_contract_local_component_manifests(
        architecture, bundles, interface
    )
    assert [item["component_type"] for item in manifests] == [
        "assertion_checker",
        "coverage_sampler",
        "protocol_source_driver",
    ]
    assert all(item["scope"] == "contract_local_only" for item in manifests)
    assert all(item["promotion"] == "not_implemented" for item in manifests)
    assert all(request["feature_name"] in item["implements_residual_capabilities"] for item in manifests)


def test_runtime_gate_rejects_declared_or_inert_component_reuse() -> None:
    architecture, interface = axi_lite_contracts()
    architecture["verification_extensions"] = [_protocol_request()]
    bundle = _protocol_bundle()
    source = _protocol_source()

    errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert any("omits deterministically selected component" in item for item in errors)

    resolution = resolve_extension_components(architecture, interface)["entries"][0]
    bundle["reuse"]["helpers"] = resolution["required_reuse_component_ids"]
    errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert any("claims reusable component" in item for item in errors)

    source["content"] = source["content"].replace(
        "from cocotb.triggers import RisingEdge",
        """from cocotb.triggers import RisingEdge
from multigent.verifier_tool.protocol.stimulus.cocotb import drive_protocol_transfers""",
    ).replace(
        "    await drive_ready_recovery(dut)",
        """    await drive_protocol_transfers(
        dut,
        "clk",
        {
            "direction": "input",
            "valid": "cmd_valid",
            "ready": "cmd_ready",
            "fields": {},
        },
        [],
    )
    await drive_ready_recovery(dut)""",
    )
    errors = validate_verifier_extension_bundles(
        architecture,
        [bundle],
        source_files=[source],
        interface=interface,
        require_runtime_evidence=True,
    )
    assert not any("claims reusable component" in item for item in errors)
    assert not any("omits deterministically selected component" in item for item in errors)


def test_wishbone_stall_is_not_misclassified_as_ready_valid_reuse() -> None:
    case = CASE_ROOT.parent / "p02_wishbone_cross_clock"
    architecture = yaml.safe_load(
        (case / "architecture_contract.yaml").read_text(encoding="utf-8")
    )
    interface = yaml.safe_load(
        (case / "interface_contract.yaml").read_text(encoding="utf-8")
    )
    entries = resolve_extension_components(architecture, interface)["entries"]
    for entry in entries:
        assert "protocol.driver.role_bound_source" not in entry[
            "required_reuse_component_ids"
        ]
        assert "protocol.driver.role_bound_sink" not in entry[
            "required_reuse_component_ids"
        ]
        assert "protocol.coverage.temporal_monitor" not in entry[
            "pipeline_managed_reuse_component_ids"
        ]
        assert "protocol.driver.contract_event_source" in entry[
            "required_reuse_component_ids"
        ]
        assert "handshake" not in entry["residual_capabilities"]


def test_pipeline_owned_components_are_not_explicit_reuse_obligations() -> None:
    architecture, interface = axi_lite_contracts()
    architecture["verification_extensions"] = [_protocol_request()]
    entry = resolve_extension_components(architecture, interface)["entries"][0]
    automatic = {item["id"]: item for item in entry["automatic_reuse"]}
    assert set(entry["required_reuse_component_ids"]).isdisjoint(
        entry["pipeline_managed_reuse_component_ids"]
    )
    for component_id in entry["pipeline_managed_reuse_component_ids"]:
        assert automatic[component_id]["execution_owner"] == "pipeline"
