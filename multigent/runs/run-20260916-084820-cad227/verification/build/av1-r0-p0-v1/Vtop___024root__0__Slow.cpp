// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__u8_registered_adder__DOT__clk__0 
        = vlSelfRef.u8_registered_adder__DOT__clk;
}

VL_ATTR_COLD void Vtop___024root___eval_initial(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_initial\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

VL_ATTR_COLD void Vtop___024root___eval_final(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_final\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG
VL_ATTR_COLD bool Vtop___024root___eval_phase__stl(Vtop___024root* vlSelf);

VL_ATTR_COLD void Vtop___024root___eval_settle(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_settle\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VstlIterCount;
    // Body
    __VstlIterCount = 0U;
    vlSelfRef.__VstlFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VstlIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl-integration/multigent/runs/run-20260916-084820-cad227/rtl/u8_registered_adder.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        vlSelfRef.__VstlPhaseResult = Vtop___024root___eval_phase__stl(vlSelf);
        vlSelfRef.__VstlFirstIteration = 0U;
    } while (vlSelfRef.__VstlPhaseResult);
}

VL_ATTR_COLD bool Vtop___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___dump_triggers__stl\n"); );
    // Body
    if ((1U & (~ (IData)(Vtop___024root___trigger_anySet__stl(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD bool Vtop___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_anySet__stl\n"); );
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

VL_ATTR_COLD bool Vtop___024root___eval_phase__stl(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__stl\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VstlExecute;
    // Body
    {
        // Inlined CFunc: _eval_triggers_vec__stl
        vlSelfRef.__VstlTriggered[0U] = ((0xfffffffffffffffeULL 
                                          & vlSelfRef.__VstlTriggered[0U]) 
                                         | (IData)((IData)(vlSelfRef.__VstlFirstIteration)));
    }
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtop___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
    }
#endif
    __VstlExecute = Vtop___024root___trigger_anySet__stl(vlSelfRef.__VstlTriggered);
    if (__VstlExecute) {
        {
            // Inlined CFunc: _eval_stl
            if ((1ULL & vlSelfRef.__VstlTriggered[0U])) {
                {
                    // Inlined CFunc: _ico_sequent__TOP__0
                    vlSelfRef.u8_registered_adder__DOT__clk 
                        = vlSelfRef.clk;
                    vlSelfRef.out_valid = vlSelfRef.u8_registered_adder__DOT__out_valid;
                    vlSelfRef.u8_registered_adder__DOT__in_valid 
                        = vlSelfRef.in_valid;
                    vlSelfRef.out_payload = vlSelfRef.u8_registered_adder__DOT__out_payload;
                    vlSelfRef.u8_registered_adder__DOT__in_payload 
                        = vlSelfRef.in_payload;
                    vlSelfRef.u8_registered_adder__DOT__rst_n 
                        = vlSelfRef.rst_n;
                    vlSelfRef.u8_registered_adder__DOT__out_ready 
                        = vlSelfRef.out_ready;
                    vlSelfRef.u8_registered_adder__DOT__operand_a_ext 
                        = (0x000000ffU & (IData)(vlSelfRef.u8_registered_adder__DOT__in_payload));
                    vlSelfRef.u8_registered_adder__DOT__operand_b_ext 
                        = (0x000000ffU & ((IData)(vlSelfRef.u8_registered_adder__DOT__in_payload) 
                                          >> 8U));
                    vlSelfRef.u8_registered_adder__DOT__sum_next 
                        = (0x000001ffU & ((IData)(vlSelfRef.u8_registered_adder__DOT__operand_a_ext) 
                                          + (IData)(vlSelfRef.u8_registered_adder__DOT__operand_b_ext)));
                    vlSelfRef.u8_registered_adder__DOT__in_ready 
                        = ((IData)(vlSelfRef.u8_registered_adder__DOT__rst_n) 
                           & ((~ (IData)(vlSelfRef.u8_registered_adder__DOT__out_valid)) 
                              | (IData)(vlSelfRef.u8_registered_adder__DOT__out_ready)));
                    vlSelfRef.in_ready = vlSelfRef.u8_registered_adder__DOT__in_ready;
                }
            }
        }
    }
    return (__VstlExecute);
}

bool Vtop___024root___trigger_anySet__ico(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__ico(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___dump_triggers__ico\n"); );
    // Body
    if ((1U & (~ (IData)(Vtop___024root___trigger_anySet__ico(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: Internal 'ico' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

bool Vtop___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(Vtop___024root___trigger_anySet__act(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge u8_registered_adder.clk)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtop___024root___ctor_var_reset(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___ctor_var_reset\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
    vlSelf->clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16707436170211756652ull);
    vlSelf->rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1638864771569018232ull);
    vlSelf->in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2339549897027650563ull);
    vlSelf->in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1122049356863891575ull);
    vlSelf->in_payload = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 10382003690224316768ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_payload = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 18344552412885796964ull);
    vlSelf->u8_registered_adder__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11363607981026819648ull);
    vlSelf->u8_registered_adder__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14036169773426937190ull);
    vlSelf->u8_registered_adder__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10444420837587324302ull);
    vlSelf->u8_registered_adder__DOT__in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6319704198013373749ull);
    vlSelf->u8_registered_adder__DOT__in_payload = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 15959787722536161788ull);
    vlSelf->u8_registered_adder__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15601251455377081135ull);
    vlSelf->u8_registered_adder__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9443854253537793170ull);
    vlSelf->u8_registered_adder__DOT__out_payload = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 5464237553198041656ull);
    vlSelf->u8_registered_adder__DOT__operand_a_ext = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 6939283557489290989ull);
    vlSelf->u8_registered_adder__DOT__operand_b_ext = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 16652744334339378556ull);
    vlSelf->u8_registered_adder__DOT__sum_next = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 1851266582024598340ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__u8_registered_adder__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
