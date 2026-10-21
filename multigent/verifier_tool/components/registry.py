"""Load checked-in reusable component manifests and their entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib
import inspect
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from .interfaces import (
    ABI_CALL_CONSTRAINTS,
    ABI_REQUIRED_PARAMETERS,
    KNOWN_ABIS,
    KNOWN_COMPONENT_TYPES,
    KNOWN_EXECUTION_OWNERS,
)


ROOT = Path(__file__).resolve().parent
CATALOG_ROOT = ROOT / "catalog"
_ID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_ENTRYPOINT = re.compile(
    r"^multigent\.verifier_tool\.[A-Za-z0-9_.]+:[A-Za-z_][A-Za-z0-9_]*$"
)


class ComponentCatalogError(ValueError):
    """A checked-in component manifest is unsafe or internally inconsistent."""


@dataclass(frozen=True)
class ComponentSpec:
    id: str
    component_type: str
    abi: str
    entrypoint: str
    domains: tuple[str, ...]
    description: str
    execution_owner: str = "verifier_extension"
    supported_profiles: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    required_semantic_classes: tuple[str, ...] = ()
    required_architecture_sections: tuple[str, ...] = ()
    supported_directions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    match_terms: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    auto_reuse: bool = False
    requires_protocol_semantics: bool = False
    requires_protocol_event_relations: bool = False
    source: str = ""

    @property
    def module_name(self) -> str:
        return self.entrypoint.split(":", 1)[0]

    @property
    def symbol_name(self) -> str:
        return self.entrypoint.split(":", 1)[1]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "component_type": self.component_type,
            "abi": self.abi,
            "entrypoint": self.entrypoint,
            "domains": list(self.domains),
            "description": self.description,
            "execution_owner": self.execution_owner,
            "supported_profiles": list(self.supported_profiles),
            "required_roles": list(self.required_roles),
            "required_semantic_classes": list(self.required_semantic_classes),
            "required_architecture_sections": list(self.required_architecture_sections),
            "supported_directions": list(self.supported_directions),
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
            "match_terms": list(self.match_terms),
            "limitations": list(self.limitations),
            "auto_reuse": self.auto_reuse,
            "requires_protocol_semantics": self.requires_protocol_semantics,
            "requires_protocol_event_relations": self.requires_protocol_event_relations,
            "source": self.source,
        }


def _strings(raw: object, location: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item for item in raw):
        raise ComponentCatalogError(f"{location} must be a list of non-empty strings")
    if len(raw) != len(set(raw)):
        raise ComponentCatalogError(f"{location} must not contain duplicates")
    return tuple(raw)


def _parse(raw: Mapping[str, Any], *, source: str, index: int) -> ComponentSpec:
    location = f"{source}:components[{index}]"
    identity = str(raw.get("id", ""))
    component_type = str(raw.get("component_type", ""))
    abi = str(raw.get("abi", ""))
    entrypoint = str(raw.get("entrypoint", ""))
    description = str(raw.get("description", "")).strip()
    execution_owner = str(raw.get("execution_owner", "verifier_extension"))
    if not _ID.fullmatch(identity):
        raise ComponentCatalogError(f"{location}.id is not a stable dotted identifier")
    if component_type not in KNOWN_COMPONENT_TYPES:
        raise ComponentCatalogError(f"{location}.component_type={component_type!r} is unknown")
    if abi not in KNOWN_ABIS:
        raise ComponentCatalogError(f"{location}.abi={abi!r} is unknown")
    if not _ENTRYPOINT.fullmatch(entrypoint):
        raise ComponentCatalogError(
            f"{location}.entrypoint must be a verifier_tool module:symbol"
        )
    if not description:
        raise ComponentCatalogError(f"{location}.description must not be empty")
    if execution_owner not in KNOWN_EXECUTION_OWNERS:
        raise ComponentCatalogError(
            f"{location}.execution_owner={execution_owner!r} is unknown"
        )
    domains = _strings(raw.get("domains"), f"{location}.domains")
    if not domains or not set(domains) <= {"protocol", "lifecycle", "operation", "common"}:
        raise ComponentCatalogError(f"{location}.domains contains an unsupported domain")
    return ComponentSpec(
        id=identity,
        component_type=component_type,
        abi=abi,
        entrypoint=entrypoint,
        domains=domains,
        description=description,
        execution_owner=execution_owner,
        supported_profiles=_strings(raw.get("supported_profiles"), f"{location}.supported_profiles"),
        required_roles=_strings(raw.get("required_roles"), f"{location}.required_roles"),
        required_semantic_classes=_strings(
            raw.get("required_semantic_classes"),
            f"{location}.required_semantic_classes",
        ),
        required_architecture_sections=_strings(
            raw.get("required_architecture_sections"),
            f"{location}.required_architecture_sections",
        ),
        supported_directions=_strings(
            raw.get("supported_directions"), f"{location}.supported_directions"
        ),
        capabilities=_strings(raw.get("capabilities"), f"{location}.capabilities"),
        tags=_strings(raw.get("tags"), f"{location}.tags"),
        match_terms=_strings(raw.get("match_terms"), f"{location}.match_terms"),
        limitations=_strings(raw.get("limitations"), f"{location}.limitations"),
        auto_reuse=bool(raw.get("auto_reuse", False)),
        requires_protocol_semantics=bool(raw.get("requires_protocol_semantics", False)),
        requires_protocol_event_relations=bool(
            raw.get("requires_protocol_event_relations", False)
        ),
        source=source,
    )


@lru_cache(maxsize=1)
def load_component_catalog() -> tuple[ComponentSpec, ...]:
    specs: list[ComponentSpec] = []
    for path in sorted(CATALOG_ROOT.glob("*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(document, Mapping) or document.get("schema_version") != 1:
            raise ComponentCatalogError(f"{path.name} needs schema_version: 1")
        raw_components = document.get("components", [])
        if not isinstance(raw_components, list):
            raise ComponentCatalogError(f"{path.name}.components must be a list")
        specs.extend(
            _parse(item, source=f"components/catalog/{path.name}", index=index)
            for index, item in enumerate(raw_components)
            if isinstance(item, Mapping)
        )
        if len(raw_components) != sum(isinstance(item, Mapping) for item in raw_components):
            raise ComponentCatalogError(f"{path.name}.components entries must be mappings")
    identities = [spec.id for spec in specs]
    if len(identities) != len(set(identities)):
        duplicates = sorted({item for item in identities if identities.count(item) > 1})
        raise ComponentCatalogError(f"duplicate component ids {duplicates}")
    return tuple(specs)


def load_component_entrypoint(component: str | ComponentSpec) -> Any:
    spec = (
        component
        if isinstance(component, ComponentSpec)
        else next((item for item in load_component_catalog() if item.id == component), None)
    )
    if spec is None:
        raise ComponentCatalogError(f"unknown component {component!r}")
    module = importlib.import_module(spec.module_name)
    try:
        entrypoint = getattr(module, spec.symbol_name)
    except AttributeError as exc:
        raise ComponentCatalogError(
            f"component {spec.id!r} entrypoint {spec.entrypoint!r} does not exist"
        ) from exc
    if not callable(entrypoint):
        raise ComponentCatalogError(
            f"component {spec.id!r} entrypoint {spec.entrypoint!r} is not callable"
        )
    try:
        parameters = inspect.signature(entrypoint).parameters
    except (TypeError, ValueError) as exc:
        raise ComponentCatalogError(
            f"component {spec.id!r} entrypoint signature cannot be inspected"
        ) from exc
    missing = sorted(set(ABI_REQUIRED_PARAMETERS[spec.abi]) - set(parameters))
    if missing:
        raise ComponentCatalogError(
            f"component {spec.id!r} does not implement ABI {spec.abi!r}; "
            f"missing parameter(s) {missing}"
        )
    return entrypoint


def component_call_contract(component: str | ComponentSpec) -> dict[str, Any]:
    """Build the exact, versioned callable contract shown to the Verifier."""

    spec = (
        component
        if isinstance(component, ComponentSpec)
        else next((item for item in load_component_catalog() if item.id == component), None)
    )
    if spec is None:
        raise ComponentCatalogError(f"unknown component {component!r}")
    entrypoint = load_component_entrypoint(spec)
    signature = inspect.signature(entrypoint)
    required = ABI_REQUIRED_PARAMETERS[spec.abi]
    arguments = ", ".join(f"{name}=<{name}>" for name in required)
    if inspect.isclass(entrypoint):
        invocation = f"component = {spec.symbol_name}({arguments})"
    elif inspect.iscoroutinefunction(entrypoint):
        invocation = f"result = await {spec.symbol_name}({arguments})"
    else:
        invocation = f"result = {spec.symbol_name}({arguments})"
    follow_up = {
        "plan_coverage_monitor_v1": "hits = component.sample(<real_snapshot>)",
        "runtime_monitor_v1": (
            "component.sample_snapshot(<real_snapshot>, <protocol_assertion_plan>)"
        ),
        "operation_sampling_monitor_v1": (
            "sampling is invoked by the pipeline-owned operation monitor"
        ),
    }.get(spec.abi)
    return {
        "schema_version": 1,
        "authority": "normative_verifier_tool_api_for_this_run",
        "execution_owner": spec.execution_owner,
        "import": f"from {spec.module_name} import {spec.symbol_name}",
        "signature": f"{spec.symbol_name}{signature}",
        "required_parameters": list(required),
        "invocation_template": invocation,
        **(
            {"semantic_constraints": dict(ABI_CALL_CONSTRAINTS[spec.abi])}
            if spec.abi in ABI_CALL_CONSTRAINTS
            else {}
        ),
        **({"follow_up_template": follow_up} if follow_up else {}),
        "evidence_rule": (
            "Replace angle-bracket placeholders with frozen-contract bindings or "
            "real runtime observations; expected/fabricated traces are not evidence."
        ),
    }


__all__ = [
    "ComponentCatalogError",
    "ComponentSpec",
    "component_call_contract",
    "load_component_catalog",
    "load_component_entrypoint",
]
