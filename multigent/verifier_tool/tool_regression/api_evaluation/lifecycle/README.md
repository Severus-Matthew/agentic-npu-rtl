# Lifecycle API cases

These cases add timing or recovery observations around the existing GEMM job.
Built-in acceptance, busy, completion, error, reset, and single-inflight checks
remain active. The Verifier must not replace them; it adds only the requested
residual monitor, coverage, and stimulus path.

Record for each attempt: trigger/end condition, parameterized timing bound,
required events/signals, preserved lifecycle features, generated entry-point
symbols, reachability result, and final deterministic verdict.
