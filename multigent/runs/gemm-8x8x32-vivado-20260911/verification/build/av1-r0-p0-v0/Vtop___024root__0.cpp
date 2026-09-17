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
    vlSelfRef.y_valid = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__y_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__y_ready 
        = vlSelfRef.y_ready;
    vlSelfRef.y_data = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__y_data;
    vlSelfRef.done = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done;
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
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_done 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_done;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_err 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_err;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_start 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (5U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__finalize_start 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (6U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__emit_start 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk = vlSelfRef.clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst = vlSelfRef.rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_valid 
        = vlSelfRef.a_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_data 
        = vlSelfRef.a_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_valid 
        = vlSelfRef.b_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_data 
        = vlSelfRef.b_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_valid 
        = vlSelfRef.bias_valid;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_ready 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_data 
        = vlSelfRef.bias_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_en 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (2U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_en 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (3U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_en 
        = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
           & (4U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_valid;
    vlSelfRef.a_ready = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__a_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_valid;
    vlSelfRef.b_ready = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__b_data;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_valid 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_valid;
    vlSelfRef.bias_ready = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_ready;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_data 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__bias_data;
    vlSelfRef.error = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_en;
    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_en 
        = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_en;
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

void Vtop___024root___eval_nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__0
            CData/*3:0*/ __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state;
            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0;
            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state;
            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__rst) {
                __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 0U;
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky = 0U;
            } else {
                vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 0U;
                if ((8U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((4U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                    } else if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                    } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 0U;
                    } else {
                        vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done = 1U;
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 1U;
                    }
                } else if ((4U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                            if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__emit_done) {
                                __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 8U;
                            }
                        } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__finalize_done) {
                            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 7U;
                        }
                    } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_done) {
                            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 6U;
                        }
                    } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_done) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 5U;
                    }
                } else if ((2U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                        if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_done) {
                            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 4U;
                        }
                    } else if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_done) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 3U;
                    }
                } else if ((1U & (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state))) {
                    if ((1U & (~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)))) {
                        __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 2U;
                    }
                } else {
                    __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state = 1U;
                }
                if (vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_err) {
                    vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky = 1U;
                }
            }
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state 
                = __Vinline_0__nba_sequent__TOP__0___Vdly__gemm8x8x32_bias_relu_top__DOT__state;
            vlSelfRef.done = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__done;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__compute_start 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (5U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__finalize_start 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (6U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__emit_start 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (7U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_en 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (2U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_en 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (3U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_en 
                = ((~ (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error_sticky)) 
                   & (4U == (IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__state)));
            vlSelfRef.error = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__error;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_en 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_a_en;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_en 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_b_en;
            vlSelfRef.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_en 
                = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__load_bias_en;
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
                                                        ((IData)(vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk) 
                                                         & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0)))));
        vlSelfRef.__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0 
            = vlSelfRef.gemm8x8x32_bias_relu_top__DOT__clk;
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
    if (VL_UNLIKELY(((vlSelfRef.a_valid & 0xfeU)))) {
        Verilated::overWidthError("a_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.b_valid & 0xfeU)))) {
        Verilated::overWidthError("b_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bias_valid & 0xfeU)))) {
        Verilated::overWidthError("bias_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.y_ready & 0xfeU)))) {
        Verilated::overWidthError("y_ready");
    }
}
#endif  // VL_DEBUG
