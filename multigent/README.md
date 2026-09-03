# Multi-Agent NPU Runtime

This directory contains the executable multi-agent runtime for autonomous NPU RTL generation, independent verification, repair, and implementation-quality evaluation.

All LLM roles use the same configured API model so model capability remains controlled across one-shot, single-agent, and multi-agent experiments.

## User input

The user provides computational intent only, for example:

```text
design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type
```

The Architect is not given a hand-written microarchitecture. A deterministic intake layer adds only fixed technical constraints:

- synthesizable SystemVerilog
- forbidden RTL constructs
- verification requirements
- deterministic Synopsys-report policy

The Architect must resolve unspecified technical choices such as:

- exact arithmetic and overflow semantics
- supported M/N/K bounds
- compute organization and array dimensions
- tiling/dataflow
- operand reuse and storage
- buffering
- pipeline/control
- interface and backpressure
- reset behavior
- parameterization
- module decomposition

This separation makes architecture choices attributable to the Architect rather than hidden in the user input.

Fixed technical constraints live in:

```text
multigent/config/project_constraints.yaml
```

The intake builder lives in:

```text
multigent/intake/request_builder.py
```

## Architect execution

The Architect receives only its technical skill plus the deterministic intake envelope. It does not receive unrelated Debugger/PPA/workflow instructions.

Run:

```bash
python -m multigent.agents.architect \
  --request "design a GEMM_BIAS_RELU NPU of int8 x int8 x int32 type" \
  --run-id dense-gemm-001
```

The exact request and injected technical policy are recorded at:

```text
multigent/workspace/specs/request-dense-gemm-001.yaml
```

On `READY`, the Architect writes:

```text
multigent/workspace/architecture/
├── architecture_contract.yaml
├── interface_contract.yaml
├── module_manifest.json
├── acceptance_criteria.yaml
└── architect_result.json
```

The Architect never writes SystemVerilog.

## Architect contract requirements

Before returning `READY`, the architecture must close all implementation-critical semantics. In particular:

- INT arithmetic widths/signedness/extension/overflow must be explicit.
- Supported dimension bounds must be explicit.
- Every operand's ordering, supply frequency, reuse strategy, storage strategy, and capacity must be explicit.
- Tiled reuse must be realizable from the stated storage and interface protocol.
- Buffer capacities must be sufficient for the declared dimension bounds and schedule.
- Compile-time parameters must have concrete defaults and legality constraints.
- Interface widths must remain legal at minimum parameter values.
- Reset must restore control/protocol state without unnecessary bulk memory clearing.
- No EDA metric may be invented; synthesis/PPA values come only from deterministic Synopsys reports.

## Preparing RTL Generator input

After the Architect produces a valid frozen contract:

```bash
python -m multigent.scripts.prepare_rtl_input \
  --run-id dense-gemm-001
```

This creates:

```text
multigent/workspace/specs/derived/rtl-input-dense-gemm-001.yaml
```

The RTL input is assembled from:

1. the exact original user request,
2. fixed RTL/synthesis constraints, and
3. the frozen architecture/interface/module/acceptance artifacts.

The user does not restate architecture details for the RTL Generator.

## API setup

Install dependencies:

```bash
pip install -r multigent/requirements.txt
```

Configure `.env` locally:

```bash
OPENAI_API_KEY=your_real_key
OPENAI_BASE_URL=
NPU_AGENT_MODEL=gpt-5.3-codex
NPU_AGENT_API_MODE=responses
NPU_AGENT_TRUST_ENV=false
```

`.env` is gitignored. Verify API access with:

```bash
python -m multigent.scripts.check_api --list-models
```

## Technical synthesis boundary

`tools/synopsys_interface.py` defines the integration contract for Synopsys execution. The multi-agent runtime consumes real structured reports from that interface and never substitutes LLM-estimated timing, area, power, frequency, or utilization.

## Core rule

**LLMs propose. Deterministic engineering tools decide correctness and implementation metrics.**
