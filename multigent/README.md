# Multi-Agent Hardware RTL Runtime

This directory contains the executable multi-agent runtime for autonomous hardware architecture, RTL generation, independent verification, repair, and implementation-quality evaluation.

The runtime is intentionally workload-agnostic. A GEMM accelerator is one benchmark instance, not a framework default. The same agent/runtime contracts must support other architectures whose operations, dimensions, arithmetic, storage, interfaces, and module structure are different.

All LLM roles use the same configured API model in controlled experiments so improvements can be attributed to role specialization, structured communication, deterministic feedback, and orchestration rather than different model capability.

## Core rule

**LLMs propose. Deterministic engineering tools decide correctness and implementation metrics.**

## User input

The user supplies minimal computational/behavioral intent, for example:

```text
design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type
```

or a completely different hardware request. Runtime code must not inject benchmark-specific microarchitecture defaults.

A deterministic intake layer adds only fixed technical policy such as synthesizable SystemVerilog requirements, verification policy, and the deterministic Synopsys-report boundary.

Fixed technical constraints live in:

```text
multigent/config/project_constraints.yaml
```

The deterministic context builder lives in:

```text
multigent/intake/request_builder.py
```

## Agent 1: Architect

The Architect converts the minimal request into a frozen, internally consistent implementation contract. It chooses unspecified technical details appropriate to the requested workload and does not write RTL.

Run:

```bash
python -m multigent.agents.architect \
  --request "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type" \
  --run-id dense-gemm-008
```

On `READY`, it writes:

```text
multigent/workspace/architecture/
├── architecture_contract.yaml
├── interface_contract.yaml
├── module_manifest.json
├── acceptance_criteria.yaml
└── architect_result.json
```

The exact original request is retained under `multigent/workspace/specs/` for provenance.

Before acceptance, the Architect output passes strict JSON-schema validation plus deterministic semantic cross-reference checks. Architecture is then treated as frozen for downstream agents.

## Deterministic RTL context

The RTL Generator does not ask the user to restate architecture details. Its context is assembled deterministically from:

1. the exact original request,
2. fixed RTL/synthesis policy, and
3. the frozen Architect artifacts.

Optional manual inspection/export:

```bash
python -m multigent.scripts.prepare_rtl_input \
  --run-id dense-gemm-008
```

which writes:

```text
multigent/workspace/specs/derived/rtl-input-dense-gemm-008.yaml
```

LangGraph nodes may build the same context directly without this intermediate file.

## Agent 2: RTL Generator

The RTL Generator is accelerator-agnostic. It derives all operations, widths, signedness, dimensions, parameters, storage, sequencing, interfaces, reset behavior, and module names from the frozen architecture.

Supported task modes are:

```text
INITIAL_GENERATION
FUNCTIONAL_REPAIR
SYNTHESIS_REPAIR
PPA_OPTIMIZATION
```

For initial generation:

```bash
python -m multigent.agents.rtl_generator \
  --run-id dense-gemm-008 \
  --task-type INITIAL_GENERATION
```

The agent returns one of:

```text
RTL_GENERATED
ARCHITECTURE_CONFLICT
REPAIR_BLOCKED
```

`RTL_GENERATED` writes only `.sv` files under:

```text
multigent/workspace/rtl/
```

Initial generation must implement exactly the modules in the frozen manifest. It may not invent helper modules or change the architecture/interface.

If the frozen architecture cannot be implemented coherently, the RTL Generator returns a structured `ARCHITECTURE_CONFLICT` with affected modules, technical evidence, and the exact decision required from the Architect. It does not silently make that architectural decision.

## LangGraph orchestration

LangGraph is the communication and routing backbone for the multi-agent workflow. Agents do not conduct uncontrolled free-form conversations with one another.

Shared graph state is defined in:

```text
multigent/orchestration/state.py
```

The RTL node adapter is:

```text
multigent/orchestration/rtl_node.py
```

`RTLGeneratorAgent.run_from_state(...)` accepts graph state and returns a partial state update containing:

```text
rtl_status
rtl_result
rtl_files
architecture_conflict
needs_regression
```

This allows deterministic graph routing such as:

```text
Architect
   ↓
frozen architecture
   ↓
RTL Generator
   ├── RTL_GENERATED ─────────→ verification/tool nodes
   ├── ARCHITECTURE_CONFLICT ─→ Architect revision route
   └── REPAIR_BLOCKED ────────→ orchestrator retry/failure policy
```

Routing and iteration budgets belong to LangGraph, not to individual agents.

The later complete graph will add independent Verifier, deterministic compile/simulation, Debugger/repair, Synopsys integration, PPA Judge, and optimization/regression loops using the same typed state.

## API and dependencies

Install dependencies:

```bash
pip install -r multigent/requirements.txt
```

The runtime uses LangGraph 1.x and supports the cluster's Python 3.12 environment.

Configure `.env` locally:

```bash
OPENAI_API_KEY=your_real_key
OPENAI_BASE_URL=
NPU_AGENT_MODEL=gpt-5.3-codex
NPU_AGENT_API_MODE=responses
NPU_AGENT_TRUST_ENV=false
```

`.env` is gitignored. Verify API access with:

```bash
python -m multigent.scripts.check_api --list-models
```

## Tests

Run the current Architect and RTL Generator offline tests before paid agent calls:

```bash
pytest \
  multigent/tests/test_agent_runtime.py \
  multigent/tests/test_architect.py \
  multigent/tests/test_architect_skill.py \
  multigent/tests/test_rtl_generator.py \
  -v
```

The RTL Generator tests use a non-GEMM streaming FIR fixture to guard against benchmark-specific runtime assumptions.

## Technical synthesis boundary

`multigent/tools/synopsys_interface.py` defines the technical integration contract for Synopsys execution. The multi-agent runtime consumes real structured reports from that boundary and never substitutes LLM-estimated timing, area, power, frequency, or utilization.
