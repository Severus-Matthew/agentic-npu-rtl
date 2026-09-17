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
        VL_IN8(in_valid,0,0);
        VL_OUT8(in_ready,0,0);
        VL_IN8(in_type,1,0);
        VL_IN8(in_last,0,0);
        VL_OUT8(out_valid,0,0);
        VL_IN8(out_ready,0,0);
        VL_OUT8(out_last,0,0);
        VL_OUT8(busy,0,0);
        VL_OUT8(status_err,0,0);
        CData/*0:0*/ mv_npu_top__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__in_valid;
        CData/*0:0*/ mv_npu_top__DOT__in_ready;
        CData/*1:0*/ mv_npu_top__DOT__in_type;
        CData/*0:0*/ mv_npu_top__DOT__in_last;
        CData/*0:0*/ mv_npu_top__DOT__out_valid;
        CData/*0:0*/ mv_npu_top__DOT__out_ready;
        CData/*0:0*/ mv_npu_top__DOT__out_last;
        CData/*0:0*/ mv_npu_top__DOT__busy;
        CData/*0:0*/ mv_npu_top__DOT__status_err;
        CData/*0:0*/ mv_npu_top__DOT__cfg_valid;
        CData/*0:0*/ mv_npu_top__DOT__x_we;
        CData/*7:0*/ mv_npu_top__DOT__x_waddr;
        CData/*7:0*/ mv_npu_top__DOT__x_wdata;
        CData/*0:0*/ mv_npu_top__DOT__a_lane_valid;
        CData/*0:0*/ mv_npu_top__DOT__bias_valid;
        CData/*0:0*/ mv_npu_top__DOT__cfg_bias_en;
        CData/*0:0*/ mv_npu_top__DOT__cfg_relu_en;
        CData/*0:0*/ mv_npu_top__DOT__compute_step_pulse;
        CData/*0:0*/ mv_npu_top__DOT__row_finalize_pulse;
        CData/*0:0*/ mv_npu_top__DOT__job_done_pulse;
        CData/*7:0*/ mv_npu_top__DOT__x_rdata;
        CData/*7:0*/ mv_npu_top__DOT__x_raddr;
        CData/*0:0*/ mv_npu_top__DOT__start_row;
        CData/*0:0*/ mv_npu_top__DOT__step_valid;
        CData/*7:0*/ mv_npu_top__DOT__a_val;
        CData/*7:0*/ mv_npu_top__DOT__x_val;
        CData/*0:0*/ mv_npu_top__DOT__out_in_valid;
        CData/*0:0*/ mv_npu_top__DOT__out_in_last;
        CData/*0:0*/ mv_npu_top__DOT__out_accept_pulse;
        CData/*0:0*/ mv_npu_top__DOT__bias_en_runtime;
        CData/*0:0*/ mv_npu_top__DOT__relu_en_runtime;
        CData/*0:0*/ mv_npu_top__DOT__compute_active;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__in_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__in_last;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__out_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__out_ready;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__out_last;
        CData/*0:0*/ mv_npu_top__DOT__u_out__DOT__out_accept_pulse;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__bias_en;
        CData/*0:0*/ mv_npu_top__DOT__u_post__DOT__relu_en;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__start_row;
        CData/*0:0*/ mv_npu_top__DOT__u_mac__DOT__step_valid;
        CData/*7:0*/ mv_npu_top__DOT__u_mac__DOT__a_val;
        CData/*7:0*/ mv_npu_top__DOT__u_mac__DOT__x_val;
        CData/*0:0*/ mv_npu_top__DOT__u_xmem__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_xmem__DOT__we;
        CData/*7:0*/ mv_npu_top__DOT__u_xmem__DOT__waddr;
    };
    struct {
        CData/*7:0*/ mv_npu_top__DOT__u_xmem__DOT__wdata;
        CData/*7:0*/ mv_npu_top__DOT__u_xmem__DOT__raddr;
        CData/*7:0*/ mv_npu_top__DOT__u_xmem__DOT__rdata;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__in_beat_accepted;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__busy;
        CData/*0:0*/ mv_npu_top__DOT__u_ctrl__DOT__status_err;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__clk;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__rst_n;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__in_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__in_ready;
        CData/*1:0*/ mv_npu_top__DOT__u_input_router__DOT__in_type;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__cfg_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__x_we;
        CData/*7:0*/ mv_npu_top__DOT__u_input_router__DOT__x_waddr;
        CData/*7:0*/ mv_npu_top__DOT__u_input_router__DOT__x_wdata;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__a_lane_valid;
        CData/*0:0*/ mv_npu_top__DOT__u_input_router__DOT__bias_valid;
        CData/*7:0*/ mv_npu_top__DOT__u_input_router__DOT__x_count;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_out__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_xmem__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__mv_npu_top__DOT__u_input_router__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        SData/*8:0*/ mv_npu_top__DOT__cfg_m;
        SData/*8:0*/ mv_npu_top__DOT__cfg_n;
        SData/*8:0*/ mv_npu_top__DOT__m_runtime;
        SData/*8:0*/ mv_npu_top__DOT__n_runtime;
        SData/*8:0*/ mv_npu_top__DOT__row_idx;
        SData/*8:0*/ mv_npu_top__DOT__col_idx;
        SData/*15:0*/ mv_npu_top__DOT__u_mac__DOT__prod;
        SData/*8:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_m;
        SData/*8:0*/ mv_npu_top__DOT__u_ctrl__DOT__cfg_n;
        VL_IN(in_data,31,0);
        VL_OUT(out_data,31,0);
        IData/*31:0*/ mv_npu_top__DOT__in_data;
        IData/*31:0*/ mv_npu_top__DOT__out_data;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__a_lane_data;
        IData/*31:0*/ mv_npu_top__DOT__bias_data;
        IData/*31:0*/ mv_npu_top__DOT__acc_out;
        IData/*31:0*/ mv_npu_top__DOT__bias_hold;
        IData/*31:0*/ mv_npu_top__DOT__y_post;
        IData/*31:0*/ mv_npu_top__DOT__out_in_data;
        IData/*31:0*/ mv_npu_top__DOT__u_out__DOT__in_data;
        IData/*31:0*/ mv_npu_top__DOT__u_out__DOT__out_data;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__acc_in;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__bias_in;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__y_out;
        IData/*31:0*/ mv_npu_top__DOT__u_post__DOT__y_pre;
    };
    struct {
        IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__acc_out;
        IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__acc;
        IData/*31:0*/ mv_npu_top__DOT__u_input_router__DOT__in_data;
        VlWide<4>/*127:0*/ mv_npu_top__DOT__u_input_router__DOT__a_lane_data;
        IData/*31:0*/ mv_npu_top__DOT__u_input_router__DOT__bias_data;
        IData/*31:0*/ __VactIterCount;
        QData/*63:0*/ mv_npu_top__DOT__cfg_word;
        QData/*63:0*/ mv_npu_top__DOT__u_input_router__DOT__cfg_word;
        VlUnpacked<CData/*7:0*/, 256> mv_npu_top__DOT__u_xmem__DOT__mem;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ mv_npu_top__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MAX_M = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__MW = 9U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__NW = 9U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__XAW = 8U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_mac__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_xmem__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__LANES = 0x00000010U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__MAX_M = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_ctrl__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_input_router__DOT__MAX_N = 0x00000100U;
    static constexpr IData/*31:0*/ mv_npu_top__DOT__u_input_router__DOT__LANES = 0x00000010U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
