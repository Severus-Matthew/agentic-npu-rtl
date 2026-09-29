"""Known-operation directed and randomized vector generation."""

from .stimulus_generator import (
    canonical_bin_dispositions,
    CanonicalStimulusGenerationError,
    evaluate_canonical_operation,
    generate_canonical_discriminating_stimuli,
    generate_canonical_stimulus_for_bin,
    generate_canonical_stimulus_suite,
    generate_random_canonical_stimuli,
    generate_solver_compiled_stimulus_for_bin,
    reachable_canonical_bins_for_concept,
)

__all__ = [
    "canonical_bin_dispositions",
    "CanonicalStimulusGenerationError",
    "evaluate_canonical_operation",
    "generate_canonical_discriminating_stimuli",
    "generate_canonical_stimulus_for_bin",
    "generate_canonical_stimulus_suite",
    "generate_random_canonical_stimuli",
    "generate_solver_compiled_stimulus_for_bin",
    "reachable_canonical_bins_for_concept",
]
