"""Debug / Repair Agent wrapper.

Consumes deterministic compiler/simulator/synthesis evidence, classifies the
failure, identifies the earliest likely root cause, and emits a constrained repair
plan. It diagnoses; it does not directly rewrite RTL.
"""
