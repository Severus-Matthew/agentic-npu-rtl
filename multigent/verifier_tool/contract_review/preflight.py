"""One deterministic Contract Reviewer preflight over all frozen artifacts."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .reuse import resolve_extension_reuse


def _finding(check_id: str, artifact: str, message: object) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "blocking",
        "owner": "architect_contract",
        "artifact": artifact,
        "paths": [],
        "message": str(message),
    }


def review_contract_deterministically(
    architecture: Mapping[str, Any],
    interface: Mapping[str, Any],
    module_manifest: Mapping[str, Any] | None = None,
    acceptance_criteria: Mapping[str, Any] | list[Any] | None = None,
    *,
    require_lifecycle_policy: bool = True,
    require_operation_arithmetic: bool = True,
) -> dict[str, Any]:
    """Return structured findings and immutable reuse before reviewer reasoning.

    The function performs no model call and never edits a contract.  A future
    Contract Reviewer agent consumes this report; Architect may call it as a
    temporary early gate until that independent node is merged.
    """

    from multigent.verifier_tool.extensions import (
        interface_vocabulary_extensions,
        validate_architect_extension_requests,
    )
    from multigent.verifier_tool.operation.coverage.plan import (
        validate_architecture_operation_features,
    )
    from multigent.verifier_tool.pool.lifecycle_policy_pool import (
        validate_architecture_lifecycle_policies,
    )
    from multigent.verifier_tool.pool.operation_metadata import (
        blocking_compilation_errors,
        build_architect_operation_metadata,
        compilation_capability_notes,
        validate_architecture_operation_arithmetic,
    )
    from multigent.verifier_tool.pool.role_pool.interface_semantics import (
        validate_interface_semantics,
    )
    from multigent.verifier_tool.pool.role_pool.signal_roles import (
        validate_interface_signal_roles,
    )
    from multigent.verifier_tool.pool.role_pool.standard_protocols import (
        compile_standard_protocol_plan,
        validate_standard_protocol_bindings,
    )
    from multigent.verifier_tool.pool.tag_pool import validate_contract_vocabulary
    from multigent.verifier_tool.protocol.coverage.plan import (
        build_interface_coverage_plan,
    )

    findings: list[dict[str, Any]] = []

    def collect(check_id: str, artifact: str, callback: Callable[[], object]) -> object | None:
        try:
            result = callback()
        except (ValueError, AssertionError, KeyError, TypeError) as exc:
            findings.append(_finding(check_id, artifact, exc))
            return None
        if isinstance(result, list):
            findings.extend(_finding(check_id, artifact, item) for item in result)
        return result

    vocabulary = collect(
        "contract_vocabulary", "architecture_contract/interface_contract",
        lambda: validate_contract_vocabulary(architecture, interface),
    )
    del vocabulary
    collect(
        "extension_requests", "architecture_contract",
        lambda: validate_architect_extension_requests(architecture, interface),
    )
    try:
        role_extensions, semantic_extensions = interface_vocabulary_extensions(architecture)
    except ValueError as exc:
        role_extensions, semantic_extensions = {}, {}
        findings.append(_finding("contract_vocabulary", "architecture_contract", exc))
    collect(
        "signal_roles", "interface_contract",
        lambda: validate_interface_signal_roles(interface, role_extensions=role_extensions),
    )
    collect(
        "interface_semantics", "interface_contract",
        lambda: validate_interface_semantics(
            interface,
            role_extensions=role_extensions,
            semantic_class_extensions=semantic_extensions,
        ),
    )
    collect(
        "standard_protocol_bindings", "interface_contract",
        lambda: validate_standard_protocol_bindings(interface),
    )
    collect(
        "operation_features", "architecture_contract",
        lambda: validate_architecture_operation_features(architecture),
    )
    collect(
        "lifecycle_policy", "architecture_contract",
        lambda: validate_architecture_lifecycle_policies(
            architecture, require_policy=require_lifecycle_policy,
        ),
    )
    collect(
        "operation_arithmetic", "architecture_contract",
        lambda: validate_architecture_operation_arithmetic(
            architecture, require_arithmetic=require_operation_arithmetic,
        ),
    )
    collect(
        "standard_protocol_plan", "interface_contract",
        lambda: compile_standard_protocol_plan(interface),
    )
    collect(
        "interface_coverage_plan", "interface_contract",
        lambda: build_interface_coverage_plan(
            interface,
            role_extensions=role_extensions,
            semantic_class_extensions=semantic_extensions,
        ),
    )
    operation_metadata = collect(
        "operation_metadata", "architecture_contract/interface_contract",
        lambda: build_architect_operation_metadata(architecture, interface),
    )
    capability_notes: list[dict[str, Any]] = []
    if isinstance(operation_metadata, Mapping):
        # Only defects the Architect can resolve block. A valid contract the tool
        # cannot automate (tool_capability) or one whose declaration another
        # validator above already owns is reported as a note, never a finding.
        for message in blocking_compilation_errors(operation_metadata):
            findings.append(
                _finding("operation_compilation", "architecture_contract/interface_contract", message)
            )
        capability_notes = compilation_capability_notes(operation_metadata)

    if module_manifest is not None:
        top = str(module_manifest.get("top", ""))
        modules = {
            str(item.get("name", ""))
            for item in module_manifest.get("modules", [])
            if isinstance(item, Mapping)
        }
        if not top or top not in modules:
            findings.append(
                _finding(
                    "module_manifest_identity", "module_manifest",
                    f"module_manifest.top {top!r} must name exactly one declared module",
                )
            )

    if acceptance_criteria is not None and not isinstance(
        acceptance_criteria, (Mapping, list)
    ):
        findings.append(
            _finding(
                "acceptance_criteria_shape", "acceptance_criteria",
                "acceptance criteria must be a mapping or list",
            )
        )

    try:
        resolved_reuse = resolve_extension_reuse(architecture, interface)
    except (ValueError, AssertionError, KeyError, TypeError) as exc:
        resolved_reuse = {"schema_version": 1, "entries": [], "diagnostics": [str(exc)]}
        findings.append(_finding("extension_reuse", "architecture_contract/interface_contract", exc))
    for entry in resolved_reuse.get("entries", []):
        if isinstance(entry, Mapping) and not entry.get("match_satisfied", True):
            findings.append(
                _finding(
                    "extension_match",
                    "architecture_contract/interface_contract",
                    f"extension request {entry.get('request_id')!r} does not match "
                    f"its exact target: {entry.get('missing_match_requirements', {})}",
                )
            )

    unique_findings: list[dict[str, Any]] = []
    seen_findings: set[tuple[str, str]] = set()
    for item in findings:
        identity = (str(item.get("artifact", "")), str(item.get("message", "")))
        if identity in seen_findings:
            continue
        seen_findings.add(identity)
        unique_findings.append(item)

    return {
        "schema_version": 1,
        "status": "PASS" if not unique_findings else "BLOCKED",
        "findings": unique_findings,
        "resolved_extension_reuse": resolved_reuse,
        "capability_notes": capability_notes,
    }


__all__ = ["review_contract_deterministically"]
