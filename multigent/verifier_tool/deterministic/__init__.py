"""Deterministic, code-owned TB review and local-patch helpers.

``review.py`` replaces the old LLM-based TB review stage with stable, deterministic
validation. ``patch.py`` applies bounded local corrections to Verifier-owned
metadata for findings ``review.py`` raises. Neither module is an LLM agent; both
are pure functions over frozen artifacts. Public callers use the
``multigent.verifier_tool`` facade rather than importing this package directly.
"""
