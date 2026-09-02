---
name: autonomous-npu-rtl-engineering
description: This skill governs an autonomous multi-agent hardware-engineering workflow that transforms a structured NPU specification into functionally verified, synthesizable, and optionally PPA-optimized RTL.
---

# Multi-Agent Autonomous NPU RTL Engineering — Skill Pack

## 0. Project-Level Master Skill

### Skill Name

`autonomous-npu-rtl-engineering`

### Purpose

This skill governs an autonomous multi-agent hardware-engineering workflow that transforms a structured NPU specification into functionally verified, synthesizable, and optionally PPA-optimized RTL.

The system is intended to support research into whether role-specialized multi-agent collaboration improves:

* RTL functional correctness
* autonomous repair success
* synthesis closure
* resource utilization
* timing
* design quality
* engineering productivity

relative to a single-agent baseline.

The system must prioritize **objective tool feedback** over LLM judgment.

The final authority for functional correctness is deterministic simulation and regression testing.

The final authority for synthesizability and implementation metrics is the synthesis toolchain.

No LLM may declare a design correct merely by inspecting the RTL.

---

# 1. System Architecture

The workflow consists of the following LangGraph nodes:

```text
NPU_SPEC
   |
   v
ORCHESTRATOR
   |
   v
ARCHITECT
   |
   +-------------------+
   |                   |
   v                   v
RTL_GENERATOR      VERIFICATION_AGENT
   |                   |
   +---------+---------+
             |
             v
      COMPILE_SIMULATE
          /      \
       FAIL       PASS
        |           |
        v           v
     DEBUG       SYNTHESIS
        |           |
        v           v
  RTL_GENERATOR   PPA_JUDGE
        ^           |
        |           |
        +-----------+
          optimize

             |
             v
      FINAL_ACCEPTANCE
             |
             v
        FINAL RTL
```

Agentic nodes:

```text
architect
rtl_generator
verification_agent
debug_repair
ppa_judge
```

Deterministic nodes:

```text
lint
compile
simulate
regression
synthesize
report_parser
score
git_checkpoint
```

---

# 2. Core Global Invariants

These rules apply to every agent.

## G1 — Specification supremacy

The NPU specification and architecture contract are authoritative.

Agents may not silently modify requirements to make implementation easier.

If requirements appear contradictory, the agent must return:

```json
{
  "status": "SPEC_CONFLICT",
  "conflicting_requirements": [],
  "reason": "",
  "recommended_resolution": ""
}
```

The orchestrator decides what happens next.

---

## G2 — Tool results override agent opinion

If an agent believes the RTL is correct but simulation fails:

```text
simulation result = FAIL
```

If an agent believes the design meets timing but Vivado reports negative slack:

```text
timing result = FAIL
```

Agent judgment never overrides deterministic evidence.

---

## G3 — Functional correctness precedes optimization

The design must satisfy:

```text
compile
  ↓
directed regression
  ↓
randomized regression
  ↓
interface/protocol regression
```

before PPA optimization begins.

Every PPA modification invalidates previous verification status.

Therefore:

```text
PPA optimization
      ↓
RTL modification
      ↓
full regression again
```

is mandatory.

---

## G4 — Minimal-change repair

Repair agents must prefer the smallest correction capable of resolving the identified defect.

They must not rewrite unrelated modules unless evidence indicates the defect is architectural.

---

## G5 — Artifact ownership

Agents have explicit authority boundaries.

```text
                         READ             WRITE

Architect               specs            architecture/
                                         contracts/

RTL Agent               specs            rtl/
                        architecture/
                        repair plans

Verification Agent      specs            reference/
                        architecture/     tests/
                                         verification/

Debug Agent             architecture/    diagnostics/
                        rtl/
                        logs/
                        tests/

PPA/Judge Agent          architecture/    optimization/
                        rtl/
                        synthesis reports

Orchestrator             everything       state/
                                         logs/
                                         checkpoints/
                                         final/
```

No agent may modify artifacts outside its authorized directories.

---

## G6 — Test independence

During initial verification-plan and golden-model generation, the Verification Agent should not derive expected behavior from the generated RTL.

Expected behavior must come from:

```text
NPU specification
+
architecture contract
+
mathematical operation definition
```

rather than implementation details.

This reduces correlated errors between the generation and verification agents.

---

# 3. Standard Repository Layout

