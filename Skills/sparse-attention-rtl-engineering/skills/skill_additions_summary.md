# Added Skill Instructions

Actual added English wording, organized as numbered instructions. Only line wrapping and list formatting have changed; the content is not summarized.

Line references point to the updated `SKILL.md` files. Added-line counts include blank lines.

## Architect

Added: 172 lines.

### 1. Normalize requested behavior

Added lines: L42–L50.

1. For a multi-stage datapath, declare each logical stage as `present`, `absent`, or `deferred`. This includes applicable work/index selection, Q-by-K or equivalent score generation, score conversion, masking, row reduction/normalization, weighted-value accumulation, and final conversion/writeback. An early-stage checkpoint must not imply that deferred downstream stages exist.

2. Express these distinctions through the existing operation semantics and acceptance criteria; do not invent unsupported contract fields or mandatory operating modes.

### 2. Define data types

Added lines: L64–L98.

1. Define formats at conversion boundaries rather than assigning one datatype to an entire multi-stage operator. Distinguish mathematical reduction state, converted or stored state, normalization state, coefficients, and final output. For online normalization, define how a new maximum rescales every prior state component.

2. When applicable, also freeze:

    1. floating-point zero/subnormal, NaN, infinity, signed-zero, exception, and rounding rules

    2. block/group scale ownership, exponent range, guard bits, legal alignment distances, and whether rounding occurs per contribution or only after the reduction

    3. the interpretation of a stored mantissa-plus-exponent pair

    4. whether a changed scale or exponent invalidates retained operand/row state

    5. probability/value precision separately from Q/K multiplication precision

3. Freeze score units and coefficient derivation, including operand quantizer/group scales and any requested per-head normalization. A prototype's integer divisor is not automatically the model's score scale. When a base-2 implementation evaluates a natural exponential, specify `exp(s) = exp2(s*log2(e))` or its equivalent fused coefficient, applied exactly once. Freeze clipping and approximation-error criteria before comparing implementations.

4. For exact online weighted normalization, use the declared representation of the following recurrence, or specify the requested alternative explicitly:

    1. `m_new = max(m_old, max(valid scores in the next selected tile))`

    2. `alpha = exp(m_old - m_new)`

    3. `l_new = alpha*l_old + sum(exp(s_j - m_new))`

    4. `z_new = alpha*z_old + sum(exp(s_j - m_new)*v_j)`

    5. `output = z_final/l_final`

5. Handle the initial/empty row explicitly. Selected key tiles contribute to one row normalization; their independently normalized outputs cannot simply be added.

### 3. Define logical data objects

Added lines: L114–L119.

1. When work may be selected, merged, or reordered, define the minimal identity carried with each object, such as job/head, query row or group, selected unit, selection rank, key offset, and output slot. If a later value path exists, selected key and value objects must retain the same logical token identity through reordering, deduplication, coalescing, and tails.

### 4. Define legal runtime dimensions/bounds

Added lines: L131–L136.

1. For Q/K/V work, distinguish query count, key count, head/reduction dimension, value dimension, selection count, and physical block size. The key tensor, reduction dimension, and Top-K budget must not share ambiguous notation. If multiple heads or shared KV heads are requested, define their index mapping and state lifetimes explicitly rather than using a model hidden width as the per-head dot-product length.

### 6. Choose compute organization

Added lines: L154–L196.

1. For selective work also define the selection source and granularity, whether it is per row/group/head/job, ordering and tie behavior, duplicate policy, clipping, and tail handling. State the unit of every index and stride: byte, element, token, tile, block, or page.

2. Keep selection membership, structural lane validity, padding/tail validity, and semantic score masks separate. For each mask define polarity, coordinates, application stage, storage effect, reduction effect, and fully masked-row behavior. A valid numerical zero is not an invalid position.

3. Specify whether an invalid/masked lane's numerical payload is defined or ignored. Do not require zero-valued masked outputs unless downstream behavior requires that encoding; validity, masking, completion, and meaningful exception flags remain explicit.

4. For causal/window policies, specify aligned local blocks versus rolling windows, inclusive endpoints, boundary clipping, and per-token exclusion within a selected diagonal block. Padding operands with zeros alone does not remove them from a normalization denominator.

5. When selection uses per-page min/max bounds, define bound precision, construction, freshness, score reduction, and tie order. Distinguish the selection surrogate from the actual QK score. Define the union of per-query selections independently of the per-query budget: the merged worklist may be larger than that budget, with a different row-membership mask for each selected page.

6. Preserve per-query membership when sharing selected pages across a group. A page selected by one row is not automatically selected by every row in that group.

7. If selected work can exceed available lanes, define admission and whether the contract rejects it, queues it, or partitions it into passes. Deferred work is still selected work. Specify pass membership, operand replay/retention, original identity, and the completion rule for empty passes or contexts with different reduction lengths.

8. For lanes shared across operand contexts, define any group-level context restriction and require the descriptor packer to obey it. Budget retained contexts and routing bandwidth together; independent per-lane context selection can be more expensive than the arithmetic it feeds.

