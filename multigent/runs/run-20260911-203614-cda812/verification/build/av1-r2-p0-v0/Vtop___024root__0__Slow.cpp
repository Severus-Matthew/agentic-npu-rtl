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
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_post__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_post__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_vec_buffer__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0 
        = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk;
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(posedge mv_npu_top.u_post.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @(posedge mv_npu_top.u_mac.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 3U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 3 is active: @(posedge mv_npu_top.u_vec_buffer.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 4U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 4 is active: @(posedge mv_npu_top.u_ctrl.clk)\n");
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
    vlSelf->mv_npu_top__DOT__cfg_M = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 15222806651321999944ull);
    vlSelf->mv_npu_top__DOT__cfg_N = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 6559628504396159347ull);
    vlSelf->mv_npu_top__DOT__cfg_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2035107461700010798ull);
    vlSelf->mv_npu_top__DOT__cfg_relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12953129548909296439ull);
    vlSelf->mv_npu_top__DOT__state_compute_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7363011149846035072ull);
    vlSelf->mv_npu_top__DOT__lane_valid_mask = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 14794769344700201951ull);
    vlSelf->mv_npu_top__DOT__cmd_accept = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16861512349379454308ull);
    vlSelf->mv_npu_top__DOT__vec_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13450935612907480000ull);
    vlSelf->mv_npu_top__DOT__mat_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14401222911552075030ull);
    vlSelf->mv_npu_top__DOT__bias_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17811519942170025527ull);
    vlSelf->mv_npu_top__DOT__out_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10947026573004658131ull);
    vlSelf->mv_npu_top__DOT__vec_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9516444413200301671ull);
    vlSelf->mv_npu_top__DOT__rd_chunk_base = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11059310204116571976ull);
    vlSelf->mv_npu_top__DOT__row_idx = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 5680174584632623194ull);
    vlSelf->mv_npu_top__DOT__k_chunk_idx = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 7405138137944419032ull);
    vlSelf->mv_npu_top__DOT__chunks_per_row = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 17432237434581336803ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__mat_lanes, __VscopeHash, 7347440659266228959ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__vec_lanes, __VscopeHash, 18409058714365463806ull);
    vlSelf->mv_npu_top__DOT__compute_en_core = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11369380288640758063ull);
    vlSelf->mv_npu_top__DOT__new_row_core = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16758811575946938908ull);
    vlSelf->mv_npu_top__DOT__row_accum_out = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6159131982989781601ull);
    vlSelf->mv_npu_top__DOT__row_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10002999906432884887ull);
    vlSelf->mv_npu_top__DOT__pp_in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11284373150763071899ull);
    vlSelf->mv_npu_top__DOT__pp_in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5501196868041556617ull);
    vlSelf->mv_npu_top__DOT__pp_bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17290655717942316891ull);
    vlSelf->mv_npu_top__DOT__pp_out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9059238517775471970ull);
    vlSelf->mv_npu_top__DOT__pp_out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6372360512939986688ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3952763536319362021ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5911558897156351740ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 762399030490554684ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11423274384408478252ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14234720343315961813ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7129289340581795957ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7800779304029014420ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 18028017012417325094ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17593793411564768943ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9643131519417787267ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4983806020959574119ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9423440973194518028ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__pre_act = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 205231925792766172ull);
    vlSelf->mv_npu_top__DOT__u_post__DOT__post_act = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4834376036233582378ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7549347585318227069ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9969377171661006185ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__compute_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9495902910905544202ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__new_row = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9525621421879019314ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__lane_valid_mask = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 15113676886648348607ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_mac__DOT__mat_lane_data, __VscopeHash, 3055307139195162298ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_mac__DOT__vec_lane_data, __VscopeHash, 3174353539935130290ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__row_accum_out = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2631424899531227062ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__row_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12120157026537858512ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__sum32 = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2067350739656587553ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__i = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2235074000439114452ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__m_i = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15731572940093504297ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__v_i = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5296962163437401129ull);
    vlSelf->mv_npu_top__DOT__u_mac__DOT__p_i = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 7845275033021712630ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1980279028420378523ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14823934148446452465ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5184330384463097580ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9987840741349525261ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 8617768319771042515ull);
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5944208154184472951ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__rd_data, __VscopeHash, 5957444684376311423ull);
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__mem[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11283087988261183368ull);
    }
    vlSelf->mv_npu_top__DOT__u_vec_buffer__DOT__j = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 17732102639724855233ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_stream_if__DOT__mat_data_in, __VscopeHash, 13121076479346259667ull);
    VL_SCOPED_RAND_RESET_W(128, vlSelf->mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out, __VscopeHash, 17174731656854616601ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7962526279257061907ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16605192630489440892ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cmd_accept = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2631997944229571545ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cmd_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 561759789874296493ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__vec_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4866525385713408675ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__mat_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1398365049910272437ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__bias_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6054689333059724867ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__out_xfer = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18179674423486888832ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_M = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11461960868794306752ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_N = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11934189929845795169ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13133319420536599535ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16195362898742466352ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__state_compute_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16932318118060345193ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 4760654888223058649ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__status_busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12887788202794821654ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11500515720548868380ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__st = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 12452436254931944467ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__vec_cnt = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 14099539250344716853ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__row_cnt = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 17259470504805414867ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 6222831350318365605ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 15131022866741378466ull);
    vlSelf->mv_npu_top__DOT__u_ctrl__DOT__rem = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 9091751601475699868ull);
    vlSelf->__VdfgRegularize_h6e95ff9d_0_0 = 0;
    vlSelf->__VdfgRegularize_h6e95ff9d_0_1 = 0;
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
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_post__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_vec_buffer__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
