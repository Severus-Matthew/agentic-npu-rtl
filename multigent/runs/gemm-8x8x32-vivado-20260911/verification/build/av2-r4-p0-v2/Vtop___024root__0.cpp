// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

bool Vtop___024root___trigger_anySet__ico(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_anySet__ico\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void Vtop___024root___ico_sequent__TOP__0(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___ico_sequent__TOP__0\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.done = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_out;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_post;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__post_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_compute;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_load;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_error 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_valid 
        = vlSelfRef.s_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_data 
        = vlSelfRef.s_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_type 
        = vlSelfRef.s_type;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_ready 
        = vlSelfRef.m_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__busy = 
        (0U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__sticky_error;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_m 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_n 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready 
        = ((1U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
           | ((2U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
              | ((3U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
                 | (4U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)))));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst = vlSelfRef.rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk = vlSelfRef.clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_type;
    vlSelfRef.m_valid = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_ready;
    vlSelfRef.m_data = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_data;
    vlSelfRef.busy = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__busy;
    vlSelfRef.error = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_m;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_n;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rst 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__rst 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__rst 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.s_ready = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_ready;
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__ico(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vtop___024root___eval_phase__ico(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__ico\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VicoExecute;
    // Body
    {
        // Inlined CFunc: _eval_triggers_vec__ico
        vlSelfRef.__VicoTriggered[0U] = ((0xfffffffffffffffeULL 
                                          & vlSelfRef.__VicoTriggered[0U]) 
                                         | (IData)((IData)(vlSelfRef.__VicoFirstIteration)));
    }
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtop___024root___dump_triggers__ico(vlSelfRef.__VicoTriggered, "ico"s);
    }
#endif
    __VicoExecute = Vtop___024root___trigger_anySet__ico(vlSelfRef.__VicoTriggered);
    if (__VicoExecute) {
        {
            // Inlined CFunc: _eval_ico
            if ((1ULL & vlSelfRef.__VicoTriggered[0U])) {
                Vtop___024root___ico_sequent__TOP__0(vlSelf);
            }
        }
    }
    return (__VicoExecute);
}

bool Vtop___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_anySet__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void Vtop___024root___nba_sequent__TOP__4(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__4\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run = 0;
    CData/*2:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m = 0;
    CData/*2:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n = 0;
    CData/*4:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue = 0;
    CData/*4:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp = 0;
    IData/*31:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc = 0;
    CData/*0:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 0;
    CData/*0:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid = 0;
    // Body
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid;
    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__rst) {
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr = 0U;
    } else {
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue;
        if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute) {
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run = 1U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 1U;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr = 0U;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr = 0U;
        } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run) {
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr 
                    = (0x000000ffU & (((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m) 
                                       << 5U) + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue)));
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr 
                    = (0x000000ffU & (((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue) 
                                       << 3U) + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n)));
                if ((0x1fU == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue))) {
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 0U;
                } else {
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue 
                        = (0x0000001fU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue)));
                }
            }
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16 
                    = (0x0000ffffU & VL_MULS_III(16, 
                                                 (0x0000ffffU 
                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data))), 
                                                 (0x0000ffffU 
                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data)))));
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod32 
                    = (((- (IData)((1U & ((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16) 
                                          >> 0x0fU)))) 
                        << 0x00000010U) | (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16));
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__sum32 
                    = (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc 
                       + vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod32);
                if ((0x1fU == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp))) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid = 1U;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__sum32;
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc = 0U;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n;
                    if (((7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m)) 
                         & (7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n)))) {
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run = 0U;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done = 1U;
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 0U;
                    } else {
                        if ((7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n))) {
                            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m 
                                = (7U & ((IData)(1U) 
                                         + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m)));
                            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n = 0U;
                        } else {
                            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n 
                                = (7U & ((IData)(1U) 
                                         + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n)));
                        }
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue = 0U;
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 1U;
                    }
                } else {
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__sum32;
                }
            }
        } else {
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = 0U;
        }
    }
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_m 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_n 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_m;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_n;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__acc_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_addr;
}

void Vtop___024root___nba_sequent__TOP__5(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__5\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*2:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 0;
    CData/*7:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca = 0;
    CData/*7:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb = 0;
    CData/*2:0*/ __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc = 0;
    // Body
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc;
    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st;
    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst) {
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb = 0U;
        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data = 0U;
    } else {
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en = 0U;
        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en = 0U;
        if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load) {
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 1U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb = 0U;
            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc = 0U;
        } else if ((4U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
            if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
                __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st 
                    = ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))
                        ? 0U : 6U);
            } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
                __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 0U;
            } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid) {
                if ((3U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type))) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = 1U;
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 6U;
                } else {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en = 1U;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data;
                    if ((7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc))) {
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 5U;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done = 1U;
                    } else {
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc 
                            = (7U & ((IData)(1U) + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc)));
                    }
                }
            }
        } else if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
            if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid) {
                    if (((2U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type)) 
                         | (0U != (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data 
                                   >> 8U)))) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = 1U;
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 6U;
                    } else {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en = 1U;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data 
                            = (0x000000ffU & vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data);
                        if ((0xffU == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb))) {
                            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 4U;
                        } else {
                            __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb 
                                = (0x000000ffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb)));
                        }
                    }
                }
            } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid) {
                if (((1U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type)) 
                     | (0U != (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data 
                               >> 8U)))) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = 1U;
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 6U;
                } else {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en = 1U;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr 
                        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data 
                        = (0x000000ffU & vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data);
                    if ((0xffU == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca))) {
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 3U;
                    } else {
                        __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca 
                            = (0x000000ffU & ((IData)(1U) 
                                              + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca)));
                    }
                }
            }
        } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st))) {
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid) {
                if ((IData)(((0U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type)) 
                             | (1U != vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data)))) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = 1U;
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 6U;
                } else {
                    __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = 2U;
                }
            }
        }
    }
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st 
        = __Vdly__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_error 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready 
        = ((1U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
           | ((2U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
              | ((3U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)) 
                 | (4U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st)))));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_wr_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready;
    vlSelfRef.s_ready = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__s_ready;
}

