# Orchestration

The cross-cutting code that genuinely does not belong to any single
verification domain ([`../protocol/`](../protocol/README.md),
[`../operation/`](../operation/README.md),
[`../lifecycle/`](../lifecycle/README.md)) because each file here coordinates
*across* all three at once:

| File | What it orchestrates |
|---|---|
| `instrumentation.py` | Renders the generated cocotb testbench's contract-owned block — embeds assertion, coverage, *and* stimulus output from all three domains into one file (`render_contract_generated_block`, `install_contract_generated_block`), including a human-readable golden-model formula and worked-trace comment per `integer_matrix_multiply` operation (`render_operation_golden_model_comment_lines`, sourced from `pool/operation_metadata/canonical.py::integer_matrix_multiply_events` so it cannot drift from what the DUT check actually computes). |
| `runtime.py` | `InterfaceCoverageTracker`/`get_coverage_tracker` — the shared runtime coverage database every domain's coverage plan is sampled into, plus `record_stimulus`/`sample_operation` used by both coverage and stimulus code. |
| `cocotb_model.py` | The `cocotb_coverage` (third-party library) coverage object model `runtime.py` builds on. |
| `history.py` | `rebuild_stimulus_history` — aggregates the stimulus ledger across every run, domain-agnostic by construction. |
| `campaign.py` | `run_code_owned_verification_campaign` — the fully-automatic test-generation-time driver that dispatches into `protocol/stimulus/drivers/` (AXI4-Lite, full AXI4 — via a separate multi-port register-started path for `control_plane_sequence` operations — or the LLM-declared memory-like `custom_mmio` profile) or the generic ready-valid path, samples coverage via `runtime.py`, and is what `instrumentation.py` embeds when `automatic_campaign_support()` says a design qualifies. If only arithmetic is LLM-owned, it still runs `_run_arithmetic_blocked_operation_smoke`: real protocol/lifecycle traffic without inventing a golden output. `any_operation_supported` therefore means at least one operation has an executable protocol/lifecycle path, while per-operation `supported` still means the full golden-checked campaign is available. |

The campaign records each checked job through `_record_case`, which turns the
driver's observed beats into logical output elements and hands them, with the
code-owned golden result, to the coverage/ledger runtime. What a "beat" is
depends on the driver, and `_record_case`'s `beats_are_canonical_elements`
keyword says which:

- **Raw bus words** (the default, `False`) — the AXI4-Lite driver returns one
  physical write-data word per beat. When the output binding has a
  `memory_mapping`, `_record_case` unpacks each word into
  `elements_per_word` logical elements with `unpack_words`. For example, a
  32-bit write carrying four signed INT8 results is one retirement response but
  four observed result elements. Ready/valid collectors also use the default;
  their outputs have no `memory_mapping`, so each beat is one element passed
  through sign handling only.
- **Already-decoded elements** (`True`) — `execute_axi4_memory_job` (both
  `run_code_owned_axi4_operation_case` and the control-plane variant) and the
  custom_mmio path read the shared memory image back through
  `OperationMemoryAdapter.read_output_values`, i.e. they already return one
  decoded canonical element per beat. Passing those through `unpack_words`
  again would treat each element as a multi-lane bus word and corrupt every
  lane after the first whenever `elements_per_word > 1` (for example a 512-bit
  AXI4 bus carrying 32-bit results), so those three call sites pass
  `beats_are_canonical_elements=True`.

For `control_plane_sequence` jobs on the real HLS-style AXI4-Lite control
subordinate, `campaign.py` starts the completion-register poll immediately
after the start transaction, while the independent AXI4 memory drivers are
still running. The generated lifecycle monitor checks that a successful poll
cannot precede the final declared output retirement. Polling only after the
drivers returned concealed a falsely early `ap_done` readback. The real-RTL
regression in `../../tests/test_int8_gemm_hls_golden.py` copies the golden
Verilog into a temporary directory and mutates only that readback bit;
golden passes and the mutant fails `completion_matches_final_output`.
The automatic campaign now dispatches this policy to a separate multi-port
AXI4/control-plane path instead of the generic single-manager AXI4 path. The
unchanged HLS RTL now passes the normal generated TB with all 137 required
bins, no assertion failures, and a PASS ledger. Individual checker/bin mutant
qualification remains open; the manually assembled regression above is smoke
evidence and does not earn a strict matrix check by itself.
The control-plane campaign compiles timing and page-split variants from the
resolved protocol feature plan, then reuses the AXI4 memory driver's
first-transfer READY policy and the AXI4-Lite master's response sinks.
These scenarios change only bus timing; every completed job still passes
through accepted-input capture and the tool-owned golden comparison.

`automatic_campaign_support` also reports operations that **could not be compiled**
into metadata (`build_architect_operation_metadata(...)["unrepresentable_operations"]`),
which used to be invisible to it: each appears in `operations[<name>]` as
`{"supported": False, "reasons": ["<name>:operation_not_compiled=<reason_code>"],
"arithmetic_reasons": [], "protocol_lifecycle_supported": False, "compile_blocked":
True, "category", "owner", "reason_code"}`, its reason joins the top-level `reasons`
(so `supported` is `False` and the hand-authored-structure checks apply), and a
top-level `blocked_operations` mapping (present only when non-empty) carries
`blocked_by`, `affected_domains`, `affected_feature_ids`, `message` and
`resolution_hint`. `any_operation_supported` ignores them and the campaign runner
never sees them (it iterates compiled `operations` only); for a fully compiled
contract the report is unchanged. `code_owned_obligations_for_supported_operations`
also counts a blocked operation's bound channels/status signals as occupied, so a
channel shared with an operation that will not be driven is not credited as
code-owned on a sibling's account.

