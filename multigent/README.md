# Multi-Agent NPU Runtime

This directory contains the executable LangGraph-based multi-agent system for autonomous NPU RTL generation, verification, repair, and optimization planning.

All LLM roles use the **same configured API model** so model capability remains controlled across one-shot, single-agent, and multi-agent experiments. The role instructions live separately under `../Skills/npu_multiagent_skills/skills/`. Every agent loads `project_contract` plus its role-specific skill.

## User-facing input philosophy

The user should provide only the computational intent, not a hand-written architecture specification.

Example:

```text
design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type
```

The runtime then separates three sources of authority:

```text
USER
  └── computation / datatype intent only

RUNTIME
  └── fixed project rules
      ├── SystemVerilog
      ├── synthesizable RTL only
      ├── forbidden RTL constructs
      ├── verification policy
      └── external Synopsys ownership

ARCHITECT AGENT
  └── actual architecture decisions
      ├── compute organization
      ├── array dimensions
      ├── dataflow
      ├── buffering
      ├── pipeline
      ├── interface / handshake
      ├── reset behavior
      ├── overflow semantics
      ├── parameterization
      ├── control
      ├── latency model
      └── module decomposition
```

This distinction is important experimentally: architecture choices are attributable to the Architect agent rather than being hidden in a large user-authored YAML file.

Fixed project rules live in:

```text
multigent/config/project_constraints.yaml
```

The natural-language intake builder lives in:

```text
multigent/intake/request_builder.py
```

## Ownership boundary

The multi-agent team owns architecture generation, RTL generation, independent verification, debug/repair, and PPA decision logic.

**Synopsys execution is externally owned.** `tools/synopsys_interface.py` is only the integration contract. The runtime must never fabricate synthesis, timing, power, or area values when a real Synopsys report is unavailable.

## Runtime Flow

```text
minimal natural-language request
             |
             v
 deterministic intake builder
             |
             v
Architect Agent (API model)
      |
      +-----------------------+
      |                       |
      v                       v
RTL Generator            Verifier
 (API model)             (API model)
      |                       |
      +-----------+-----------+
                  |
                  v
        Deterministic Verification
        lint / compile / simulation
              /          \
           FAIL          PASS
            |              |
            v              v
   Debugger (API model)  verified RTL handoff
            |              |
            +--> RTL       v
                    external Synopsys flow
                              |
                              v
                    PPA Judge (API model)
                              |
                    +---------+---------+
                    |                   |
                optimize             accept
                    |                   |
                    +--> RTL            v
                                   Final RTL
```

## Agent execution model

Agents call the configured OpenAI API directly through the Python SDK. The model returns schema-constrained structured proposals; each Python role wrapper writes only that role's whitelisted artifacts. This gives us enforceable ownership boundaries rather than relying solely on prompt instructions.

## Local API setup

Install dependencies:

```bash
pip install -r multigent/requirements.txt
```

Copy the example configuration:

```bash
cp .env.example .env
```

For the standard OpenAI endpoint, `OPENAI_BASE_URL` may be left blank.

```bash
OPENAI_API_KEY=your_real_key
OPENAI_BASE_URL=
NPU_AGENT_MODEL=gpt-5.3-codex
NPU_AGENT_API_MODE=responses
NPU_AGENT_TRUST_ENV=false
```

`.env` is gitignored. Never commit or paste the real API key into GitHub, issues, logs, or prompts.

Check the connection before running an agent:

```bash
python -m multigent.scripts.check_api --list-models
```

## Agent 1: Architect

The normal Architect command is now:

```bash
python -m multigent.agents.architect \
  --request "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type" \
  --run-id dense-gemm-001
```

The runtime automatically records the exact request plus injected project policy at:

```text
multigent/workspace/specs/request-dense-gemm-001.yaml
```

On `READY`, the Architect may create only:

```text
multigent/workspace/architecture/
├── architecture_contract.yaml
├── interface_contract.yaml
├── module_manifest.json
├── acceptance_criteria.yaml
└── architect_result.json
```

It must not create or edit SystemVerilog.

The old `--spec <yaml>` input remains only for legacy benchmarks/tests and is not the preferred research workflow.

## Preparing the RTL Generator input

After the Architect succeeds, build the next agent's complete input deterministically:

```bash
python -m multigent.scripts.prepare_rtl_input \
  --run-id dense-gemm-001
```

This creates:

```text
multigent/workspace/specs/derived/rtl-input-dense-gemm-001.yaml
```

That file combines:

1. the exact original user request,
2. fixed RTL/project constraints, and
3. the Architect's frozen architecture/interface/module/acceptance contracts.

The user does **not** need to restate those details for the RTL Generator.

## Directory Responsibilities

- `intake/` — converts minimal user intent into machine-owned agent context without inventing architecture.
- `orchestrator/` — LangGraph state, nodes, routing, retry limits, checkpoints, and termination.
- `agents/` — API-backed role wrappers that load the project contract and role-specific skills.
- `tools/` — deterministic verification tools plus the external Synopsys integration boundary.
- `schemas/` — machine-readable contracts for all agent handoffs and tool results.
- `config/` — project constraints, workflow, retry, toolchain, and experiment settings.
- `workspace/` — run-time artifacts produced by the agents and deterministic tools.
- `benchmarks/` — fixed natural-language benchmark requests and legacy structured fixtures.
- `experiments/` — one-shot, single-agent, and multi-agent experiment definitions/results.
- `tests/` — software tests for the graph, schemas, permissions, and tool wrappers.
- `scripts/` — CLI entry points for workflow, context preparation, and baselines.

## Workspace ownership

```text
workspace/specs/          original/derived runtime inputs
workspace/architecture/   Architect Agent
workspace/rtl/            RTL Generator
workspace/reference/      Verifier
workspace/tests/          Verifier
workspace/diagnostics/    Debugger
workspace/synthesis/      external Synopsys results only
workspace/optimization/   PPA Judge
workspace/logs/           orchestrator + agent/tool logs
workspace/final/          accepted deliverables only
```

LLMs propose. Deterministic engineering tools decide correctness. Synopsys-generated reports decide implementation metrics when the external integration is available.
