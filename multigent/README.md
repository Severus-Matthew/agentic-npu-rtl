# Multi-Agent NPU Runtime

This directory contains the executable LangGraph-based multi-agent system for autonomous NPU RTL generation, verification, repair, and optimization planning.

All LLM roles use the same Codex backend (`gpt-5.3-codex`) so model capability remains controlled across one-shot, single-agent, and multi-agent experiments. The role instructions live separately under `../Skills/npu_multiagent_skills/skills/`. Every agent loads `project_contract` plus its role-specific skill.

## Ownership boundary

The multi-agent team owns architecture generation, RTL generation, independent verification, debug/repair, and PPA decision logic.

**Synopsys execution is externally owned.** `tools/synopsys_interface.py` is only the integration contract. The runtime must never fabricate synthesis, timing, power, or area values when a real Synopsys report is unavailable.

## Runtime Flow

```text
NPU specification
      |
      v
Architect Agent (Codex)
      |
      +-----------------------+
      |                       |
      v                       v
RTL Generator            Verifier
   (Codex)                 (Codex)
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
      Debugger (Codex)   verified RTL handoff
            |              |
            +--> RTL       v
                    external Synopsys flow
                              |
                              v
                       PPA Judge (Codex)
                              |
                    +---------+---------+
                    |                   |
                optimize             accept
                    |                   |
                    +--> RTL            v
                                   Final RTL
```

## Agent execution model

Agents are invoked through non-interactive `codex exec`. Codex itself is run read-only. Each Python role wrapper takes the schema-constrained result and writes only that role's whitelisted artifacts. This gives us enforceable ownership boundaries rather than relying solely on prompt instructions.

Before running live agents, install/login to Codex and install the Python dependencies:

```bash
codex login
pip install -r multigent/requirements.txt
```

### First executable agent: Architect

```bash
python -m multigent.agents.architect \
  --spec multigent/benchmarks/dense_gemm/npu_8x8_int8.yaml \
  --run-id dense-gemm-001
```

On `READY`, it may create only:

```text
multigent/workspace/architecture/
├── architecture_contract.yaml
├── interface_contract.yaml
├── module_manifest.json
├── acceptance_criteria.yaml
└── architect_result.json
```

It must not create or edit SystemVerilog.

## Directory Responsibilities

- `orchestrator/` — LangGraph state, nodes, routing, retry limits, checkpoints, and termination.
- `agents/` — Codex role wrappers that load the project contract and role-specific skills.
- `tools/` — deterministic verification tools plus the external Synopsys integration boundary.
- `schemas/` — machine-readable contracts for all agent handoffs and tool results.
- `config/` — model, workflow, retry, toolchain, and experiment settings.
- `workspace/` — run-time artifacts produced by the agents and deterministic tools.
- `benchmarks/` — fixed NPU specifications used for development and controlled experiments.
- `experiments/` — one-shot, single-agent, and multi-agent experiment definitions/results.
- `tests/` — software tests for the graph, schemas, permissions, and tool wrappers.
- `scripts/` — CLI entry points for workflow and baseline execution.

## Workspace ownership

```text
workspace/specs/          user / benchmark input
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
