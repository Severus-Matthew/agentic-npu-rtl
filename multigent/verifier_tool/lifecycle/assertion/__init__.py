"""Code-owned lifecycle assertion generation and runtime."""

from .generator import lifecycle_assertion_metadata, render_lifecycle_assertion_lines
from .runtime import (
    build_lifecycle_assertion_plan,
    check_lifecycle_assertions,
    finalize_lifecycle_assertions,
)

__all__ = [
    "build_lifecycle_assertion_plan",
    "check_lifecycle_assertions",
    "finalize_lifecycle_assertions",
    "lifecycle_assertion_metadata",
    "render_lifecycle_assertion_lines",
]
