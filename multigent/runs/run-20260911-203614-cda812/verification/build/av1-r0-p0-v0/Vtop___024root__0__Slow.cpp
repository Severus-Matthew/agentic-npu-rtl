// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-203614-cda812/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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

VL_ATTR_COLD void Vtop___024root___ctor_var_reset(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___ctor_var_reset\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
    vlSelf->clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16707436170211756652ull);
    vlSelf->rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1638864771569018232ull);
    vlSelf->cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15271417814813862642ull);
    vlSelf->cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7995897193997220869ull);
    vlSelf->cmd_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 9522006951793221091ull);
    vlSelf->vec_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15817961075239821267ull);
    vlSelf->vec_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16640783594057183062ull);
    vlSelf->vec_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18426674535685177404ull);
    vlSelf->mat_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5731595643385755291ull);
    vlSelf->mat_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 546069766646939253ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mat_data, __VscopeHash, 2392287793211018950ull);
    vlSelf->bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13116399899941129227ull);
    vlSelf->bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7578028605184267322ull);
    vlSelf->bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2951340689979324719ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10144880484820144978ull);
    vlSelf->status_busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1086216333236379016ull);
    vlSelf->status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15902287485226522327ull);
    vlSelf->mv_npu_top__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3170224052951053090ull);
    vlSelf->mv_npu_top__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 741136130367822273ull);
    vlSelf->mv_npu_top__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15808442951845746892ull);
    vlSelf->mv_npu_top__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12740378044228612526ull);
    vlSelf->mv_npu_top__DOT__cmd_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 6184191359006382978ull);
    vlSelf->mv_npu_top__DOT__vec_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17983096442588274343ull);
    vlSelf->mv_npu_top__DOT__vec_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 876482469833080851ull);
    vlSelf->mv_npu_top__DOT__vec_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 2200466210242210372ull);
    vlSelf->mv_npu_top__DOT__mat_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13350916786271703914ull);
    vlSelf->mv_npu_top__DOT__mat_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8056573951080725817ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__mat_data, __VscopeHash, 12310883770907298366ull);
    vlSelf->mv_npu_top__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13145018347512483040ull);
    vlSelf->mv_npu_top__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8904612580580819387ull);
    vlSelf->mv_npu_top__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14138610282582201381ull);
    vlSelf->mv_npu_top__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1048464542106939252ull);
    vlSelf->mv_npu_top__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12053026138112786039ull);
    vlSelf->mv_npu_top__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11832525713391568783ull);
    vlSelf->mv_npu_top__DOT__status_busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7981488256358114478ull);
    vlSelf->mv_npu_top__DOT__status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 133602609474899732ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
}
