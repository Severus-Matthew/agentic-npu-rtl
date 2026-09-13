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
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m));
    vlSelfRef.fc_accelerator__DOT__cmd_valid = vlSelfRef.cmd_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_step 
        = (5U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_init 
        = (4U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_we 
        = (6U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__out_ready = vlSelfRef.out_ready;
    vlSelfRef.fc_accelerator__DOT__status_ready = vlSelfRef.status_ready;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_wbase 
        = (0x00000ff8U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat 
                          << 3U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_wbase 
        = (0x0000003eU & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
                          << 1U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_wbase 
        = (0x00000ff8U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat 
                          << 3U));
    vlSelfRef.fc_accelerator__DOT__clk = vlSelfRef.clk;
    vlSelfRef.fc_accelerator__DOT__rst_n = vlSelfRef.rst_n;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_ready 
        = (0U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_ready 
        = (1U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_ready 
        = (2U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_ready 
        = (3U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_valid 
        = (7U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_valid 
        = (8U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__a_data = vlSelfRef.a_data;
    vlSelfRef.fc_accelerator__DOT__w_data = vlSelfRef.w_data;
    vlSelfRef.fc_accelerator__DOT__bias_data = vlSelfRef.bias_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg;
    vlSelfRef.fc_accelerator__DOT__cmd_data = vlSelfRef.cmd_data;
    vlSelfRef.fc_accelerator__DOT__bias_valid = vlSelfRef.bias_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rpair 
        = (0x000007ffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat);
    vlSelfRef.fc_accelerator__DOT__a_valid = vlSelfRef.a_valid;
    vlSelfRef.fc_accelerator__DOT__w_valid = vlSelfRef.w_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_valid 
        = vlSelfRef.fc_accelerator__DOT__cmd_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_step;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_init;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_ready 
        = vlSelfRef.fc_accelerator__DOT__out_ready;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_ready 
        = vlSelfRef.fc_accelerator__DOT__status_ready;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__clk 
        = vlSelfRef.fc_accelerator__DOT__clk;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__rst_n 
        = vlSelfRef.fc_accelerator__DOT__rst_n;
    vlSelfRef.fc_accelerator__DOT__cmd_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_ready;
    vlSelfRef.fc_accelerator__DOT__a_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_ready;
    vlSelfRef.fc_accelerator__DOT__w_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_ready;
    vlSelfRef.fc_accelerator__DOT__bias_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_ready;
    vlSelfRef.fc_accelerator__DOT__out_valid = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_valid;
    vlSelfRef.fc_accelerator__DOT__status_valid = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_data 
        = vlSelfRef.fc_accelerator__DOT__a_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_data 
        = vlSelfRef.fc_accelerator__DOT__w_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_data 
        = vlSelfRef.fc_accelerator__DOT__bias_data;
    vlSelfRef.fc_accelerator__DOT__status_code = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_data 
        = vlSelfRef.fc_accelerator__DOT__cmd_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_valid 
        = vlSelfRef.fc_accelerator__DOT__bias_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rpair;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_valid 
        = vlSelfRef.fc_accelerator__DOT__a_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_valid 
        = vlSelfRef.fc_accelerator__DOT__w_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
                + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r) 
               < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai 
            = ((((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
                 + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r) 
                * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k)) 
               + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k));
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active
            [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] 
                = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem
                [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai)];
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base) 
                + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c) 
               < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi 
            = ((((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k) 
                 * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)) 
                + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base)) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active
            [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem
                [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi)];
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)][(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                                  & VL_EXTENDS_II(16,8, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a
                                                                  [
                                                                  (7U 
                                                                   & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)])), 
                                             (0x0000ffffU 
                                              & VL_EXTENDS_II(16,8, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w
                                                              [
                                                              (7U 
                                                               & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]))));
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)][(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = (((- (IData)((1U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product
                                      [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                                      [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                                      >> 0x0fU)))) 
                    << 0x00000010U) | vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid = 0U;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l = 0U;
    while (VL_GTS_III(32, 2U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair) 
                << 1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row 
            = VL_DIVS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index, (IData)(8U));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col 
            = VL_MODDIVS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index, (IData)(8U));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
            = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col 
            = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index 
            = ((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
                * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col);
        if ((((VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row) 
               & VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col)) 
              & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
                 < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m))) 
             & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col 
                < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)))) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid 
                = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid) 
                   | (3U & ((IData)(1U) << (1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l))));
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = (0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row)]
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col)] 
                   + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem
                   [(0x0000003fU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col)]);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = ((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum
                    [(1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                    >> 0x1fU) ? 0U : vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum
                   [(1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)]);
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__clk;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__rst_n;
    vlSelfRef.cmd_ready = vlSelfRef.fc_accelerator__DOT__cmd_ready;
    vlSelfRef.a_ready = vlSelfRef.fc_accelerator__DOT__a_ready;
    vlSelfRef.w_ready = vlSelfRef.fc_accelerator__DOT__w_ready;
    vlSelfRef.bias_ready = vlSelfRef.fc_accelerator__DOT__bias_ready;
    vlSelfRef.out_valid = vlSelfRef.fc_accelerator__DOT__out_valid;
    vlSelfRef.status_valid = vlSelfRef.fc_accelerator__DOT__status_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wdata 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wdata 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_data;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_data;
    vlSelfRef.status_code = vlSelfRef.fc_accelerator__DOT__status_code;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_m 
        = (0x0000007fU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_data);
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_n 
        = (0x0000007fU & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_data 
                          >> 7U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_k 
        = (0x0000007fU & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_data 
                          >> 0x0000000eU));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we = 0U;
    if (((3U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_valid))) {
        if (((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
              << 1U) < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we 
                = (1U | (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we));
        }
        if ((((IData)(1U) + (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
                             << 1U)) < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we 
                = (2U | (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we));
        }
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata = 0ULL;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair) 
           << 1U);
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n));
    if (VL_LTS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata 
            = ((0xffffffff00000000ULL & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata) 
               | (IData)((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem
                                 [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index)])));
    }
    if (VL_LTS_III(32, ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index), vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata 
            = ((0x00000000ffffffffULL & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata) 
               | ((QData)((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem
                                  [(0x00000fffU & ((IData)(1U) 
                                                   + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index))])) 
                  << 0x00000020U));
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we = 0U;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we = 0U;
    if (((1U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_valid))) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane)) {
            if ((((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat 
                   << 3U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane) 
                 < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_total)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we 
                    = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we) 
                       | (0x00ffU & ((IData)(1U) << 
                                     (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane))));
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane);
        }
    }
    if (((2U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_valid))) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane)) {
            if ((((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat 
                   << 3U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane) 
                 < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_total)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we 
                    = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we) 
                       | (0x00ffU & ((IData)(1U) << 
                                     (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane))));
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane);
        }
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rdata 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_data 
        = (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rdata 
           & (- (QData)((IData)((7U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))))));
    vlSelfRef.fc_accelerator__DOT__out_data = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_data;
    vlSelfRef.out_data = vlSelfRef.fc_accelerator__DOT__out_data;
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

