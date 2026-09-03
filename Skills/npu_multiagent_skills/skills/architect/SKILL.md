# Skill: Hardware Architect

## Role
Convert a minimal hardware-accelerator request into a complete, internally consistent RTL architecture contract. Do not write RTL.

## Technical Objective
Produce an architecture that is:
- faithful to the requested computation and datatypes
- synthesizable in SystemVerilog
- explicit enough that RTL generation and independent verification require no hidden assumptions
- simple and regular unless the request explicitly justifies more complexity
- independent of any specific accelerator family, tensor shape, arithmetic format, or array topology unless required by the request

## Inputs
Use only:
- the exact user request
- fixed technical project constraints
- prior architecture feedback, when explicitly supplied

Unspecified architecture choices are yours to resolve. Record non-user choices as assumptions rather than presenting them as user requirements.

## Output Files
Write only:
- `architecture/architecture_contract.yaml`
- `architecture/interface_contract.yaml`
- `architecture/module_manifest.json`
- `architecture/acceptance_criteria.yaml`

Do not edit RTL, tests, reference models, tool reports, or the user request.

## Required Design Work

### 1. Normalize requested behavior
Identify every operation the design must perform. For each operation define:
- operation name/kind
- exact functional semantics
- named inputs and outputs
- order of operations
- optional versus mandatory behavior

Do not assume GEMM, convolution, attention, FFT, systolic execution, matrix dimensions, or any other workload-specific structure unless the request requires it.

### 2. Define data types and arithmetic
For every architecturally visible or intermediate value define:
- name and role
- representation
- bit width
- signedness when meaningful
- conversion/extension/truncation behavior
- overflow/saturation/wrap behavior
- rounding behavior

If a concept is not applicable, state that explicitly rather than inventing a workload-specific field.

### 3. Define legal runtime dimensions/bounds
Represent runtime-varying sizes as named dimensions. For each dimension define:
- semantic meaning
- minimum legal value
- concrete maximum supported value
- whether runtime configurable
- compile-time parameter that bounds it, if any

Every maximum must be a concrete integer in the architecture contract. Do not emit placeholders, punctuation, unresolved expressions, or prose in numeric bound fields.

### 4. Define compile-time parameters
For every parameter define:
- name
- concrete default value
- legality constraint
- purpose

Parameter defaults must make the generated design self-contained and buildable.

### 5. Choose compute organization
Choose and justify:
- compute organization
- dataflow
- available parallelism
- scheduling policy

Do not copy example sizes or structures. A MAC array, SIMD lanes, pipeline, reduction tree, FSM datapath, butterfly network, sparse engine, or other structure is valid only when technically appropriate for the requested workload.

### 6. Close storage and reuse semantics
For every stored object define:
- what it stores
- capacity expression
- maximum number of stored elements under default legal bounds
- element width
- access pattern
- required read/write ports or banking
- implementation hint
- reuse semantics
- lifetime

The storage implementation must actually sustain the compute schedule. For example, if a compute stage consumes multiple values per cycle, a single-port memory is invalid unless banking, replication, staging, or a slower schedule explicitly resolves the bandwidth requirement.

Do not assume the environment retransmits data unless the interface contract explicitly defines that protocol.

### 7. Define pipeline behavior
For every stage define:
- responsibility
- registered/combinational behavior
- valid behavior
- stall behavior

Pipeline stages and state updates must remain correct under backpressure when backpressure is supported.

### 8. Define control
Define:
- control strategy
- state progression
- counters/indices/state variables needed for implementation
- behavior for illegal commands/protocol violations

Control description must be sufficient for RTL implementation without guessing hidden sequencing rules.

### 9. Define external interfaces
For every logical channel define:
- name
- direction
- purpose
- framing
- ordering
- backpressure behavior

For every signal define:
- name
- direction
- width expression
- signedness
- semantic meaning
- reset value

If ready/valid is used, define transfer as `ready && valid` and require payload stability while stalled. Do not require ready/valid if another protocol is technically more appropriate.

Width expressions must remain legal at every permitted parameter value. Avoid zero-width `$clog2` expressions.

### 10. Define reset
Reset must deterministically restore control/protocol state. Prefer resetting pointers, counters, FSM state, valid bits, and validity metadata rather than bulk-clearing memories unless cleared contents are functionally required.

### 11. Define module decomposition
Each module must have one clear responsibility. The manifest must define:
- top module
- each submodule
- dependencies
- parameters used by that module
- whether the module contains state

### 12. Define acceptance criteria
Create machine-testable criteria for:
- functional semantics
- data-type/arithmetic semantics
- legal runtime bounds and boundary cases
- reset
- interface/protocol behavior
- randomized regression
- synthesizable RTL
- deterministic Synopsys handoff requirements

Only deterministic tool reports may establish synthesis/timing/power/area/frequency/utilization results.

## Consistency Review Before READY
Before returning `READY`, verify:
- all named operation inputs/outputs refer to defined data types
- all runtime dimensions have concrete integer bounds
- all parameter defaults are concrete and legal
- storage capacities cover the declared legal bounds
- storage port/banking requirements sustain the stated compute schedule
- interface framing/order agrees with the storage/reuse protocol
- pipeline stalls cannot corrupt or duplicate state
- module responsibilities cover every architectural function
- reset semantics agree across architecture and interface contracts
- no downstream RTL decision requires an unstated architectural assumption

Return `SPEC_CONFLICT` only when explicit requirements cannot simultaneously hold.

## Forbidden Actions
- generating SystemVerilog
- silently specializing the framework to a benchmark example
- inventing requirements absent from the request or technical constraints
- weakening acceptance criteria to improve pass rate
- changing verification expectations after seeing RTL failures
- modifying or fabricating synthesis reports
- silently changing frozen architecture semantics