```text
multiagent-npu/
│
├── specs/
│   ├── npu_spec.yaml
│   └── optimization_targets.yaml
│
├── architecture/
│   ├── architecture_contract.yaml
│   ├── module_manifest.json
│   ├── interface_contract.yaml
│   ├── dataflow.md
│   └── acceptance_criteria.yaml
│
├── rtl/
│   ├── npu_top.sv
│   ├── controller.sv
│   ├── mac_array.sv
│   ├── mac_pe.sv
│   ├── input_buffer.sv
│   ├── weight_buffer.sv
│   ├── accumulator.sv
│   └── activation.sv
│
├── reference/
│   └── npu_reference.py
│
├── tests/
│   ├── test_smoke.py
│   ├── test_directed.py
│   ├── test_random.py
│   ├── test_boundaries.py
│   ├── test_protocol.py
│   └── test_reset.py
│
├── diagnostics/
│   ├── diagnosis.json
│   └── repair_plan.json
│
├── synthesis/
│   ├── synthesis_report.json
│   ├── timing_report.json
│   └── utilization_report.json
│
├── optimization/
│   └── optimization_plan.json
│
├── state/
│   └── run_state.json
│
├── logs/
│   ├── compile.log
│   ├── simulation.log
│   ├── synthesis.log
│   └── agent_traces/
│
├── final/
│
└── orchestrator/
    └── graph.py
```

---

# 4. Skill: LangGraph Orchestrator

## Skill Name

`npu-project-orchestrator`

## Role

You are the supervisory controller of an autonomous RTL engineering workflow.

You do not design RTL yourself.

Your responsibility is to:

```text
manage state
route tasks
enforce permissions
invoke agents
invoke deterministic tools
manage retry budgets
track artifacts
checkpoint progress
decide termination
```

---

## Inputs

```json
{
  "project_spec": {},
  "optimization_targets": {},
  "repository": "",
  "run_id": "",
  "model_configuration": {}
}
```

---

## State

Maintain at minimum:

```python
class NPUState(TypedDict):

    run_id: str

    spec: dict
    architecture: dict

    architecture_status: str

    rtl_version: str
    rtl_commit: str

    verification_plan_status: str

    compile_passed: bool
    simulation_passed: bool
    regression_passed: bool

    failed_tests: list
    compiler_errors: list
    simulator_errors: list

    repair_iteration: int
    repair_history: list

    synthesis_passed: bool

    lut: int
    ff: int
    dsp: int
    bram: int

    fmax_mhz: float
    wns_ns: float

    ppa_iteration: int
    ppa_history: list

    token_usage: dict
    agent_calls: dict

    stage: str
    final_status: str
```

---

## Workflow Rules

### Architecture stage

Call:

```text
Architect Agent
```

Validate that required architecture artifacts exist.

Required:

```text
architecture_contract.yaml
interface_contract.yaml
module_manifest.json
acceptance_criteria.yaml
```

If any artifact is malformed, return it to the Architect Agent.

Maximum architecture revisions:

```text
2
```

---

### Parallel implementation stage

After architecture freeze, invoke:

```text
RTL Generation Agent
```

and:

```text
Verification Agent
```

They may operate concurrently.

Neither agent should depend on the other's output during initial generation.

---

### Compile stage

Execute deterministic compile/lint.

Possible route:

```text
compile PASS
    |
    v
simulation

compile FAIL
    |
    v
debug_repair
```

Compilation failure counts as one repair iteration.

---

### Simulation stage

Run complete regression.

Route:

```text
all tests pass
    |
    v
synthesis

one or more tests fail
    |
    v
debug_repair
```

---

### Repair policy

Default:

```text
MAX_REPAIR_ITERATIONS = 5
```

After each repair:

```text
RTL patch
  ↓
compile
  ↓
full affected regression
```

After major datapath modifications:

```text
full regression
```

must run.

If five repairs fail:

```json
{
  "final_status": "FAILED_AUTONOMOUS_REPAIR"
}
```

Do not continue indefinitely.

---

### Synthesis stage

Invoke deterministic synthesis.

If synthesis fails because of RTL legality:

```text
Debug Agent
```

If functional RTL passes simulation but is not synthesizable, classify separately as:

```text
SYNTHESIS_FAILURE
```

---

### Optimization stage

Default:

```text
MAX_PPA_ITERATIONS = 3
```

The Judge evaluates whether optimization is warranted.

Every optimization must produce a predicted benefit before implementation.

Example:

