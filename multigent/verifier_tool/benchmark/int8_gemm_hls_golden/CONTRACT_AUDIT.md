# Frozen contract audit against the real HLS RTL

This audit precedes generated-TB qualification. It compares the hand-authored
`architecture_contract.yaml` and `interface_contract.yaml` with
`gemm_golden/int8_gemm.v`, `int8_gemm_control_s_axi.v`, the three
`int8_gemm_gmem_*_m_axi.v` files, and the HLS C++ source. Passing schema
validation alone is **not** evidence that the contract describes the RTL.

| Contract claim | RTL/source evidence | Result |
| --- | --- | --- |
| Fixed signed INT8 GEMM, M=32, K=64, N=128, INT32 output | `gemm_hls/int8_gemm.cpp` and the fixed HLS wrapper | Matched; the packed A/B encodings and row-major C remain subject to end-to-end generated-TB comparison. |
| Job starts through AXI4-Lite registers, not a top-level command pin | `int8_gemm_control_s_axi.v`: A/B/C low/high registers at 0x10/14, 0x1c/20, 0x28/2c; control bits `ap_start=0`, `ap_done=1` | Matched. The lifecycle policy must use `control_plane_sequence`, not a ready/valid command. |
| Repeated `ap_ctrl_chain` jobs | Control bit 4 drives `int_ap_continue`; the top-level `ap_done_reg` clears only when `ap_continue` is asserted | **Corrected:** the contract now writes `ap_continue` before each next job's pointer programming/start. Without it, a stale done can make later jobs incorrect or hang. |
| Three active AXI4 memory paths | gmem_a/b read, gmem_c write; manager RTL has AXI4 LEN/SIZE/BURST/LAST/ID signals | Matched for active traffic. The top-level also physically exposes unused directions on each port; they are intentionally not modeled as active data-object paths. |
| AXI4 manager capability bins | The HLS wrappers tie AxBURST to INCR, AxSIZE to 64-byte full width, AxID to zero; the wrapper instantiates 16 read-outstanding slots. The 4-KiB burst converter can split the fixed 32/64-word job into short bursts when the legal base pointer is page-offset. | **Corrected:** only attainable type/size/alignment/ID bins are required, but **all three burst-length bins remain required**. Protocol assertions still check illegal encodings if a mutant emits them. |
| AXI4 gmem_c AW/W ordering | The wrapper can present AW and W together; the earlier generated run observed `same_cycle` | **Corrected:** `same_cycle` and `address_first` are admitted, not only `address_first`. Both remain required until an independently driven campaign proves them. |
| AXI4-Lite control write ordering and depth | The control write FSM accepts AW in `WRIDLE`, W later in `WRDATA`, B in `WRRESP`; the read FSM is independent | **Corrected:** required write-order bin is `address_first`. One read and one write may be outstanding simultaneously, so the combined `multiple` depth bin remains required. Sparse/zero WSTRB and unaligned address behavior were **not** silently removed from coverage; they need dedicated legal stimulus or further contract evidence. |
| Reset timing | Top-level reset passes through `ap_rst_reg_2`, `ap_rst_reg_1`, then `ap_rst_n_inv` | The contract declares four settle cycles for reset-time output checks. |
| AXI4-Lite `RDATA` during reset | Control RTL assigns `RDATA = rdata`; `rdata` is updated on reads but has no reset assignment | **Corrected:** no reset value is asserted for `RDATA`. The bus data is checked on accepted read responses, not while `RVALID=0` in reset. |
| Busy/error/illegal-command status | No top-level busy/error pins or opcode command channel exist | The generic lifecycle policy fields are mandatory vocabulary, but their named status/illegal-command claims are **not qualified for this HLS design** merely by schema acceptance. Only observable control-plane behavior may receive benchmark credit. |

After these corrections, the normal generated plan has 77 obligations and 137
required bins. The original HLS RTL now passes that generated TB with 137/137
bins, no assertion failures, and a PASS stimulus ledger with 20 entries
(`/private/tmp/hls_generated_qualification_20260926_v15/original/`). The
earlier accepted B-memory reconstruction failure was a capture-adapter
grouping defect: separate AXI4 memory groups had been read as one stream.
This positive baseline does **not** qualify every individual checker or bin;
the paired named-mutant results are tracked only in
`../../HLS_GOLDEN_BENCHMARK_MATRIX.md`.
