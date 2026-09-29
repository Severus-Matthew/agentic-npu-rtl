"""Qualify AXI4 exclusive-access rules with matched contract/RTL variants.

The frozen HLS top exposes legacy two-bit AxLOCK ports and the frozen contract
declares their exact physical representation.  This runner renders the normal
generated TB from that contract and injects one illegal exclusive descriptor
into a copied RTL tree.  No source contract or golden RTL file is modified.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

import yaml

from multigent.verifier_tool.pool.role_pool.standard_protocols import (
    compile_standard_protocol_plan,
)

from .generated_mutation_qualification import (
    HERE,
    RTL_DIR,
    _simulate,
    generate_tb_from_contracts,
)


EXCLUSIVE_VARIANTS: dict[str, dict[str, str]] = {
    "gmem_a_reserved_lock_bit_high": {
        "group": "gmem_a",
        "channel": "m_axi_gmem_a_ar",
        "signal": "m_axi_gmem_a_ARLOCK",
        "rtl_file": "int8_gemm_gmem_a_m_axi.v",
        "rtl_anchor": "assign out_BUS_ARLOCK   = 2'b00;",
        "rtl_mutation": "assign out_BUS_ARLOCK   = 2'b10;",
        "diagnostic": "feature=protocol.gmem_a.exclusive_access_restrictions; legacy two-bit AxLOCK=0b10 sets reserved-zero bits",
    },
    "gmem_a_illegal_exclusive_read": {
        "group": "gmem_a",
        "channel": "m_axi_gmem_a_ar",
        "signal": "m_axi_gmem_a_ARLOCK",
        "rtl_file": "int8_gemm_gmem_a_m_axi.v",
        "rtl_anchor": "assign out_BUS_ARLOCK   = 2'b00;",
        "rtl_mutation": "assign out_BUS_ARLOCK   = 2'b01;",
        "diagnostic": "feature=protocol.gmem_a.exclusive_access_restrictions",
    },
    "gmem_b_illegal_exclusive_read": {
        "group": "gmem_b",
        "channel": "m_axi_gmem_b_ar",
        "signal": "m_axi_gmem_b_ARLOCK",
        "rtl_file": "int8_gemm_gmem_b_m_axi.v",
        "rtl_anchor": "assign out_BUS_ARLOCK   = 2'b00;",
        "rtl_mutation": "assign out_BUS_ARLOCK   = 2'b01;",
        "diagnostic": "feature=protocol.gmem_b.exclusive_access_restrictions",
    },
    "gmem_c_illegal_exclusive_write": {
        "group": "gmem_c",
        "channel": "m_axi_gmem_c_aw",
        "signal": "m_axi_gmem_c_AWLOCK",
        "rtl_file": "int8_gemm_gmem_c_m_axi.v",
        "rtl_anchor": "assign out_BUS_AWLOCK   = 2'b00;",
        "rtl_mutation": "assign out_BUS_AWLOCK   = 2'b01;",
        "diagnostic": "feature=protocol.gmem_c.exclusive_access_restrictions",
    },
}


def _replace_exact(path: Path, anchor: str, replacement: str) -> None:
    source = path.read_text(encoding="utf-8")
    if source.count(anchor) != 1:
        raise AssertionError(f"exclusive qualification anchor is absent or ambiguous: {path}: {anchor!r}")
    path.write_text(source.replace(anchor, replacement), encoding="utf-8")


def matched_exclusive_interface(spec: Mapping[str, str]) -> dict[str, Any]:
    """Return the frozen interface after checking its truthful LOCK binding."""

    interface = yaml.safe_load((HERE / "interface_contract.yaml").read_text())
    signal = next(
        item for item in interface["signals"] if item["name"] == spec["signal"]
    )
    if (
        str(signal.get("width")) != "2"
        or signal.get("channel") != spec["channel"]
        or signal.get("physical_encoding") != "legacy_hls_2bit"
        or signal.get("logical_bit") != 0
        or signal.get("reserved_zero_bits") != [1]
    ):
        raise AssertionError(f"frozen LOCK binding is not the actual HLS two-bit port: {signal!r}")
    plan = compile_standard_protocol_plan(interface)
    group = next(item for item in plan["groups"] if item["name"] == spec["group"])
    if group["capabilities"].get("exclusive_access") is not False:
        raise AssertionError(
            f"frozen group {spec['group']!r} must explicitly disable exclusive access"
        )
    return interface


def qualify_exclusive_variant(name: str, output_dir: Path) -> dict[str, Any]:
    if name not in EXCLUSIVE_VARIANTS:
        raise ValueError(f"unknown exclusive variant {name!r}")
    spec = EXCLUSIVE_VARIANTS[name]
    architecture = yaml.safe_load((HERE / "architecture_contract.yaml").read_text())
    interface = matched_exclusive_interface(spec)
    generated = output_dir / "generated"
    generation = generate_tb_from_contracts(generated, architecture, interface)

    positive_rtl = output_dir / "positive_rtl"
    shutil.copytree(RTL_DIR, positive_rtl)
    mutant_rtl = output_dir / "mutant_rtl"
    shutil.copytree(positive_rtl, mutant_rtl)
    _replace_exact(
        mutant_rtl / spec["rtl_file"],
        spec["rtl_anchor"],
        spec["rtl_mutation"],
    )

    mutant = _simulate(mutant_rtl, generated, output_dir / "mutant")
    positive = _simulate(positive_rtl, generated, output_dir / "positive")
    precise_failure = (
        mutant["status"] == "SIMULATION_FAILURE"
        and spec["diagnostic"].lower() in mutant["stdout"].lower()
    )
    coverage = positive["coverage"]
    positive_complete = bool(
        positive["status"] == "PASS"
        and coverage["status"] == "PASS"
        and coverage["required_bins"] == coverage["hit_bins"]
        and not coverage["missing_bins"]
        and not coverage["assertion_failures"]
        and positive["ledger"]["status"] == "PASS"
    )
    summary = {
        "name": name,
        "status": "QUALIFIED" if precise_failure and positive_complete else "UNQUALIFIED",
        "expected_diagnostic": spec["diagnostic"],
        "mutant_precise_failure": precise_failure,
        "positive_complete": positive_complete,
        "generation": generation,
        "mutant": {key: value for key, value in mutant.items() if key != "stdout"},
        "positive": {key: value for key, value in positive.items() if key != "stdout"},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "qualification.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=sorted(EXCLUSIVE_VARIANTS))
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(qualify_exclusive_variant(args.name, args.output_dir), indent=2))