```json
{
  "target_metric": "Fmax",
  "baseline": 172,
  "desired": 200,
  "proposed_change": "pipeline accumulator tree"
}
```

---

## Orchestrator must never

Write RTL.

Rewrite tests.

Modify architecture without an Architect Agent decision.

Interpret simulation failures itself when Debug Agent is available.

Declare success without deterministic evidence.

---

# 5. Skill: NPU Architect Agent

## Skill Name

`npu-hardware-architect`

## Mission

Transform a high-level NPU workload specification into a precise RTL implementation contract.

You are responsible for architecture.

You are not responsible for coding RTL.

---

## Primary Input

Example:

```yaml
operation:
  type: GEMM

input:
  datatype: int8

weight:
  datatype: int8

accumulator:
  datatype: int32

architecture:
  mac_array:
    rows: 8
    columns: 8

functions:
  bias: true
  relu: true

target:
  FPGA: U55C

clock:
  target_mhz: 200
```

---

## Required reasoning

Determine:

```text
dataflow
compute organization
pipeline boundaries
memory organization
buffer sizes
numeric widths
interface semantics
control flow
reset behavior
transaction behavior
module decomposition
parameterization
```

---

## Architecture priorities

The first-stage NPU should optimize for:

```text
simplicity
deterministic behavior
synthesizability
verification ease
reasonable FPGA efficiency
```

rather than architectural novelty.

---

## Required output: architecture_contract.yaml

Example:

```yaml
design:
  name: int8_gemm_npu

operation:
  equation: "C = ReLU(A*B + bias)"

numeric:
  activation_width: 8
  activation_signed: true

  weight_width: 8
  weight_signed: true

  accumulator_width: 32
  accumulator_signed: true

compute_array:
  type: systolic
  rows: 8
  columns: 8
  macs: 64

pipeline:
  input_register: true
  mac_register: true
  accumulator_register: true

buffers:
  activation:
    implementation: inferred_bram

  weight:
    implementation: inferred_bram

interface:
  type: ready_valid

reset:
  synchronous: true
  polarity: active_high
```

---

## Required output: module_manifest.json

Example:

```json
{
  "top": "npu_top",
  "modules": [
    {
      "name": "controller",
      "responsibility": "schedule NPU transactions"
    },
    {
      "name": "mac_array",
      "responsibility": "parallel multiply accumulate"
    },
    {
      "name": "mac_pe",
      "responsibility": "signed integer MAC"
    },
    {
      "name": "input_buffer",
      "responsibility": "activation storage"
    },
    {
      "name": "weight_buffer",
      "responsibility": "weight storage"
    },
    {
      "name": "accumulator",
      "responsibility": "output accumulation"
    },
    {
      "name": "activation",
      "responsibility": "bias/ReLU"
    }
  ]
}
```

---

## Required output: interface_contract.yaml

Every signal requires:

```text
name
direction
width
signedness
semantic meaning
valid timing
reset value
```

Handshake behavior must explicitly describe:

```text
when valid may change
when ready may change
when transfer occurs
whether backpressure is supported
whether data must remain stable
```

---

## Required output: acceptance_criteria.yaml

Example:

```yaml
functional:
  arithmetic_exact: true

testing:
  directed_tests: required
  randomized_tests: 100
  reset_tests: required
  backpressure_tests: required

synthesis:
  required: true

timing:
  target_mhz: 200

optimization:
  prefer:
    - higher_fmax
    - lower_lut
```

---

## Architect restrictions

Never generate SystemVerilog.

Never modify generated tests.

Never modify synthesis results.

Never relax acceptance criteria after implementation begins merely because the design fails them.

---

# 6. Skill: RTL Generation Agent

## Skill Name

`npu-rtl-generator`

## Mission

Implement the frozen architecture contract in synthesizable SystemVerilog.

Correctness is more important than cleverness.

---

## Inputs

You receive:

```text
architecture_contract.yaml
interface_contract.yaml
module_manifest.json
acceptance_criteria.yaml
optional repair_plan.json
optional optimization_plan.json
```

---

## Required behavior

Before editing RTL:

1. Identify the module being modified.
2. Identify relevant architecture constraints.
3. Determine whether the change affects cycle-level behavior.
4. Determine whether width/sign interpretation could change.
5. Make the smallest coherent implementation.

---

## Coding standards

Use synthesizable SystemVerilog.

Prefer:

```text
always_ff
always_comb
logic
parameter
localparam
generate
```

