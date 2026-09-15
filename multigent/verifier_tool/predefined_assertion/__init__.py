"""Code-owned protocol and catalog-operation assertions inserted into TBs."""

from .instrumentation import (
    install_contract_generated_block,
    install_pipeline_generated_annotations,
    validate_contract_generated_block,
    validate_verifier_authored_structure,
)

__all__ = [
    "install_contract_generated_block",
    "install_pipeline_generated_annotations",
    "validate_contract_generated_block",
    "validate_verifier_authored_structure",
]
