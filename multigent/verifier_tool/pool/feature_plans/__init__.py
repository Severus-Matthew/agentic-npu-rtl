"""Domain-specific resolved feature planners sharing one output schema."""

from .catalog import (
    LIFECYCLE_FEATURES_PATH,
    OPERATION_FEATURES_PATH,
    PROTOCOL_FEATURES_PATH,
    load_lifecycle_feature_catalog,
    load_operation_feature_catalog,
    load_protocol_feature_catalog,
    operation_feature_groups,
    operation_feature_selections,
    operation_optional_concepts,
)
from .compiler import (
    compile_assertion_feature_plan,
    compile_coverage_feature_plan,
    compile_feature_branch,
    compile_stimulus_feature_plan,
)
from .lifecycle import build_lifecycle_feature_plan
from .operation import build_operation_feature_plan
from .protocol import build_protocol_feature_plan
from .schema import (
    RESOLVED_FEATURE_PLAN_SCHEMA_PATH,
    load_resolved_feature_plan_schema,
    validate_resolved_feature_plan,
)

__all__ = [
    "build_lifecycle_feature_plan",
    "build_operation_feature_plan",
    "build_protocol_feature_plan",
    "compile_assertion_feature_plan",
    "compile_coverage_feature_plan",
    "compile_feature_branch",
    "compile_stimulus_feature_plan",
    "LIFECYCLE_FEATURES_PATH",
    "OPERATION_FEATURES_PATH",
    "PROTOCOL_FEATURES_PATH",
    "load_lifecycle_feature_catalog",
    "load_operation_feature_catalog",
    "load_protocol_feature_catalog",
    "operation_feature_groups",
    "operation_feature_selections",
    "operation_optional_concepts",
    "RESOLVED_FEATURE_PLAN_SCHEMA_PATH",
    "load_resolved_feature_plan_schema",
    "validate_resolved_feature_plan",
]
