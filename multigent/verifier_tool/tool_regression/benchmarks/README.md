# Local frozen-contract qualification

`frozen_contract_qualification.py` executes the user-required sequence without
an external API or a hand-written `test.py`: load four frozen Architect files,
run deterministic preflight, generate the normal verifier-tool TB, test the
unchanged previous RTL, then test the corrected RTL against **that same TB**.
It writes `contract.diff`, `rtl.diff`, `generation.log`, each simulator report,
and `qualification.json`. It only reports PASS when the previous RTL fails
for the caller-specified exact diagnostic **or exactly the named set of
missing required coverage bins** and the corrected RTL passes every
required bin, assertion, and generated stimulus-ledger check. When the new
contract introduces a port or output format that prevents the old RTL from
reaching the semantic checker, supply an additional interface-compatible
semantic-stage RTL and its expected diagnostic or exact missing-bin set; the
structural failure alone is not counted as semantic qualification. For a
coverage-only semantic stage, use `--semantic-stage-rtl-dir <path>` together
with `--expected-semantic-missing-bins <bin1> <bin2> ...`; this requires
`COVERAGE_MISS`, no assertion failures, and no additional missing bins.

The current runner uses the existing 4×4×4 GEMM benchmark renderer and top
module. It is **not** a universal runner for arbitrary Architect designs or
protocols. In particular, it must not be used to claim AXI4-Stream/custom
operation qualification unless the normal renderer emits their complete
campaign. The status and open gaps are tracked in the executable
[`qualification ledger`](../qualification/ledger.json).

Example, assuming frozen contract and RTL copies are under `/private/tmp`:

```sh
PYTHONPATH=. .venv/bin/python -m multigent.verifier_tool.tool_regression.benchmarks.frozen_contract_qualification \
  /private/tmp/frozen-relu \
  /private/tmp/previous-rtl \
  /private/tmp/relu-rtl \
  /private/tmp/relu-qualification \
  --previous-contract-dir /private/tmp/frozen-base \
  --expected-previous-failure 'role-bound accepted DUT outputs differ'
```

For a coverage-only feature with no assertion checker, replace the last
option with `--expected-previous-missing-bin <full.obligation.bin>`. This
requires `COVERAGE_MISS`, no assertion failure, and that the named bin be the
**only** missing required bin; an unrelated timeout or coverage miss cannot
qualify the negative run. When one contract choice maps to several fields,
use `--expected-previous-missing-bins <bin1> <bin2> ...` to require that
**exact set** and no other missing bins.

The contract/RTL inputs must be preserved; a later check should consume the
previously passing corrected pair as its new baseline. Do not edit the
Architect, RTL Generator, or Debugger to make a local qualification pass.

The separate `int8_gemm_hls_golden` contract targets the actual Vitis-HLS
32×64×128 GEMM RTL in `gemm_golden/`, with three AXI4 memory groups and an
AXI4-Lite `ap_ctrl_chain` control group. Its real-RTL smoke and early-`ap_done`
mutant regression live in
[`../rtl/test_int8_gemm_hls_golden.py`](../rtl/test_int8_gemm_hls_golden.py). The
contract-to-RTL audit, including corrected control sequencing and AXI
capabilities, is in `int8_gemm_hls_golden/CONTRACT_AUDIT.md`. The audit is not a
generated-TB pass claim. The mutant is made in a pytest temporary RTL copy,
never in `gemm_golden/`: it
changes only the control-register `ap_done` readback to 1. A genuine early
readback must fail the tool-owned `completion_matches_final_output` lifecycle
checker even when every GEMM output value is otherwise correct. This is a
targeted real-RTL mutation test, not a claim that every HLS protocol bin or
the complete automatic campaign has passed.

