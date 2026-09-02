"""PPA / Judge Agent wrapper.

Evaluates verified synthesis/timing/utilization evidence, decides ACCEPT versus
OPTIMIZE, and emits evidence-backed optimization plans. Any RTL-changing plan must
route back through full functional verification before acceptance.
"""
