# Generalized LangGraph hardware generation

See [the integration notes](INTEGRATION.md) for the current branch, exact changes,
398-test validation, successful live smoke run, and deferred Vivado work.

## Live browser interface and model selection

Launch on Delta (no Tk/X11/display server or additional UI dependencies needed):

```bash
cd /u/mjha1/agentic-npu-rtl
bash multigent/scripts/start_ui.sh --port 8765
```

In a terminal on your laptop, keep an SSH tunnel running:

```bash
ssh -N -L 8765:127.0.0.1:8765 mjha1@dtai-login.delta.ncsa.illinois.edu
```

Open the **full localhost link printed by the server**, including its `#` session
token. The server listens only on loopback. The token stays in browser session
storage and API keys remain on the server. This is a private, single-user tool,
not a public web deployment. Keep the UI server running while a run is active;
restarting it does not reattach its process monitor. Existing saved artifacts remain
viewable and a lost process monitor is explicitly identified.

Choose GPT-5.3 Codex, GPT-5.6 Sol, or GPT-6 Astra at the top, enter any hardware
request, and click **Start pipeline**. Each run gets a unique directory under
`multigent/runs/`. The model is fixed for that run and recorded in state. Model
switching is available before the next run; all agent roles use the chosen model.
The selector and request are disabled while the server has an active run.

The left panel groups generated files by role and opens them as read-only text.
Earlier attempts and logs can also be expanded. Simulator build products and files
outside the run are excluded. Large previews are explicitly truncated. The right
panel follows real `started`/`finished`/`failed` events from LangGraph, polling every
1.5 seconds. A finished stage is not a functional PASS. Diagnostic and repair loops
are shown, and missing Vivado or failed checks never become fabricated success.
Older runs without events use recorded history and may have no recorded model ID.
On narrow screens the panels stack vertically; use a desktop-width browser for the
side-by-side view. This UI launches new runs; saved-state resume remains a CLI action.
The UI defaults to stopping after functional verification while Vivado is deferred.
Vivado target configuration remains in the CLI for now.

CLI model selection:

```bash
export NPU_WORKSPACE_ROOT="$PWD/multigent/runs/my-new-run"
python -m multigent.orchestration.graph --model gpt-6-astra \
  --request "YOUR HARDWARE REQUEST" --run-id my-new-run
```

Resuming a run with a recorded model preserves that model; changing it requires a
new run. `NPU_AGENT_REASONING_EFFORT` continues to control reasoning separately.

Check actual API access and structured-output compatibility for all three models:

```bash
.venv/bin/python -m multigent.scripts.check_models \
  --output multigent/reports/model-check.json
```

This sends one small arithmetic/friendly-sentence prompt per model, checks the
answer and strict JSON response, and records returned model IDs and usage. All
three passed with the configured Delta API account on 2026-09-11. This is an API
compatibility check, not a hardware-generation benchmark. UI/model additions bring
the repository suite to **139 passing tests** (13.42 seconds in the recorded run).

The executable workflow is `multigent.orchestration.graph`. The older
`multigent.orchestrator.graph` and `multigent.scripts.run_workflow` entry points
forward to it. Runtime logic has no GEMM-specific dimensions, names or arithmetic.

## Flow and ownership

Natural-language request → Architect ↔ **Contract Reviewer** → **parallel RTL Generator
and Independent Testbench Generator** → Testbench Reviewer → deterministic Verilator
lint and full cocotb regression, including the retained coverage, protocol and handoff
checks. The reviewer agents are separate model calls with separate contexts. Review
approval never substitutes for tool execution.

The `verifier_v2` role pools, operation families, protocol profiles, coverage monitors,
observed sampling and local revision-patch machinery are retained. Contract Reviewer
checks consistency and executable meaning; Architect owns every contract edit. Local
patch safeguards remain: a structural redesign outside their scope ends in an explicit
SPEC_CONFLICT rather than silently rewriting the design.

