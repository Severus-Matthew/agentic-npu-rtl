# Contract review and parallel-generation integration

Integration branch: `integration/contract-review-parallel`.
DeltaAI checkout: `/u/mjha1/agentic-npu-rtl-integration`.
The original `/u/mjha1/agentic-npu-rtl` checkout stays on `blackhole`, updated to
`2a6ec12` (PicoRV32 CPU source). The integration merges `verifier_v2` at `5c71a19`
with that blackhole head. Historical run/build files stay on disk and in their
original branch; they are not reintroduced into version control by this merge.

## Preserved contributor work

The entire `multigent/verifier_tool/` subtree is unchanged from `verifier_v2`:
role pools, protocol profiles, operation families, generated assertions, coverage
bins, observed-operation sampling, stimulus history, and protocol/handoff checks.
The Architect agent and its existing contract schema and local revision-patch
implementation are retained. The existing TB-only reviewer and source-patch repair
mechanisms are retained. The empty `__init__.py` exception from blackhole is restored
without permitting empty implementation/test files or bypassing security checks.

## New and adjusted implementation

- `agents/contract_reviewer.py`, `schemas/contract_review.schema.json`, and the
  `contract-reviewer` skill implement a distinct API-backed contract reviewer.
  Its prompt contains contracts, the user's request, prior review, and contract
  patch only. Approval is hash-bound and is invalidated by an Architect update.
- `orchestration/contract_review_node.py` routes precise reviewer findings back
  to Architect, then re-reviews. Three corrections are allowed per review episode;
  approval resets that episode counter. Failed approval never authorizes generation.
- `orchestration/parallel_generation.py` implements the actual LangGraph fan-out
  and barrier join. Generator workers return disjoint update keys and take only
  allowed state fields. Workers snapshot their own inputs; the join publishes a
  combined durable state. No worker writes the shared latest checkpoint.
- `orchestration/architecture_escalation.py` collects separate, contract-only RTL
  and TB critiques, then asks Debugger to examine those critiques with authoritative
  failures and source. Only Architect can enact a requested amendment.
- `graph.py`, `routes.py`, `state.py`, and `debugger_node.py` enforce the new gates
  and budgets. Seven dispatched functional/coverage repair attempts are allowed
  per cycle after its first failure. Three escalation rounds can follow the initial
  cycle. Global repair IDs never reset; per-cycle counters reset after escalation.
  Both RTL repair and TB repair count. TB preflight/schema/reviewer correction remains
  the existing separate bounded path before deterministic simulation can run. Exhausting it with RTL present also
  triggers architecture diagnosis using static evidence and the rejected TB draft.
- `artifacts.py` now gates generation on current contract approval, and retains
  the existing TB review/hash gate before simulation and verified-artifact gate
  before synthesis. Original failures remain in attempt snapshots.
- The Debugger accepts evidence-backed `COVERAGE_MISS` as a possible verifier-owned
  repair, while still requiring high confidence and a supported cause domain.
  Coverage misses therefore go through Debugger instead of directly to TB repair.
- The UI displays parallel generator blocks, both reviewers, and architecture
  diagnosis. Review files are browsable. Verification-only runs are the default
  while Vivado is deferred. Every new agent uses the run's selected model.

Architect local patches still prohibit structural redesign. If a genuine fix falls
outside that scope, the run must report SPEC_CONFLICT; it cannot rewrite frozen
interfaces or relax acceptance to hide a failed implementation.

## Validation

Full DeltaAI suite: **398 passed** in **29.81 seconds**, with Verilator available.
This includes the contributor's real simulator/coverage tests and new behavioral
checks for overlapping generation, independent contexts, hash-bound approval,
review correction, failure joining, model selection, and all three escalation rounds.
The full repeated-failure graph test dispatches 28 RTL repairs, performs 29 failed
simulations, collects six independent critiques, and stops after three escalations.
Those graph-budget tests use controlled fake agents/tool results; they are not
claims of generated-hardware correctness or measured PPA.

The new Contract Reviewer skill passes the skill validator. `git diff --check`
passes. The browser UI was exercised with real API-backed runs and file browsing.

Real runs are under `multigent/runs/` (ignored by Git):

- `contract-parallel-gemm-20260916` (GPT-5.3 Codex): Architect/reviewer corrections
  and parallel generation executed; stopped on remaining contract-review findings.
  This exposed the review-episode counter/continuity improvement now included.
- `run-20260916-084352-50e490` (GPT-5.3 Codex, streaming adder): contract review and
  parallel generation executed; TB generation corrected several preflight defects,
  reached TB review, and stopped after its bounded source-repair attempts on an
  unannotated assertion. The validator's reported source line matched the source
  supplied for repair. No checks or generated RTL were manually changed.

- `run-20260916-084820-cad227` (GPT-5.6 Sol, streaming adder): **SUCCESS**.
  Contract Reviewer approved the architecture; RTL and TB generation overlapped.
  One semantic TB correction supplied the required assertion annotation; TB Reviewer
  then approved. Verilator returned PASS/exit 0. Full cocotb regression passed
  (one test function containing 9 directed and 100 randomized checked stimuli).
  All **31/31 required observed coverage bins** were hit, with no missing bins.
  Final artifact hashes match the verified hashes. No generated RTL was manually
  edited. Vivado was skipped through `--verification-only`.

A stopped run is a recorded failure, not functional acceptance. The current merge
is tested orchestration; model-generated designs can still exhaust bounded review
or repair attempts. Vivado installation/target validation is deferred by request.

## Run it

The integration UI is served on port 8766, separately from the prior app on 8765:

```bash
cd /u/mjha1/agentic-npu-rtl-integration
bash multigent/scripts/start_ui.sh --port 8766
```

Do not start a second server if this port is already occupied. From the laptop,
forward the port using the existing DeltaAI control connection:

```bash
ssh -S /tmp/delta-ui-reconnect -O forward \
  -L 8766:127.0.0.1:8766 mjha1@dtai-login.delta.ncsa.illinois.edu
```

Use the full session link printed by the UI server. Its session token and API
credentials must not be committed. The integration checkout reuses the original
checkout's `.venv` and private `.env` through local ignored symlinks.

A CLI run should set a new `NPU_WORKSPACE_ROOT` before Python starts, choose a model,
provide `--request` and `--run-id`, and use `--verification-only` until Vivado is ready.
Review and repair budgets are explicit CLI flags documented in `README.md`.
