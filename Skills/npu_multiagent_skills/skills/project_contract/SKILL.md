# Skill: Project Contract — Autonomous Multi-Agent NPU RTL Engineering

## Purpose
This skill defines the global contract for every agent and deterministic tool node in the project. It is the highest-authority project document after the user-provided NPU specification. Every specialized skill MUST obey this contract.

## Primary Objective
Transform a structured NPU specification into functionally verified, synthesizable RTL, then optionally improve PPA while preserving correctness. The system is also an experimental platform for comparing one-shot, single-agent, and multi-agent RTL engineering.

## Core Principle
**LLMs propose; deterministic engineering tools decide.**

Compilation, simulation, regression, synthesis, timing, and resource reports are authoritative. An agent may explain or diagnose a tool result, but may never override it.

## Global Workflow
1. Read and freeze the NPU specification.
2. Architect Agent creates an architecture contract and acceptance criteria.
3. RTL Generator and Verifier independently create implementation and verification artifacts.
4. Deterministic compile/simulation executes.
5. On failure, Debugger diagnoses and issues a constrained repair plan.
6. RTL Generator applies the repair; verification reruns.
7. On functional pass, synthesis runs.
8. PPA Judge evaluates timing/resources and may request constrained optimization.
9. Every optimization invalidates previous functional-pass status and forces regression.
10. Final acceptance requires deterministic PASS for compilation, regression, and synthesis.

## Authority Order
When artifacts conflict, use this precedence:
1. User-provided task / NPU specification
2. This project contract
3. Frozen architecture contract
4. Interface contract and acceptance criteria
5. Deterministic tool output
6. Specialized-agent recommendation
7. Implementation convenience

## Non-Negotiable Invariants

### Specification Supremacy
Agents MUST NOT weaken, silently reinterpret, or delete requirements to make the design pass. Contradictions must be escalated as `SPEC_CONFLICT`.

### Architecture Freeze
After architecture approval, only the Architect Agent may authorize changes to architectural semantics. RTL, Debugger, Verifier, and PPA Judge may recommend an architectural change, but must not enact one themselves.

### Independent Verification
The Verifier derives expected behavior from the specification and architecture contract, not from the generated RTL. Test expectations must never be altered solely to make RTL pass.

### Functional Correctness Before PPA
No PPA optimization may begin until the required functional suite passes. Every RTL-changing optimization triggers at least the required regression scope, and major datapath/control changes trigger the full regression suite.

### Minimal Repair
Repair work must target the diagnosed root cause and avoid unrelated rewrites unless the evidence proves a broader architectural defect.

### Deterministic Evidence
Every pass/fail transition must cite machine-generated evidence: compiler return code, test summary, synthesis status, timing metric, utilization metric, or equivalent.

### Reproducibility
Every run must record:
- run_id
- model name/configuration per agent
- prompt/skill version
- artifact hashes or Git commit IDs
- deterministic tool versions
- random seeds
- agent-call counts
- token usage when available
- repair iterations
- PPA iterations
- human interventions

## Artifact Ownership

### Architect may write
- `architecture/*`

### RTL Generator may write
- `rtl/*`

### Verifier may write
- `reference/*`
- `tests/*`
- `verification/*`

### Debugger may write
- `diagnostics/*`

### PPA Judge may write
- `optimization/*`
- judge reports under `reports/*`

### Experiment Evaluator may write
- `experiments/*`
- aggregate benchmark reports

### No specialized agent may directly modify
- another agent's owned artifacts
- original `specs/*`
- raw deterministic tool logs

## Recommended Repository Layout
```text
project/
├── specs/
│   ├── npu_spec.yaml
│   └── optimization_targets.yaml
├── architecture/
│   ├── architecture_contract.yaml
│   ├── interface_contract.yaml
│   ├── module_manifest.json
│   ├── acceptance_criteria.yaml
│   └── dataflow.md
├── rtl/
├── reference/
├── tests/
├── verification/
├── diagnostics/
├── synthesis/
├── optimization/
├── reports/
├── experiments/
├── logs/
├── state/
└── final/
```

## Standard Handoff Envelope
Every agent-to-agent handoff should be short, structured, and artifact-centric.

```json
{
  "run_id": "",
  "sender": "",
  "receiver": "",
  "stage": "",
  "action": "",
  "input_artifacts": [],
  "output_artifacts": [],
  "affected_modules": [],
  "protected_artifacts": [],
  "evidence": [],
  "constraints": [],
  "regression_required": "NONE|TARGETED|FULL",
  "status": ""
}
```

## Standard Status Vocabulary
Use only clear machine-readable statuses such as:
- `READY`
- `PASS`
- `FAIL`
- `SPEC_CONFLICT`
- `ARCHITECTURE_CONFLICT`
- `RTL_GENERATED`
- `VERIFICATION_READY`
- `COMPILE_FAILURE`
- `SIMULATION_FAILURE`
- `SYNTHESIS_FAILURE`
- `TIMING_FAILURE`
- `RESOURCE_FAILURE`
- `REPAIR_REQUIRED`
- `OPTIMIZATION_REQUIRED`
- `NO_CHANGE_RECOMMENDED`
- `FAILED_AUTONOMOUS_REPAIR`
- `SUCCESS`

## Failure Taxonomy
Classify failures as one of:
- `SPEC_ERROR`
- `ARCHITECTURE_ERROR`
- `SV_SYNTAX_ERROR`
- `ELABORATION_ERROR`
- `WIDTH_ERROR`
- `SIGNEDNESS_ERROR`
- `ARITHMETIC_ERROR`
- `OVERFLOW_ERROR`
- `PIPELINE_ALIGNMENT_ERROR`
- `VALID_READY_PROTOCOL_ERROR`
- `FSM_ERROR`
- `RESET_ERROR`
- `BUFFER_INDEX_ERROR`
- `MEMORY_ERROR`
- `REFERENCE_MODEL_ERROR`
- `TESTBENCH_ERROR`
- `SIMULATION_TIMEOUT`
- `UNSYNTHESIZABLE_RTL`
- `SYNTHESIS_ERROR`
- `TIMING_FAILURE`
- `RESOURCE_FAILURE`
- `UNKNOWN`

## Initial Phase Scope
For the first two-week milestone, prefer a dense GEMM-style NPU such as:
- INT8 activations
- INT8 weights
- INT32 accumulation
- parameterized MAC array
- optional bias
- ReLU
- simple ready/valid interface

Do not introduce unless explicitly required:
- sparse attention
- softmax
- PCIe
- HBM/DDR controller design
- full host runtime
- floating-point arithmetic
- complex dynamic scheduling

## Suggested Iteration Budgets
- Architecture revisions: 2
- Functional repair rounds: 5
- PPA optimization rounds: 3

The orchestrator may use stricter limits for controlled experiments.

## Final Acceptance
A run is successful only if all required acceptance criteria are satisfied and the final output includes:
- verified synthesizable RTL
- frozen architecture artifacts
- independent golden model
- regression tests
- functional verification report
- synthesis report
- timing report
- utilization report
- run provenance summary

No agent may call the project complete before these conditions are machine-verified.
