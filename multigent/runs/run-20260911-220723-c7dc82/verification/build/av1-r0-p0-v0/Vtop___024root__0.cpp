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

void Vtop___024root___ico_sequent__TOP__0(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___ico_sequent__TOP__0\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.mv_npu_top__DOT__in_last = vlSelfRef.in_last;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_valid 
        = vlSelfRef.mv_npu_top__DOT__out_in_valid;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_data 
        = vlSelfRef.mv_npu_top__DOT__out_in_data;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_last 
        = vlSelfRef.mv_npu_top__DOT__out_in_last;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__start_row 
        = vlSelfRef.mv_npu_top__DOT__start_row;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__step_valid 
        = vlSelfRef.mv_npu_top__DOT__step_valid;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__raddr = vlSelfRef.mv_npu_top__DOT__x_raddr;
    vlSelfRef.mv_npu_top__DOT__x_rdata = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__rdata;
    vlSelfRef.mv_npu_top__DOT__compute_step_pulse = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse;
    vlSelfRef.mv_npu_top__DOT__row_finalize_pulse = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse;
    vlSelfRef.mv_npu_top__DOT__job_done_pulse = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse;
    vlSelfRef.mv_npu_top__DOT__a_lane_valid = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid;
    vlSelfRef.mv_npu_top__DOT__a_lane_data[0U] = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U];
    vlSelfRef.mv_npu_top__DOT__a_lane_data[1U] = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[1U];
    vlSelfRef.mv_npu_top__DOT__a_lane_data[2U] = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[2U];
    vlSelfRef.mv_npu_top__DOT__a_lane_data[3U] = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[3U];
    vlSelfRef.mv_npu_top__DOT__bias_valid = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_valid;
    vlSelfRef.mv_npu_top__DOT__bias_data = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_data;
    vlSelfRef.mv_npu_top__DOT__in_data = vlSelfRef.in_data;
    vlSelfRef.mv_npu_top__DOT__in_type = vlSelfRef.in_type;
    vlSelfRef.mv_npu_top__DOT__out_valid = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid;
    vlSelfRef.mv_npu_top__DOT__out_data = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_data;
    vlSelfRef.mv_npu_top__DOT__out_last = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_last;
    vlSelfRef.mv_npu_top__DOT__busy = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__busy;
    vlSelfRef.mv_npu_top__DOT__status_err = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_err;
    vlSelfRef.mv_npu_top__DOT__x_we = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_we;
    vlSelfRef.mv_npu_top__DOT__x_waddr = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_waddr;
    vlSelfRef.mv_npu_top__DOT__x_wdata = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_wdata;
    vlSelfRef.mv_npu_top__DOT__cfg_valid = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_valid;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__a_val = vlSelfRef.mv_npu_top__DOT__a_val;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__x_val = vlSelfRef.mv_npu_top__DOT__x_val;
    vlSelfRef.mv_npu_top__DOT__in_valid = vlSelfRef.in_valid;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_in 
        = vlSelfRef.mv_npu_top__DOT__bias_hold;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en 
        = vlSelfRef.mv_npu_top__DOT__bias_en_runtime;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en 
        = vlSelfRef.mv_npu_top__DOT__relu_en_runtime;
    vlSelfRef.mv_npu_top__DOT__rst_n = vlSelfRef.rst_n;
    vlSelfRef.mv_npu_top__DOT__out_ready = vlSelfRef.out_ready;
    vlSelfRef.mv_npu_top__DOT__clk = vlSelfRef.clk;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc_out 
        = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc;
    vlSelfRef.mv_npu_top__DOT__cfg_word = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_word;
    vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_data 
        = vlSelfRef.mv_npu_top__DOT__in_data;
    vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type 
        = vlSelfRef.mv_npu_top__DOT__in_type;
    vlSelfRef.out_valid = vlSelfRef.mv_npu_top__DOT__out_valid;
    vlSelfRef.out_data = vlSelfRef.mv_npu_top__DOT__out_data;
    vlSelfRef.out_last = vlSelfRef.mv_npu_top__DOT__out_last;
    vlSelfRef.busy = vlSelfRef.mv_npu_top__DOT__busy;
    vlSelfRef.status_err = vlSelfRef.mv_npu_top__DOT__status_err;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__we = vlSelfRef.mv_npu_top__DOT__x_we;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__waddr = vlSelfRef.mv_npu_top__DOT__x_waddr;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__wdata = vlSelfRef.mv_npu_top__DOT__x_wdata;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_valid 
        = vlSelfRef.mv_npu_top__DOT__cfg_valid;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__prod = (0x0000ffffU 
                                                   & VL_MULS_III(16, 
                                                                 (0x0000ffffU 
                                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__a_val))), 
                                                                 (0x0000ffffU 
                                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__x_val)))));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__in_beat_accepted 
        = vlSelfRef.mv_npu_top__DOT__in_valid;
    vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_valid 
        = vlSelfRef.mv_npu_top__DOT__in_valid;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__rst_n 
        = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_ready 
        = vlSelfRef.mv_npu_top__DOT__out_ready;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__clk 
        = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__acc_out = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc_out;
    vlSelfRef.mv_npu_top__DOT__cfg_m = (0x000000ffU 
                                        & (IData)((vlSelfRef.mv_npu_top__DOT__cfg_word 
                                                   >> 8U)));
    vlSelfRef.mv_npu_top__DOT__cfg_n = (0x000000ffU 
                                        & (IData)((vlSelfRef.mv_npu_top__DOT__cfg_word 
                                                   >> 0x00000010U)));
    vlSelfRef.mv_npu_top__DOT__cfg_bias_en = (1U & (IData)(vlSelfRef.mv_npu_top__DOT__cfg_word));
    vlSelfRef.mv_npu_top__DOT__cfg_relu_en = (1U & (IData)(
                                                           (vlSelfRef.mv_npu_top__DOT__cfg_word 
                                                            >> 1U)));
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_accept_pulse 
        = ((IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid) 
           & (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_ready));
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in 
        = vlSelfRef.mv_npu_top__DOT__acc_out;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m = vlSelfRef.mv_npu_top__DOT__cfg_m;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n = vlSelfRef.mv_npu_top__DOT__cfg_n;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_bias_en;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_relu_en;
    vlSelfRef.mv_npu_top__DOT__out_accept_pulse = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_accept_pulse;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre = 
        ((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en)
          ? (vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in 
             + vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_in)
          : vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in);
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_out = 
        (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en) 
          & (vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre 
             >> 0x1fU)) ? 0U : vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre);
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted 
        = vlSelfRef.mv_npu_top__DOT__out_accept_pulse;
    vlSelfRef.mv_npu_top__DOT__y_post = vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_out;
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
                Vtop___024root___ico_sequent__TOP__0(vlSelf);
            }
        }
    }
    return (__VicoExecute);
}

