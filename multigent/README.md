# Generalized LangGraph hardware generation

The executable workflow is `multigent.orchestration.graph`. The older
`multigent.orchestrator.graph` and `multigent.scripts.run_workflow` entry points
forward to it. Runtime logic has no GEMM-specific dimensions, names or arithmetic.

## Flow and ownership

Natural-language request → Architect → independent Verifier generates the golden
model and TB → TB-only Verifier Reviewer → RTL Generator → deterministic Verilator
lint and full cocotb regression. If Verifier cannot derive one executable expected
behavior, it asks Architect before initial RTL generation. Architect alone decides
whether to patch the contract or confirm that the existing contract is already clear.
The Reviewer never contacts Architect. Failures go to Debugger, then constrained RTL
repair, high-confidence independent verification-infrastructure repair, or an
explicit terminal failure; Debugger never changes or escalates the contract.
A functional PASS proceeds to the deterministic external Vivado adapter, then PPA
Optimizer and, when justified, RTL optimization → full regression → Vivado again.
LangGraph owns every transition and retry budget. Agents only return structured
artifacts; they do not invoke each other.

Architect owns architecture; RTL Generator owns RTL; Verifier owns reference and
tests; Debugger owns diagnosis and repair plans; PPA Optimizer owns optimization
plans. Generation calls receive role skills from
`Skills/npu_multiagent_skills/skills/`. Prompt/skill hashes and API usage are logged.
Generated artifacts pass schema and semantic validation before writing.

Verifier generation never receives RTL, RTL Generator responses, Debugger prose,
or compiler/simulator source excerpts. On a confirmed TESTBENCH_ERROR, the graph
sends a fixed infrastructure-review request plus the Verifier's own previous files
and frozen contracts. Original artifacts and failures remain in attempt snapshots.
RTL repair and optimization reuse the frozen, reviewed Verifier artifacts. A real
Architecture revision invalidates them and runs Verifier again; an Architect
`CONTRACT_CONFIRMED` decision preserves the contract version and returns its exact
resolution to Verifier. Initial RTL generation is blocked until the current TB-only
review approves the actual reference/tests/coverage definitions. The Verifier remains
independent of RTL and receives an up-front first-candidate checklist for checked
traffic, observed evidence and exact stimulus-intent labels.

## Run

Install `multigent/requirements.txt`; provide Verilator and its C++ build tools.
Export the API configuration from your private `.env` (never commit credentials).
Choose a separate workspace **before Python starts**:

```bash
export NPU_WORKSPACE_ROOT="$PWD/multigent/runs/my-run"
python -m multigent.orchestration.graph \
  --request "Design an 8 x 8 x 32 GEMM accelerator with signed int8 inputs, int32 accumulation, bias and ReLU" \
  --run-id my-run --max-repair-iterations 5 --max-verifier-revisions 2 \
  --max-architecture-revisions 2 --max-ppa-iterations 3
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
