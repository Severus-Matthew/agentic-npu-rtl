"""Reusable verifier component catalog, resolution, and plugin loading."""

from .registry import (
    ComponentCatalogError,
    ComponentSpec,
    component_call_contract,
    load_component_catalog,
    load_component_entrypoint,
)
from .resolver import (
    build_contract_local_component_manifests,
    resolve_extension_components,
)

__all__ = [
    "ComponentCatalogError",
    "ComponentSpec",
    "build_contract_local_component_manifests",
    "component_call_contract",
    "load_component_catalog",
    "load_component_entrypoint",
    "resolve_extension_components",
]
