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
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VstlPhaseResult;
    CData/*0:0*/ __VicoFirstIteration;
    CData/*0:0*/ __VicoPhaseResult;
    VL_INW(mat_data,127,0,4);
    VL_IN(bias_data,31,0);
    VL_OUT(out_data,31,0);
    VlWide<4>/*127:0*/ mv_npu_top__DOT__mat_data;
    IData/*31:0*/ mv_npu_top__DOT__bias_data;
    IData/*31:0*/ mv_npu_top__DOT__out_data;
    VL_IN64(cmd_data,63,0);
    QData/*63:0*/ mv_npu_top__DOT__cmd_data;
    VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;

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

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