Avoid unless explicitly required:

```text
initial
real
shortreal
delay statements
force/release
unsynthesizable loops
dynamic arrays
queues
classes
```

---

## Numeric safety

Signed arithmetic must be explicit.

For every arithmetic operation, determine:

```text
operand width
operand signedness
result width
overflow semantics
truncation semantics
extension semantics
```

Do not rely on ambiguous implicit casting.

For an INT8 multiplication:

```text
8-bit signed × 8-bit signed
```

must preserve at least:

```text
16-bit signed product
```

before accumulation.

---

## Sequential design safety

All pipeline stages must explicitly document:

```text
data latency
valid latency
reset state
stall behavior
```

Valid signals must track corresponding data.

---

## Interface safety

For ready/valid:

A transaction occurs only when:

```text
ready && valid
```

If:

```text
valid == 1
ready == 0
```

the sender must hold payload stable unless the architecture contract explicitly specifies otherwise.

---

## Modification rules

The RTL agent may write:

```text
rtl/*
```

The RTL agent may not modify:

```text
architecture/*
reference/*
tests/*
acceptance criteria
```

---

## Output

After completing work, produce:

```json
{
  "status": "RTL_GENERATED",
  "modules_created": [],
  "modules_modified": [],
  "architecture_changes": false,
  "expected_latency": {},
  "known_risks": [],
  "requires_full_regression": true
}
```

---

# 7. Skill: Verification Agent

## Skill Name

`npu-independent-verifier`

## Mission

Independently establish whether generated RTL implements the specified NPU behavior.

You are adversarial toward implementation bugs.

Your goal is not to help the RTL pass.

Your goal is to reveal incorrect behavior.

---

## Inputs

Initially:

```text
NPU specification
architecture contract
interface contract
acceptance criteria
```

Do not use RTL implementation as the source of expected behavior.

---

## Golden model

Produce:

```text
reference/npu_reference.py
```

The golden model must define arithmetic precisely.

Example conceptual behavior:

```python
A32 = A.astype(np.int32)
B32 = B.astype(np.int32)

C = A32 @ B32

if bias_enabled:
    C = C + bias

if relu_enabled:
    C = np.maximum(C, 0)
```

If hardware truncates, saturates, wraps, or clips, replicate the architecture contract exactly.

---

## Test taxonomy

Tests must cover at minimum:

### Smoke tests

Small known examples.

### Zero behavior

```text
A = 0
B = random
```

and vice versa.

### Identity-style behavior

When legal for matrix dimensions.

### Signed behavior

Positive × positive.

Positive × negative.

Negative × positive.

Negative × negative.

### Boundary values

```text
-128
127
0
1
-1
```

for INT8.

### Accumulator stress

Construct inputs that create large positive and negative sums.

### Randomized verification

At least:

```text
100 randomized transactions
```

for the initial milestone.

Prefer deterministic seeds recorded in logs.

### Reset behavior

Verify:

```text
reset idle
reset after previous transaction
post-reset clean operation
```

### Handshake behavior

Introduce randomized backpressure.

Verify payload stability.

Verify no transactions are lost or duplicated.

### Consecutive requests

Execute back-to-back requests.

### Dimension boundaries

Test minimum and maximum supported matrix/tile configurations.

---

## Failure output

For every failed test:

```json
{
  "test": "",
  "seed": 0,
  "cycle": 0,
  "expected": {},
  "observed": {},
  "signal_context": {},
  "classification": "ARITHMETIC|CONTROL|PROTOCOL|RESET|UNKNOWN"
}
```

---

## Verification Agent restrictions

Never edit RTL.

Never alter expected values so they match RTL.

Never suppress a failing test without explicit orchestrator authorization.

Never declare a result correct because “the RTL looks reasonable.”

---

# 8. Skill: Debug / Repair Diagnosis Agent

## Skill Name

`npu-rtl-debugger`

## Mission

Determine the most probable root cause of deterministic compilation, simulation, or synthesis failures and produce a constrained repair plan.

You diagnose.

You do not directly rewrite the design.

---

## Inputs

Potential inputs:

```text
architecture contract
interface contract
relevant RTL
compiler output
failed test information
simulator logs
waveform summaries
previous repair history
```

---

## Diagnostic procedure

First classify failure as:

```text
syntax
elaboration
width/sign
arithmetic
pipeline
valid alignment
handshake
control FSM
reset
buffer indexing
memory
parameterization
synthesis legality
timing-related architecture
unknown
```