void Vtop___024root___nba_sequent__TOP__0(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__0\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*7:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0 = 0;
    SData/*11:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0 = 0;
    CData/*7:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0 = 0;
    SData/*11:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0 = 0;
    CData/*2:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0 = 0;
    CData/*2:0*/ __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0;
    __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0 = 0;
    IData/*31:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 = 0;
    CData/*2:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 = 0;
    CData/*2:0*/ __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1;
    __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 = 0;
    CData/*2:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2 = 0;
    CData/*2:0*/ __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2;
    __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2 = 0;
    IData/*31:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 = 0;
    CData/*5:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 = 0;
    CData/*0:0*/ __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 = 0;
    IData/*31:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 = 0;
    CData/*5:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 = 0;
    CData/*0:0*/ __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 = 0;
    IData/*31:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 = 0;
    SData/*11:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 = 0;
    CData/*0:0*/ __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 = 0;
    IData/*31:0*/ __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1;
    __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 = 0;
    SData/*11:0*/ __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1;
    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 = 0;
    CData/*0:0*/ __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 = 0;
    // Body
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 = 0U;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 = 0U;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 = 0U;
    __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 = 0U;
    if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)) {
            if ((1U & ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we) 
                       >> (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)))) {
                __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0 
                    = (0x000000ffU & (IData)((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wdata 
                                              >> (0x0000003fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)))));
                __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0 
                    = (0x00000fffU & ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase) 
                                      + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l));
                vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem.enqueue(__VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0, (IData)(__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem__v0));
            }
            if ((1U & ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we) 
                       >> (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)))) {
                __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0 
                    = (0x000000ffU & (IData)((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wdata 
                                              >> (0x0000003fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)))));
                __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0 
                    = (0x00000fffU & ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase) 
                                      + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l));
                vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem.enqueue(__VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0, (IData)(__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem__v0));
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l);
        }
    }
    if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n) {
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
            while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
                while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
                    __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0 
                        = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
                    __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0 
                        = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
                    vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator.enqueue(0U, (IData)(__VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0), __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v0);
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
                        = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
                }
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
                    = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
            }
        } else if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
            while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
                while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
                    if ((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active
                         [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] 
                         & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active
                         [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)])) {
                        __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 
                            = (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator
                               [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                               [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext
                               [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                               [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]);
                        __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 
                            = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
                        __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1 
                            = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
                        vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator.enqueue(__VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1, (IData)(__VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1), __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v1);
                    }
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
                        = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
                }
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
                    = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
            }
        }
    } else {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
            while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
                __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2 
                    = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
                __VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2 
                    = (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
                vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator.enqueue(0U, (IData)(__VdlyDim1__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2), __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator__v2);
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
                    = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
        }
    }
    if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n) {
        if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we))) {
            __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 
                = (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata);
            __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 
                = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase;
            __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0 = 1U;
        }
        if ((2U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we))) {
            __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 
                = (IData)((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata 
                           >> 0x20U));
            __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 
                = (0x0000003fU & ((IData)(1U) + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase)));
            __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1 = 1U;
        }
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we) {
            if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid))) {
                __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 
                    = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[0U];
                __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 
                    = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[0U];
                __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0 = 1U;
            }
            if ((2U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid))) {
                __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 
                    = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[1U];
                __VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 
                    = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[1U];
                __VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1 = 1U;
            }
        }
    }
    vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem.commit(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem);
    vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem.commit(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem);
    vlSelfRef.__VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator.commit(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator);
    if (__VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem[__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0] 
            = __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v0;
    }
    if (__VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem[__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1] 
            = __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem__v1;
    }
    if (__VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem[__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0] 
            = __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v0;
    }
    if (__VdlySet__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem[__VdlyDim0__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1] 
            = __VdlyVal__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem__v1;
    }
}