bool Vtop___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_anySet__act\n"); );
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

void Vtop___024root___nba_sequent__TOP__4(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__4\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    SData/*8:0*/ __Vdly__mv_npu_top__DOT__row_idx;
    __Vdly__mv_npu_top__DOT__row_idx = 0;
    SData/*8:0*/ __Vdly__mv_npu_top__DOT__col_idx;
    __Vdly__mv_npu_top__DOT__col_idx = 0;
    CData/*0:0*/ __Vdly__mv_npu_top__DOT__compute_active;
    __Vdly__mv_npu_top__DOT__compute_active = 0;
    // Body
    __Vdly__mv_npu_top__DOT__row_idx = vlSelfRef.mv_npu_top__DOT__row_idx;
    __Vdly__mv_npu_top__DOT__col_idx = vlSelfRef.mv_npu_top__DOT__col_idx;
    __Vdly__mv_npu_top__DOT__compute_active = vlSelfRef.mv_npu_top__DOT__compute_active;
    if (vlSelfRef.mv_npu_top__DOT__rst_n) {
        vlSelfRef.mv_npu_top__DOT__start_row = 0U;
        vlSelfRef.mv_npu_top__DOT__step_valid = 0U;
        vlSelfRef.mv_npu_top__DOT__out_in_valid = 0U;
        if (vlSelfRef.mv_npu_top__DOT__cfg_valid) {
            vlSelfRef.mv_npu_top__DOT__bias_en_runtime 
                = vlSelfRef.mv_npu_top__DOT__cfg_bias_en;
            vlSelfRef.mv_npu_top__DOT__relu_en_runtime 
                = vlSelfRef.mv_npu_top__DOT__cfg_relu_en;
            __Vdly__mv_npu_top__DOT__row_idx = 0U;
            __Vdly__mv_npu_top__DOT__col_idx = 0U;
            __Vdly__mv_npu_top__DOT__compute_active = 1U;
            vlSelfRef.mv_npu_top__DOT__start_row = 1U;
        }
        if (((IData)(vlSelfRef.mv_npu_top__DOT__compute_active) 
             & (IData)(vlSelfRef.mv_npu_top__DOT__a_lane_valid))) {
            vlSelfRef.mv_npu_top__DOT__a_val = (0x000000ffU 
                                                & vlSelfRef.mv_npu_top__DOT__a_lane_data[0U]);
            vlSelfRef.mv_npu_top__DOT__x_raddr = (0x000000ffU 
                                                  & (IData)(vlSelfRef.mv_npu_top__DOT__col_idx));
            vlSelfRef.mv_npu_top__DOT__x_val = vlSelfRef.mv_npu_top__DOT__x_rdata;
            vlSelfRef.mv_npu_top__DOT__step_valid = 1U;
            if (((IData)(vlSelfRef.mv_npu_top__DOT__col_idx) 
                 == (0x000001ffU & ((IData)(vlSelfRef.mv_npu_top__DOT__n_runtime) 
                                    - (IData)(1U))))) {
                __Vdly__mv_npu_top__DOT__col_idx = 0U;
                if (vlSelfRef.mv_npu_top__DOT__bias_valid) {
                    vlSelfRef.mv_npu_top__DOT__bias_hold 
                        = vlSelfRef.mv_npu_top__DOT__bias_data;
                }
                vlSelfRef.mv_npu_top__DOT__out_in_valid = 1U;
                vlSelfRef.mv_npu_top__DOT__out_in_data 
                    = vlSelfRef.mv_npu_top__DOT__y_post;
                if (((IData)(vlSelfRef.mv_npu_top__DOT__row_idx) 
                     == (0x000001ffU & ((IData)(vlSelfRef.mv_npu_top__DOT__m_runtime) 
                                        - (IData)(1U))))) {
                    vlSelfRef.mv_npu_top__DOT__out_in_last = 1U;
                    __Vdly__mv_npu_top__DOT__compute_active = 0U;
                } else {
                    vlSelfRef.mv_npu_top__DOT__out_in_last = 0U;
                    __Vdly__mv_npu_top__DOT__row_idx 
                        = (0x000001ffU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.mv_npu_top__DOT__row_idx)));
                    vlSelfRef.mv_npu_top__DOT__start_row = 1U;
                }
            } else {
                __Vdly__mv_npu_top__DOT__col_idx = 
                    (0x000001ffU & ((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__col_idx)));
            }
        }
        if (vlSelfRef.mv_npu_top__DOT__cfg_valid) {
            vlSelfRef.mv_npu_top__DOT__n_runtime = vlSelfRef.mv_npu_top__DOT__cfg_n;
            vlSelfRef.mv_npu_top__DOT__m_runtime = vlSelfRef.mv_npu_top__DOT__cfg_m;
        }
    } else {
        vlSelfRef.mv_npu_top__DOT__bias_en_runtime = 0U;
        vlSelfRef.mv_npu_top__DOT__relu_en_runtime = 0U;
        __Vdly__mv_npu_top__DOT__row_idx = 0U;
        __Vdly__mv_npu_top__DOT__col_idx = 0U;
        __Vdly__mv_npu_top__DOT__compute_active = 0U;
        vlSelfRef.mv_npu_top__DOT__x_raddr = 0U;
        vlSelfRef.mv_npu_top__DOT__start_row = 0U;
        vlSelfRef.mv_npu_top__DOT__step_valid = 0U;
        vlSelfRef.mv_npu_top__DOT__a_val = 0U;
        vlSelfRef.mv_npu_top__DOT__x_val = 0U;
        vlSelfRef.mv_npu_top__DOT__bias_hold = 0U;
        vlSelfRef.mv_npu_top__DOT__out_in_valid = 0U;
        vlSelfRef.mv_npu_top__DOT__out_in_data = 0U;
        vlSelfRef.mv_npu_top__DOT__out_in_last = 0U;
        vlSelfRef.mv_npu_top__DOT__n_runtime = 0U;
        vlSelfRef.mv_npu_top__DOT__m_runtime = 0U;
    }
    vlSelfRef.mv_npu_top__DOT__row_idx = __Vdly__mv_npu_top__DOT__row_idx;
    vlSelfRef.mv_npu_top__DOT__col_idx = __Vdly__mv_npu_top__DOT__col_idx;
    vlSelfRef.mv_npu_top__DOT__compute_active = __Vdly__mv_npu_top__DOT__compute_active;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en 
        = vlSelfRef.mv_npu_top__DOT__bias_en_runtime;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en 
        = vlSelfRef.mv_npu_top__DOT__relu_en_runtime;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__start_row 
        = vlSelfRef.mv_npu_top__DOT__start_row;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__step_valid 
        = vlSelfRef.mv_npu_top__DOT__step_valid;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_valid 
        = vlSelfRef.mv_npu_top__DOT__out_in_valid;
    vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__raddr = vlSelfRef.mv_npu_top__DOT__x_raddr;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_data 
        = vlSelfRef.mv_npu_top__DOT__out_in_data;
    vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_last 
        = vlSelfRef.mv_npu_top__DOT__out_in_last;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__a_val = vlSelfRef.mv_npu_top__DOT__a_val;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__x_val = vlSelfRef.mv_npu_top__DOT__x_val;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_in 
        = vlSelfRef.mv_npu_top__DOT__bias_hold;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__prod = (0x0000ffffU 
                                                   & VL_MULS_III(16, 
                                                                 (0x0000ffffU 
                                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__a_val))), 
                                                                 (0x0000ffffU 
                                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__x_val)))));
}

