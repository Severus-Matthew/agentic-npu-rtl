"""Protocol coverage obligation construction."""

from .plan import (
    INTERFACE_COVERAGE_TEMPLATES_PATH,
    build_interface_coverage_plan,
    load_interface_coverage_templates,
)

__all__ = [
    "INTERFACE_COVERAGE_TEMPLATES_PATH",
    "build_interface_coverage_plan",
    "load_interface_coverage_templates",
]