9. Separate physical MAC dimensions, logical output-tile dimensions, and the reduction dimension. A wider logical tile can be scheduled on smaller hardware. State whether an excluded pair is skipped before compute or computed then discarded so useful work and executed work can be distinguished.

### 7. Close storage, ingress, and reuse semantics

Added lines: L210–L225.

1. For intermediate/result buffers, define ownership states, completion condition, readback, and release. Compute completion and buffer retirement are distinct when a consumer still owns unread results. Preserve enough identity metadata to map stored results to logical work without relying on physical arrival order.

2. When background configuration overlaps execution, distinguish pending and active assignments. Define a safe promotion event and keep mappings stable while a computation depends on them. Reusing storage earlier requires independent snapshots of all identity still needed by in-flight results. Pending configuration must not reset active work.

3. Choose full-input buffering, tile buffering, or streaming from the supported problem bounds. Account for score width, exponents, descriptors, row state, and value accumulators as well as operand bytes. Do not infer that data resident in external device memory is already resident in FPGA SRAM. If storage is claimed independent of context length, identify which state remains bounded as context grows.

### 8. Define pipeline behavior

Added lines: L238–L246.

1. Numerical payload, logical identity, masks, buffer tag, and ownership must advance under coherent enables. Any schedule that reorders work must define the mapping from logical selection order through physical execution order to output order.

2. For a pipelined producer that can finish work after downstream readiness drops, provide a coherent stall path or sufficient elastic capacity for all in-flight results. A completion indication must coincide with the promised snapshot becoming available, including simultaneous finish, consume, and next-start events.

### 10. Define external interfaces and exact transport encoding

Added lines: L314–L329.

1. For address or descriptor fields, define the represented unit explicitly. Do not leave downstream agents to infer whether a stride counts bytes, elements, tokens, tiles, blocks, or pages.

2. When adapting a platform wrapper, define pointer packing, register offsets, burst layout, memory-bank mapping, and completion/error registers together. Reusing a three-pointer interface or packed operand layout is valid only when the new logical objects and transfer counts fit it. Identify firmware/IP regeneration requirements when the interface changes; the Architect specifies these dependencies rather than editing build artifacts.

3. For memory-backed tiling, define transfer limits and burst segmentation, beat/lane packing, final-beat markers, partial-write strobes, and how transfer completion differs from tile/job completion. A contiguous burst may stream through a small FIFO; its total length does not alone require a full-burst local buffer.

### 11. Prove schedule/transport compatibility

Added lines: L360–L369.

1. For overlapped stages, budget operand load, MAC feed/fill/flush, array drain, score transfer, normalization, value accumulation, and buffer release separately. An ideal steady-state lower bound is the slowest stage's service interval, but shared resources and dependencies can make the achievable interval larger. Match lane count and memory ports to the actual drain cadence; a reduction dimension alone is not a tile interval.

2. If one compute fabric serves both score generation and weighted-value accumulation, budget arbitration, operand repacking/transposition, value precision, and persistent row-state updates. Arithmetic reuse does not eliminate these dataflow costs.

### 12. Prove output ordering is realizable

Added lines: L372–L375.

1. If selected work is merged or reordered, distinguish selection rank, physical execution order, and output slot. Define their mapping instead of deriving logical position from completion order.

### 13. Define reset

Added lines: L381–L385.

1. When metadata or operands are reusable, distinguish compute reset/abort, selected-bank prepare, result release, and full invalidation. Define which contents and readiness bits survive each declared event, including partial metadata updates and starts before all required metadata is valid. Do not add controls absent from the request.

### 15. Define acceptance criteria

Added lines: L412–L419.

1. Create criteria separately for every present stage. A final-output criterion does not replace an independently observable score-stage criterion. If an internal stage has neither a contract-visible boundary nor an independently elaborable test top, record that observability gap rather than requiring undeclared monitor signals.

2. Keep behavioral/model, RTL simulation, out-of-context implementation, full-device route, board/system, and model-quality evidence as distinct acceptance scopes.

### Consistency Review Before READY

Added lines: L449–L453.

1. every multi-stage operation marks downstream stages present, absent, or deferred

2. selected-work identity survives merging/reordering and maps uniquely to output

3. mask classes and fully masked-row behavior are unambiguous

4. key and value selection identity agrees whenever a value path exists

5. completed buffers cannot be reused before the declared release event

## RTL Generator

Added: 115 lines.

### Width and Numeric Semantics

Added lines: L81–L107.

1. For staged reductions, keep operand sign, product width, mathematical accumulation, stored conversion, coefficient application, rounding, and overflow as distinct operations. Ensure every reduction element contributes exactly once. For online normalization, update maximum, denominator, and weighted-value state coherently and rescale all required prior state before consuming a dependent update.

