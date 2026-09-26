"""Stable public facade for the three independent domain feature planners.

Only their output schema is shared. Protocol, lifecycle, and operation matching
remain separate because their contracts and applicability rules are different.
"""

from multigent.verifier_tool.pool.feature_plans import (
    build_lifecycle_feature_plan,
    build_operation_feature_plan,
    build_protocol_feature_plan,
)

__all__ = [
    "build_lifecycle_feature_plan",
    "build_operation_feature_plan",
    "build_protocol_feature_plan",
]