void Vtop___024root___eval_nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__0
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__mv_npu_top__DOT__u_xmem__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__mv_npu_top__DOT__u_xmem__DOT__mem__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__mv_npu_top__DOT__u_xmem__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__mv_npu_top__DOT__u_xmem__DOT__mem__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__0___VdlySet__mv_npu_top__DOT__u_xmem__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__mv_npu_top__DOT__u_xmem__DOT__mem__v0 = 0;
            __Vinline_0__nba_sequent__TOP__0___VdlySet__mv_npu_top__DOT__u_xmem__DOT__mem__v0 = 0U;
            if (vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__we) {
                __Vinline_0__nba_sequent__TOP__0___VdlyVal__mv_npu_top__DOT__u_xmem__DOT__mem__v0 
                    = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__wdata;
                __Vinline_0__nba_sequent__TOP__0___VdlyDim0__mv_npu_top__DOT__u_xmem__DOT__mem__v0 
                    = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__waddr;
                __Vinline_0__nba_sequent__TOP__0___VdlySet__mv_npu_top__DOT__u_xmem__DOT__mem__v0 = 1U;
            }
            vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__rdata 
                = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__mem
                [vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__raddr];
            if (__Vinline_0__nba_sequent__TOP__0___VdlySet__mv_npu_top__DOT__u_xmem__DOT__mem__v0) {
                vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__mem[__Vinline_0__nba_sequent__TOP__0___VdlyDim0__mv_npu_top__DOT__u_xmem__DOT__mem__v0] 
                    = __Vinline_0__nba_sequent__TOP__0___VdlyVal__mv_npu_top__DOT__u_xmem__DOT__mem__v0;
            }
        }
    }
    if ((0x0000000000000020ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__1
            if (vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__rst_n) {
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_we = 0U;
                if (vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_valid) {
                    if ((2U & (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type))) {
                        if ((1U & (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type))) {
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_valid = 1U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_data 
                                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_data;
                        }
                        if ((1U & (~ (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type)))) {
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid = 1U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U] = 0U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[1U] = 0U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[2U] = 0U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[3U] = 0U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U] 
                                = ((0xffffff00U & vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U]) 
                                   | (0x000000ffU & vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_data));
                        }
                    }
                    if ((1U & (~ ((IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type) 
                                  >> 1U)))) {
                        if ((1U & (~ (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type)))) {
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_valid = 1U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_word 
                                = (QData)((IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_data));
                        }
                        if ((1U & (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_type))) {
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_we = 1U;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_wdata 
                                = (0x000000ffU & vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__in_data);
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_waddr 
                                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_count;
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_count 
                                = (0x000000ffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_count)));
                        } else {
                            vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_count = 0U;
                        }
                    }
                }
            } else {
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_we = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U] = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[1U] = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[2U] = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[3U] = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_data = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_wdata = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_count = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_waddr = 0U;
                vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_word = 0ULL;
            }
            vlSelfRef.mv_npu_top__DOT__x_we = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_we;
            vlSelfRef.mv_npu_top__DOT__x_wdata = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_wdata;
            vlSelfRef.mv_npu_top__DOT__x_waddr = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__x_waddr;
            vlSelfRef.mv_npu_top__DOT__cfg_word = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_word;
            vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__we 
                = vlSelfRef.mv_npu_top__DOT__x_we;
            vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__wdata 
                = vlSelfRef.mv_npu_top__DOT__x_wdata;
            vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__waddr 
                = vlSelfRef.mv_npu_top__DOT__x_waddr;
        }
    }
    if ((4ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__2
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc;
            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc = 0;
            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc 
                = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc;
            if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__rst_n) {
                if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__start_row) {
                    __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc = 0U;
                } else if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__step_valid) {
                    __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc 
                        = (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc 
                           + (((- (IData)((1U & ((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__prod) 
                                                 >> 0x0fU)))) 
                               << 0x00000010U) | (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__prod)));
                }
            } else {
                __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__u_mac__DOT__acc;
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc_out 
                = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc;
            vlSelfRef.mv_npu_top__DOT__acc_out = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__acc_out;
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in 
                = vlSelfRef.mv_npu_top__DOT__acc_out;
        }
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__3
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid;
            __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid = 0;
            __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid 
                = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid;
            if (vlSelfRef.mv_npu_top__DOT__u_out__DOT__rst_n) {
                if (((IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid) 
                     & (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_ready))) {
                    __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid = 0U;
                }
                if ((((~ (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid)) 
                      | ((IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid) 
                         & (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_ready))) 
                     & (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_valid))) {
                    __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid = 1U;
                    vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_data 
                        = vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_data;
                    vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_last 
                        = vlSelfRef.mv_npu_top__DOT__u_out__DOT__in_last;
                }
            } else {
                __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_data = 0U;
                vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_last = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_out__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__out_data = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_data;
            vlSelfRef.mv_npu_top__DOT__out_last = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_last;
            vlSelfRef.mv_npu_top__DOT__out_valid = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_accept_pulse 
                = ((IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_valid) 
                   & (IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_ready));
            vlSelfRef.out_data = vlSelfRef.mv_npu_top__DOT__out_data;
            vlSelfRef.out_last = vlSelfRef.mv_npu_top__DOT__out_last;
            vlSelfRef.out_valid = vlSelfRef.mv_npu_top__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__out_accept_pulse 
                = vlSelfRef.mv_npu_top__DOT__u_out__DOT__out_accept_pulse;
        }
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtop___024root___nba_sequent__TOP__4(vlSelf);
    }
    if ((0x0000000000000010ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__5
            if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rst_n) {
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse = 0U;
                if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__in_beat_accepted) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse = 1U;
                }
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse = 0U;
                if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse = 1U;
                }
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse = 0U;
                if (((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__busy) 
                     & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted))) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse = 0U;
                }
                if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_valid) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_err 
                        = ((((0U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m)) 
                             | (0U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n))) 
                            | (0x0100U < (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m))) 
                           | (0x0100U < (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n)));
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__busy 
                        = (1U & (~ ((((0U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m)) 
                                      | (0U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n))) 
                                     | (0x0100U < (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m))) 
                                    | (0x0100U < (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n)))));
                }
            } else {
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse = 0U;
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse = 0U;
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_err = 0U;
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse = 0U;
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__busy = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__compute_step_pulse 
                = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse;
            vlSelfRef.mv_npu_top__DOT__row_finalize_pulse 
                = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse;
            vlSelfRef.mv_npu_top__DOT__status_err = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_err;
            vlSelfRef.mv_npu_top__DOT__job_done_pulse 
                = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse;
            vlSelfRef.status_err = vlSelfRef.mv_npu_top__DOT__status_err;
            vlSelfRef.mv_npu_top__DOT__busy = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__busy;
            vlSelfRef.busy = vlSelfRef.mv_npu_top__DOT__busy;
        }
    }
    if ((0x0000000000000020ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__6
            vlSelfRef.mv_npu_top__DOT__cfg_bias_en 
                = (1U & (IData)(vlSelfRef.mv_npu_top__DOT__cfg_word));
            vlSelfRef.mv_npu_top__DOT__cfg_relu_en 
                = (1U & (IData)((vlSelfRef.mv_npu_top__DOT__cfg_word 
                                 >> 1U)));
            vlSelfRef.mv_npu_top__DOT__a_lane_valid 
                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid;
            vlSelfRef.mv_npu_top__DOT__a_lane_data[0U] 
                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[0U];
            vlSelfRef.mv_npu_top__DOT__a_lane_data[1U] 
                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[1U];
            vlSelfRef.mv_npu_top__DOT__a_lane_data[2U] 
                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[2U];
            vlSelfRef.mv_npu_top__DOT__a_lane_data[3U] 
                = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__a_lane_data[3U];
            vlSelfRef.mv_npu_top__DOT__bias_valid = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_valid;
            vlSelfRef.mv_npu_top__DOT__bias_data = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__bias_data;
            vlSelfRef.mv_npu_top__DOT__cfg_n = (0x000000ffU 
                                                & (IData)(
                                                          (vlSelfRef.mv_npu_top__DOT__cfg_word 
                                                           >> 0x00000010U)));
            vlSelfRef.mv_npu_top__DOT__cfg_m = (0x000000ffU 
                                                & (IData)(
                                                          (vlSelfRef.mv_npu_top__DOT__cfg_word 
                                                           >> 8U)));
            vlSelfRef.mv_npu_top__DOT__cfg_valid = vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__cfg_valid;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en 
                = vlSelfRef.mv_npu_top__DOT__cfg_bias_en;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en 
                = vlSelfRef.mv_npu_top__DOT__cfg_relu_en;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_n 
                = vlSelfRef.mv_npu_top__DOT__cfg_n;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_m 
                = vlSelfRef.mv_npu_top__DOT__cfg_m;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_valid 
                = vlSelfRef.mv_npu_top__DOT__cfg_valid;
        }
    }
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__7
            vlSelfRef.mv_npu_top__DOT__x_rdata = vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__rdata;
        }
    }
    if ((5ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__0
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre 
                = ((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en)
                    ? (vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in 
                       + vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_in)
                    : vlSelfRef.mv_npu_top__DOT__u_post__DOT__acc_in);
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_out 
                = (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en) 
                    & (vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre 
                       >> 0x1fU)) ? 0U : vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_pre);
            vlSelfRef.mv_npu_top__DOT__y_post = vlSelfRef.mv_npu_top__DOT__u_post__DOT__y_out;
        }
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__8
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted 
                = vlSelfRef.mv_npu_top__DOT__out_accept_pulse;
        }
    }
}

