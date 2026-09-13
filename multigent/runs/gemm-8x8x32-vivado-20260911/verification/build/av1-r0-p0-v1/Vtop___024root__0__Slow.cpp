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
    vlSelf->a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5999066857457713185ull);
    vlSelf->a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3935154664531327546ull);
    vlSelf->a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13897448395925857588ull);
    vlSelf->b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1040118903267060698ull);
    vlSelf->b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3038769386468159021ull);
    vlSelf->b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17962703699480683040ull);
    vlSelf->bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13116399899941129227ull);
    vlSelf->bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7578028605184267322ull);
    vlSelf->bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2951340689979324719ull);
    vlSelf->y_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1066321402564708146ull);
    vlSelf->y_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9950491916439527133ull);
    vlSelf->y_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15158982641115618104ull);
    vlSelf->done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10296494685231209730ull);
    vlSelf->error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10895628271336369153ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2757538468995222865ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16021625955201252385ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4549866181493334971ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11258933844350289250ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 1146611858209141741ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17650975831326411272ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13528713523027782832ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 2948571571009840431ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6940094793061281932ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17289348869597038549ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 9386323631192450797ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18314478993088913931ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2506128256186894231ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 7086219423683828821ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13964459205642241505ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4237783490888098262ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__state = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 12146882581848733512ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__error_sticky = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15976843556978942728ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_a_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 138351807142236229ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_b_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5785508831297401608ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5235238545023128924ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_a_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11683767963303669680ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_b_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 528803562243554457ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_bias_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 963676666338638837ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__load_err = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4855176753401942665ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__compute_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10992005770108695810ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__compute_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2964800755800801835ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__finalize_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11443149908512120472ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__finalize_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5943993372463039545ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__emit_start = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11054178795669490931ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__emit_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 906218319675421795ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2286574247672900904ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 7417449538878271117ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4124880590807366641ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_rd_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9588131995083615567ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_rd_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15446684993620282703ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1168305611889252415ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5924973302432228366ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7943850273659238215ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4034028274974467105ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14779135233374388127ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16715767352838180281ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 7543968167306710707ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 6099719052068310621ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_rd_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13199848433107277042ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 14189168611742222732ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_rd_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 16702811786478085490ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 4610080659613263272ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_rd_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 3785216883176293338ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_wr_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 4588808576478043401ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_rd_addr = VL_SCOPED_RAND_RESET_I(6, __VscopeHash, 13753735551860900518ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9019744592389719160ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15506629145992719347ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 11504092266679806000ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__y_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 17873257030418508640ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__acc_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14260896829633530764ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3277258681766304540ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6073624536148885441ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6135771005778573287ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 9718561424584154285ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11412472162219420490ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3134756120155490440ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3831669213381057293ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 2020835232959173858ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15359156266302861907ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12679919760425612573ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9461554713765708273ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7147236709420631752ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12866589599019235878ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 1393773505047713868ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17497179234185198356ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17535077048959732281ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11854670960727986387ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15526361237211893730ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 11719699908955578844ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 15240152099450850668ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 1287167607840613090ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 18287780518496057671ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 5686014590454951391ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2356847225723857455ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17970615829684071303ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_done = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4594780541114709ull);
    vlSelf->gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_err = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13526503080369819976ull);
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
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