At simulation end `InterfaceCoverageTracker.report()` is unchanged in verdict
logic — every `required` bin with zero hits is `missing_bins` and fails the run —
but when an unhit bin belongs to an obligation carrying an `automation` record (a
blocked operation's restored lifecycle obligations, see
[`../pool/feature_plans/README.md`](../pool/feature_plans/README.md)) the report also
carries `unmet_by_blocker`: `{"<operation>:<reason_code>": [bin ids]}`, so the failure
names its owner, and `automation_state`: per-domain
`{"state": "ready" | "partial" | "blocked", "code_owned", "blocked", "blocked_by"}`
rolled up from the feature-level `automation` records of the plan's lifecycle features.
Both keys are absent when nothing is blocked. There is no new
status: a bin hit by anyone (a tool monitor, or a Verifier-authored sampler for a
contract-local extension) is covered.

`automatic_campaign_support` checks AXI4-Lite operation capabilities per
operation. Its current memory driver can reconstruct a complete GEMM output
only from full-strobe writes at aligned object bases. A contract requiring
AXI4-Lite `sparse`/`all_zero` write-strobe bins or an `unaligned` address bin
therefore reports a targeted `...not_executable` reason instead of claiming
that its automatic operation campaign can close those bins. The standard
protocol checker and coverage templates still recognize these legal bus
behaviors; a Verifier-authored extension may implement that specific memory
layout without disabling unrelated supported operations.

For AXI4-Lite jobs, `campaign.py` starts the expected status-pulse waiter
before the memory driver: completion for a successful checked job, or error
for an injected response fault. This is intentional because a legal one-cycle
status pulse may coincide with the final response and end before the
bus-serving coroutine returns; starting the waiter afterward would miss real
lifecycle evidence. Before recording a checked job, the AXI4-Lite path waits
for the runtime monitor's completion-event counter to advance; it does not use
a guessed scheduler delay as proof. Non-recording callers still return while
the one-cycle pulse itself is asserted, preserving their observable behavior.

The AXI4-Lite subcampaign also closes the operation's independent command
channel. It creates simultaneous command/READY arrival on reset release, then
times held overlapping commands from real final-AW/W and early-BRESP evidence.
Adjacent final-request offsets probe one-cycle and short backpressure without
reading internal DUT state; an early-response overlap exercises the long bin.
Coverage is credited only from the command handshakes actually observed.
The newly accepted overlap job is reset-aborted before the next probe.
The held command is published on the triggering falling edge before the
generated monitor's `FallingEdge + ReadOnly` snapshot. Waiting 1 ps before
publishing let an invalid, one-cycle early command acceptance escape the
`single_inflight` assertion; the local faulty RTL then failed only by missing
command-stall coverage. The current scheduling catches that acceptance as
`legal_command_starts_one_job` while the corrected RTL still closes all bins.

## Known limitations of the register-started (`control_plane_sequence`) path

Read directly from `campaign.py`; none of these is fixed here.

- `run_code_owned_axi4_operation_case_via_control_plane_sequence` is the
  happy-path job driver only; `_run_axi4_control_plane_operation_campaign` runs
  transport variants (READY stalls, simultaneous first transfer, page-split
  tails, delayed W) and post-job control-bus probes, but not the reset-abort,
  illegal-command, or error-injection sweeps that
  `_run_axi4_operation_campaign` runs for a ready/valid-started AXI4 operation
  (the function's own docstring says the same).
- `_run_arithmetic_blocked_operation_smoke` dispatches `{"axi4"}` operations to
  `run_code_owned_axi4_operation_case`, which requires exactly one resolved
  ready/valid command channel (`"AXI4 job needs one resolved legal command"`).
  `_operation_protocol_lifecycle_reasons` accepts a `control_plane_sequence`
  operation, so a control-plane operation whose arithmetic is `llm_extension`
  would (by reading the code; not exercised by any test) reach that smoke path
  and raise there, rather than being driven through the control-plane runner.
- Lifecycle coverage obligations and the lifecycle stimulus plan are not
  produced for such an operation (no command channel; see
  [`../pool/lifecycle_policy_pool/README.md`](../pool/lifecycle_policy_pool/README.md)).

## Historical overviews

`OLD_assertion_overview.md`, `OLD_coverage_overview.md`,
`OLD_stimulus_overview.md` are the pre-domain-first-reorg top-level READMEs
for what used to be `assertion/`, `coverage/`, `stimulus/` (when those were
the top-level folders and `protocol`/`lifecycle`/`operation` were nested
inside each). Kept for their still-accurate deep documentation of the files
that ended up here (`campaign.py`, `runtime.py`, `instrumentation.py`, etc.)
and of the files that moved into `../protocol/`, `../operation/`,
`../lifecycle/` — but written from the old, now-inverted directory
structure's point of view, so treat any relative path or "this package"
framing in them as describing the *old* layout, not this one. These should
eventually be split apart and merged into `../protocol/`, `../operation/`,
`../lifecycle/`, and this file, rather than kept as a separate three-file
detour — not yet done.
