# Multi-Agent NPU Runtime

This directory contains the executable LangGraph-based multi-agent system for autonomous NPU RTL generation, verification, repair, and optimization planning.

All LLM roles use the **same configured API model** so model capability remains controlled across one-shot, single-agent, and multi-agent experiments. If the university endpoint exposes a Codex model, configure that model for every role. Otherwise use the same strongest available GPT coding-capable model for every role. The role instructions live separately under `../Skills/npu_multiagent_skills/skills/`. Every agent loads `project_contract` plus its role-specific skill.

## Ownership boundary

The multi-agent team owns architecture generation, RTL generation, independent verification, debug/repair, and PPA decision logic.

**Synopsys execution is externally owned.** `tools/synopsys_interface.py` is only the integration contract. The runtime must never fabricate synthesis, timing, power, or area values when a real Synopsys report is unavailable.

## Runtime Flow

```text
NPU specification
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

Agents call the configured OpenAI/OpenAI-compatible API directly through the Python SDK. No Codex CLI installation or `codex login` is required. The model returns schema-constrained structured proposals; each Python role wrapper writes only that role's whitelisted artifacts. This gives us enforceable ownership boundaries rather than relying solely on prompt instructions.

The backend supports both:

- `responses` — OpenAI Responses API (`/responses`)
- `chat_completions` — Chat Completions (`/chat/completions`) for compatible university gateways that do not expose Responses

## Local API setup

Install dependencies:

```bash
pip install -r multigent/requirements.txt
```

Copy the example configuration:

```bash
cp .env.example .env
```

Then edit `.env` locally:

```bash
OPENAI_API_KEY=your_real_key
OPENAI_BASE_URL=https://your-university-endpoint.example.edu/v1
NPU_AGENT_MODEL=the-exact-model-or-deployment-name
NPU_AGENT_API_MODE=responses
```

`.env` is gitignored. Never commit or paste the real API key into GitHub, issues, logs, or prompts.

If the university gateway supports only Chat Completions, use:

```bash
NPU_AGENT_API_MODE=chat_completions
```

Check the connection before running an agent:

```bash
python -m multigent.scripts.check_api
```

If the provider supports model listing, this can help identify the exact deployment/model name:

```bash
python -m multigent.scripts.check_api --list-models
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
- `agents/` — API-backed role wrappers that load the project contract and role-specific skills.
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