2. For packed arithmetic, prove field isolation, signed extraction, and any carry or borrow correction over the full frozen operand and accumulation domains. A DSP attribute alone does not implement multiple independent products. Do not reuse a packing scheme for wider probability/value operands without re-establishing those invariants; keep logical lane results independent.

3. For floating-point or block/group-scaled arithmetic, implement the frozen special values, exponent range, legal alignment window, and exception propagation. Widen before taking the magnitude of the most-negative signed value. Testable RTL must make shift direction, discarded bits, ties-to-even increment, and sign restoration explicit. Carry exponent and scale metadata with the mantissa to the stored result.

4. Keep per-group partial sums separate until their declared alignment point; summing unscaled group integers and applying one scale afterward is not generally equivalent. Use range proofs to bound shifters, comparators, and carry chains only when the frozen numerical domain permits the simplification.

5. Keep score scaling and exponential-base conversion explicit even when fused into one coefficient. Apply each once, preserving the declared clipping, table domain, rounding, and output units rather than copying a prototype's divisor or cutoff.

### Storage and Datapath

Added lines: L127–L160.

1. For selective work, use explicit named quantities for byte address, element index, token index, tile/block/page index, lane offset, selection rank, and output slot. Perform unit conversions at reviewable boundaries. Derive identity from arrival order only when the frozen ordering makes that mapping unambiguous; otherwise carry explicit tags. When both key and value paths exist, derive them from the same frozen logical selection identity.

2. Keep selection membership, structural lane validity, tail validity, and semantic score masks distinct until their prescribed effects occur. Apply semantic exclusion before the relevant row maximum, exponential sum, and weighted-value update; handle empty/fully masked rows exactly as specified. Zero-padding an operand is insufficient when its score must be absent from normalization.

3. For selection from signed scores, preserve negative scores, deterministic ties, and the frozen duplicate policy. For a merged worklist, combine membership masks while retaining each query's original selected rank. Validate page lengths, descriptor indices, and bounds as specified; do not replace them with constants from a prototype.

4. Treat intermediate/result buffers as owned resources with contract-equivalent empty, filling, complete/readable, and released states. Count accepted writes, do not reuse an unread completed bank, and confirm memory primitive inference from synthesis rather than source attributes alone.

5. Separate bank availability, loaded/valid state, executing state, captured-result state, and consumer ownership when the contract distinguishes them. A loaded flag alone must not retrigger a completed bank. Snapshot result tags before that bank can be prepared for another descriptor; results still draining may belong to an older job even after the operand bank becomes reusable.

6. For inference-sensitive arrays, avoid unintended whole-array resets, variable-index multiwrites, or full partitioning that turns RAM into register/mux logic. Maintain the frozen read latency and read-during-write behavior. Use supplied synthesis hierarchy to verify the actual primitive and port organization.

### Pipeline and Control

Added lines: L163–L188.

1. Advance logical coordinates, selection rank, masks, buffer tag, and ownership under the same enable as their numerical payload. Represent invalid or excluded work explicitly; a valid zero result must not be mistaken for masked work. Any timing pipeline change must delay data, valid, identity, mask, and ownership together.

2. Latch descriptor and mask changes on the relevant acceptance event. Emit first/last, end-of-group, end-of-page, and end-of-job markers from the logical schedule; row skew or pipeline bubbles must not turn them into raw cycle-count markers. Shared exponent or lookup logic requires a proven access schedule and matching delay for every lane.

3. For a producer with several results in flight, gate launches using available capacity or stall every affected pipeline stage coherently. An output holding register alone is insufficient if later results can still overwrite it. Handle simultaneous enqueue/dequeue and completion/next-start without losing ownership.

4. When configuration can overlap computation, keep pending-map updates independent of the active execution state. Promote a new map only at the frozen retirement boundary, and hold each lane's source assignment until its reduction completes. Stop issuing a context after its accepted last operand even if another context has a longer reduction. Capture completion data before exposing completion to a consumer.

5. For paged/queued execution, retain the original selected mask and identity across passes. A position deferred to a later pass must not become a masked result. Follow the specified operand replay order, empty-context completion, and per-pass admission rules; grouped routers and their descriptor packers must enforce the same context rule.

### Interface Protocol

Added lines: L212–L220.

1. When a new consumer adds another readiness term, use the complete handshake at the joined boundary for counters and retirement. For paired operand writes, advance the source only when the frozen atomic-pair rule is satisfied; do not let Q-side and K-side progress diverge through independent stalls.

2. For memory bursts, derive accepted-beat counts and last markers from the same transaction state. Keep burst completion, logical tile completion, and job completion distinct across segmentation, tail strobes, stalls, and repeated launches.

### Reset and Error Behavior

Added lines: L223–L227.

1. Apply the distinct frozen effects of compute reset, abort, bank preparation, result release, and full clear. Invalidate stale in-flight results and completion state, while retaining reusable metadata or operands only when the contract requires it. Check reset wiring through every nested controller/serializer, not only the top FSM.

### PPA Optimization

Added lines: L250–L255.

