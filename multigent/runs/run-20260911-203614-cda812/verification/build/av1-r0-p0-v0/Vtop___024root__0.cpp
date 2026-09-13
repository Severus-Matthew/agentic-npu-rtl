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
                {
                    // Inlined CFunc: _ico_sequent__TOP__0
                    vlSelfRef.mv_npu_top__DOT__clk 
                        = vlSelfRef.clk;
                    vlSelfRef.mv_npu_top__DOT__rst_n 
                        = vlSelfRef.rst_n;
                    vlSelfRef.mv_npu_top__DOT__cmd_valid 
                        = vlSelfRef.cmd_valid;
                    vlSelfRef.cmd_ready = vlSelfRef.mv_npu_top__DOT__cmd_ready;
                    vlSelfRef.mv_npu_top__DOT__cmd_data 
                        = vlSelfRef.cmd_data;
                    vlSelfRef.mv_npu_top__DOT__vec_valid 
                        = vlSelfRef.vec_valid;
                    vlSelfRef.vec_ready = vlSelfRef.mv_npu_top__DOT__vec_ready;
                    vlSelfRef.mv_npu_top__DOT__vec_data 
                        = vlSelfRef.vec_data;
                    vlSelfRef.mv_npu_top__DOT__mat_valid 
                        = vlSelfRef.mat_valid;
                    vlSelfRef.mat_ready = vlSelfRef.mv_npu_top__DOT__mat_ready;
                    vlSelfRef.mv_npu_top__DOT__mat_data[0U] 
                        = vlSelfRef.mat_data[0U];
                    vlSelfRef.mv_npu_top__DOT__mat_data[1U] 
                        = vlSelfRef.mat_data[1U];
                    vlSelfRef.mv_npu_top__DOT__mat_data[2U] 
                        = vlSelfRef.mat_data[2U];
                    vlSelfRef.mv_npu_top__DOT__mat_data[3U] 
                        = vlSelfRef.mat_data[3U];
                    vlSelfRef.mv_npu_top__DOT__bias_valid 
                        = vlSelfRef.bias_valid;
                    vlSelfRef.bias_ready = vlSelfRef.mv_npu_top__DOT__bias_ready;
                    vlSelfRef.mv_npu_top__DOT__bias_data 
                        = vlSelfRef.bias_data;
                    vlSelfRef.out_valid = vlSelfRef.mv_npu_top__DOT__out_valid;
                    vlSelfRef.mv_npu_top__DOT__out_ready 
                        = vlSelfRef.out_ready;
                    vlSelfRef.out_data = vlSelfRef.mv_npu_top__DOT__out_data;
                    vlSelfRef.status_busy = vlSelfRef.mv_npu_top__DOT__status_busy;
                    vlSelfRef.status_error = vlSelfRef.mv_npu_top__DOT__status_error;
                }
            }
        }
    }
    return (__VicoExecute);
}

void Vtop___024root___eval(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VicoIterCount;
    // Body
    __VicoIterCount = 0U;
    vlSelfRef.__VicoFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VicoIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__ico(vlSelfRef.__VicoTriggered, "ico"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-203614-cda812/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
        }
        __VicoIterCount = ((IData)(1U) + __VicoIterCount);
        vlSelfRef.__VicoPhaseResult = Vtop___024root___eval_phase__ico(vlSelf);
        vlSelfRef.__VicoFirstIteration = 0U;
    } while (vlSelfRef.__VicoPhaseResult);
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
    if (VL_UNLIKELY(((vlSelfRef.rst_n & 0xfeU)))) {
        Verilated::overWidthError("rst_n");
    }
    if (VL_UNLIKELY(((vlSelfRef.cmd_valid & 0xfeU)))) {
        Verilated::overWidthError("cmd_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.vec_valid & 0xfeU)))) {
        Verilated::overWidthError("vec_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.mat_valid & 0xfeU)))) {
        Verilated::overWidthError("mat_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bias_valid & 0xfeU)))) {
        Verilated::overWidthError("bias_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
}
#endif  // VL_DEBUG
