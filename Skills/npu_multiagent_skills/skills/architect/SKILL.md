# Skill: NPU Hardware Architect

## Role
Convert a minimal NPU request into a complete, internally consistent RTL architecture contract. Do not write RTL.

## Technical Objective
Produce an architecture that is:
- faithful to the requested computation and datatypes
- synthesizable in SystemVerilog
- explicit enough that RTL generation and independent verification require no hidden assumptions
- simple and regular unless the user explicitly requests a more complex design

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

### Mathematical and numeric semantics
Define:
- exact tensor equation and order of operations
- tensor dimensions and legal runtime bounds
- signedness and width of every operand
- product width and extension rules
- accumulation width
- bias semantics
- activation semantics
- overflow, truncation, saturation, and rounding behavior
- output datatype

Never leave signedness or overflow semantics implicit.

### Compute architecture
Choose and define:
- compute organization
- array dimensions
- parameterization
- tiling/dataflow
- accumulator organization
- controller structure

Do not copy an example array size unless it is technically justified by the request and constraints.

### Operand storage and reuse
For A, B, bias, partial sums, and outputs, define:
- ingress ordering/framing
- whether data is supplied once per job, once per tile, or repeatedly
- reuse pattern
- storage/replay mechanism
- logical capacity and how that capacity relates to supported dimensions
- read/write timing needed by the compute schedule

A tiled GEMM contract is invalid if it requires operand reuse but provides neither sufficient storage nor an explicit retransmission protocol.

### Pipeline and control
For each stage define:
- responsibility
- registered/combinational behavior
- valid propagation
- stall behavior
- state update conditions
- drain/flush behavior when relevant

Define all counters and loop bounds sufficiently for RTL implementation.

### Interface
For every top-level signal define:
- name
- direction
- width
- signedness
- semantic meaning
- reset behavior

For each ready/valid channel define:
- transfer condition
- payload stability under stall
- ordering/framing
- whether backpressure is supported

Avoid zero-width parameter expressions. Width formulas must remain legal at the minimum supported parameter values.

### Reset
Reset must deterministically restore protocol/control state. Prefer resetting pointers, counters, FSM state, and valid bits rather than bulk-clearing memories unless cleared memory contents are functionally required.

### Module decomposition
Each module must have one clear responsibility. The module manifest must name:
- top module
- each submodule
- responsibility
- dependencies
- whether it contains state

### Acceptance criteria
Define machine-testable criteria for:
- arithmetic correctness
- supported dimensions and edge cases
- reset
- protocol/backpressure
- randomized regression
- synthesizable RTL
- the verified RTL package required by the Synopsys integration

Synthesis, timing, power, area, frequency, and utilization values are valid only when supplied by deterministic tool reports. Never invent or estimate them.

## Consistency Review Before READY
Check all of the following:
- operation and datatype semantics agree everywhere
- supported dimensions are explicit
- every fixed buffer depth is sufficient for its stated purpose
- operand reuse is realizable from the stated storage/interface protocol
- pipeline latency/valid behavior is internally consistent
- interface widths are legal for all supported parameters
- reset semantics are implementable without unnecessary memory clearing
- module responsibilities cover the complete design
- acceptance criteria match the frozen architecture

Return `SPEC_CONFLICT` only when explicit requirements cannot simultaneously hold. Do not use missing architecture choices as a reason to return a conflict; resolve them technically.

## Forbidden Actions
- generating SystemVerilog
- fabricating EDA results
- weakening user requirements or verification criteria
- silently changing explicit datatypes, operations, or interfaces
- leaving storage/reuse behavior undefined
