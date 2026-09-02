# Autonomous NPU Multi-Agent Skill Pack

This package contains seven role-specific skills for a LangGraph/Codex-style autonomous NPU RTL engineering project.

## Skills
- `skills/project_contract/` — global invariants, ownership, handoff protocol, acceptance rules
- `skills/architect/` — NPU architecture specification and contract generation
- `skills/rtl_generator/` — synthesizable SystemVerilog implementation and constrained patches
- `skills/verifier/` — independent golden model and regression generation
- `skills/debugger/` — root-cause analysis and repair-plan generation
- `skills/ppa_judge/` — synthesis/PPA evaluation and optimization planning
- `skills/experiment_evaluator/` — controlled one-shot vs single-agent vs multi-agent research evaluation

The `project_contract` should be loaded for every agent, followed by that agent's specialized skill.

Recommended next step: add JSON/YAML schemas and LangGraph node wrappers that enforce each skill's read/write permissions and handoff format.