1. Implement only the authorized structural change. A shared lookup, local control register, RAM mapping change, or predecoded address decision must retain its full metadata and lifecycle behavior. HLS resource reports may inform a plan for imported logic, but they do not authorize this role to emit C/HLS or edit build/firmware files outside the RTL ownership boundary.

### Self-Review Before RTL_GENERATED

Added lines: L269–L276.

1. stage omission, duplication, or reordering

2. query/key index or transpose reversal

3. token/tile/block/page/byte unit confusion

4. numerical payload and identity/mask pipeline skew

5. selection rank confused with physical completion order

6. valid zero results discarded as invalid work

7. key/value identity mismatch after reordering or tails

8. buffer completion based on issued rather than committed work

## Verifier

Added: 144 lines.

### 2. Build an independent reference model

Added lines: L67–L97.

1. For a multi-stage datapath, model each present stage independently: work selection, QK or equivalent score reduction, score conversion, masking, normalization, weighted-value accumulation, and final conversion. Preserve expected intermediates for diagnosis even when only the final output is externally visible. Keep a bit-accurate hardware model separate from any higher-precision quality model.

2. For group-scaled or floating-point inputs, prefer exact integer/rational decoding for the arithmetic reference where practical. Verify that a host floating-point intermediate has enough range and precision before using it as an exact oracle. Decode a stored mantissa-plus-exponent pair independently, including scale units, guard bits, per-contribution rounding, and final conversion.

3. Where arithmetic lanes are packed, compute expected logical products/reductions independently rather than reproducing the packed extraction formula. Vary one lane while holding its neighbor fixed, including opposite signs and representable extrema, to expose cross-field carry/borrow contamination at the available observation boundary.

4. For approximated exponential/normalization paths, distinguish the frozen bit-accurate mapping from the mathematical target. Check score-scale units and any natural/base-2 conversion independently, including zero argument, table/segment and integer-fraction boundaries, clipping boundaries, and small weights lost during conversion when applicable. Keep the approved numerical tolerance fixed; agreement with the same approximation does not establish its error against the mathematical target. Use mathematical error as an acceptance check only when the frozen criteria define it; otherwise report characterization without inventing a tolerance.

5. Use analytically known small examples to distinguish normalizing each selected tile independently from carrying one row maximum, denominator, and weighted-value numerator across all selected tiles. Include a later tile that changes the maximum and a case where failure to rescale the old value numerator produces a different final output.

### 3. Build protocol-aware cocotb tests

Added lines: L100–L111.

1. Test the earliest frozen observation boundary directly. A full-pipeline test does not replace an independently exposed score-stage test. If an internal stage has no declared interface or independent test top, use discriminating end-to-end or metamorphic cases and record an observability gap; do not invent hierarchical monitors or claim nonexistent assertions.

2. Identify which checks are externally observable and which only validate the reference/stimulus. Several semantic categories may be checked by one numerical scoreboard; do not inflate assertion counts to imply separate internal checkers. Use independent submodule test tops only when the frozen verification setup exposes them. Do not alter contracts to obtain additional observation points.

### 4. Cover the contract, not a benchmark template

Added lines: L127–L129, L173–L246.

1. Every named assertion must correspond to executable checker logic. Evidence labels, plan items, and coverage names do not become assertions merely by being named.

2. For selective or Q/K/V-style datapaths, include applicable cases for:

    1. one-hot/index-revealing operands and every reduction group contributing once

    2. exact positive and negative conversion, rounding, overflow, or saturation boundaries

    3. first/interior/last selected indices, ties, duplicates, overlap, reordering, and tails

    4. byte/element/token/tile/block/page address-unit conversions

    5. structural, padding, selection, causal/window, and additive masks independently

    6. a valid zero result, fully masked rows, and positions just inside/outside mask boundaries

    7. lower/equal/higher new row maxima, old-state rescaling, and consecutive rows/jobs

    8. key/value identity after selection, deduplication, reordering, and tail handling

    9. completed-buffer hold, readback, release, and reuse

3. Check both numerical result and logical destination, including no missing, duplicate, or unexpected writes. For fixed selection, or paired cases where the reference confirms the selected set is unchanged, changing excluded operands must not affect output. With data-dependent selection, recompute selection and metadata before applying that property. Use index-encoded value data to expose key/value mismatches.

4. In integrated bounds-based selection tests, derive bounds from the actual key data and use the same logical queries in selection and score computation. Derive expected selected outputs from the original logical tensor, not a host-compacted or DUT-selected operand list. Independent unit tests may isolate these components, but their separate passes do not prove that they operate on coherent data together.