RTL and TB generation are separate LangGraph fan-out nodes, with disjoint input
allowlists, owned output directories, branch-local state and attempt snapshots. A join
collects both results and writes a durable checkpoint before review/simulation. Agents
are API calls without filesystem tools; the runtime writes their validated artifacts.
RTL-only repair and PPA optimization reuse the reviewed tests. A contract revision
invalidates approval and runs both generators against the new reviewed version.

Runtime failures, including missing observed coverage, go through Debugger. It selects
RTL repair or independent TB repair; the TB receives its own artifacts and sanitized
contract/tool evidence, never generated RTL or arbitrary Debugger prose. Testbench
schema/semantic and review failures still use the contributor's bounded local correction
path before simulation. Exhausting preflight corrections with RTL available also
escalates to architecture diagnosis; rejected drafts and static errors are explicitly
distinguished from simulation evidence. Previous attempts and failure reports remain available.

By default, seven unsuccessful dispatched repairs exhaust one implementation cycle.
The initial failed simulation precedes those seven repairs. LangGraph then asks RTL and
TB agents to independently critique **only the contracts**, and asks Debugger to examine
those critiques with full failure evidence. Debugger can request an Architect patch or
confirm the contract and re-localize the implementation defect. Up to three such
architecture escalation rounds follow the initial cycle. Global repair IDs stay
monotonic; only the per-cycle budget resets. Contract-review correction attempts have
a separate bounded budget (three per review episode, reset on approval), as do preflight TB corrections (seven).

A functional PASS proceeds to the existing deterministic Vivado adapter and constrained
PPA Optimizer → RTL optimization → full regression → Vivado. Vivado installation and
FPGA target validation are deferred. `--verification-only` stops successfully at a
real functional PASS. No missing synthesis result is represented as measured PPA.

Role skills are under `Skills/npu_multiagent_skills/skills/`; the new skill is
`contract-reviewer/SKILL.md`. The UI shows the two generators side by side, both review
stages and escalated architecture diagnosis. Contract review reports are browsable
under `contract_reviews/`. CLI budgets are recorded in run state and cannot be increased
by resuming a run.

## Run

Install `multigent/requirements.txt`; provide Verilator and its C++ build tools.
Export the API configuration from your private `.env` (never commit credentials).
Choose a separate workspace **before Python starts**:

```bash
export NPU_WORKSPACE_ROOT="$PWD/multigent/runs/my-run"
python -m multigent.orchestration.graph \
  --request "Design an 8 x 8 x 32 GEMM accelerator with signed int8 inputs, int32 accumulation, bias and ReLU" \
  --run-id my-run --max-repair-iterations 7 --max-verifier-revisions 7 \
  --max-architecture-revisions 12 --max-architecture-escalations 3 \
  --max-contract-review-revisions 3 --verification-only
```

`NPU_WORKSPACE_ROOT` defaults to `multigent/workspace` for compatibility. Use an
empty, dedicated directory for a new run. Do not run two processes in one workspace.
The existing dense-gemm-008 workspace is not required by the new benchmark.

Delta's current Conda Verilator uses unavailable Conda compiler tools. The validated
local environment is:

```bash
export PATH="$PWD/.venv/bin:/u/mjha1/.local/verilator-env/bin:$PATH"
export MAKEFLAGS="CXX=g++ LINK=g++ AR=ar"
```

This selects the installed system compiler/archiver. The runner also puts the active
Python executable's directory first for Verilator's Python build helpers.

Resume using the **exact original request and run-id**, with the same workspace:

```bash
python -m multigent.orchestration.graph --request "$ORIGINAL_REQUEST" \
  --run-id my-run --resume-state "$NPU_WORKSPACE_ROOT/state/latest.json"
```

Resuming reruns verification before consuming PPA. Resume budgets come from the
saved state. `--use-frozen-architecture --use-existing-rtl` also supports older
workspaces but starts a new history; prefer saved-state resume for new runs.

## Deterministic verification

Verilator lint/elaboration must pass before cocotb runs. Cocotb 2.x runner results
must contain executed, non-skipped tests, no failures/errors, and a successful worker
exit. Inherited test-filter variables are cleared. Seeds are fixed by the plan;
whole-process timeouts kill the compiler/simulator process group. Build configuration
failures are distinct from RTL failures. Individual attempts include ppa/verifier
revision identifiers so optimization results cannot overwrite prior evidence.

