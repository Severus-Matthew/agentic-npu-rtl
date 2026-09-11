# Hardware generation: REPAIR_BUDGET_EXHAUSTED

Request: Design an 8 x 8 x 32 GEMM accelerator with bias and ReLU: Y[M,N] = ReLU(A[M,K] @ B[K,N] + bias[N]), M=8, N=8, K=32, signed int8 inputs, signed int32 accumulation and bias, two-complement int32 wrap on overflow before signed ReLU. Support reset and output backpressure.

Functional verification: SIMULATION_TIMEOUT
Vivado: NOT_RUN
RTL repair iterations: 5
Verifier revisions: 2
PPA iterations: 0

Selected RTL: None

## Errors
AgentRuntimeError: Verifier context missing required fields: ['frozen_architecture', 'provenance', 'user_request', 'verification_policy']
AgentRuntimeError: No RTL changed during REPAIR_BLOCKED; regression must be NONE
AgentRuntimeError: Verifier context missing required fields: ['frozen_architecture', 'provenance', 'user_request', 'verification_policy']
AgentRuntimeError: debugger API request failed using mode 'responses' and model 'gpt-5.3-codex': Error code: 400 - {'error': {'message': 'Your input exceeds the context window of this model. Please adjust your input and try again.', 'type': 'invalid_request_error', 'param': 'input', 'code': 'context_length_exceeded'}}

## Limitations
Generated oracle and tests undergo deterministic structural checks and simulation; this is not a proof of oracle correctness.
Vivado adapter requires validation against the installed Vivado version and FPGA target.
Out-of-context PPA excludes board I/O integration; power is a tool estimate and maximum frequency is not measured.