5. Where the frozen arithmetic supports them, also exercise:

    1. signed zero, normal/subnormal transitions, NaN/infinity, underflow, exception flags, ties-to-even, large exponent differences, and unequal-magnitude cancellation

    2. where an approximation/error criterion exists, outliers and wide dynamic ranges that expose shared-scale loss; check score error and selection/rank agreement separately

    3. group-boundary first/last markers, bubbles between groups, maximum legal shift, a partial metadata update, and unchanged metadata reused with different operands

    4. all-negative selection scores, fewer candidates than the selection budget, deterministic ties, invalid bounds, and per-query selections whose union exceeds that budget

    5. local versus absolute row coordinates, shuffled merged-page execution, and rank remaining attached to the correct storage slot

    6. concurrent paired operand loading, forbidden active-bank writes, at least three buffer uses to exercise wraparound, and stale loaded-state duplicate prevention

    7. abort during partial work, compute reset preserving metadata, full clear invalidating it, and release while a read response is pending when legal

    8. zero, partial, exact-capacity, and over-capacity selections under the frozen rejection/queue/pagination policy; when passes partition selected positions, prove disjoint membership whose union equals the original selected set, including residual and empty contexts; reduction-chunk passes may revisit an output, so check their declared contribution coverage rather than requiring disjoint output positions

    9. unequal context lengths with background configuration, immutable active mappings, activation at the declared promotion event, preservation of outstanding result tags during any permitted early reuse, and packer/router group-context compatibility

    10. transfers just below, at, and above a declared burst limit, with stalls, final-beat markers, tail strobes where applicable, and restart at a distinct address

6. Compare invalid or masked numeric payload only when the contract defines it; still check the meaningful valid/mask, coordinate, completion, and exception behavior. Drive each pass using its required active contexts and lengths rather than an inactive context's longer reduction. Observe completion continuously as required by the declared pulse or handshake protocol.

7. Derive expected counts from the frozen index set for each transaction. Descriptor counts, discarded outputs, and stalls from one overlap pattern are not universal constants. Enumerate clipped windows and tail lanes independently of the driver. Check zero-filled padded operands separately from semantic exclusion: a zero key still produces a score and may affect a denominator unless excluded by the contract.

8. Track expected destinations with an independent set/bitmap or equivalent scoreboard. Completion is valid only when required accepted outputs or committed writes are complete. Snapshot per-group counts at the defining event; a delayed done pulse may occur after the next group has already changed cumulative counters.

9. For a frozen overlap/throughput criterion, observe startup, steady state, and final drain separately. Measure accepted-tile intervals, producer/consumer active overlap, wait cycles, and buffer releases under both ideal feed and declared stalls. Equal steady-state throughput does not imply equal final-tail latency.

### 5. Randomized regression

Added lines: L251–L266.

1. A constraint solver proves the encoded constraints, not that the encoding matches the contract. Keep unbounded mathematical reduction state separate from converted, wrapped, clipped, or saturated hardware state. Re-evaluate every solver-generated directed case with an independent concrete helper and assert that it reaches the named bin before driving the DUT.

2. Report achieved functional bins in addition to random transaction counts. Sample coverage from validated stimulus or observed transactions, and distinguish unreachable bins from bins that were simply not hit.

3. Cover useful functional crosses within the supplied coverage plan and legal configuration, such as sign/boundary, selection/tail position, mask/boundary, stall/ownership, reset/pending result, and old/new maximum relation. Keep local functional bins separate from tool-owned obligation IDs; never invent new IDs to claim unsupported runtime coverage. Record seeds and meaningful unmet bins.

### 7. Verification plan

Added lines: L279–L286.

1. Report selection, score, transform/mask, normalization/value, and lifecycle status separately with the deterministic evidence supporting each claim.

2. State whether a suite targets an arithmetic primitive, complete operator, or system wrapper. Where supplied build metadata selects the test entrypoint, confirm that it invokes the intended suite; a packed-multiply unit test cannot establish coverage of a newly assembled normalization/value operator.

## Debugger

Added: 117 lines.

### 1. Establish the first authoritative failure

Added lines: L50–L61.

1. Classify both the failing layer and the earliest implicated functional stage. Layers include tool/build, generated source, testbench scheduling, stimulus generation, reference model, RTL protocol/control, RTL arithmetic, storage/ownership, and physical implementation. Functional stages include applicable selection, score reduction, conversion, masking, normalization, weighted-value accumulation, writeback, and retirement/reset.

2. Tie source, simulator result, routed checkpoint, constraints, and reported clock to the same candidate. A passing implementation may use different RTL from the current working copy; contradictory history must be resolved by artifact identity and actual tool outputs, not by choosing the most favorable summary.

### 3. Classify narrowly

Added lines: L83–L91.

1. For solver-generated directed tests, distinguish solver failure, incorrect constraint encoding, wrong stimulus classification, and a valid stimulus exposing an RTL defect. A satisfiable model proves only the encoded constraints. Recompute the target predicate concretely before attributing the failure to RTL; mathematical and converted accumulator states must not share one symbolic variable.

2. Do not label an incorrect arithmetic encoding as a solver implementation bug. Treat SAT/UNSAT as evidence about the actual formula and inspect that formula first.

### 4. Locate the causal implementation defect

Added lines: L102–L143.