Verifier generation has one semantic self-correction attempt in addition to the API
schema retry. Exhaustion is a structured failure with a final report, not an uncaught
traceback. Testbench repair has its own bounded graph route through Debugger. Static
checks do **not** prove a generated golden model correct or prove coverage claims.
The skill requires analytical oracle checks, precise cycle ownership, legal phase
writes, signed arithmetic, held valid/payload, and preservation of failing cases.
The real-simulator infrastructure smoke test independently checks signed extrema,
backpressure, reset and rejection of an intentionally wrong expected result.

## Vivado handoff

No FPGA target is guessed. Supply `--vivado-config target.json` containing:

```json
{"part":"YOUR_EXACT_FPGA_PART","clock_port":"YOUR_CONTRACT_CLOCK","period_ns":10.0}
```

An optional `xdc` path adds user constraints. For multiple clocks, the XDC must define
all clocks and relationships. This is an out-of-context synthesis/place/route flow,
not board integration or bitstream generation. Inspect unconstrained paths in
`timing_summary.rpt` before making system-level timing claims.

After functional PASS the adapter snapshots RTL, constraints, script and hashes into
`synthesis/<candidate>/`. `run.tcl` runs synthesis, optimization, placement, physical
optimization, routing, utilization, timing/critical-path, power and DRC reports.
`manifest.json` binds inputs to the verification evidence. The adapter records raw
logs, return status, report hashes and parsed metrics in `result.json`.

Missing Vivado produces `TOOL_UNAVAILABLE` with **null metrics**. Missing target
configuration, timeout, implementation failure, stale output, incomplete report
layout, provenance mismatch, DRC and timing failures are explicit statuses. No
optimizer call is made without complete deterministic reports. A bundle lacking
configuration must be regenerated using an explicit target; do not edit its frozen
manifest or script in place.

On a compatible machine with the same package installed and the prepared bundle:

```bash
python -m multigent.tools.vivado --bundle /path/to/candidate --timeout 3600
```

Return the entire bundle, then rerun full verification and import its reports:

```bash
python -m multigent.orchestration.graph --request "$ORIGINAL_REQUEST" \
  --run-id my-run --resume-state "$NPU_WORKSPACE_ROOT/state/latest.json" \
  --vivado-config target.json --external-vivado-bundle /path/to/returned/candidate
```

Import checks current RTL, target, constraints, script and raw report hashes and
re-parses metrics. It cannot authenticate that an untrusted third party actually ran
Vivado; only use bundles from your trusted tool host. Parsing is tested with clearly
labeled fixtures; real Vivado validation remains required on a compatible machine.
FPGA area is resource counts, power is Vivado's activity-dependent estimate, and
`fmax_mhz` remains null because a frequency sweep has not been run. Reported slack and
critical-path delay must not be misrepresented as a measured maximum frequency.

## Optimization and acceptance

`--ppa-objective` selects `lut`, `estimated_power_w`, or `critical_path_delay_ns`
(minimize). A plan must cite the current report manifest, name allowed modules,
protect all others, preserve contracts, and require FULL regression. RTL cannot
modify outside the plan. Architecture-changing optimizations stop for a new design
decision instead of silently changing semantics. No direct free-form agent channel
exists. Optimizer → RTL is therefore appropriate as a constrained LangGraph handoff.

Only functionally verified, timing-feasible candidates are eligible. A worse/equal
objective stops optimization and keeps the better snapshot. Exhausted budgets never
turn an infeasible design into PASS. A missing tool is not SUCCESS. Exit code 0 means
SUCCESS; exit code 2 includes explicit incomplete/tool-unavailable outcomes. Selected
RTL is identified separately from the latest working candidate.

## Artifacts and tests

