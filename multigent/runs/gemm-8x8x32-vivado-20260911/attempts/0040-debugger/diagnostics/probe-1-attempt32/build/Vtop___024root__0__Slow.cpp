// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/gemm-8x8x32-vivado-20260911/rtl/gemm8x8x32_bias_relu_top.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge gemm8x8x32_bias_relu_top.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(posedge gemm8x8x32_bias_relu_top.u_mem.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @(posedge gemm8x8x32_bias_relu_top.u_out.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 3U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 3 is active: @(posedge gemm8x8x32_bias_relu_top.u_post.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 4U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 4 is active: @(posedge gemm8x8x32_bias_relu_top.u_gemm.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 5U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 5 is active: @(posedge gemm8x8x32_bias_relu_top.u_loader.clk)\n");
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
    vlSelf->rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18209466448985614591ull);
    vlSelf->s_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3620650391335490897ull);
    vlSelf->s_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 869066129896787687ull);
    vlSelf->s_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3556786919841555277ull);
    vlSelf->s_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 14160813609151945433ull);
    vlSelf->m_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8711207929187084452ull);
    vlSelf->m_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15810413859825986029ull);
    vlSelf->m_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13032575655833598985ull);
    vlSelf->busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6386567572483775230ull);
    vlSelf->done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10296494685231209730ull);
    vlSelf->error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10895628271336369153ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2757538468995222865ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16021625955201252385ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__s_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9290385759140171681ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__s_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4531300413893388590ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__s_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4994796767160056024ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__s_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 8337090980931761866ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__m_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11646069673151958436ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__m_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3662133290152586266ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__m_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5217309963286909606ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8122926871083422677ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13964459205642241505ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4237783490888098262ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__state = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 12146882581848733512ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__start_load = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9715291563631092643ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__start_compute = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6650972518765796746ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__start_post = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2678889537751684555ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__start_out = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2678036319993343432ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11857051883076795450ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1715163219402328546ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__compute_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2964800755800801835ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14548886811507811643ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_m = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 11452375483703313745ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_n = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 4362047780858773808ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13830683364574257102ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__post_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8792485505406337226ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12629570604841169038ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1168305611889252415ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5924973302432228366ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7943850273659238215ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12964821492804838760ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16715767352838180281ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7543968167306710707ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6099719052068310621ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13199848433107277042ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 14189168611742222732ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_rd_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 16702811786478085490ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 2839059973101465750ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_rd_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 4419007748218498759ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9019744592389719160ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15506629145992719347ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4124880590807366641ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9588131995083615567ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11504092266679806000ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 7417449538878271117ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9168692064520875925ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__out_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4801762059917810464ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__sticky_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11664939247697891612ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__cmd_hs_idle = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12347509904548842036ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16394820513673452209ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9399973925676632972ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7286756946638685913ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 3784040350622594684ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 8329106992538829570ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15299045129948097130ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 856563384787013311ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11263215922945895567ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 1142185364324175946ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15016853673144492475ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11757806174819797648ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16955662737478483705ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 6062312609081063944ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2665371499885669605ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 12829740418226709141ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4704985795525639048ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11373883951823421420ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 7317060230255723348ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9481515663364511779ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 18118947520981999476ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5667977650134917350ull);
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9829504636947948925ull);
    }
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7146597946264138440ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 16863182212587377072ull);
    }
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10903652542902460928ull);
    }
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8730328252205008781ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5617228392750725663ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14605416377813719594ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 8492166192983094838ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10010657083240757413ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5348770305259795452ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3309289721899255558ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 17812279893606749227ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7984489405835355487ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14130756568960181711ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rd_issue_idx = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 13519845003493342533ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__sent_cnt = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 17994079195201436419ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_out__DOT__pending_data = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3310737812781435793ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15440540340598925162ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9547819180506048469ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1278814145897532911ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 729432637797989818ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 7214419338232395817ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 17942552241394469793ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13348082358031519316ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 4345984689757855344ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5420522705895817510ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11262078006080798954ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 6746545511991955512ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15860408623319985763ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17657311345132955072ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__active = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13405180210740610784ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pend = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14121961612561247950ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 17157400351717916818ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 1692277719425958927ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 1874584476010715703ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_post__DOT__sum = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13641339115564606409ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10975961655620721014ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5627107454810311746ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8996247316699235641ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12617343271316091683ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4599969287086651674ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12860471593508206761ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12121790758094943106ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11085340589801677814ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 7262123392529722122ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 2361493355374611053ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 8001139009117915525ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9143613859386922078ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10893266593958146289ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 9537032150272257597ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 7106699003376278991ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_issue = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 12327092214581880956ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k_resp = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 8321268099526459750ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6694773094731922393ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__req_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2650709774716497870ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__resp_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4610815974096230989ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16 = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 1408272006291174980ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod32 = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5373123547052473139ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__sum32 = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4883107894838046932ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3277258681766304540ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6073624536148885441ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6979452611046386025ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4350370496144706948ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8881062251078252182ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15281959045380500374ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 6529962395480248968ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17497179234185198356ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15526361237211893730ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 1287167607840613090ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17535077048959732281ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11719699908955578844ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18287780518496057671ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11854670960727986387ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 15240152099450850668ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5686014590454951391ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15486666877286233013ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5285582760802705017ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 9629301775075249497ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16794358189085879093ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4876859981102699365ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 14362928134080297975ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
