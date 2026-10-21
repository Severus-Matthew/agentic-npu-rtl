# External feature-extension benchmark

This suite evaluates whether the verifier can extend deterministic verification
to real, previously unsupported RTL behavior. It contains 30 selected cases:
10 protocol, 10 lifecycle, and 10 operation cases. Selection is not a
qualification result. A case becomes qualified only after the pinned upstream
RTL, frozen contract, generated TB, positive controls, known mutants, and
held-out mutants have all completed the evidence sequence below.

The suite deliberately separates three questions:

1. **Contract completeness:** Does the frozen contract accurately describe the
   relevant behavior in the upstream specification?
2. **Generated-TB correctness:** Does the generated TB pass the pristine design
   and legal positive variants while closing every required obligation?
3. **Fault detection:** Does the same frozen TB reject both development-visible
   mutants and mutants withheld until final evaluation, with the intended
   diagnostic rather than an unrelated timeout?

Passing pristine RTL alone is never qualification, and 100% coverage alone is
not proof that a checker detects faults.

## Sources and reproducibility

`benchmark_manifest.json` pins every public source repository to a full commit
SHA. The selected projects are:

- ZipCPU `wb2axip`: formally verified Wishbone, APB, and AXI components.
- PULP `axi`, `obi`, and `axi_stream`: synthesizable protocol IP.
- OpenTitan: documented IP-level lifecycle and official DV collateral.
- Koios RTL from the exact VTR fork revision pinned by SLDB: ten concrete
  machine-learning accelerator designs with checked-in Verilog.

The protocol cases are `P01` through `P10`, lifecycle cases are `L01` through
`L10`, and operation cases are `O01` through `O10`. Their exact source target,
unknown feature, reusable baseline, isolation rule, and two development-visible
mutation operators are defined in the manifest. Each case reserves at least one
additional held-out mutant without revealing its fault definition.

Downloaded source, simulator output, and evaluator-private holdouts are local
artifacts and are ignored by Git. The checked-in benchmark contains provenance,
case definitions, frozen contracts once audited, mutation recipes that were
visible during development, and compact final evidence.

## Domain isolation

- **Protocol cases** use a trivial data transform and simple lifecycle. The
  unknown obligation is the transport behavior.
- **Lifecycle cases** verify the selected controller/state behavior separately
  from operation correctness. Transparent harnesses may expose IP-level events,
  but may not replace the state machine being evaluated.
- **Operation cases** use a supported transport adapter and simple lifecycle so
  that the unknown obligation is the externally observable computation.

Any case that cannot preserve this isolation must be marked `mixed` in its
evidence and cannot be used as a single-domain result.

## Required evaluation sequence

For every case, use this order:

1. Audit the official specification and write the frozen contract.
2. Run the pinned upstream regression or independent reference test.
3. Generate the TB without exposing any held-out mutant.
4. Freeze the generated TB and all extension artifacts by content hash.
5. Require the pristine RTL and legal positive controls to pass.
6. Run the two declared known mutants and require the intended feature-specific
   failure.
7. Only after step 4, author and run the evaluator-private held-out mutant.
8. Record obligation execution, mutation detection, diagnostic cause, human
   edits, attempts, and reused helpers in the evidence record.

An assertion failure, golden mismatch, driver rejection, and timeout are
different detection strengths. A timeout must never be reported as a named
feature assertion.

## Holdout policy

The manifest records only the number of held-out mutants required. Their fault
definitions must not be written into this source tree before TB freeze. They
belong in an evaluator-controlled location such as `private_holdouts/`, which is
ignored by Git and excluded from Verifier prompts. This prevents the generated
TB from specializing to the final faults.

## Validation

Validate the checked-in suite definition without downloading RTL or calling an
API:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.validate_manifest
```

List or materialize the exact source revisions:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.materialize_sources \
  --list

# Example: materialize only the first protocol source into the ignored cache.
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.materialize_sources \
  --source zipcpu_wb2axip
```

For a large repository, materialize only the directories containing selected
case targets while retaining the pinned Git checkout:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.materialize_sources \
  --source opentitan --sparse
```

Sparse checkout is a storage optimization, not a standalone build guarantee.
Shared packages, DV collateral, and generated dependencies required by a later
qualification runner must be added from the same pinned revision rather than
silently copied from another checkout.

Materialization and qualification runners will be added only after each
upstream build has been audited. Until then every case remains `selected`, not
`qualified`.

After materializing a source, audit its checked-out revision and every case
target that refers to it:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.audit_materialized_sources \
  --source zipcpu_wb2axip
```

This command checks provenance and file presence only. It does not turn a
selected case into a qualification result.

Final compact results must conform to `evidence.schema.json`. In particular,
the schema records upstream and generated-TB runs separately, requires at least
one legal positive control, and reports timeouts and driver rejections apart
from correctly diagnosed assertion failures.

## Contract candidates and bounded API generation

`build_contract_candidates.py` materializes one six-artifact directory for
every selected benchmark. These files are source-backed **candidates**, not
automatically frozen contracts. Unsupported behavior is represented by explicit
`verification_extensions` requests; the builder does not infer a missing bus,
lifecycle policy, mathematical function, width, or port direction.

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.build_contract_candidates \
  --overwrite
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.review_contract_candidates
```

The preflight summary distinguishes `reviewer_pass_candidate` from `blocked`.
Even a deterministic PASS is not called frozen until source-port binding and
upstream build dependencies are independently audited. API generation is limited
to reviewer-pass candidates and stops at the Verifier; it never invokes the RTL
Generator or Debugger:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api \
  P01 P02 P03 --max-api-calls 5
```

The API budget is global, not per case. An `ARCHITECTURE_CONFLICT` is recorded
verbatim and stops that case; it is never sent through the Verifier-local artifact
repair loop.

For audited one-call-at-a-time evaluation, use the resumable step runner. Its state
is stored only below the gitignored `local_results/<case>/` directory, and it carries
forward exactly the deterministic repair context an uninterrupted bounded run would
use. This allows source inspection and general validator repair between calls without
restarting the Verifier from its initial empty draft:

```bash
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api_step \
  P01 --reset

# Inspect the saved candidate/result, then resume with exactly one more API call.
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api_step \
  P01

# After a general validator improvement rejects a previously accepted candidate,
# reopen that exact saved candidate without spending an API call.
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api_step \
  P01 --reopen-reviewed-candidate

# After an audited RTL simulation failure, provide one local structured-finding
# JSON file and resume the same repair context on the next separately authorized call.
python -m \
  multigent.verifier_tool.tool_regression.benchmarks.external_feature_benchmarks.run_external_api_step \
  P01 --reopen-simulation-failure local_results/p01/simulation_finding.json
```

This runner is evaluation infrastructure only. It does not alter a frozen contract,
production prompt, or verifier-tool pool. Reopening a candidate performs no API call;
it only updates gitignored evaluation state.