- `state/latest.json`: durable state after each node.
- `attempts/`: pre-node source/contract/test snapshots, hashes and outcomes.
- `logs/agent_traces/`: model configuration, usage and prompt/skill hashes.
- `verification/`: lint, simulator results and build output.
- `synthesis/`: portable Vivado candidate bundles.
- `optimization/`: constrained optimizer plans.
- `reports/final.json` and `reports/final.md`: status, selected artifact, errors and limitations.

```bash
python -m pytest multigent/tests -q
```

Fixtures cover non-GEMM roles, negative adapter/report/provenance cases, independent
Verifier state projection, bounded repair, protected artifacts and a complete mocked
LangGraph optimization cycle. The real cocotb smoke test skips only when Verilator
is absent. No synthetic fixture metric is used as a benchmark PPA result.

API references: [cocotb timing model](https://docs.cocotb.org/en/v2.0.0/timing_model.html),
[AMD report_timing](https://docs.amd.com/r/2024.1-English/ug835-vivado-tcl-commands/report_timing),
[AMD report_timing_summary](https://docs.amd.com/r/2024.1-English/ug835-vivado-tcl-commands/report_timing_summary).

## Diagnostic escalation

`EVIDENCE_INSUFFICIENT` can trigger up to two diagnostic probes through LangGraph.
The probe instruments **copies** of the frozen test functions with a read-only
monitor, enables public simulator signals, and records the last 128 signal changes
sampled every 1 ns. Each diagnostic test has a 100 us cap, distinct from the original
full-regression policy. Diagnostic outcomes never establish PASS. Only Debugger
receives the trace; Verifier receives no implementation-derived trace or prose.
The same original full regression is required after any resulting RTL repair.

Architecture outputs now require complete internal module port lists, and the
provider-neutral acceptance field is `fpga_handoff`. Historical contracts remain
loadable; only Verifier or RTL Generator may ask Architect for a missing design
decision before an executable candidate is accepted. RTL
semantic validation rejects placeholders, empty modules, hidden extra modules and
module-to-file remapping during constrained changes. One bounded self-correction
attempt occurs before an invalid RTL response becomes a terminal report.

A saved-state resume can omit `--request` and `--run-id`; their exact original values
are read from the state. Keep `NPU_WORKSPACE_ROOT` pointed at that same run directory.

## Architect contract self-correction

Initial generation and downstream architecture revision share a semantic validation
loop: one candidate plus at most two corrected candidates. The Architect receives
the exact relational validation errors and its rejected candidate, while retaining
the original request and any revision feedback. Invalid candidates are never written
as frozen architecture artifacts. Genuine SPEC_CONFLICT responses stop normally;
transport/authentication errors do not trigger semantic retries. Retry API calls
have distinct trace filenames and emit an Architect `retrying` progress event.
Exhaustion remains a reported failure, rather than a silently accepted contract.
These corrections occur within the Architect LangGraph stage; downstream handoffs
remain controlled by the graph and only occur after successful validation.
The limit is separate from the budget for revising an accepted architecture after
RTL/verification feedback. Changes apply to newly started Python processes.

## Independent Testbench Generator

The UI now calls the former Independent Verifier the **Independent Testbench
Generator**: it writes reference models and cocotb tests from frozen contracts;
Verilator/cocotb then execute the deterministic checks. Internal `verifier` stage
IDs and artifact paths remain compatible with older runs.

The completion/error signal check accepts handle aliases, literal `getattr` reads,
and snapshot-key assertions across generated tests and reference/helper files.
It no longer requires the exact spelling `dut.signal` inside the test file itself.
This check establishes syntactic references only, not executed coverage or proven
DUT-to-snapshot dataflow. Bare comments or documentation strings do not satisfy it.
Functional simulation remains required for acceptance.

Signal-reference uncertainty is now advisory rather than a generation gate.
Findings are saved in `verification/static_review.json` with `ADVISORY_ONLY` status,
so they remain visible in the file browser without blocking simulation or spending
semantic retries. Empty implementations, invalid syntax/schema, ownership violations,
forbidden capabilities, and regression-plan mismatches remain hard errors. Actual
simulation failures and missing tool results still cannot become PASS. The static
review neither proves coverage nor proves that coverage is missing.
