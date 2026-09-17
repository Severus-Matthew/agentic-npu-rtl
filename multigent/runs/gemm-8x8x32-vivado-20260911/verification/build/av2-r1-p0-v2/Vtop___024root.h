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
        VL_IN8(s_valid,0,0);
        VL_OUT8(s_ready,0,0);
        VL_IN8(s_type,1,0);
        VL_OUT8(m_valid,0,0);
        VL_IN8(m_ready,0,0);
        VL_OUT8(busy,0,0);
        VL_OUT8(done,0,0);
        VL_OUT8(error,0,0);
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__s_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__s_ready;
        CData/*1:0*/ gemm8x8x32_bias_relu_top__DOT__s_type;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__m_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__m_ready;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__busy;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__error;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__state;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__start_load;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__start_compute;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__start_post;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__start_out;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__load_error;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__compute_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__acc_valid;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__acc_m;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__acc_n;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__post_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__out_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_en;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__out_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_rd_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__bias_rd_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__out_wr_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__out_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__a_rd_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__b_rd_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__sticky_error;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr;
    };
    struct {
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_ready;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en;
        CData/*5:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pending;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready;
        CData/*1:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr;
        CData/*7:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done;
        CData/*0:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag;
        CData/*2:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
    };
    struct {
        CData/*0:0*/ __VnbaPhaseResult;
        SData/*15:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16;
        VL_IN(s_data,31,0);
        VL_OUT(m_data,31,0);
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__s_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__m_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__acc_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__bias_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__bias_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__out_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__out_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__idx;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__unnamedblk1__DOT__sum;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb;
        IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc;
        IData/*31:0*/ __VactIterCount;
        VlUnpacked<CData/*7:0*/, 256> gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA;
        VlUnpacked<CData/*7:0*/, 256> gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB;
        VlUnpacked<IData/*31:0*/, 8> gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias;
        VlUnpacked<IData/*31:0*/, 64> gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__K_MAX = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__A_ELEM_W = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__A_DEPTH = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__B_DEPTH = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__O_DEPTH = 0x00000040U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__A_AW = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__B_AW = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__N_AW = 3U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__O_AW = 6U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__K_MAX = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__A_ELEM_W = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_out__DOT__O_DEPTH = 0x00000040U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_post__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__K_MAX = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__A_ELEM_W = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__M_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__N_MAX = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__K_MAX = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_ELEM_W = 8U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ACC_W = 0x00000020U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_CNT_MAX = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__B_CNT_MAX = 0x00000100U;
    static constexpr IData/*31:0*/ gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__C_CNT_MAX = 8U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