1. Use these multi-stage signatures only as hypotheses to confirm:

    1. correct value at wrong location -> tag delay, selection-rank mapping, or address unit

    2. missing zero results -> validity incorrectly encoded by numerical value

    3. failures only at mask edges -> coordinate, inclusivity, polarity, or stage order

    4. correct score but wrong normalized output -> conversion/mask order or row state

    5. failure only when a new maximum appears -> prior denominator/value state not rescaled

    6. plausible output from the wrong value item -> key/value identity divergence

    7. later jobs fail after the first -> stale state, ownership, release, or reset

    8. timing repair changes function -> numerical and metadata pipeline skew

2. For selection/address defects, trace logical token through tile/block/page, beat/lane, byte address, physical execution order, and output slot. Diagnose masks by mask class and required effect rather than by signal name.

3. For scaled arithmetic, first decode mantissa, exponent/base, guard bits, rounding, and alignment distance. An integer difference equal to a scale factor can be a reference-unit error. A partial exponent update may leave the base outside the legal alignment window; establish stimulus legality before repairing metadata reuse.

4. For completion failures, compare the final handshake, result capture, ownership update, done pulse, and next accepted transaction cycle by cycle. Two distinct causes require different repairs: RTL may expose done before the payload is captured, or a monitor may check exact counters after a legal next transaction has begun. Expand combined assertions so every failing predicate is visible.

5. If all expected outputs exist but a test times out, inspect whether the driver overran an inactive pass/context or began waiting after a one-cycle done pulse. For a changed legal schedule, distinguish a stale watchdog bound from a real liveness failure; preserve the exact contractual latency check when correcting it.

6. For reset failures, trace every affected state owner. Compute abort may preserve operand/scale metadata while full clear invalidates it; both still have to remove in-flight completion. Check nested serializer and accumulator reset wiring before rewriting the scheduler. An occupied completed-result buffer may correctly keep job-ready low after compute-busy drops.

7. For resource/timing failures, distinguish arithmetic depth, control fanout, muxing, failed RAM inference, and actual routing congestion. A large register count with missing RAM primitives suggests an inference problem even when simulation passes. Positive setup slack with failing hold or unresolved routes is incomplete evidence.

### 5. Treat the approved TB as the executable answer sheet

Added lines: L150–L155.

1. For generated tests, inspect source-generation errors before any DUT diagnosis. Missing declarations, reserved identifiers, inconsistent timescales, brittle text replacement counts, or a monitor that omits a new downstream-ready term belong to the harness when the contract-based evidence establishes that cause. Preserve the failing case and use the existing verification-repair route rather than weakening it.

### 8. Repair history awareness

Added lines: L175–L179.

1. Record why an attempted register boundary, one-hot rewrite, extra lane count, or resource-sharing change was insufficient. Reinspect the new critical path after each candidate; it may move to a different subsystem. A reduction in negative slack is useful evidence but does not establish closure.

### Required Diagnosis Content

Added lines: L198–L200, L203–L206.

1. exact preconditions and investigation sequence

2. disproved alternatives and failed or insufficient prior directions

3. applicability boundary for reusing the same repair concept

4. Place the additional diagnostic narrative inside supported output-schema fields; do not introduce new routing statuses or required JSON keys. Explain the case self-containedly rather than requiring a source chat or contributor identity.

### Repair Constraints

Added lines: L217–L221.

1. Reverification must include the smallest reproducer, all corrected-stage tests, adjacent upstream/downstream stage tests, affected protocol/reset/ownership tests, and full regression. Pipeline, memory, arithmetic-width, or scheduling changes also invalidate prior synthesis and timing evidence.

### Forbidden Actions

Added lines: L229–L233.

1. treating a failed directed-stimulus generator as an RTL arithmetic failure

2. encoding invalid or excluded work as zero when zero is a legal result

3. pipelining numerical data without matching identity, mask, valid, and ownership

4. deriving logical output slots from arrival order without a frozen ordering guarantee

5. increasing timeouts or weakening clock constraints to hide the observed failure

### Bounded diagnostic evidence

Added lines: L254–L279.

1. For a failure before RTL execution or inside the implementation tool, request the exact binary/version, phase, invocation, environment, and clean build-log evidence. Separate simulator startup, Tcl option parsing, timing-report parsing, and optimizer crashes from DUT failures. A successful test followed by a tool process that does not exit is also a different failure from a timed-out DUT test.

2. Compare simulator-wrapper exit status with fatal/assertion diagnostics and actual suite completion. A successful process exit or compile banner alone is not a test pass. Report conflicting status/log evidence through the existing infrastructure route; do not weaken the failing numerical tolerance or edit the runner to hide it.

3. Any proposed tool workaround must be bounded to the demonstrated failing pass and validated by the remaining normal checks. It does not authorize RTL, constraints, or tool-script edits by the Debugger. A quiet live implementation log alone is not evidence for an RTL repair; request progress and process-status evidence as needed.

4. Check the effective generated script and unique report directory for each candidate; a saved source edit may not be the script actually executed, and reused report paths can overwrite the comparison baseline. Before a retry, establish whether an earlier tool process still owns the build directory; request an isolated run when needed.