`int8_gemm_hls_golden/generated_mutation_qualification.py` instead renders the
normal contract-generated Cocotb campaign and coverage plan, runs an RTL mutant
first and the unmodified HLS RTL second, and writes a `qualification.json` in
the requested output directory. It does not call an external model API. A
mutant counts only if the intended precise failure occurs **and** the original
run closes every required bin, assertion, and stimulus-ledger check. The
separate [`HLS benchmark qualification matrix`](../qualification/hls_benchmark_qualification_matrix.md)
records each strict paired result. The unchanged HLS RTL now passes the normal
generated TB with 152/152 required bins, zero assertion failures, and a PASS
stimulus ledger; this is a positive baseline, not blanket mutant qualification.
`int8_gemm_hls_golden/qualify_named_mutant.py` reuses that saved baseline only
when the regenerated test and coverage plan have identical hashes, then runs
one exact-anchor RTL mutant and checks its named diagnostic. A mutant may have
several exact edits only when a single protocol fault requires coupled fields
(for example, selecting WRAP and an illegal WRAP length); every edit records
and validates its expected anchor count before copying or simulating RTL.

`int8_gemm_hls_golden/prepare_qualification_catalog.py` performs no simulation.
It expands all 134 current HLS matrix targets (71 required-bin-bearing coverage
obligations plus 63 assertion/checker features) into the ignored, regenerated
`prepared_qualification_catalog.json`, separates executable RTL mutants from
driver fault injection, matched contract/RTL variants, coverage stimulus
evidence, topology exclusions, and checker gaps, and validates the named
registry. The current registry contains 62 locally reviewable mutants.
`int8_gemm_hls_golden/batch_qualify_mutants.py` executes that named registry
against a newly approved baseline with bounded local parallelism (two workers
by default, four maximum):

```sh
.venv/bin/python -m \
  multigent.verifier_tool.tool_regression.benchmarks.int8_gemm_hls_golden.batch_qualify_mutants \
  /private/tmp/hls-mutant-batch \
  --baseline-dir /private/tmp/new-baseline/original \
  --baseline-generated /private/tmp/new-baseline/generated \
  --jobs 2 --names all
```

Use `--list --names all` to validate every substitution without compiling or
simulating. Driver/contract/stimulus recipes in the catalog are not silently
treated as RTL mutants: they need their corresponding reusable harness before
strict execution. The all-pool inventory is in the executable
[`qualification ledger`](../qualification/ledger.json).

Coverage is qualified separately from RTL correctness assertions.
`qualify_positive_coverage.py` cross-checks one real generated-TB HLS report
against every matrix obligation and bin. `qualify_coverage_evidence.py` then
removes one required-bin hit at a time while deliberately retaining the
top-level PASS and aggregate hit count; the gate must reject all 152 variants
for the exact zero-hit bin. This is coverage-evidence qualification, not an RTL
mutant, and the benchmark matrix marks it with `E` rather than `✓`.

Environment-owned protocol fault helpers are also benchmark-local. The HLS
folder contains `protocol_fault_plan.py`, the fault-aware AXI4/control driver
copies, and `fault_bootstrap.py`. A negative run writes a temporary
`sitecustomize.py` beside its copied generated TB; only that simulator process
replaces the clean production drivers with the HLS benchmark copies. The core
protocol and lifecycle drivers contain no `NPU_PROTOCOL_FAULT_PLAN` lookup or
qualification mutation branch.

[`../rtl/test_int8_gemm_hls_mutations.py`](../rtl/test_int8_gemm_hls_mutations.py)
adds 20 independent, real-RTL
mutants against the same frozen contract: 7 operation (multiply, signedness,
A/B read payload, accumulation, and output packing), 5 lifecycle/control
(start, completion, and pointer programming), and 8 AXI4 protocol/address
(burst encoding, transfer size, length, LAST, WSTRB, and output address).
Each mutant is a one-anchor change to a fresh pytest temporary copy; the
source `gemm_golden/` is never edited. The test requires a simulation failure
with the expected diagnostic, not merely a successful Verilator build failure.
Some mutants are caught by named deterministic assertions, others by the
memory driver, the golden-output comparison, or a finite simulation timeout;
these are distinct detection strengths. Run them locally with
`./.venv/bin/python -m pytest multigent/verifier_tool/tool_regression/rtl/test_int8_gemm_hls_mutations.py -q`.
