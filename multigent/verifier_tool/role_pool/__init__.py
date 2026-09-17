"""Closed interface role, semantic-class, and protocol-profile pools."""

from .interface_semantics import (
    INTERFACE_PROTOCOL_TAXONOMY_PATH,
    INTERFACE_SEMANTIC_TAXONOMY_PATH,
    derive_interface_coverage_seed,
    load_interface_protocol_taxonomy,
    load_interface_semantic_taxonomy,
    render_interface_semantic_catalog,
    validate_interface_semantics,
)
from .signal_roles import (
    SIGNAL_ROLE_TAXONOMY_PATH,
    load_signal_role_taxonomy,
    render_signal_role_catalog,
    signals_with_coverage_tags,
    signals_with_roles,
    validate_interface_signal_roles,
)

__all__ = [
    "INTERFACE_PROTOCOL_TAXONOMY_PATH",
    "INTERFACE_SEMANTIC_TAXONOMY_PATH",
    "SIGNAL_ROLE_TAXONOMY_PATH",
    "derive_interface_coverage_seed",
    "load_interface_protocol_taxonomy",
    "load_interface_semantic_taxonomy",
    "load_signal_role_taxonomy",
    "render_interface_semantic_catalog",
    "render_signal_role_catalog",
    "signals_with_coverage_tags",
    "signals_with_roles",
    "validate_interface_semantics",
    "validate_interface_signal_roles",
]
