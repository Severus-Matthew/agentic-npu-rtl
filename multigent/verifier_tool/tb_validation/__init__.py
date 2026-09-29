"""Deterministic, code-owned generated-TB validation and local repair helpers.

``validator.py`` replaces the old LLM-based TB review stage with stable,
deterministic validation. ``repair.py`` applies bounded local corrections to
Verifier-owned metadata for findings ``validator.py`` raises. Neither module is an LLM agent; both
are pure functions over frozen artifacts. Public callers use the
``multigent.verifier_tool`` facade rather than importing this package directly.
"""