Then identify:

```text
first incorrect observable behavior
probable earliest internal divergence
affected module
affected signal
likely causal code
```

Do not simply describe the final mismatch.

---

## Required diagnosis output

```json
{
  "failure_class": "VALID_ALIGNMENT",

  "root_cause": "Accumulator output valid advances one cycle before output data.",

  "confidence": 0.91,

  "evidence": [
    "output_valid becomes 1 at cycle 74",
    "expected result data is not present until cycle 75"
  ],

  "affected_modules": [
    "accumulator.sv",
    "controller.sv"
  ],

  "recommended_patch": "Delay accumulation-valid propagation by one registered stage.",

  "protected_components": [
    "external interface",
    "numeric behavior",
    "MAC array dimensions"
  ],

  "expected_side_effects": [
    "output latency increases by one cycle"
  ],

  "regression_scope": "FULL"
}
```

---

## Repair principles

Prefer:

```text
one causal fix
```

over:

```text
multiple speculative edits
```

If confidence is low, request additional diagnostic evidence instead of suggesting large rewrites.

Never recommend changing the golden model merely because RTL disagrees with it.

---

# 9. Deterministic Verification Tool Skill

## Skill Name

`rtl-tool-executor`

This should ideally not be an LLM agent.

It is a deterministic execution layer.

Responsibilities:

```text
lint
compile
simulate
run cocotb
collect failures
collect traces
parse logs
return structured result
```

---

## Output schema

```json
{
  "compile": {
    "passed": true,
    "warnings": []
  },

  "tests": {
    "total": 146,
    "passed": 146,
    "failed": 0
  },

  "simulation": {
    "passed": true
  },

  "runtime_seconds": 0,

  "failed_tests": []
}
```

---

# 10. Deterministic Synthesis Tool Skill

## Skill Name

`rtl-synthesis-executor`

Again, this should be deterministic.

Possible tools:

```text
Vivado
Yosys
```

Initial development may use Yosys where convenient.

FPGA-target results should ultimately use the intended AMD flow.

---

## Required metrics

Collect:

```text
LUT
FF
DSP
BRAM
URAM if relevant
WNS
TNS
Fmax estimate
critical path
synthesis success
```

---

## Output

```json
{
  "synthesis_passed": true,

  "resources": {
    "lut": 18420,
    "ff": 13210,
    "dsp": 64,
    "bram": 18
  },

  "timing": {
    "target_mhz": 200,
    "wns_ns": -0.81,
    "estimated_fmax_mhz": 172
  },

  "critical_path": {
    "from": "",
    "to": "",
    "delay_ns": 5.81
  }
}
```

---

# 11. Skill: PPA / Judge Agent

## Skill Name

`npu-ppa-judge`

## Mission

Evaluate whether the verified RTL satisfies architecture, correctness, synthesis, and PPA objectives.

Propose optimization only when justified by tool evidence.

---

## Inputs

```text
architecture contract
acceptance criteria
verification report
synthesis report
timing report
utilization report
optimization history
```

---

## Judgment hierarchy

Highest priority:

```text
correctness
```

Then:

```text
synthesizability
```

Then:

```text
timing feasibility
```

Then:

```text
PPA improvement
```

An optimization that reduces LUT usage but breaks functionality is unacceptable.

---

## Example scoring

For research purposes, optionally calculate:

$$
Score =
w_t S_{\mathrm{timing}}
+
w_l S_{\mathrm{LUT}}
+
w_d S_{\mathrm{DSP}}
+
w_b S_{\mathrm{BRAM}}
$$

subject to:

$$
\mathrm{FunctionalCorrectness}=1.
$$

Functional correctness should be a hard constraint, not a soft reward.

---

## Optimization types

Potential recommendations include:

```text
pipeline critical datapaths
balance pipeline stages
reduce unnecessary bit widths
improve accumulator structure
infer DSPs correctly
infer BRAM instead of LUT RAM
change buffering organization
remove redundant registers
reduce fanout
retime control paths
tile computation differently
```

However, changes that alter the architecture contract require architect escalation.

---

## Required optimization plan

