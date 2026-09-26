"""Code-owned canonical operation assembly and feature classification."""

from .architect_metadata import (
    ArchitectMetadataError,
    blocking_compilation_errors,
    build_architect_operation_metadata,
    compilation_capability_notes,
    render_architect_metadata_format,
    validate_architect_operation_metadata,
    validate_operation_compilation,
)
from .arithmetic_metadata import (
    OPERATION_ARITHMETIC_SCHEMA_PATH,
    ArithmeticMetadataError,
    compile_operation_arithmetic,
    operation_arithmetic_schema,
    validate_architecture_operation_arithmetic,
    with_operation_arithmetic_schema,
)
from .canonical import (
    CanonicalOperationError,
    assemble_canonical_job,
    canonical_bins_for_concept,
    classify_checked_operations,
    classify_operation_job,
    supported_code_owned_concepts,
)
from .protocol import ProtocolAdapterError, ReadyValidCaptureAdapter

__all__ = [
    "ArchitectMetadataError",
    "CanonicalOperationError",
    "ProtocolAdapterError",
    "ReadyValidCaptureAdapter",
    "assemble_canonical_job",
    "blocking_compilation_errors",
    "build_architect_operation_metadata",
    "canonical_bins_for_concept",
    "compilation_capability_notes",
    "classify_checked_operations",
    "classify_operation_job",
    "render_architect_metadata_format",
    "supported_code_owned_concepts",
    "validate_architect_operation_metadata",
    "validate_operation_compilation",
    "OPERATION_ARITHMETIC_SCHEMA_PATH",
    "ArithmeticMetadataError",
    "compile_operation_arithmetic",
    "operation_arithmetic_schema",
    "validate_architecture_operation_arithmetic",
    "with_operation_arithmetic_schema",
]
