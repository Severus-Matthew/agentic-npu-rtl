# Compact reviewed evidence

This directory contains paper-facing summaries, not raw API artifacts.

- `evaluation_ledger.json`: machine-readable, human-reviewed attempt facts.
- `VERIFIER_BUGGY_ATTEMPTS.md`: one-line failure index plus short technical
  details and the deterministic gate that caught each issue.

The ledger distinguishes catalog cases from executed attempts. Adding a case
does not count as model evidence until an actual API call is reviewed and an
attempt row is added. Suggested paper metrics are first-attempt success by
domain, deterministic rejection rate, failure category, helper reuse, and
whether the Verifier changed only the unsupported delta.

Raw responses, generated files, and logs belong under ignored
`../local_results/` and must never be copied here.
