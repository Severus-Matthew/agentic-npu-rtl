# Hardware generation: REPAIR_BUDGET_EXHAUSTED

Request: Design an 8 x 8 x 32 GEMM accelerator with signed int8 inputs, int32 wraparound accumulation, per-column int32 bias and ReLU. Use a simple sequential implementation with streaming inputs and outputs and explicit ready/valid handshakes. No optional modes. Fully specify reset and transaction ordering.

Functional verification: PENDING
Vivado: NOT_RUN
RTL repair iterations: 0
Verifier revisions: 0
Coverage/assertion review: PENDING (not simulation PASS)
PPA iterations: 0

Selected RTL: None

## Errors
None

## Limitations
Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.
Vivado adapter requires validation against the installed Vivado version and FPGA target.
Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.