void Vtop___024root___eval_nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__0
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 = 0;
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 = 0;
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 = 0;
            CData/*5:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 = 0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 = 0U;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 = 0U;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 = 0U;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 = 0U;
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en) {
                __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data;
                __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr;
                __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0 = 1U;
            }
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en) {
                __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data;
                __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr;
                __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0 = 1U;
            }
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en) {
                __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data;
                __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr;
                __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0 = 1U;
            }
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en) {
                __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data;
                __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 
                    = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr;
                __Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0 = 1U;
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias
                [vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr];
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB
                [vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr];
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA
                [vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr];
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut
                [vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr];
            if (__Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias[__Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0] 
                    = __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias__v0;
            }
            if (__Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB[__Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0] 
                    = __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB__v0;
            }
            if (__Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA[__Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0] 
                    = __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA__v0;
            }
            if (__Vinline_0__nba_sequent__TOP__0___VdlySet__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0) {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut[__Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0] 
                    = __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut__v0;
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data;
        }
    }
    if ((4ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__1
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active = 0;
            CData/*5:0*/ __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx = 0;
            CData/*5:0*/ __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 0;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data;
            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rst) {
                __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active = 0U;
                __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx = 0U;
                __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt = 0U;
                __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr = 0U;
                __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done = 0U;
            } else {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done = 0U;
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out) {
                    __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active = 1U;
                    __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx = 0U;
                    __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt = 0U;
                    __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = 1U;
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr = 0U;
                    __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 0U;
                } else {
                    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data;
                        __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 1U;
                        __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = 0U;
                    }
                    if ((((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active) 
                          & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid)) 
                         & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_ready))) {
                        if ((0x3fU == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt))) {
                            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done = 1U;
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active = 0U;
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 0U;
                        } else {
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt 
                                = (0x0000003fU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt)));
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx 
                                = (0x0000003fU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx)));
                            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr 
                                = (0x0000003fU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx)));
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = 0U;
                            __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = 1U;
                        }
                    }
                }
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active 
                = __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx 
                = __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt 
                = __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data 
                = __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid 
                = __Vinline_0__nba_sequent__TOP__1___Vdly__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_valid 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_addr;
            vlSelfRef.m_valid = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_valid;
            vlSelfRef.m_data = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__m_data;
        }
    }
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__2
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn = 0;
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata = 0;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn;
            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata;
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__rst) {
                __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active = 0U;
                __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr = 0U;
                __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm = 0U;
                __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn = 0U;
                __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done = 0U;
            } else {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done = 0U;
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post) {
                    __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active = 1U;
                }
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active) {
                    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__sum 
                            = (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata 
                               + vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data);
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__wr_addr_calc 
                            = (0x0000003fU & (((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm) 
                                               << 3U) 
                                              + (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn)));
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en = 1U;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__wr_addr_calc;
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data 
                            = ((vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__sum 
                                >> 0x1fU) ? 0U : vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__sum);
                        __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend = 0U;
                        if (((7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm)) 
                             & (7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn)))) {
                            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done = 1U;
                            __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active = 0U;
                        }
                    }
                    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n;
                        __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m;
                        __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n;
                        __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata 
                            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data;
                        __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend = 1U;
                    }
                }
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_en 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_en;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_addr;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_wr_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr;
        }
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__3
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state;
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst) {
                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_load = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_compute = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_post = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_out = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__sticky_error = 0U;
            } else {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_load = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_compute = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_post = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_out = 0U;
                if ((4U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                    } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                    } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_done) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 1U;
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 5U;
                    }
                } else if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__post_done) {
                            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_out = 1U;
                            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 4U;
                        }
                    } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_done) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_post = 1U;
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 3U;
                    }
                } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_done) {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_compute = 1U;
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 2U;
                    }
                } else if ((1U & (~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__sticky_error)))) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_load = 1U;
                    __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 1U;
                }
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_error) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__sticky_error = 1U;
                }
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__gemm8x8x32_bias_relu_top__DOT__state;
            vlSelfRef.done = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_post;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_out;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__busy 
                = (0U != (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state));
            vlSelfRef.busy = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__busy;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__sticky_error;
            vlSelfRef.error = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error;
        }
    }
    if ((0x0000000000000010ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtop___024root___nba_sequent__TOP__4(vlSelf);
    }
    if ((0x0000000000000020ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtop___024root___nba_sequent__TOP__5(vlSelf);
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__6
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_rd_data;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_rd_data;
        }
    }
    if ((4ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__7
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__out_done 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done;
        }
    }
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__8
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__post_done 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done;
        }
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__9
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_compute;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__start_load;
        }
    }
}

