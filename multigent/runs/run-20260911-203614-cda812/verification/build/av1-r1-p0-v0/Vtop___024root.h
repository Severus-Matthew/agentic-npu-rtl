// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtop.h for the primary calling header

#ifndef VERILATED_VTOP___024ROOT_H_
#define VERILATED_VTOP___024ROOT_H_  // guard

#include "verilated.h"


class Vtop__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtop___024root final {
  public:

    // DESIGN SPECIFIC STATE
    // Anonymous structures to workaround compiler member-count bugs
    struct {
        VL_IN8(clk,0,0);
        VL_IN8(rst_n,0,0);
        VL_IN8(cmd_valid,0,0);
        VL_OUT8(cmd_ready,0,0);
        VL_IN8(vec_valid,0,0);
        VL_OUT8(vec_ready,0,0);
        VL_IN8(vec_data,7,0);
        VL_IN8(mat_valid,0,0);
        VL_OUT8(mat_ready,0,0);
        VL_IN8(bias_valid,0,0);
        VL_OUT8(bias_ready,0,0);
        VL_OUT8(out_valid,0,0);
        VL_IN8(out_ready,0,0);
        VL_OUT8(status_busy,0,0);
        VL_OUT8(status_error,0,0);
        CData/*0:0*/ mv_npu_top__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__cmd_valid;
        CData/*0:0*/ mv_npu_top__DOT__cmd_ready;
        CData/*0:0*/ mv_npu_top__DOT__vec_valid;
        CData/*0:0*/ mv_npu_top__DOT__vec_ready;
        CData/*7:0*/ mv_npu_top__DOT__vec_data;
        CData/*0:0*/ mv_npu_top__DOT__mat_valid;
        CData/*0:0*/ mv_npu_top__DOT__mat_ready;
        CData/*0:0*/ mv_npu_top__DOT__bias_valid;
        CData/*0:0*/ mv_npu_top__DOT__bias_ready;
        CData/*0:0*/ mv_npu_top__DOT__out_valid;
        CData/*0:0*/ mv_npu_top__DOT__out_ready;
        CData/*0:0*/ mv_npu_top__DOT__status_busy;
        CData/*0:0*/ mv_npu_top__DOT__status_error;
        CData/*0:0*/ mv_npu_top__DOT__cfg_bias_en;
        CData/*0:0*/ mv_npu_top__DOT__cfg_relu_en;
        CData/*0:0*/ mv_npu_top__DOT__state_compute_en;
        CData/*0:0*/ mv_npu_top__DOT__cmd_accept;
        CData/*0:0*/ mv_npu_top__DOT__vec_xfer;
        CData/*0:0*/ mv_npu_top__DOT__mat_xfer;
        CData/*0:0*/ mv_npu_top__DOT__bias_xfer;
        CData/*0:0*/ mv_npu_top__DOT__out_xfer;
        CData/*7:0*/ mv_npu_top__DOT__vec_wr_addr;
        CData/*7:0*/ mv_npu_top__DOT__rd_chunk_base;
        CData/*0:0*/ mv_npu_top__DOT__compute_en_core;
        CData/*0:0*/ mv_npu_top__DOT__new_row_core;
        CData/*0:0*/ mv_npu_top__DOT__row_done_pulse;
        CData/*0:0*/ mv_npu_top__DOT__pp_in_valid;
        CData/*0:0*/ mv_npu_top__DOT__pp_in_ready;
        CData/*0:0*/ mv_npu_top__DOT__pp_bias_valid;
        CData/*0:0*/ mv_npu_top__DOT__pp_out_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__in_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__bias_en;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__relu_en;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__bias_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__out_ready;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__out_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__in_ready;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__compute_en;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__new_row;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__row_done_pulse;
        CData/*7:0*/ mv_npu_top__DOT__u_mac__DOT__m_i;
        CData/*7:0*/ mv_npu_top__DOT__u_mac__DOT__v_i;
        CData/*0:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__clk;
    };
    struct {
        CData/*0:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__wr_en;
        CData/*7:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr;
        CData/*7:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__wr_data;
        CData/*7:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cmd_accept;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__vec_xfer;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__mat_xfer;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__bias_xfer;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__out_xfer;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__state_compute_en;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__status_busy;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__status_error;
        CData/*1:0*/ mv_npu_top__DOT__u_ctrl__DOT__st;
        CData/*4:0*/ mv_npu_top__DOT__u_ctrl__DOT__rem;
        CData/*0:0*/ __VdfgRegularize_h6e95ff9d_0_0;
        CData/*0:0*/ __VdfgRegularize_h6e95ff9d_0_1;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_post__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_vec_buffer__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        SData/*15:0*/ mv_npu_top__DOT__cfg_M;
        SData/*15:0*/ mv_npu_top__DOT__cfg_N;
        SData/*15:0*/ mv_npu_top__DOT__lane_valid_mask;
        SData/*15:0*/ mv_npu_top__DOT__row_idx;
        SData/*15:0*/ mv_npu_top__DOT__k_chunk_idx;
        SData/*15:0*/ mv_npu_top__DOT__chunks_per_row;
        SData/*15:0*/ mv_npu_top__DOT__u_mac__DOT__lane_valid_mask;
        SData/*15:0*/ mv_npu_top__DOT__u_mac__DOT__p_i;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_M;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_N;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__vec_cnt;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__row_cnt;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt;
        SData/*15:0*/ mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row;
        VL_INW(mat_data,127,0,4);
        VL_IN(bias_data,31,0);
        VL_OUT(out_data,31,0);
        VlWide<4>/*127:0*/ mv_npu_top__DOT__mat_data;
        IData/*31:0*/ mv_npu_top__DOT__bias_data;
        IData/*31:0*/ mv_npu_top__DOT__out_data;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__mat_lanes;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__vec_lanes;
        IData/*31:0*/ mv_npu_top__DOT__row_accum_out;
        IData/*31:0*/ mv_npu_top__DOT__pp_out_data;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__in_data;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__bias_data;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__out_data;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__pre_act;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__post_act;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_mac__DOT__mat_lane_data;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_mac__DOT__vec_lane_data;
    };
    struct {
        IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__row_accum_out;
        IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__sum32;
        IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__i;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__rd_data;
        IData/*31:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__j;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_stream_if__DOT__mat_data_in;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out;
        IData/*31:0*/ __VactIterCount;
        VL_IN64(cmd_data,63,0);
        QData/*63:0*/ mv_npu_top__DOT__cmd_data;
        QData/*63:0*/ mv_npu_top__DOT__u_ctrl__DOT__cmd_data;
        VlUnpacked<CData/*7:0*/, 256> mv_npu_top__DOT__u_vec_buffer__DOT__mem;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MAX_M = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__CMD_W = 0x00000040U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MAT_DATA_W = 0x00000080U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__VEC_DATA_W = 8U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__BIAS_DATA_W = 0x00000020U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__OUT_DATA_W = 0x00000020U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__AW = 8U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_vec_buffer__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_stream_if__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_stream_if__DOT__MAT_DATA_W = 0x00000080U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__MAX_M = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__CMD_W = 0x00000040U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
