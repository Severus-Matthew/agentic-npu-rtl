# Multi-Agent NPU Runtime

This directory contains the executable LangGraph-based multi-agent system for autonomous NPU RTL generation, verification, repair, synthesis, and PPA optimization.

The role instructions live separately under `../Skills/npu_multiagent_skills/skills/`. Every agent must load `project_contract` plus its role-specific skill.

## Runtime Flow

```text
NPU specification
      |
      v
Architect Agent
      |
      +-----------------------+
      |                       |
      v                       v
RTL Generator            Verifier
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
        Debugger        Synthesis
            |              |
            +--> RTL       v
                       PPA Judge
                           |
                 +---------+---------+
                 |                   |
             optimize             accept
                 |                   |
                 +--> RTL            v
                                Final RTL
```

## Directory Responsibilities

- `orchestrator/` — LangGraph state, nodes, routing, retry limits, checkpoints, and termination.
- `agents/` — role wrappers that load the project contract and role-specific skills.
- `tools/` — deterministic lint, simulation, synthesis, Git, and report-parsing tool nodes.
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
workspace/synthesis/      deterministic synthesis tools
workspace/optimization/   PPA Judge
workspace/logs/           orchestrator + tool logs
workspace/final/          accepted deliverables only
```

LLM agents propose. Deterministic engineering tools decide correctness, synthesizability, timing, and resource usage.
