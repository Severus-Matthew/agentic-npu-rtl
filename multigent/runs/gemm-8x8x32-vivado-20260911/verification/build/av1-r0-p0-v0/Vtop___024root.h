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
        VL_IN8(rst,0,0);
        VL_IN8(a_valid,0,0);
        VL_OUT8(a_ready,0,0);
        VL_IN8(a_data,7,0);
        VL_IN8(b_valid,0,0);
        VL_OUT8(b_ready,0,0);
        VL_IN8(b_data,7,0);
        VL_IN8(bias_valid,0,0);
        VL_OUT8(bias_ready,0,0);
        VL_OUT8(y_valid,0,0);
        VL_IN8(y_ready,0,0);
        VL_OUT8(done,0,0);
        VL_OUT8(error,0,0);
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__a_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__a_ready;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__b_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__b_ready;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__bias_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__bias_ready;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__y_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__y_ready;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__error;
        CData/*3:0*/ gemm8x8x32_bias_relu_top__DOT__state;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__error_sticky;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_a_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_b_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_bias_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_a_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_b_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_bias_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_err;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__compute_start;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__compute_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__finalize_start;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__finalize_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__emit_start;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__emit_done;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_rd_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_rd_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__y_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__acc_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_rd_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__bias_rd_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__y_wr_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__y_rd_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__acc_wr_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__acc_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst;
    };
    struct {
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_ready;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_ready;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_ready;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_err;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        VL_IN(bias_data,31,0);
        VL_OUT(y_data,31,0);
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__bias_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__y_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__acc_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__bias_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__y_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__y_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__acc_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data;
        IData/*31:0*/ __VactIterCount;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__M_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__N_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__K_FIXED = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__A_ELEMS_FIXED = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__B_ELEMS_FIXED = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__Y_ELEMS_FIXED = 0x00000040U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__ACC_ELEMS = 0x00000040U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__M_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__N_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__K_FIXED = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__Y_ELEMS_FIXED = 0x00000040U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__M_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__N_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_core__DOT__M_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_core__DOT__N_FIXED = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_core__DOT__K_FIXED = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_ELEMS_FIXED = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__B_ELEMS_FIXED = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__N_FIXED = 8U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
