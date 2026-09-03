# Multi-Agent Hardware RTL Runtime

This directory contains the executable multi-agent runtime for autonomous hardware architecture, RTL generation, independent verification, repair, and implementation-quality evaluation.

The runtime is intentionally workload-agnostic. A GEMM accelerator is one benchmark instance, not a framework default. The same agent/runtime contracts must support other architectures whose operations, dimensions, arithmetic, storage, interfaces, and module structure are different.

All LLM roles use the same configured API model in controlled experiments so improvements can be attributed to role specialization, structured communication, deterministic feedback, and orchestration rather than different model capability.

## Core rule

**LLMs propose. Deterministic engineering tools decide correctness and implementation metrics.**

## User input and deterministic context

The user supplies minimal computational/behavioral intent. A deterministic intake layer adds only fixed technical policy. Runtime code must not inject benchmark-specific microarchitecture defaults.

Fixed policy:

```text
multigent/config/project_constraints.yaml
```

Deterministic context builders:

```text
multigent/intake/request_builder.py
```

The RTL and Verifier contexts are intentionally different. RTL receives the frozen architecture needed for implementation. Verifier receives the original request, frozen Architect artifacts, and verification policy but **not generated RTL source or RTL Generator output**.

## Agent 1: Architect

The Architect converts the minimal request into a frozen, internally consistent implementation contract and does not write RTL.

```bash
python -m multigent.agents.architect \
  --request "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type" \
  --run-id dense-gemm-008
```

On `READY` it writes:

```text
multigent/workspace/architecture/
├── architecture_contract.yaml
├── interface_contract.yaml
├── module_manifest.json
├── acceptance_criteria.yaml
└── architect_result.json
```

Before acceptance, output passes strict JSON-schema validation plus deterministic semantic cross-reference checks.

## Agent 2: RTL Generator

The RTL Generator derives all implementation details from the frozen contract. It may return:

```text
RTL_GENERATED
ARCHITECTURE_CONFLICT
REPAIR_BLOCKED
```

Initial generation writes exactly the manifest modules under:

```text
multigent/workspace/rtl/
```

It may not silently change architecture/interface semantics.

## Agent 3: Independent Verifier

The Verifier creates:

```text
multigent/workspace/reference/*.py
multigent/workspace/tests/*.py
multigent/workspace/verification/verification_plan.yaml
multigent/workspace/verification/verifier_result.json
```

Its generation context excludes generated RTL. Expected behavior is derived from the original request plus frozen architecture/interface/acceptance artifacts.

The Verifier returns only:

```text
VERIFICATION_READY
ARCHITECTURE_CONFLICT
```

`VERIFICATION_READY` does **not** mean the RTL passed. It means an independent executable reference/test environment is ready for deterministic tools.

## Deterministic verification

After `VERIFICATION_READY`, LangGraph runs:

```text
Verilator lint/elaboration
        ↓ PASS
cocotb full regression using Verilator
```

Tool wrappers:

```text
multigent/tools/verilator.py
multigent/tools/cocotb_runner.py
```

Verilator process return codes and cocotb xUnit results are authoritative. Infrastructure states such as `TOOL_UNAVAILABLE` are kept separate from RTL failures.

Deterministic evidence is stored under:

```text
multigent/workspace/verification/
├── verilator-lint-<tag>.json
├── cocotb-<tag>.json
├── verification-result-<tag>.json
└── build/<tag>/...
```

Current deterministic routing is:

```text
PASS                -> READY_FOR_SYNTHESIS
COMPILE_FAILURE     -> REPAIR_REQUIRED
SIMULATION_FAILURE  -> REPAIR_REQUIRED
SIMULATION_TIMEOUT  -> REPAIR_REQUIRED
TOOL_UNAVAILABLE    -> VERIFICATION_TOOL_UNAVAILABLE
```

`REPAIR_REQUIRED` is currently a terminal placeholder. The next graph extension replaces it with Debugger -> constrained RTL repair -> deterministic re-verification.

## LangGraph orchestration

LangGraph is the communication and routing backbone. Agents do not conduct uncontrolled free-form conversations.

```text
User / checkpoint
       ↓
Architect
       ↓
RTL Generator
   ├── ARCHITECTURE_CONFLICT ─────→ Architect revision
   └── RTL_GENERATED
             ↓
Independent Verifier
   ├── ARCHITECTURE_CONFLICT ─────→ Architect revision
   └── VERIFICATION_READY
             ↓
Verilator + cocotb
   ├── PASS ──────────────────────→ synthesis placeholder
   └── FAIL ──────────────────────→ repair placeholder
```

Shared typed state:

```text
multigent/orchestration/state.py
```

Routing:

```text
multigent/orchestration/routes.py
```

Graph:

```text
multigent/orchestration/graph.py
```

## Resume the current dense-gemm-008 RTL at verification

The current six generated RTL files can be reused without another Architect or RTL Generator API call:

```bash
python -m multigent.orchestration.graph \
  --request "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type" \
  --run-id dense-gemm-008 \
  --use-frozen-architecture \
  --use-existing-rtl \
  --max-architecture-revisions 2
```

This starts at the independent Verifier, then runs deterministic verification.

## Dependencies

```bash
pip install -r multigent/requirements.txt
```

The Python regression wrapper uses cocotb 2.x Python Runners with Verilator. `verilator` itself must be installed/loaded and available on `PATH`.

API configuration:

```bash
OPENAI_API_KEY=your_real_key
OPENAI_BASE_URL=
NPU_AGENT_MODEL=gpt-5.3-codex
NPU_AGENT_API_MODE=responses
NPU_AGENT_TRUST_ENV=false
```

## Offline tests

Before paid agent calls:

```bash
pytest \
  multigent/tests/test_agent_runtime.py \
  multigent/tests/test_architect.py \
  multigent/tests/test_architect_skill.py \
  multigent/tests/test_rtl_generator.py \
  multigent/tests/test_verifier.py \
  multigent/tests/test_verification_tools.py \
  multigent/tests/test_orchestration.py \
  -v
```

RTL Generator and Verifier tests use non-GEMM streaming FIR fixtures to guard against benchmark-specific runtime assumptions.

## Technical synthesis boundary

`multigent/tools/synopsys_interface.py` defines the deterministic Synopsys integration contract. The runtime never substitutes LLM-estimated timing, area, power, frequency, or utilization for authoritative tool reports.
