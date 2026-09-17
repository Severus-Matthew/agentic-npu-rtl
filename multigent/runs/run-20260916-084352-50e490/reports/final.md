# Hardware generation: FAILED

Request: Design a small clocked unsigned adder. Each accepted input transaction carries two 8-bit operands and produces their exact 9-bit sum. Use one shared input valid/ready handshake and one output valid/ready handshake, a single-entry output register, active-low synchronous reset, and one-cycle latency without stalls. Hold output stable under backpressure. Reset discards pending work and deasserts output valid. Use one top module, no optional modes or runtime configuration.

Functional verification: PENDING
Vivado: NOT_RUN
RTL repair iterations: 0
Verifier revisions: 7
Coverage/assertion review: PENDING (not simulation PASS)
PPA iterations: 0

Selected RTL: None

## Errors
Generated test file test_rv_uadd8.py contains no executable async @cocotb.test() functions; imports, coverage declarations and comments are not test bodies. Return complete executable source now, not a description of future runtime delivery.
Invalid operation sampling bindings: Unknown or ambiguous dimension 'scalar_len'
Invalid operation sampling bindings: Unknown or ambiguous dimension 'tx_elems'
Verifier conflict references undeclared modules: ['tests/test_rv_uadd8.py']; affected_modules must use exact names from module_manifest.modules[].name, never a test/reference file name. Declared modules are: ['rv_uadd8_top']
Verifier TB review structure is invalid: Stimulus 'boundary_00' needs a # STIMULUS [boundary_00] comment
Verifier TB review structure is invalid: Stimulus 'one_cycle_stall' needs a # STIMULUS [one_cycle_stall] comment
Verifier TB review structure is invalid: Every Verifier-authored assert needs a feature comment immediately above it; line 84

## Limitations
Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.
Vivado adapter requires validation against the installed Vivado version and FPGA target.
Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.