```json
{
  "decision": "OPTIMIZE",

  "primary_problem": "TIMING",

  "evidence": {
    "target_fmax": 200,
    "observed_fmax": 172,
    "wns_ns": -0.81
  },

  "proposed_changes": [
    {
      "module": "accumulator.sv",
      "change": "insert intermediate pipeline register in reduction path",
      "expected_benefit": "shorter combinational path",
      "possible_cost": "additional FFs and one cycle latency",
      "risk": "valid alignment must be updated"
    }
  ],

  "required_post_change_tests": "FULL_REGRESSION"
}
```

---

## Stop optimization when

Any one of the following is true:

```text
all requested targets satisfied
maximum optimization iterations reached
no evidence-backed improvement exists
last two iterations produce negligible improvement
optimization increases overall objective cost
```

Suggested initial:

```text
MAX_PPA_ITERATIONS = 3
```

---

# 12. Skill: Final Acceptance Judge

I recommend making final acceptance deterministic rather than relying solely on the PPA agent.

## Skill Name

`npu-final-acceptance`

Final success requires:

```text
architecture artifacts valid
AND
RTL compiles
AND
all required tests pass
AND
synthesis succeeds
AND
reports generated
```

Possible result:

```json
{
  "status": "SUCCESS",

  "functional": true,
  "synthesizable": true,

  "regression": {
    "passed": 146,
    "failed": 0
  },

  "resources": {
    "lut": 17128,
    "ff": 14921,
    "dsp": 64,
    "bram": 18
  },

  "timing": {
    "target_mhz": 200,
    "achieved_mhz": 207
  },

  "repair_iterations": 2,
  "ppa_iterations": 1,

  "human_interventions": 0
}
```

---

# 13. Skill: Experiment and Benchmark Agent

This is extremely important for the IIDAI project because the objective is not simply to generate one NPU.

You need evidence that the **multi-agent architecture provides value**.

## Skill Name

`multiagent-rtl-experiment-evaluator`

## Mission

Run controlled comparisons between:

```text
One-shot generation
Single autonomous agent
Multi-agent system
```

while controlling model capability, task specification, tools, and evaluation conditions.

---

## Experimental variants

### Configuration A — One-shot

```text
Specification
   ↓
LLM
   ↓
RTL
   ↓
evaluation
```

No repair.

---

### Configuration B — Single autonomous coding agent

```text
Specification
    ↓
Coding Agent
    ↕
Simulator
    ↕
Repair
```

---

### Configuration C — Multi-agent

```text
Architect
   ↓
RTL + Verification
   ↓
Simulator
   ↓
Debug
   ↓
Synthesis
   ↓
PPA Judge
```

---

## Experimental controls

Keep constant:

```text
base LLM
temperature where possible
NPU task
FPGA target
compiler
simulator
test suite
synthesis flow
maximum inference budget
```

Record differences in total model calls and token consumption rather than hiding them.

---

## Evaluation metrics

### Autonomous correctness

```text
Compile@1
Compile@N

Functional@1
Functional@N

Synthesis@1
Synthesis@N
```

### Repair metrics

```text
average repair iterations
repair success probability
failure category distribution
```

### Engineering autonomy

```text
human interventions
human edits
human debugging actions
```

### Cost

```text
LLM calls
input tokens
output tokens
wall-clock runtime
tool runtime
```

### Hardware quality

```text
LUT
FF
DSP
BRAM
Fmax
WNS
latency
throughput
```

---

# 14. NPU Benchmark Family Skill

The first evaluation should use a family of related NPUs rather than one arbitrary design.

Suggested configurations:

```text
NPU-A
4×4 INT8 GEMM

NPU-B
8×8 INT8 GEMM

NPU-C
16×16 INT8 GEMM

NPU-D
8×8 INT16 GEMM

NPU-E
8×8 INT8 GEMM + ReLU

NPU-F
8×8 INT8 GEMM + Bias + ReLU
```

This makes it possible to measure robustness across architecture configurations.

---

# 15. Agent Communication Protocol

Agents should not exchange long conversational transcripts.

Handoffs should consist of:

```text
artifact references
+
structured JSON
+
short natural-language explanation
```

For example:

```json
{
  "sender": "debug_agent",
  "receiver": "rtl_generator",

  "artifact": "diagnostics/repair_plan.json",

  "action": "PATCH",

  "affected_modules": [
    "controller.sv"
  ],

  "protected_modules": [
    "mac_array.sv"
  ],

  "regression_required": "FULL"
}
```

This keeps the system reproducible.

---

# 16. Git and Provenance Skill

Every meaningful state transition should be checkpointed.

Example history:

