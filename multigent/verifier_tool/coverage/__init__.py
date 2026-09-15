"""Coverage plans, cocotb coverage objects, runtime sampling, and reports."""

from .operation.plan import (
    OPERATION_COVERAGE_FAMILIES_PATH,
    build_operation_coverage_plan,
    load_operation_coverage_families,
    merge_coverage_plans,
    operation_family,
    render_operation_coverage_catalog,
    validate_architecture_operation_features,
    validate_operation_coverage,
)
from .protocol.plan import (
    INTERFACE_COVERAGE_TEMPLATES_PATH,
    build_interface_coverage_plan,
    load_interface_coverage_templates,
)
from .runtime import (
    CoverageRuntimeError,
    InterfaceCoverageTracker,
    contract_coverage,
    get_coverage_tracker,
    normalize_verification_value,
    record_stimulus,
    sample_operation,
)

__all__ = [
    "CoverageRuntimeError",
    "INTERFACE_COVERAGE_TEMPLATES_PATH",
    "InterfaceCoverageTracker",
    "OPERATION_COVERAGE_FAMILIES_PATH",
    "build_interface_coverage_plan",
    "build_operation_coverage_plan",
    "contract_coverage",
    "get_coverage_tracker",
    "load_interface_coverage_templates",
    "load_operation_coverage_families",
    "merge_coverage_plans",
    "normalize_verification_value",
    "operation_family",
    "record_stimulus",
    "render_operation_coverage_catalog",
    "sample_operation",
    "validate_architecture_operation_features",
    "validate_operation_coverage",
]
