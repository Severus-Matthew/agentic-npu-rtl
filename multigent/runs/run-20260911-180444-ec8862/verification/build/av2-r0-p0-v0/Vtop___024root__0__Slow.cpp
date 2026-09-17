// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__clk__0 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk__0 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk;
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-180444-ec8862/rtl/fc_accelerator.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge fc_accelerator.u_controller.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(posedge fc_accelerator.u_controller.u_datapath.clk)\n");
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
    vlSelf->cmd_data = VL_SCOPED_RAND_RESET_I(21, __VscopeHash, 9522006951793221091ull);
    vlSelf->a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5999066857457713185ull);
    vlSelf->a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3935154664531327546ull);
    vlSelf->a_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 13897448395925857588ull);
    vlSelf->w_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1598689714110194787ull);
    vlSelf->w_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6191156139041826059ull);
    vlSelf->w_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 1356167372520825866ull);
    vlSelf->bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13116399899941129227ull);
    vlSelf->bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7578028605184267322ull);
    vlSelf->bias_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 2951340689979324719ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 10144880484820144978ull);
    vlSelf->status_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5375727165888105717ull);
    vlSelf->status_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9072398566468288528ull);
    vlSelf->status_code = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 16972304869017100834ull);
    vlSelf->fc_accelerator__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9817034084509594712ull);
    vlSelf->fc_accelerator__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6203582106304956459ull);
    vlSelf->fc_accelerator__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3105223022091643349ull);
    vlSelf->fc_accelerator__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4808239341766834272ull);
    vlSelf->fc_accelerator__DOT__cmd_data = VL_SCOPED_RAND_RESET_I(21, __VscopeHash, 15458015423988704945ull);
    vlSelf->fc_accelerator__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14401722356724763967ull);
    vlSelf->fc_accelerator__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11736004027734866720ull);
    vlSelf->fc_accelerator__DOT__a_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 4470234817418633297ull);
    vlSelf->fc_accelerator__DOT__w_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1102028740296714026ull);
    vlSelf->fc_accelerator__DOT__w_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9665471045395519865ull);
    vlSelf->fc_accelerator__DOT__w_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 3458712308445611537ull);
    vlSelf->fc_accelerator__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13445699919633315575ull);
    vlSelf->fc_accelerator__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18354183254124421497ull);
    vlSelf->fc_accelerator__DOT__bias_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 5225667538899566198ull);
    vlSelf->fc_accelerator__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15857902396052782298ull);
    vlSelf->fc_accelerator__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14450671550963426611ull);
    vlSelf->fc_accelerator__DOT__out_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 5940819773275297118ull);
    vlSelf->fc_accelerator__DOT__status_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14335719715641806967ull);
    vlSelf->fc_accelerator__DOT__status_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2698543958225907554ull);
    vlSelf->fc_accelerator__DOT__status_code = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 2868270391218714191ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15570946492996405076ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5107563566628885238ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11004754671311121728ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13134840291393508146ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_data = VL_SCOPED_RAND_RESET_I(21, __VscopeHash, 1862080687494837192ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4024302350430094481ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14868494181261412555ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 9391890750551428150ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1484927259708310113ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3203910436283021643ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 10228491349505028413ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7438817078524514244ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17304123607167088757ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 6523200944510803321ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10461965834770466682ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14373916485126490577ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__out_data = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 7814419033426136674ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__status_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14127574887386942222ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__status_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7568540669583397265ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__status_code = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 9994356892208925862ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__state = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 15706339638296201107ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 4858419457540308381ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 6749148627818414680ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 3921060053802455950ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__tile_m_base = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 2252897809267995715ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__tile_n_base = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 18394560622936656580ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__compute_k = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 7425937949518692116ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__finalize_pair = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 6952288279525897413ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__result_rpair = VL_SCOPED_RAND_RESET_I(11, __VscopeHash, 1455667382023176903ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__status_code_reg = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 5538895288694337662ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__activation_beat = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4544649989239792555ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__weight_beat = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15823752510164368624ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_beat = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2342955215463512883ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__output_beat = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11787582121821621974ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_total = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13998894079010875020ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_total = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9976207094421606052ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__b_total = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 8004696702869876968ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__out_total = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13082026686060405939ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__lane = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15578611512861282361ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_we = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6630807743501504240ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__a_wbase = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 11380224839384253468ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_we = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 3565247964847351238ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__w_wbase = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 11783088780382853894ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_we = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 15864686564235565834ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__bias_wbase = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 6183234876117056783ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__tile_init = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13534917010667553140ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__compute_step = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11931978447545445814ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__finalize_we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5800842371880271613ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__result_rdata = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 14690230499802115736ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_m = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 16480115738106550096ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_n = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 9255435278610504070ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__cmd_k = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 6457809250817369145ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16321245152306786008ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1978008891403833111ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 13059621276426166539ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 14046920936128483675ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 6558947799779304269ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15157227845916427038ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 17070308478380161524ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wdata = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 10080643716732234043ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12221886255768903373ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 5937191681323604107ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wdata = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 16988314793381970886ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 12238505851618914772ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 7924674397692925417ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 15466433970722520249ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 6923839333541561669ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 15377209110424616712ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4685087193818676026ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14472706191136627166ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 2548128983359352598ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9059283221778908123ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 11293666200086480573ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair = VL_SCOPED_RAND_RESET_I(11, __VscopeHash, 9381739903394606484ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata = VL_SCOPED_RAND_RESET_Q(64, __VscopeHash, 7024318135698120167ull);
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12414794650066937678ull);
    }
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17983805188903640852ull);
    }
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14574509699170375208ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        for (int __Vi1 = 0; __Vi1 < 8; ++__Vi1) {
            vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator[__Vi0][__Vi1] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 7829060444590157339ull);
        }
    }
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3439661027476148116ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16702692215497935987ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 8606201458265247406ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        for (int __Vi1 = 0; __Vi1 < 8; ++__Vi1) {
            vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product[__Vi0][__Vi1] = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11545895193977640711ull);
        }
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        for (int __Vi1 = 0; __Vi1 < 8; ++__Vi1) {
            vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext[__Vi0][__Vi1] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15853230476922866856ull);
        }
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active[__Vi0] = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17093652236648747436ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active[__Vi0] = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2619436567397796547ull);
    }
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 1111346998595070046ull);
    for (int __Vi0 = 0; __Vi0 < 2; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[__Vi0] = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 14901088432217112139ull);
    }
    for (int __Vi0 = 0; __Vi0 < 2; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3606509834855076750ull);
    }
    for (int __Vi0 = 0; __Vi0 < 2; ++__Vi0) {
        vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4644535470964486725ull);
    }
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5683392416616435470ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 7160688687010600847ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14489949313222685044ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11822514309513746342ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11799829574085339547ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 17121029429869705468ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13887811753074205257ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3766710739992857148ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11700359394194739472ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14976789243816874414ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11405543870870966052ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 16543998223981809128ull);
    vlSelf->fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5928568829420939957ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