5. For platform integration, verify that the packaged IP, register map, bank wiring, firmware executable, and image belong to the same build. Editing firmware source does not update a packaged executable automatically. Treat timing-parser format changes as parser issues: missing/unknown metrics are not zero or a timing pass.

## PPA Optimizer

Added: 133 lines.

### Bottleneck Localization

New heading. Added lines: L14–L35.

1. Tie every proposal to the exact top, clock, implementation stage, path endpoints, resource hierarchy and verified RTL version. Classify the measured cause as arithmetic/reduction depth, selection or address logic, high-fanout control, wide mux/routing, memory inference or port pressure, buffer/backpressure fanout, normalization/division logic, or insufficient contract-legal stage overlap.

2. Separate logic delay from route delay. Inspect control-set, fanout, hierarchy, memory primitive and operator counts before blaming the MAC array. Scaling a small tile can make control distribution or exponent formatting dominate even when arithmetic maps efficiently to DSPs.

3. Do not transfer a conclusion between out-of-context and full-device runs or between different tops, constraints, arithmetic profiles, dimensions, or included stages.

4. Bind every observation to its source/checkpoint and evidence_manifest_sha256. A passing route for an older reader or datapath does not establish that a newer source variant passes. Check unconstrained paths, placement containment, setup, hold, and requested versus selected clock before ranking a physical candidate. Changing a minimum I/O delay is diagnostic unless the real integration timing justifies it.

### Contract-Preserving Transformations

New heading. Added lines: L36–L98.

1. When supported by reports, consider:

    1. balancing or pipelining reduction and compare trees

    2. registering/localizing high-fanout control with identical metadata delay

    3. replacing long priority/union chains with bounded trees, staged logic, or one-hot forms when semantics permit

    4. changing memory coding, banking, or shape to obtain intended primitives while preserving capacity, ports, latency, and ordering

    5. removing accidental array partitioning or operator replication

    6. sharing expensive normalization/division hardware when service rate remains legal

    7. replicating a resource only when it is the measured throughput bottleneck

    8. adding elastic/ping-pong buffering or producer/consumer overlap only when already permitted by the frozen ownership and schedule contract

    9. reducing widths only from frozen numerical range evidence

2. Apply these transformations conditionally:

    1. For cascaded ranking comparisons, compute independent comparisons in parallel before the local rank update; preserve negative-score and tie semantics.

    2. For associative selection/union, test a short shift-register FIFO or parallel compare with fixed per-entry enables when pointer muxes and variable-index writes are measured bottlenecks. Preserve simultaneous enqueue/dequeue and membership.

    3. For regular skewed metadata access, share one lookup and delay its output per lane only after proving the access sequence. A broad one-hot rewrite can add wide OR networks and increase LUTs; retain ordinary muxing when it measures better.

    4. For multi-PE control fanout, consider local control registers or narrowly scoped preservation of registers the synthesizer merged. Avoid blanket hierarchy/keep constraints without evidence; remeasure reset and enable distribution after scale-up.

    5. For exponent conversion, split exponent arithmetic, alignment, rounding, and accumulation at legal boundaries. Bound shifts and carry widths from the numerical contract. Simplifying a general formatter is valid only when the full legal domain and rounding behavior remain covered.

    6. For packed multiplier paths, consider hoisting repeated operand packing out of replicated cells when width, timing, and enable alignment permit it. Preserve signed field extraction and carry/borrow correction; a DSP attribute is not a packing transformation. Count logical MAC lanes separately from physical DSPs.

    7. For exponential/reciprocal approximation, compare lookup, arithmetic, or piecewise implementations under the same input domain and error bound when the contract allows alternatives. Include table access ports, replication, service interval, and integrated routing; a fastest standalone function may not improve the kernel.

    8. For per-row state mux/congestion, consider banked RAM and a registered read/compute boundary. Recheck read latency, same-row dependencies, rescale state, and port conflicts.

    9. For a scheduler choice feeding a wide address addition, predecode/register the choice if allowed rather than changing a verified compute array.

    10. For HLS-derived modules, use operator/loop/partition reports to distinguish intended lane parallelism from accidental divider or full-array replication. Recommend only changes that fit the authorized implementation language and artifact ownership.

    11. For mask compaction followed by operand routing, consider registered assignments prepared once per work batch instead of a per-cycle mask-to-lane-to-MAC network. Keep active mappings stable and overlap pending configuration only when permitted.

    12. For expensive independent context muxes, consider sharing context selection across lane groups when the contract permits that scheduling restriction. Evaluate the matching packer and retained context storage with the router, not as independent wins.

    13. Remove forced-zero output muxes or operand gating only when the frozen invalid-data semantics permit it and masks/flags/handshakes remain correct. Reduced area does not by itself demonstrate lower switching power or higher useful throughput.

3. Any pipeline or overlap plan must name the data, valid, identity, mask, ownership, completion and reset paths that move with it. Do not improve timing by weakening the clock constraint or by silently reducing required throughput.

