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
    from multigent.verifier_tool.lifecycle.assertion.runtime import (
        build_lifecycle_assertion_plan,
    )
    from multigent.verifier_tool.lifecycle.coverage.plan import (
        build_lifecycle_coverage_plan,
    )
    from multigent.verifier_tool.lifecycle.stimulus.stimulus_generator import (
        build_lifecycle_stimulus_plan,
    )
    from multigent.verifier_tool.orchestration.campaign import (
        automatic_campaign_support,
    )
    from multigent.verifier_tool.pool.lifecycle_policy_pool import (
        validate_architecture_lifecycle_policies,
        validate_interface_reset_channel_policies,
    )
    from multigent.verifier_tool.pool.operation_metadata import (
        blocking_compilation_errors,
        build_architect_operation_metadata,
        compilation_capability_notes,
        operation_formula_compilation_report,
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
        "reset_channel_policies", "interface_contract",
        lambda: validate_interface_reset_channel_policies(interface),
    )
    collect(
        "operation_arithmetic", "architecture_contract",
        lambda: validate_architecture_operation_arithmetic(
            architecture, require_arithmetic=require_operation_arithmetic,
        ),
    )
    solver_compilation = collect(
        "operation_solver_compilation", "architecture_contract",
        lambda: operation_formula_compilation_report(architecture),
    )
    collect(
        "standard_protocol_plan", "interface_contract",
        lambda: compile_standard_protocol_plan(interface),
    )
    interface_plan = collect(
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
    lifecycle_plans: dict[str, Any] = {}
    campaign_support: dict[str, Any] | None = None
    if isinstance(operation_metadata, Mapping):
        # Only defects the Architect can resolve block. A valid contract the tool
        # cannot automate (tool_capability) or one whose declaration another
        # validator above already owns is reported as a note, never a finding.
        for message in blocking_compilation_errors(operation_metadata):
            findings.append(
                _finding("operation_compilation", "architecture_contract/interface_contract", message)
            )
        capability_notes = compilation_capability_notes(operation_metadata)

        # Compile the exact lifecycle plans the generated testbench will use.
        # Policy validation alone cannot prove that the resolved bindings select
        # valid assertion, coverage, and stimulus implementations.
        lifecycle_inputs = (
            interface_plan if isinstance(interface_plan, Mapping) else interface
        )
        for plan_name, callback in (
            (
                "assertion",
                lambda: build_lifecycle_assertion_plan(
                    lifecycle_inputs, operation_metadata
                ),
            ),
            (
                "coverage",
                lambda: build_lifecycle_coverage_plan(interface, operation_metadata),
            ),
            (
                "stimulus",
                lambda: build_lifecycle_stimulus_plan(interface, operation_metadata),
            ),
        ):
            plan = collect(
                f"lifecycle_{plan_name}_plan",
                "architecture_contract/interface_contract",
                callback,
            )
            if isinstance(plan, Mapping):
                lifecycle_plans[plan_name] = plan

        support = collect(
            "automatic_campaign_support",
            "architecture_contract/interface_contract",
            lambda: automatic_campaign_support(operation_metadata, architecture),
        )
        if isinstance(support, Mapping):
            # Unsupported automation is a capability result, not a malformed
            # contract.  The report exposes it without turning it into a
            # Contract Reviewer finding.
            campaign_support = dict(support)

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
        "operation_solver_compilation": solver_compilation,
        "resolved_lifecycle_plans": lifecycle_plans,
        "automatic_campaign_support": campaign_support,
    }


__all__ = ["review_contract_deterministically"]
