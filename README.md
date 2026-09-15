# agentic-npu-rtl

Generic LangGraph-orchestrated RTL generation, independent verification, deterministic tool checking, and evidence-driven repair.

## Current workflow

```text
user request
   -> Architect
   -> frozen architecture/interface/module/acceptance contracts
   -> independent Verifier
      -> Python reference model + cocotb TB
      -> ask Architect only if one expected behavior cannot be derived
   -> TB-only Verifier Reviewer
      -> repair findings return only to Verifier
   -> RTL Generator
   -> Verilator lint/elaboration
   -> cocotb full regression
      -> PASS -> verified RTL / Synopsys handoff boundary
      -> FAIL -> Debugger -> constrained repair plan
                         -> RTL Generator FUNCTIONAL_REPAIR
                         -> same frozen Verifier artifacts
                         -> Verilator + cocotb
```

Architect/RTL/Verifier/Debugger communication occurs through LangGraph state and structured artifacts, not unrestricted agent chat. LLMs propose; deterministic engineering tools decide.

Functional repair does not regenerate the verifier. The same approved frozen
reference/tests are reused until Verifier asks Architect and Architect actually
changes the contract. Debugger has no contract-change route.

## Resume a run from frozen architecture and existing RTL

```bash
python -m multigent.orchestration.graph \
  --request "<exact original hardware request>" \
  --run-id <run-id> \
  --use-frozen-architecture \
  --use-existing-rtl \
  --max-architecture-revisions 2 \
  --max-repair-iterations 5
```

The repair budget counts authorized RTL repair attempts. Deterministic compile/simulation failures route to Debugger while budget remains; exhaustion terminates as `REPAIR_BUDGET_EXHAUSTED`.

## Verification boundary

The Verifier receives only the original request, fixed verification policy, and frozen Architect artifacts. Generated RTL and RTL Generator output are excluded from its generation context. It creates specification-derived Python reference/tests; Verilator/cocotb establish PASS/FAIL.

For ready/valid interfaces, generated source drivers must stall only before presenting a beat and then hold `valid` and payload stable until handshake. Contract-defined completion/error signals must be explicitly exercised when verification policy requires them.

## Synthesis boundary

Verified RTL is handed to the external Synopsys integration. PPA/timing/area/power/utilization values are accepted only from authoritative deterministic tool reports and are never estimated by agents.

## Current executable pipeline

The complete LangGraph workflow, Delta environment instructions, isolated run and
resume commands, deterministic Vivado handoff, optimization gates and limitations
are documented in [multigent/README.md](multigent/README.md). Vivado is optional for
functional verification but required for PPA evaluation and final SUCCESS.
