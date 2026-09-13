# Hardware generation: FAILED

Request: Design an NPU for accelerating matrix-vector multiplication in neural-network inference. Use 16 parallel INT8 multiply-accumulate units, INT32 accumulators, optional bias addition, and selectable ReLU activation. The accelerator should accept input data and return results through ready/valid streaming interfaces.

Functional verification: PENDING
Vivado: NOT_RUN
RTL repair iterations: 0
Verifier revisions: 0
PPA iterations: 0

Selected RTL: None

## Errors
Independent Testbench Generator output has no recognized references to required contract-visible completion/error signals (use handle reads, getattr, or snapshot assertions in tests/helpers): out_error, out_last, out_valid

## Limitations
Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.
Vivado adapter requires validation against the installed Vivado version and FPGA target.
Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.
