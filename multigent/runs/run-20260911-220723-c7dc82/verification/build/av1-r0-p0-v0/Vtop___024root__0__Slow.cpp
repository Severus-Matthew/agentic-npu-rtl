// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_out__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_out__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_xmem__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_input_router__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__clk;
}

VL_ATTR_COLD void Vtop___024root___eval_initial(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_initial\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    {
        // Inlined CFunc: _eval_initial__TOP
        vlSelfRef.in_ready = 1U;
        vlSelfRef.mv_npu_top__DOT__in_ready = 1U;
        vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_ready = 1U;
    }
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-220723-c7dc82/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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

void Vtop___024root___ico_sequent__TOP__0(Vtop___024root* vlSelf);

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
                Vtop___024root___ico_sequent__TOP__0(vlSelf);
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge mv_npu_top.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(posedge mv_npu_top.u_out.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @(posedge mv_npu_top.u_mac.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 3U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 3 is active: @(posedge mv_npu_top.u_xmem.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 4U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 4 is active: @(posedge mv_npu_top.u_ctrl.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 5U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 5 is active: @(posedge mv_npu_top.u_input_router.clk)\n");
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
    vlSelf->in_ready = 1U;
    ;
    vlSelf->in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4057622023130387117ull);
    vlSelf->in_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 174831937439248810ull);
    vlSelf->in_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3707040869786000772ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10144880484820144978ull);
    vlSelf->out_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7203605059167855308ull);
    vlSelf->busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6386567572483775230ull);
    vlSelf->status_err = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10102147346015739813ull);
    vlSelf->mv_npu_top__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3170224052951053090ull);
    vlSelf->mv_npu_top__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 741136130367822273ull);
    vlSelf->mv_npu_top__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3965499662435369142ull);
    vlSelf->mv_npu_top__DOT__in_ready = 1U;
    ;
    vlSelf->mv_npu_top__DOT__in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 8086364312537436857ull);
    vlSelf->mv_npu_top__DOT__in_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 18293813225772265951ull);
    vlSelf->mv_npu_top__DOT__in_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9610366487640742152ull);
    vlSelf->mv_npu_top__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1048464542106939252ull);
    vlSelf->mv_npu_top__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12053026138112786039ull);
    vlSelf->mv_npu_top__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11832525713391568783ull);
    vlSelf->mv_npu_top__DOT__out_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 684187741541267573ull);
    vlSelf->mv_npu_top__DOT__busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1575734128004160562ull);
    vlSelf->mv_npu_top__DOT__status_err = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15551787149593274172ull);
    vlSelf->mv_npu_top__DOT__cfg_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14652413751551044686ull);
    vlSelf->mv_npu_top__DOT__cfg_word = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 682247850038990747ull);
    vlSelf->mv_npu_top__DOT__x_we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9760554421696083117ull);
    vlSelf->mv_npu_top__DOT__x_waddr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15911939818748232373ull);
    vlSelf->mv_npu_top__DOT__x_wdata = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5922338635761214024ull);
    vlSelf->mv_npu_top__DOT__a_lane_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8048946613928893537ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__a_lane_data, __VscopeHash, 17545229662857468549ull);
    vlSelf->mv_npu_top__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13145018347512483040ull);
    vlSelf->mv_npu_top__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14138610282582201381ull);
    vlSelf->mv_npu_top__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 210609100401833828ull);
    vlSelf->mv_npu_top__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 6852248925938786424ull);
    vlSelf->mv_npu_top__DOT__cfg_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2035107461700010798ull);
    vlSelf->mv_npu_top__DOT__cfg_relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12953129548909296439ull);
    vlSelf->mv_npu_top__DOT__compute_step_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15176885364267313616ull);
    vlSelf->mv_npu_top__DOT__row_finalize_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4438236704714267255ull);
    vlSelf->mv_npu_top__DOT__job_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13341959338199503256ull);
    vlSelf->mv_npu_top__DOT__x_rdata = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17748877284147662701ull);
    vlSelf->mv_npu_top__DOT__x_raddr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13214243239272943918ull);
    vlSelf->mv_npu_top__DOT__start_row = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 37672069540571557ull);
    vlSelf->mv_npu_top__DOT__step_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3036696469015331154ull);
    vlSelf->mv_npu_top__DOT__a_val = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6550733278571831549ull);
    vlSelf->mv_npu_top__DOT__x_val = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7741185670691023186ull);
    vlSelf->mv_npu_top__DOT__acc_out = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14321498769253785451ull);
    vlSelf->mv_npu_top__DOT__bias_hold = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 8312273875674613894ull);
    vlSelf->mv_npu_top__DOT__y_post = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6201927671052730362ull);
    vlSelf->mv_npu_top__DOT__out_in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17360530947142147474ull);
    vlSelf->mv_npu_top__DOT__out_in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4663687262070724095ull);
    vlSelf->mv_npu_top__DOT__out_in_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18234121434820294829ull);
    vlSelf->mv_npu_top__DOT__out_accept_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11441211813712039128ull);
    vlSelf->mv_npu_top__DOT__m_runtime = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 3799625798437083974ull);
    vlSelf->mv_npu_top__DOT__n_runtime = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 11460216308022469467ull);
    vlSelf->mv_npu_top__DOT__bias_en_runtime = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17175575753455222766ull);
    vlSelf->mv_npu_top__DOT__relu_en_runtime = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7762843863403526287ull);
    vlSelf->mv_npu_top__DOT__row_idx = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 5680174584632623194ull);
    vlSelf->mv_npu_top__DOT__col_idx = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 3320519624998355661ull);
    vlSelf->mv_npu_top__DOT__compute_active = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13784852658311560605ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9981759122538779016ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10329972185713595314ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3196047269061126065ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6019376527645076729ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__in_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1540508684076550897ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7083486073820982592ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8847249700522085385ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14625550811556851965ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__out_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12127813057812808563ull);
    vlSelf->mv_npu_top__DOT__u_out__DOT__out_accept_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11919986772643430535ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__acc_in = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 123290417761794636ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__bias_in = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2270205515660166511ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14234720343315961813ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7129289340581795957ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__y_out = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6979247855253968670ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__y_pre = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 1412022594814637384ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7549347585318227069ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9969377171661006185ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__start_row = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4453037393023237749ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__step_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9854450164813388695ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__a_val = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9339782838499280271ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__x_val = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17372726826985037946ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__acc_out = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11297315722304712727ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__acc = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5492205318514988888ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__prod = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 3261458848420127748ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18357155094432939323ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2589620360730480703ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__waddr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13813084462063981282ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__wdata = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4705204647871172477ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__raddr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 14465334061447439637ull);
    vlSelf->mv_npu_top__DOT__u_xmem__DOT__rdata = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5357454247254507644ull);
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->mv_npu_top__DOT__u_xmem__DOT__mem[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15664785092460641420ull);
    }
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7962526279257061907ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16605192630489440892ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4967601878920054214ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 7144456821929121902ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(9, __VscopeHash, 7616685882980713211ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13133319420536599535ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16195362898742466352ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__in_beat_accepted = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13546483389917043615ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11134544913052490180ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7217957831565711413ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14098502479213051172ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3243067078021772334ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1164391395865454154ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__status_err = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8318273223040898813ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14112847362422088126ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 121219730185949558ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16930006875385788004ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__in_ready = 1U;
    ;
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4813099599029101108ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__in_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 9977359776400563688ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__cfg_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11708699744528652986ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__cfg_word = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 1411368667446476295ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__x_we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14549406358128165291ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__x_waddr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16613932936018066937ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__x_wdata = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6662562292379018324ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__a_lane_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 324749103866138121ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_input_router__DOT__a_lane_data, __VscopeHash, 13119874022475291363ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11056847557829299938ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 12590110614982488427ull);
    vlSelf->mv_npu_top__DOT__u_input_router__DOT__x_count = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9321546433272068954ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_out__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_xmem__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_input_router__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