void Vtop___024root___nba_sequent__TOP__1(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_sequent__TOP__1\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*3:0*/ __Vdly__fc_accelerator__DOT__u_controller__DOT__state;
    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0;
    CData/*4:0*/ __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair;
    __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair = 0;
    // Body
    __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair;
    __Vdly__fc_accelerator__DOT__u_controller__DOT__state 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state;
    if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__rst_n) {
        if ((8U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
            if ((4U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0U;
            } else if ((2U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0U;
            } else if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0U;
            } else if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_ready) {
                __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0U;
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg = 0U;
            }
        } else if ((4U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
            if ((2U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                    if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_ready) {
                        if (((((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat) 
                              << 1U) >= vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_total)) {
                            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg = 0U;
                            __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 8U;
                        } else {
                            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat 
                                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat);
                        }
                    }
                } else if ((0x00000020U <= ((IData)(1U) 
                                            + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair)))) {
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair = 0U;
                    if ((((IData)(8U) + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base)) 
                         < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n))) {
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base 
                            = (0x0000007fU & ((IData)(8U) 
                                              + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base)));
                        __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 4U;
                    } else if ((((IData)(8U) + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base)) 
                                < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m))) {
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base 
                            = (0x0000007fU & ((IData)(8U) 
                                              + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base)));
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base = 0U;
                        __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 4U;
                    } else {
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat = 0U;
                        __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 7U;
                    }
                } else {
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair 
                        = (0x0000001fU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair)));
                }
            } else if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                if ((((IData)(1U) + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k)) 
                     >= (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k))) {
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair = 0U;
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 6U;
                } else {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k 
                        = (0x0000007fU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k)));
                }
            } else {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k = 0U;
                __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 5U;
            }
        } else if ((2U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
                if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_valid) {
                    if (((((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat) 
                          << 1U) >= vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total)) {
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base = 0U;
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base = 0U;
                        __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 4U;
                    } else {
                        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
                            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat);
                    }
                }
            } else if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_valid) {
                if (((((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat) 
                      << 3U) >= vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_total)) {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat = 0U;
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 3U;
                } else {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat 
                        = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat);
                }
            }
        } else if ((1U & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))) {
            if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_valid) {
                if (((((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat) 
                      << 3U) >= vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_total)) {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat = 0U;
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 2U;
                } else {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat 
                        = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat);
                }
            }
        } else {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat = 0U;
            __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair = 0U;
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k = 0U;
            if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_valid) {
                if (((((((0U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_m)) 
                         | (0U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_n))) 
                        | (0U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_k))) 
                       | (0x40U < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_m))) 
                      | (0x40U < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_n))) 
                     | (0x40U < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_k)))) {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg = 1U;
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 8U;
                } else {
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m 
                        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_m;
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n 
                        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_n;
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k 
                        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_k;
                    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg = 0U;
                    __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 1U;
                }
            }
        }
    } else {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base = 0U;
        __Vdly__fc_accelerator__DOT__u_controller__DOT__state = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k = 0U;
        __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg = 0U;
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair 
        = __Vdly__fc_accelerator__DOT__u_controller__DOT__finalize_pair;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state 
        = __Vdly__fc_accelerator__DOT__u_controller__DOT__state;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code_reg;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_wbase 
        = (0x0000003eU & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
                          << 1U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rpair 
        = (0x000007ffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__output_beat);
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_wbase 
        = (0x00000ff8U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat 
                          << 3U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_wbase 
        = (0x00000ff8U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat 
                          << 3U));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_pair;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_k;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_n_base;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_m_base;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_step 
        = (5U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_init 
        = (4U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_we 
        = (6U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_ready 
        = (0U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_ready 
        = (1U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_ready 
        = (2U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_ready 
        = (3U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_valid 
        = (7U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_valid 
        = (8U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we = 0U;
    if (((3U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_valid))) {
        if (((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
              << 1U) < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we 
                = (1U | (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we));
        }
        if ((((IData)(1U) + (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_beat 
                             << 1U)) < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__b_total)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we 
                = (2U | (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we));
        }
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_m) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_k) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n));
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we = 0U;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we = 0U;
    if (((1U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_valid))) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane)) {
            if ((((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__activation_beat 
                   << 3U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane) 
                 < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_total)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we 
                    = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we) 
                       | (0x00ffU & ((IData)(1U) << 
                                     (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane))));
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane);
        }
    }
    if (((2U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state)) 
         & (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_valid))) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane)) {
            if ((((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__weight_beat 
                   << 3U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane) 
                 < vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_total)) {
                vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we 
                    = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we) 
                       | (0x00ffU & ((IData)(1U) << 
                                     (7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane))));
            }
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__lane);
        }
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cfg_n;
    vlSelfRef.fc_accelerator__DOT__status_code = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_code;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rpair;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_wbase;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__compute_step;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__tile_init;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__finalize_we;
    vlSelfRef.fc_accelerator__DOT__cmd_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__cmd_ready;
    vlSelfRef.fc_accelerator__DOT__a_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_ready;
    vlSelfRef.fc_accelerator__DOT__w_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_ready;
    vlSelfRef.fc_accelerator__DOT__bias_ready = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_ready;
    vlSelfRef.fc_accelerator__DOT__out_valid = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_valid;
    vlSelfRef.fc_accelerator__DOT__status_valid = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__status_valid;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__bias_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__a_we;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__w_we;
    vlSelfRef.status_code = vlSelfRef.fc_accelerator__DOT__status_code;
    vlSelfRef.cmd_ready = vlSelfRef.fc_accelerator__DOT__cmd_ready;
    vlSelfRef.a_ready = vlSelfRef.fc_accelerator__DOT__a_ready;
    vlSelfRef.w_ready = vlSelfRef.fc_accelerator__DOT__w_ready;
    vlSelfRef.bias_ready = vlSelfRef.fc_accelerator__DOT__bias_ready;
    vlSelfRef.out_valid = vlSelfRef.fc_accelerator__DOT__out_valid;
    vlSelfRef.status_valid = vlSelfRef.fc_accelerator__DOT__status_valid;
}