void Vtop___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vtop___024root___eval_phase__act(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__act\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    {
        // Inlined CFunc: _eval_triggers_vec__act
        vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                        (((((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk) 
                                                            & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk__0))) 
                                                           << 5U) 
                                                          | (((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk) 
                                                              & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk__0))) 
                                                             << 4U)) 
                                                         | (((((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk) 
                                                               & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk__0))) 
                                                              << 3U) 
                                                             | (((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk__0))) 
                                                                << 2U)) 
                                                            | ((((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk__0))) 
                                                                << 1U) 
                                                               | ((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk) 
                                                                  & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0))))))));
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk;
    }
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    Vtop___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    return (0U);
}

void Vtop___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool Vtop___024root___eval_phase__nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = Vtop___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        Vtop___024root___eval_nba(vlSelf);
        Vtop___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void Vtop___024root___eval(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VicoIterCount;
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VicoIterCount = 0U;
    vlSelfRef.__VicoFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VicoIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__ico(vlSelfRef.__VicoTriggered, "ico"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/gemm-8x8x32-vivado-20260911/rtl/gemm8x8x32_bias_relu_top.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
        }
        __VicoIterCount = ((IData)(1U) + __VicoIterCount);
        vlSelfRef.__VicoPhaseResult = Vtop___024root___eval_phase__ico(vlSelf);
        vlSelfRef.__VicoFirstIteration = 0U;
    } while (vlSelfRef.__VicoPhaseResult);
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/gemm-8x8x32-vivado-20260911/rtl/gemm8x8x32_bias_relu_top.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/gemm-8x8x32-vivado-20260911/rtl/gemm8x8x32_bias_relu_top.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
            }
            vlSelfRef.__VactIterCount = ((IData)(1U) 
                                         + vlSelfRef.__VactIterCount);
            vlSelfRef.__VactPhaseResult = Vtop___024root___eval_phase__act(vlSelf);
        } while (vlSelfRef.__VactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = Vtop___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
}

#ifdef VL_DEBUG
void Vtop___024root___eval_debug_assertions(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_debug_assertions\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (VL_UNLIKELY(((vlSelfRef.clk & 0xfeU)))) {
        Verilated::overWidthError("clk");
    }
    if (VL_UNLIKELY(((vlSelfRef.rst & 0xfeU)))) {
        Verilated::overWidthError("rst");
    }
    if (VL_UNLIKELY(((vlSelfRef.s_valid & 0xfeU)))) {
        Verilated::overWidthError("s_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.s_type & 0xfcU)))) {
        Verilated::overWidthError("s_type");
    }
    if (VL_UNLIKELY(((vlSelfRef.m_ready & 0xfeU)))) {
        Verilated::overWidthError("m_ready");
    }
}
#endif  // VL_DEBUG