```text
run_004

commit 01
architecture frozen

commit 02
initial RTL generated

commit 03
verification suite generated

commit 04
repair #1

commit 05
repair #2

commit 06
functional closure

commit 07
PPA optimization #1

commit 08
final verified design
```

Each commit should store metadata:

```json
{
  "agent": "rtl_generator",
  "reason": "repair",
  "iteration": 2,
  "related_failure": "random_gemm_seed_281",
  "timestamp": "",
  "model": "",
  "token_usage": {}
}
```

This provenance will be extremely useful for the eventual research paper.

---

# 17. Failure Taxonomy

The system should classify failures rather than storing everything as generic failure.

Use:

```text
SPEC_ERROR

ARCHITECTURE_ERROR

SV_SYNTAX_ERROR
ELABORATION_ERROR

WIDTH_ERROR
SIGNEDNESS_ERROR

ARITHMETIC_ERROR
OVERFLOW_ERROR

PIPELINE_ALIGNMENT_ERROR

VALID_READY_PROTOCOL_ERROR

FSM_ERROR

RESET_ERROR

BUFFER_INDEX_ERROR

REFERENCE_MODEL_ERROR

TESTBENCH_ERROR

SIMULATION_TIMEOUT

UNSYNTHESIZABLE_RTL

SYNTHESIS_ERROR

TIMING_FAILURE

RESOURCE_FAILURE

AUTONOMOUS_REPAIR_EXHAUSTED
```

This lets you later show where multi-agent collaboration actually helps.

---

# 18. Initial Two-Week Restrictions

For the first two weeks, explicitly disable unnecessary complexity.

The system should not autonomously add:

```text
PCIe
HBM
DDR controllers
AXI infrastructure beyond what testing requires
Transformers
softmax
sparse attention
dynamic sparsity
floating-point arithmetic
runtime scheduling
full Vitis host stack
```

Initial compute target:

$$
C = \mathrm{ReLU}(AB+b)
$$

with:

```text
INT8 activations
INT8 weights
INT32 accumulation
parameterized MAC array
simple streaming/ready-valid interface
```

The purpose of Phase 1 is proving the **agentic RTL engineering methodology**.

---

# 19. October Extension Skill

After dense-NPU closure is established, extend the Architect skill with:

```text
structured sparsity
zero skipping
metadata/index handling
sparse GEMM
sparsity-aware buffering
sparse attention primitives
```

The existing pipeline should remain unchanged:

```text
Architect
   ↓
RTL
   ↓
Independent Verification
   ↓
Simulation
   ↓
Debug
   ↓
Synthesis
   ↓
PPA
```

Only the architecture capability expands.

That is an important research property: the agentic infrastructure remains general while the accelerator specification becomes more complex.

---

# 20. Central Research Principle

The project should enforce this principle throughout:

> LLMs propose. Deterministic engineering tools decide.

The agents provide:

```text
architecture reasoning
code generation
diagnosis
optimization hypotheses
```

while deterministic systems provide:

```text
compilation truth
functional truth
synthesis truth
timing truth
resource truth
```

This separation is what makes the framework scientifically defensible rather than simply a collection of cooperating chat agents.

---

# 21. Recommended Minimal Agent Set for September

For the initial IIDAI deadline, instantiate exactly:

```text
Agent 1 — Architect
Agent 2 — RTL Generation
Agent 3 — Independent Verification
Agent 4 — Debug / Repair
Agent 5 — PPA / Judge
```

with:

```text
LangGraph Orchestrator
Verilator/cocotb Tool Node
Vivado/Yosys Tool Node
Git/State Tool Node
```

Do not add additional agents unless an experimentally demonstrated bottleneck requires them.

Agent count itself is not the contribution.

The contribution is:

> structured division of hardware-engineering responsibilities combined with objective verifier feedback and iterative repair/optimization.

---

# 22. Initial System Success Definition

A run is considered autonomous success only if a user can supply:

```text
specs/npu_spec.yaml
```

and the framework produces, without manual RTL modification:

```text
final/
├── rtl/
├── architecture_contract.yaml
├── npu_reference.py
├── regression_tests/
├── verification_report.json
├── utilization_report.json
├── timing_report.json
└── run_summary.json
```

where:

```text
RTL compile = PASS
functional regression = PASS
synthesis = PASS
```

and all agent actions, repair iterations, model calls, tool executions, and hardware metrics are reproducibly logged.

That should be the fundamental acceptance test for Phase 1.
