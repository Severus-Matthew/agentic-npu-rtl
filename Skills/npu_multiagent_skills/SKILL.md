---
name: npu-multiagent-skills
description: Role-specialized skill pack for the Agentic NPU RTL project. Routes autonomous NPU hardware-engineering work across project-contract, architect, RTL-generation, independent-verification, debugging, PPA-judging, and experiment-evaluation skills while preserving strict artifact ownership and deterministic tool authority.
---

# NPU Multi-Agent Skills

## Purpose

This is the umbrella skill for the role-specialized multi-agent workflow used by the `agentic-npu-rtl` project.

Use this skill when a task involves designing, generating, verifying, repairing, synthesizing, optimizing, or experimentally evaluating an NPU/accelerator RTL design through the project's multi-agent workflow.

This skill does not replace the role-specific skills. It routes work to them and enforces their composition.

## Skill Composition

The pack contains seven skills:

1. `skills/project_contract/SKILL.md`
   - Global invariants, authority hierarchy, file ownership, handoff protocol, retry policy, and acceptance rules.
   - This skill MUST be applied to every agent invocation.

2. `skills/architect/SKILL.md`
   - Converts the NPU specification into a frozen architecture contract, module decomposition, interface contract, dataflow, and acceptance criteria.

3. `skills/rtl_generator/SKILL.md`
   - Implements or minimally patches synthesizable SystemVerilog according to the frozen architecture contract.

4. `skills/verifier/SKILL.md`
   - Independently creates the golden model, directed tests, randomized tests, protocol tests, and verification evidence.

5. `skills/debugger/SKILL.md`
   - Diagnoses compiler, simulation, protocol, arithmetic, pipeline, reset, and synthesis failures and emits constrained repair plans.

6. `skills/ppa_judge/SKILL.md`
   - Evaluates deterministic synthesis/timing/resource results, checks whether correctness is preserved, and proposes evidence-backed PPA optimizations.

7. `skills/experiment_evaluator/SKILL.md`
   - Runs and evaluates controlled one-shot, single-agent, and multi-agent experiments using common tasks, tools, budgets, and hardware metrics.

## Mandatory Loading Rule

Every role-specific invocation MUST conceptually combine:

`project_contract` + `<role-specific skill>`

Examples:

- Architect node: `project_contract` + `architect`
- RTL node: `project_contract` + `rtl_generator`
- Verification node: `project_contract` + `verifier`
- Debug node: `project_contract` + `debugger`
- PPA node: `project_contract` + `ppa_judge`
- Experimental evaluation node: `project_contract` + `experiment_evaluator`

The `project_contract` takes precedence if a role-specific instruction conflicts with a global invariant.

## Routing Rules

Route tasks by responsibility, not by which agent happens to have relevant context.

### Architecture requests

Use `architect` when the task changes or defines:

- compute architecture
- dataflow
- module decomposition
- memory/buffer organization
- numeric widths or arithmetic semantics
- pipeline structure at the architectural level
- interface semantics
- architectural parameters
- acceptance criteria

The Architect does not write production RTL.

### RTL implementation requests

Use `rtl_generator` when the task involves:

- creating synthesizable SystemVerilog
- implementing frozen module contracts
- applying a debugger-approved repair plan
- applying a PPA-approved RTL optimization
- maintaining cycle/valid alignment and numeric correctness

The RTL Generator must not silently change architecture, tests, or the golden model.

### Verification requests

Use `verifier` when the task involves:

- golden/reference model creation
- directed tests
- randomized tests
- boundary tests
- reset behavior
- backpressure and ready/valid behavior
- regression planning
- expected-value calculation
- verification failure reporting

Expected behavior must be derived from the specification and architecture contract, not copied from generated RTL.

### Debug requests

Use `debugger` when deterministic evidence reports failure, including:

- lint/compile failure
- elaboration failure
- simulation mismatch
- timeout
- protocol violation
- signedness/width problem
- pipeline or valid misalignment
- reset/FSM defect
- unsynthesizable RTL

The Debugger diagnoses and constrains a repair; the RTL Generator performs the patch.

### PPA requests

Use `ppa_judge` only after functional verification has passed and deterministic synthesis/timing reports exist.

The PPA Judge may recommend changes for:

- LUT/FF/DSP/BRAM usage
- timing/Fmax
- critical paths
- pipelining
- memory inference
- width reduction
- datapath restructuring within allowed architectural bounds

Every RTL-changing PPA optimization invalidates prior functional-verification status and MUST route back through compilation and regression.

### Research evaluation requests

Use `experiment_evaluator` for comparisons among:

- one-shot generation
- single autonomous coding agent
- multi-agent workflow

Keep model, task, simulator, test suite, synthesis target, and evaluation rules controlled whenever possible. Record token usage, calls, wall-clock/tool time, repair iterations, human interventions, correctness, synthesis closure, and PPA metrics.

## Deterministic Authority

LLM agents propose, diagnose, generate, and optimize.

Deterministic engineering tools decide objective outcomes.

Authority order:

1. NPU specification and frozen architecture contract define intended behavior.
2. Deterministic compile/simulation/regression determines functional pass/fail.
3. Deterministic synthesis/timing reports determine synthesizability and PPA.
4. Agent judgments may explain or react to these results but may not override them.

No agent may declare a design correct solely by reading RTL.

## Core Workflow

Use the following default graph:

NPU Specification
-> Architect
-> parallel RTL Generator + Verifier
-> deterministic compile/simulation/regression

On FAIL:
-> Debugger
-> constrained repair plan
-> RTL Generator
-> deterministic verification again

On PASS:
-> deterministic synthesis
-> PPA Judge

If optimization is requested:
-> RTL Generator
-> deterministic verification again
-> synthesis again
-> PPA Judge again

When acceptance criteria are satisfied or iteration limits are reached:
-> Experiment Evaluator / final run summary
-> final artifacts

## Separation of Responsibilities

Do not collapse the workflow into a group chat where every agent may edit everything.

Preserve artifact ownership and structured handoffs.

The system should communicate primarily through repository artifacts, schemas, reports, and concise structured handoffs rather than unbounded shared conversational history.

## Initial Phase Scope

For the September baseline, prioritize reliable autonomous RTL closure for a simple dense NPU/accelerator before adding sparse attention or complex platform integration.

The initial reference workload is a parameterized integer GEMM-oriented NPU, typically using INT8 activations/weights with wider accumulation and optional bias/ReLU.

Avoid introducing PCIe, HBM/DDR control, transformer softmax, dynamic sparsity, full host/runtime stacks, or other complexity unless the project specification explicitly requires it.

## Success Definition

An autonomous run is successful only when the workflow produces, without manual RTL editing:

- frozen architecture artifacts
- synthesizable RTL
- independent golden model
- regression tests
- deterministic verification report
- successful synthesis report
- timing/resource reports
- complete run metadata and provenance

with required functional tests passing and synthesis succeeding.

## Research Principle

The defining principle of this skill pack is:

**LLMs propose; deterministic engineering tools decide.**

Use specialization to improve reliability and traceability, not merely to increase agent count.
