# Hardware generation: FAILED

Request: Design a small AI accelerator for fully connected neural-network layers. The accelerator should primarily operate as a tiled GEMM engine, multiplying INT8 activation matrices by INT8 weight matrices, accumulating in INT32, adding a bias vector, and applying ReLU. Use an 8×8 compute array and support matrices larger than the array through tiling.

Functional verification: PENDING
Vivado: NOT_RUN
RTL repair iterations: 0
Verifier revisions: 0
PPA iterations: 0

Selected RTL: None

## Errors
AgentRuntimeError: Architect returned a structurally valid but internally inconsistent READY contract: data object obj_tile_context crosses the external boundary but external=false; channel cmd_ch exposes internal data object obj_tile_context

## Limitations
Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.
Vivado adapter requires validation against the installed Vivado version and FPGA target.
Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.
