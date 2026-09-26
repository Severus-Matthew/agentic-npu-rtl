# Executable extension-TB audit fixture

This fixture is the semantic counterpart to the structural request/bundle
matrix in `test_extension_scenario_matrix_additional.py`. It exists because a
schema-valid extension bundle is not evidence that its testbench is useful.

`extension_reference_dut.sv` exposes small, observable implementations for the
exact behavior under test. `test_extension_reference_tb.py` contains fifteen
cocotb cases. Every case has three bundle-shaped functions:

- `stimulate_case_N`: drives real simulator ports and returns accepted/observed
  evidence;
- `assert_case_N`: checks that evidence against an independent expected result
  or temporal rule;
- `cover_case_N`: classifies bins from observed evidence rather than declaring
  a hit because a scenario was planned.

Every test also corrupts one evidence field and requires the assertion function
to reject it. This negative control catches a checker that merely allows its
stimulus to run.

| Case | Directed stimulus | Assertion | Observed coverage |
|---|---|---|---|
| 11 | Runtime `M={1,2,4}` for signed `A[M,2] * B[2,1]` | Every valid row equals its two-term dot product; the DUT valid mask exposes exactly M rows | minimum/interior/maximum shape |
| 12 | Two nonadjacent signed sparse `(index,value)` entries | Indexed sparse dot product equals the observed result | nonadjacent indices and signed values |
| 13 | Signed three-sample/three-tap convolution | All three products are accumulated exactly once | three-tap and mixed-sign products |
| 14 | Exact two-token sparse linear attention with two mask patterns | Masked/negative scores have zero weight; integer weighted result matches | both active and one masked |
| 15 | Wishbone Classic `CYC/STB` held through three wait states | ACK is bounded and request address/data remain stable | wait state and bounded response |
| 16 | Two TileLink A requests with sources 2 and 9 | Reversed D responses preserve source/data correlation | reordering and distinct IDs |
| 17 | Avalon-MM read with `BURSTCOUNT=8` and wait states | Exactly eight ordered OK response beats arrive | multibeat burst and wait state |
| 18 | Avalon-ST final partial beat, output stalled for three cycles | DATA/SOP/EOP/EMPTY remain stable until transfer | partial final beat and stall stability |
| 19 | Four-phase request/ack sequence | `(0,0) -> (1,1) -> (0,0)` | request phase and return to zero |
| 20 | Cancel an active job | Busy drains for two cycles, clears, and never completes | cancel while active and drain/abort |
| 21 | Sticky completion followed by software ACK | Completion remains high until ACK and then clears | sticky level and software clear |
| 22 | Distinct job IDs for one active plus one queued job | Exactly two jobs are accepted and their completion IDs retire in acceptance order | queue depth two and both ordered retirements |
| 23 | Checkpoint reset plus sticky software-cleared error | Busy survives reset, the preserved job resumes to completion, and error survives until ACK | checkpoint preservation and error recovery |
| 24 | Known signed GEMM and extension-owned attention together | Each result uses its own oracle; corrupting attention cannot affect GEMM | known/extension sibling isolation |
| 25 | Rounded GEMM, retry-then-success response with epoch 3, sticky completion | Formula, retry budget, epoch preservation, and ACK clearing all hold | arithmetic/protocol/lifecycle bins independently |

## Review findings that changed the TB

The first real simulator run passed 11 of 15 cases. Direct source and timing
review found four testbench defects rather than feature failures:

1. The request helper checked READY after the active edge. A legal receiver had
   already lowered READY after accepting the second request. It now snapshots
   VALID/READY before the edge and commits that accepted snapshot at the edge.
2. The response helper started observing one edge too late and could miss a
   one-cycle response consumed immediately by READY. It now samples response
   content in the stable pre-edge phase.
3. The cancellation test began its trace after both drain cycles and therefore
   observed only idle. It now records from the accepted cancel event.
4. The queue test presented the second command on the first job's retirement
   edge, creating an ambiguous reference-DUT scheduling race. It now presents
   the second command earlier and observes both independent completion events.

The operation review also replaced a scalar value artificially multiplied by M
with a real variable-row matrix product, and replaced a masked dot-product
fragment with a complete, explicitly frozen two-token sparse linear-attention
equation. Protocol cases now use Wishbone, TileLink A/D, Avalon-MM, and
Avalon-ST field-level handshakes instead of one generic request/response proxy.

A later line-by-line semantic audit found additional false-confidence gaps that
did not cause simulation failures: runtime shape was only slicing a Python
list, queued jobs had no observable identity, checkpoint reset did not prove
the job resumed to completion, and case 24 used a different attention equation
from its frozen request. The fixture now observes a DUT result-valid mask,
completion IDs, post-reset retirement, and the exact shared two-token attention
equation. It also checks Wishbone error status, Avalon-ST consumption, and one
negative control per domain in the mixed case.

These are focused reference implementations of the extension behavior, not a
claim that this small DUT implements every rule in the corresponding standard.
The existing protocol pool remains responsible for standard baseline rules;
the contract-local TB owns only the explicitly missing behavior.