void Vtop___024root___nba_comb__TOP__0(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___nba_comb__TOP__0\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
                + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r) 
               < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai 
            = ((((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
                 + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r) 
                * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k)) 
               + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k));
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active
            [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)] 
                = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem
                [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai)];
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base) 
                + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c) 
               < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi 
            = ((((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k) 
                 * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)) 
                + (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base)) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
        if (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active
            [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem
                [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi)];
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c = 0U;
        while (VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)][(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                                  & VL_EXTENDS_II(16,8, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a
                                                                  [
                                                                  (7U 
                                                                   & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)])), 
                                             (0x0000ffffU 
                                              & VL_EXTENDS_II(16,8, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w
                                                              [
                                                              (7U 
                                                               & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]))));
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext[(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)][(7U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                = (((- (IData)((1U & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product
                                      [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                                      [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)] 
                                      >> 0x0fU)))) 
                    << 0x00000010U) | vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r)]
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c)]);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c 
                = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c);
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid = 0U;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l = 0U;
    while (VL_GTS_III(32, 2U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] = 0U;
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index 
            = (((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair) 
                << 1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row 
            = VL_DIVS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index, (IData)(8U));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col 
            = VL_MODDIVS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index, (IData)(8U));
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
            = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col 
            = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col);
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index 
            = ((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
                * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)) 
               + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col);
        if ((((VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row) 
               & VL_GTS_III(32, 8U, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col)) 
              & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row 
                 < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m))) 
             & (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col 
                < (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n)))) {
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid 
                = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid) 
                   | (3U & ((IData)(1U) << (1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l))));
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = (0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row)]
                   [(7U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col)] 
                   + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem
                   [(0x0000003fU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col)]);
            vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data[(1U 
                                                                                & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                = ((vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum
                    [(1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)] 
                    >> 0x1fU) ? 0U : vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum
                   [(1U & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l)]);
        }
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l 
            = ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l);
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata = 0ULL;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair) 
           << 1U);
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total 
        = ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m) 
           * (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n));
    if (VL_LTS_III(32, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index, vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata 
            = ((0xffffffff00000000ULL & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata) 
               | (IData)((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem
                                 [(0x00000fffU & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index)])));
    }
    if (VL_LTS_III(32, ((IData)(1U) + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index), vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total)) {
        vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata 
            = ((0x00000000ffffffffULL & vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata) 
               | ((QData)((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem
                                  [(0x00000fffU & ((IData)(1U) 
                                                   + vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index))])) 
                  << 0x00000020U));
    }
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rdata 
        = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata;
    vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_data 
        = (vlSelfRef.fc_accelerator__DOT__u_controller__DOT__result_rdata 
           & (- (QData)((IData)((7U == (IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__state))))));
    vlSelfRef.fc_accelerator__DOT__out_data = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__out_data;
    vlSelfRef.out_data = vlSelfRef.fc_accelerator__DOT__out_data;
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
                                                        ((((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk) 
                                                           & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk__0))) 
                                                          << 1U) 
                                                         | ((IData)(vlSelfRef.fc_accelerator__DOT__u_controller__DOT__clk) 
                                                            & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__clk__0))))));
        vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__clk__0 
            = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__clk;
        vlSelfRef.__Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk__0 
            = vlSelfRef.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk;
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
        {
            // Inlined CFunc: _eval_nba
            if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
                Vtop___024root___nba_sequent__TOP__0(vlSelf);
            }
            if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
                Vtop___024root___nba_sequent__TOP__1(vlSelf);
            }
            if ((3ULL & vlSelfRef.__VnbaTriggered[0U])) {
                Vtop___024root___nba_comb__TOP__0(vlSelf);
            }
        }
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-180444-ec8862/rtl/fc_accelerator.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-180444-ec8862/rtl/fc_accelerator.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-180444-ec8862/rtl/fc_accelerator.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
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
    if (VL_UNLIKELY(((vlSelfRef.cmd_valid & 0xfeU)))) {
        Verilated::overWidthError("cmd_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.cmd_data & 0xffe00000U)))) {
        Verilated::overWidthError("cmd_data");
    }
    if (VL_UNLIKELY(((vlSelfRef.a_valid & 0xfeU)))) {
        Verilated::overWidthError("a_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.w_valid & 0xfeU)))) {
        Verilated::overWidthError("w_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bias_valid & 0xfeU)))) {
        Verilated::overWidthError("bias_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
    if (VL_UNLIKELY(((vlSelfRef.status_ready & 0xfeU)))) {
        Verilated::overWidthError("status_ready");
    }
}
#endif  // VL_DEBUG