void Vtop___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtop___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vtop___024root___eval_phase__act(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__act\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    {
        // Inlined CFunc: _eval_triggers_vec__act
        vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                        (((((IData)(vlSelfRef.mv_npu_top__DOT__u_input_router__DOT__clk) 
                                                            & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_input_router__DOT__clk__0))) 
                                                           << 5U) 
                                                          | (((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk) 
                                                              & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0))) 
                                                             << 4U)) 
                                                         | (((((IData)(vlSelfRef.mv_npu_top__DOT__u_xmem__DOT__clk) 
                                                               & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_xmem__DOT__clk__0))) 
                                                              << 3U) 
                                                             | (((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0))) 
                                                                << 2U)) 
                                                            | ((((IData)(vlSelfRef.mv_npu_top__DOT__u_out__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_out__DOT__clk__0))) 
                                                                << 1U) 
                                                               | ((IData)(vlSelfRef.mv_npu_top__DOT__clk) 
                                                                  & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0))))))));
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
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    Vtop___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    return (0U);
}

void Vtop___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool Vtop___024root___eval_phase__nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_phase__nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = Vtop___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        Vtop___024root___eval_nba(vlSelf);
        Vtop___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void Vtop___024root___eval(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VicoIterCount;
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VicoIterCount = 0U;
    vlSelfRef.__VicoFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VicoIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__ico(vlSelfRef.__VicoTriggered, "ico"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-220723-c7dc82/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
        }
        __VicoIterCount = ((IData)(1U) + __VicoIterCount);
        vlSelfRef.__VicoPhaseResult = Vtop___024root___eval_phase__ico(vlSelf);
        vlSelfRef.__VicoFirstIteration = 0U;
    } while (vlSelfRef.__VicoPhaseResult);
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            Vtop___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-220723-c7dc82/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-220723-c7dc82/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
            }
            vlSelfRef.__VactIterCount = ((IData)(1U) 
                                         + vlSelfRef.__VactIterCount);
            vlSelfRef.__VactPhaseResult = Vtop___024root___eval_phase__act(vlSelf);
        } while (vlSelfRef.__VactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = Vtop___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
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
    if (VL_UNLIKELY(((vlSelfRef.in_valid & 0xfeU)))) {
        Verilated::overWidthError("in_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.in_type & 0xfcU)))) {
        Verilated::overWidthError("in_type");
    }
    if (VL_UNLIKELY(((vlSelfRef.in_last & 0xfeU)))) {
        Verilated::overWidthError("in_last");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
}
#endif  // VL_DEBUG
