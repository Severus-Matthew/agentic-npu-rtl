"""Public extension-authoring boundary; no promotion or mutation logic lives here."""

from .authoring import (
    BUNDLE_SCHEMA_PATH,
    EXAMPLES_PATH,
    FeatureExtensionError,
    REQUEST_SCHEMA_PATH,
    build_feature_extension_manifest,
    extension_bundle_schema,
    extension_request_schema,
    extension_requests,
    interface_vocabulary_extensions,
    render_architect_extension_request_guide,
    render_extension_authoring_guide,
    render_requested_extension_worklist,
    validate_architect_extension_requests,
    validate_verifier_extension_bundles,
    with_architect_extension_request_schema,
    with_verifier_extension_bundle_schema,
)

__all__ = [
    "BUNDLE_SCHEMA_PATH",
    "EXAMPLES_PATH",
    "FeatureExtensionError",
    "REQUEST_SCHEMA_PATH",
    "build_feature_extension_manifest",
    "extension_bundle_schema",
    "extension_request_schema",
    "extension_requests",
    "interface_vocabulary_extensions",
    "render_architect_extension_request_guide",
    "render_extension_authoring_guide",
    "render_requested_extension_worklist",
    "validate_architect_extension_requests",
    "validate_verifier_extension_bundles",
    "with_architect_extension_request_schema",
    "with_verifier_extension_bundle_schema",
]