### Throughput and Storage Tradeoffs

New heading. Added lines: L99–L126.

1. Budget operand loading, MAC feed/fill/flush, array drain, score transfer, normalization, weighted-value accumulation, and buffer release. Size consumer parallelism against the actual score delivery and bank-reuse deadline. Increasing normalization lanes beyond the slowest stage may improve only final-tail latency; report that separately from steady-state throughput.

2. Require full producer/consumer integration evidence after ideal-source unit experiments. The requested evaluation should cover startup, repeated bank reuse, final drain, stall cycles, tile-accept intervals, and downstream state dependencies. Buffer capacity alone does not establish enough read/write ports or service bandwidth.

3. Separate the fraction of cycles doing useful compute from lane occupancy during those cycles. Use measured setup/activation/drain states to locate overhead rather than assuming poor utilization requires a larger MAC array. Compare bounded resident context windows; a global sorting model may assume storage the hardware does not have. Keep the workload's reduction-length distribution fixed when comparing schedulers. Length-sorting gains on synthetic mixed-length dots may disappear for a fixed per-head reduction length; do not attribute that workload difference to the scheduler.

4. Distinguish smaller host-packed input, fewer device-memory read requests, and measured bus traffic. A compact input layout can reduce upload size while leaving rereads unchanged. Include gather/repacking, replica storage/update cost, selection overhead, and masked-but-executed work in the relevant comparison. Changes to the selection policy, precision, supported dimensions, or compute organization require a new architectural decision when they are frozen.

### Candidate Validation

New heading. Added lines: L127–L128, L136–L153.

1. Use one primary optimization hypothesis per candidate. Compare every candidate with the previous verified version and the best verified version using the same tool flow, top, device and constraints. Require WNS, TNS, failing endpoints, hold, routing, resource, latency/throughput, and actual memory/operator inference evidence. Reject any candidate that loses functional verification, violates a hard constraint, or trades away required behavior; do not accept it because one metric improved.

2. Preserve negative results and remaining bottlenecks. A serial mapper may save area while losing setup throughput; a wider normalizer may close in isolation while hurting integrated routing. Recommend only report-supported changes for the fixed objective and budget; the orchestrator selects candidates. Return STOP when no supported improvement remains.

3. For shared regular metadata/alignment work, require a proof that simultaneous requests cannot collide, or include the legal arbitration/queue cost. Model-level scheduling gains and unit-level resource savings remain hypotheses until the compatible scheduler, router, compute, and completion path are evaluated together.

## PPA Judge

Added: 38 lines.

### Required Input Metrics

Added lines: L51–L68.

1. Bind metrics to the exact RTL/source version, build/checkpoint, top, device, clock constraints, and selected packaged-image frequency. Distinguish kernel hierarchy from platform-shell/full-device resources, and unconstrained OOC from region-contained OOC, full-device route, and board results. A board numerical pass at an auto-scaled clock does not establish the requested frequency.

2. For a multi-stage operator, collect the included stage set, accepted tile interval, startup/final drain, stall counts, and buffer-release interval when measured. A MAC clock or ideal unit-level feed is insufficient to establish integrated throughput.

3. State whether operand/metadata preload, repacking, and transfers are included or amortized. A warm selector latency that excludes bounds-cache loading is not a cold end-to-end query latency.

4. An unparsed/missing timing or clock metric remains unknown. Require the actual supported report/image format to be decoded before accepting a result; never let a parser miss produce a default zero slack or silently reuse an older success marker.

### Evidence-Driven Optimization Examples

Added lines: L93–L97.

1. Treat local lookup sharing, one-hot selection, memory banking, control replication, operator sharing, and lane-count changes as measured candidates rather than universal improvements. Check that each fixes the actual critical path or service bottleneck; preserve negative experiments and area/latency tradeoffs in the comparison.

### Comparing Iterations

Added lines: L146–L155.

1. Check setup and hold, total negative slack and failing endpoints, route completion, intended primitive inference, and any required placement scope together. Do not rank an unconstrained route against an integrated design as if the runs were equivalent.

2. For claimed sparse/selected-work throughput, state selected-pair density, useful operations, executed operations, MAC-counting convention, precision, and stages included in elapsed time. Report dense-equivalent throughput separately. Distinguish simulation cycles, board execution cycles, launch-to-completion, and transfer-inclusive time; do not label a co-simulation estimate as a board measurement.

### Final Judge Report

Added lines: L187–L191.

1. Include any gap between requested and selected clock, between nominal and actually tested stages/shapes, and between computed memory-request bytes and measured traffic. If evidence summaries disagree, resolve the exact artifact/version instead of promoting the strongest historical claim to the current design.

## Project Contract

Added: 0 lines.

No additions; identical to the baseline.

## Scope

Total additions: 719 lines. No baseline text was deleted or replaced.

No corresponding updated file: `experiment_evaluator/SKILL.md`.
