// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    {
        // Inlined CFunc: _eval_static__TOP
        vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx = 0U;
        const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 601739865362940812ull);
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16 = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 12557392935194516879ull);
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p32 = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9065052423270128752ull);
    }
    vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__clk__0 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_out__DOT__clk__0 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_core__DOT__clk__0 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk__0 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk;
    vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk__0 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk;
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/workspace/rtl/gemm_bias_relu_npu_top.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge gemm_bias_relu_npu_top.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(posedge gemm_bias_relu_npu_top.u_out.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @(posedge gemm_bias_relu_npu_top.u_core.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 3U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 3 is active: @(posedge gemm_bias_relu_npu_top.u_loader.clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 4U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 4 is active: @(posedge gemm_bias_relu_npu_top.u_ctrl.clk)\n");
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
    VL_SCOPED_RAND_RESET_W(96, vlSelf->cmd_data, __VscopeHash, 9522006951793221091ull);
    vlSelf->a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5999066857457713185ull);
    vlSelf->a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3935154664531327546ull);
    vlSelf->a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13897448395925857588ull);
    vlSelf->b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1040118903267060698ull);
    vlSelf->b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3038769386468159021ull);
    vlSelf->b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17962703699480683040ull);
    vlSelf->bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13116399899941129227ull);
    vlSelf->bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7578028605184267322ull);
    vlSelf->bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2951340689979324719ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10144880484820144978ull);
    vlSelf->status_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1326892537498908748ull);
    vlSelf->status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15902287485226522327ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15041101644803857313ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3953134112560119803ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6474342080692419945ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12368143131170329452ull);
    VL_SCOPED_RAND_RESET_W(96, vlSelf->gemm_bias_relu_npu_top__DOT__cmd_data, __VscopeHash, 6995089157013860176ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15021830962865890648ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13711771597579996822ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18190075535898816432ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 106467337790380354ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16182831496119695763ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 14141549364008099503ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15658952057095426836ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10257124217886581992ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14134290634674679445ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1013898458841164244ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8757722553948691772ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 17545701563907221943ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__status_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 222999228421555367ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2505552099221908996ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 3831079672856762759ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 15033305491485109899ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 8860603552213309945ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__cfg_bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7313447233905052382ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__st_load_a = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16149126724319866067ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__st_load_b = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15337265815048245834ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__st_load_bias = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 374881252877605169ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__st_compute = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14629162906542184538ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__st_emit = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1456716413811764563ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__do_compute_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13718115119614452500ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__do_compute_step = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5084332902999091489ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__do_emit_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13013680734680127336ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__do_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2887652741967036925ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__load_a_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12500492745092896852ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__load_b_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12337995562423309866ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__load_bias_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14085022296558246186ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 7503194797175816252ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 18186588818441767761ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 12888851815085908882ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11166037514721024636ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16315436200922073731ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6588198486446923306ull);
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__buf_A[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 10397176955740412419ull);
    }
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__buf_B[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18425878727589540036ull);
    }
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__buf_bias[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11797170282362066262ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__idx_m = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 11482292168437215536ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__idx_n_base = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 8585012137426413405ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__idx_k = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 4063640496053184891ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__lane_active = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18064158956255069739ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__a_elem = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17741835321085685783ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__b_vec[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4143464679242310833ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__compute_tile_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 756846489883799431ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__lane_acc[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 13271294935112800953ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__lane_post[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 1722067035338365006ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__emit_busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11015713166190576515ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__emit_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10730749433779596411ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i = 0;
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6705026444590399766ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8838536522685045810ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 555948307755336010ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 633036463033325156ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9006190243320948233ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7621730986223638934ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 816137612667329896ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 793211985068683014ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14298765986049295170ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17705818965080199094ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 17166964662323591776ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_out__DOT__started = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13996600745468588495ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13447931844057065326ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9066679791763566009ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 10351739666413829732ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 18353473839632124755ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4913815623505592116ull);
    }
    for (int __Vi0 = 0; __Vi0 < 64; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 705777809685320827ull);
    }
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15491981038965335853ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i = 0;
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7248035280871109540ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17637880574563917621ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15972429390639322591ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13119300672632835827ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 3018852791716211543ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 8547034650732195816ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5675837238613436195ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11922637263397042317ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7011826836868537559ull);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5754824274113703997ull);
    }
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11209134872196617055ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i = 0;
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i = 0;
    vlSelf->gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i = 0;
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8709100720503112221ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3812008813773997767ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 524862483268482462ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15648693711329767782ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2949739052836268927ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13169160995533287320ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 2143804206927024903ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11250417713596964992ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 9272878088364989909ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14116604046949329438ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12479088847539571208ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 10686789968346560606ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1140921960041937371ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14625689734785381307ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7809341043609358252ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7572472709520866661ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9899187307035519394ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4171387709092211022ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6963290274989879336ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 816166288322628446ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6363862236822582707ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14970529538289830934ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(12, __VscopeHash, 9646333091063513249ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9528777543187246160ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10356418080633755003ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 5579365757899041668ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15960965776385448419ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 666389581653450337ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3546660460599050283ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12551829278046304584ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4943316301715170240ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4381208838080770383ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5962970680318971264ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15812128914346055398ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7029033985276401208ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4679681615917290914ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9322328907599254855ull);
    VL_SCOPED_RAND_RESET_W(96, vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data, __VscopeHash, 13082867629710912258ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18230200351501913905ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8796481509200719550ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 29407302539852171ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2846952437047651005ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17463677436596423550ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 14877411238691397319ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 8031918919194932264ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 8139987015206508716ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7903527140022917790ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4068910030498115071ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3361911428555753721ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14508120804994144033ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12939243940438869508ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17589562191646506932ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9360637488263171562ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10632118469701079487ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 795764577849587641ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17074868550342640852ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 12859508023358978806ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 12285370957215214099ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 254107550325458847ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4589962569156581303ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2970606434145657487ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 4608463808552283416ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 3942582759721776311ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 18107517063547546169ull);
    vlSelf->gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_out__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_core__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
