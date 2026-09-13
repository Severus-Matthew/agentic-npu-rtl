// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

VL_ATTR_COLD void Vtop___024root___eval_static(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_static\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__stream_matvec_int8__DOT__clk__0 
        = vlSelfRef.stream_matvec_int8__DOT__clk;
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-205759-2ecda0/rtl/stream_matvec_int8.sv", 1, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
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
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge stream_matvec_int8.clk)\n");
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
    vlSelf->cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15271417814813862642ull);
    vlSelf->cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7995897193997220869ull);
    vlSelf->cmd_rows = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 5278776639918579213ull);
    vlSelf->cmd_cols = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 6815941957877466748ull);
    vlSelf->cmd_bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18323544711493311175ull);
    vlSelf->cmd_relu_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4814549188543879735ull);
    vlSelf->in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2339549897027650563ull);
    vlSelf->in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1122049356863891575ull);
    vlSelf->in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 4057622023130387117ull);
    vlSelf->out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2886291494070200219ull);
    vlSelf->out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17332470166291283643ull);
    vlSelf->out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 10144880484820144978ull);
    vlSelf->out_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7203605059167855308ull);
    vlSelf->done_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14041563275092647750ull);
    vlSelf->done_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4926381321588099350ull);
    vlSelf->done_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12820254939764254752ull);
    vlSelf->stream_matvec_int8__DOT__clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16251021212727855779ull);
    vlSelf->stream_matvec_int8__DOT__rst = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11717362293734478313ull);
    vlSelf->stream_matvec_int8__DOT__cmd_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11214245603949138297ull);
    vlSelf->stream_matvec_int8__DOT__cmd_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4661297189348550826ull);
    vlSelf->stream_matvec_int8__DOT__cmd_rows = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 1192937665801751765ull);
    vlSelf->stream_matvec_int8__DOT__cmd_cols = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 14644031781958842156ull);
    vlSelf->stream_matvec_int8__DOT__cmd_bias_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17542907107929407872ull);
    vlSelf->stream_matvec_int8__DOT__cmd_relu_enable = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16502578444370854620ull);
    vlSelf->stream_matvec_int8__DOT__in_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5920372394853246416ull);
    vlSelf->stream_matvec_int8__DOT__in_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14817690744657063196ull);
    vlSelf->stream_matvec_int8__DOT__in_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 16725082899008214943ull);
    vlSelf->stream_matvec_int8__DOT__out_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7531195536829340826ull);
    vlSelf->stream_matvec_int8__DOT__out_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4016383984977865214ull);
    vlSelf->stream_matvec_int8__DOT__out_data = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14437291208203944857ull);
    vlSelf->stream_matvec_int8__DOT__out_last = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 11005471020595076186ull);
    vlSelf->stream_matvec_int8__DOT__done_valid = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5765702498875925300ull);
    vlSelf->stream_matvec_int8__DOT__done_ready = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13393085563275421785ull);
    vlSelf->stream_matvec_int8__DOT__done_error = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4895119666123322186ull);
    vlSelf->stream_matvec_int8__DOT__state = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 3409557178999500846ull);
    vlSelf->stream_matvec_int8__DOT__rows_q = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 9532182011334454301ull);
    vlSelf->stream_matvec_int8__DOT__cols_q = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 16966606301948005550ull);
    vlSelf->stream_matvec_int8__DOT__bias_enable_q = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4700977468773704204ull);
    vlSelf->stream_matvec_int8__DOT__relu_enable_q = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14860433034655470904ull);
    vlSelf->stream_matvec_int8__DOT__error_q = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3252513984056392113ull);
    vlSelf->stream_matvec_int8__DOT__vector_write_index = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 371928659123333101ull);
    vlSelf->stream_matvec_int8__DOT__column_index = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 2600897371959600642ull);
    vlSelf->stream_matvec_int8__DOT__tile_base = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 17820717494588607235ull);
    vlSelf->stream_matvec_int8__DOT__tile_height = VL_SCOPED_RAND_RESET_I(5, __VscopeHash, 13705374855399824489ull);
    vlSelf->stream_matvec_int8__DOT__lane_index = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 5554312612002475019ull);
    for (int __Vi0 = 0; __Vi0 < 256; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__vector_store[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 12574655479420852408ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__matrix_staging[__Vi0] = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15132303562833532911ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__bias_staging[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15198539998931542996ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__accumulator_result_bank[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 1485109512701945071ull);
    }
    vlSelf->stream_matvec_int8__DOT__vector_value = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 13977131116849455558ull);
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__product[__Vi0] = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 11083686557063147018ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__extended_product[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15053286428298948973ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__mac_value[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 14086292566226578485ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__selected_bias[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 15155802505709161111ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__biased_value[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2209361362765254883ull);
    }
    for (int __Vi0 = 0; __Vi0 < 16; ++__Vi0) {
        vlSelf->stream_matvec_int8__DOT__final_value[__Vi0] = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 3227908048446936435ull);
    }
    vlSelf->stream_matvec_int8__DOT__rows_ext = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 14892779616152671053ull);
    vlSelf->stream_matvec_int8__DOT__cols_ext = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 4547664081021953420ull);
    vlSelf->stream_matvec_int8__DOT__base_ext = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 14911129368319907558ull);
    vlSelf->stream_matvec_int8__DOT__vector_write_ext = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 1201483383130794344ull);
    vlSelf->stream_matvec_int8__DOT__column_ext = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 15506541954735726080ull);
    vlSelf->stream_matvec_int8__DOT__remaining_rows = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 17327299602578421368ull);
    vlSelf->stream_matvec_int8__DOT__next_base = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 16629928086138920863ull);
    vlSelf->stream_matvec_int8__DOT__current_row = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 11870943002177289161ull);
    vlSelf->stream_matvec_int8__DOT__last_column = VL_SCOPED_RAND_RESET_I(17, __VscopeHash, 3901922489854514536ull);
    vlSelf->stream_matvec_int8__DOT__last_lane = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3907015384827538680ull);
    vlSelf->stream_matvec_int8__DOT__final_tile = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8915950541060312371ull);
    vlSelf->stream_matvec_int8__DOT__command_legal = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18377578196157121130ull);
    vlSelf->stream_matvec_int8__DOT__unnamedblk1__DOT__i = 0;
    vlSelf->stream_matvec_int8__DOT__unnamedblk2__DOT__i = 0;
    vlSelf->stream_matvec_int8__DOT__unnamedblk3__DOT__i = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VicoTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__stream_matvec_int8__DOT__clk__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
