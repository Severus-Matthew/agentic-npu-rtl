# Delta pipeline implementation and validation

Repository: `/u/mjha1/agentic-npu-rtl`.
Run: `/u/mjha1/agentic-npu-rtl/multigent/runs/gemm-8x8x32-vivado-20260911`.

## Results

- Repository suite: **128 passed in 12.64 seconds**, including a real Verilator/cocotb smoke test and an intentionally incorrect expectation that is correctly rejected. Baseline was 87 tests.
- Final `git diff --check`: passed.
- Generated GEMM suite: four cocotb tests covering directed behavior, 100 randomized jobs with backpressure, reset, and protocol-error recovery.
- Live GEMM result: **REPAIR_BUDGET_EXHAUSTED**, with **SIMULATION_TIMEOUT** after five agent-mediated RTL repair iterations. Architecture version 2; two verifier revisions. No verified RTL candidate selected.
- Vivado: **NOT_RUN**. PPA optimization iterations: zero. No PPA measurements were fabricated.

The pipeline implementation and repository tests are complete, but successful functional generation of this GEMM benchmark remains unresolved. A timeout does not establish whether the remaining defect is in RTL or the testbench. All benchmark RTL changes flowed through the agents.

## Changes

- LangGraph now controls frozen architecture handoffs, verification reuse, Debugger-mediated RTL and verification repairs, bounded diagnostic probes, synthesis, constrained optimization, and final reporting. Durable state supports resuming a failed role without unnecessarily repeating prior work.
- Artifact guards preserve architecture, tests and reference models across RTL edits, retain attempt snapshots, and check exact verified RTL hashes before FPGA processing. The independent Verifier receives a projected architecture-only context; neither RTL nor Debugger raw evidence is exposed to it.
- Architect contracts require explicit module ports. RTL semantic validation rejects incomplete output, checks repair scope and protected modules, and permits bounded self-repair. Verifier semantic validation also has bounded retry and proper context reconstruction.
- Cocotb execution fixes reference imports, Python environment selection, subprocess timeouts, and result accounting. Empty, skipped, failed or incomplete result sets cannot become PASS. Diagnostic monitors gather evidence separately and cannot confer acceptance.
- A deterministic external Vivado adapter prepares source snapshots, Tcl, constraints and provenance manifests; parses utilization, timing, critical paths and estimated power; checks routing/DRC/report completeness; and handles unavailable tools and invalid output explicitly.
- The PPA Optimizer consumes frozen contracts, validated metrics and bounded report excerpts. Explicit optimization plans constrain RTL edits. Every candidate must pass full functional regression and another Vivado run before selection.
- Updated schemas, CLI, compatibility entry points, documentation and role skills under `Skills/npu_multiagent_skills/skills/`; added a PPA Optimizer skill.
- Fixed integration failures involving empty Verifier context, repair metadata, missing internal port contracts, cocotb reference imports, local compiler selection, and oversized diagnostic API inputs. Historical errors remain in the run report for auditability.

Main implementation files are under `multigent/tools/{vivado,cocotb_runner,diagnostic,process}.py`, `multigent/orchestration/{graph,routes,artifacts,ppa_node}.py`, and `multigent/agents/`. Full usage instructions are in `multigent/README.md`.

## Commands and artifacts

Run repository tests on Delta:

```sh
cd /u/mjha1/agentic-npu-rtl
export PATH=/u/mjha1/agentic-npu-rtl/.venv/bin:/u/mjha1/.local/verilator-env/bin:$PATH
export MAKEFLAGS="CXX=g++ LINK=g++ AR=ar"
.venv/bin/python -m pytest multigent/tests -q
```

The run directory contains `state/latest.json`, `reports/final.json`, `reports/final.md`, `reports/test_suite.txt`, generated contracts/RTL/tests, attempt snapshots and diagnostic evidence. The original default workspace was preserved. Source backup: `/tmp/npu-before-vivado-20260911.tgz` on Delta. No commit was created.

CLI options and external Vivado bundle instructions:

```sh
.venv/bin/python -m multigent.orchestration.graph --help
.venv/bin/python -m multigent.tools.vivado --help
```

Remaining blockers are the GEMM simulation timeout and subsequent validation on a compatible Vivado machine with an explicit FPGA part and clock configuration. Vivado parsing/orchestration were tested with fixtures; actual Vivado execution remains unvalidated. Generated oracle checks are not a proof of oracle correctness. Maximum operating frequency is not claimed without measurement.
