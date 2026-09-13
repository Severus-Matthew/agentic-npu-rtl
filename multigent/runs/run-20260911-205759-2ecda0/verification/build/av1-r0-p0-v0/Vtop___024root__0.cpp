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
    vlSelfRef.stream_matvec_int8__DOT__clk = vlSelfRef.clk;
    vlSelfRef.stream_matvec_int8__DOT__cmd_valid = vlSelfRef.cmd_valid;
    vlSelfRef.stream_matvec_int8__DOT__cmd_bias_enable 
        = vlSelfRef.cmd_bias_enable;
    vlSelfRef.stream_matvec_int8__DOT__cmd_relu_enable 
        = vlSelfRef.cmd_relu_enable;
    vlSelfRef.stream_matvec_int8__DOT__in_valid = vlSelfRef.in_valid;
    vlSelfRef.stream_matvec_int8__DOT__in_data = vlSelfRef.in_data;
    vlSelfRef.stream_matvec_int8__DOT__out_ready = vlSelfRef.out_ready;
    vlSelfRef.stream_matvec_int8__DOT__done_ready = vlSelfRef.done_ready;
    vlSelfRef.stream_matvec_int8__DOT__vector_write_ext 
        = vlSelfRef.stream_matvec_int8__DOT__vector_write_index;
    vlSelfRef.stream_matvec_int8__DOT__column_ext = vlSelfRef.stream_matvec_int8__DOT__column_index;
    vlSelfRef.stream_matvec_int8__DOT__last_lane = 
        ((IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height) 
         == (0x0000001fU & ((IData)(1U) + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index))));
    vlSelfRef.stream_matvec_int8__DOT__cols_ext = vlSelfRef.stream_matvec_int8__DOT__cols_q;
    vlSelfRef.stream_matvec_int8__DOT__cmd_rows = vlSelfRef.cmd_rows;
    vlSelfRef.stream_matvec_int8__DOT__cmd_cols = vlSelfRef.cmd_cols;
    vlSelfRef.stream_matvec_int8__DOT__rows_ext = vlSelfRef.stream_matvec_int8__DOT__rows_q;
    vlSelfRef.stream_matvec_int8__DOT__base_ext = vlSelfRef.stream_matvec_int8__DOT__tile_base;
    vlSelfRef.stream_matvec_int8__DOT__rst = vlSelfRef.rst;
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[0U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[1U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[2U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[3U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[4U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[5U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[6U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[7U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[8U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[9U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[10U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[11U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[12U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[13U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[14U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[15U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__vector_value 
        = vlSelfRef.stream_matvec_int8__DOT__vector_store
        [vlSelfRef.stream_matvec_int8__DOT__column_index];
    vlSelfRef.stream_matvec_int8__DOT__last_column 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__cols_ext 
                          - (IData)(1U)));
    vlSelfRef.stream_matvec_int8__DOT__command_legal 
        = ((0U != (IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_rows)) 
           & ((0U != (IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_cols)) 
              & ((0x0100U >= (IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_rows)) 
                 & (0x0100U >= (IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_cols)))));
    vlSelfRef.stream_matvec_int8__DOT__next_base = 
        (0x0001ffffU & ((IData)(0x00000010U) + vlSelfRef.stream_matvec_int8__DOT__base_ext));
    vlSelfRef.stream_matvec_int8__DOT__remaining_rows 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
                          - vlSelfRef.stream_matvec_int8__DOT__base_ext));
    vlSelfRef.stream_matvec_int8__DOT__final_tile = 
        (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
         == (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__base_ext 
                            + (IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height))));
    vlSelfRef.stream_matvec_int8__DOT__current_row 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__base_ext 
                          + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index)));
    vlSelfRef.stream_matvec_int8__DOT__cmd_ready = 0U;
    vlSelfRef.stream_matvec_int8__DOT__in_ready = 0U;
    vlSelfRef.stream_matvec_int8__DOT__out_valid = 0U;
    vlSelfRef.stream_matvec_int8__DOT__done_valid = 0U;
    vlSelfRef.stream_matvec_int8__DOT__done_error = 0U;
    vlSelfRef.stream_matvec_int8__DOT__out_data = 0U;
    vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[0U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[0U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[1U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[1U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[2U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[2U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[3U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[3U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[4U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[4U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[5U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[5U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[6U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[6U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[7U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[7U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[8U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[8U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[9U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[9U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[10U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[10U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[11U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[11U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[12U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[12U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[13U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[13U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[14U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[14U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[15U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[15U]);
    vlSelfRef.stream_matvec_int8__DOT__product[0U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[0U])), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value)))));
    vlSelfRef.stream_matvec_int8__DOT__product[1U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[1U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[2U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[2U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[3U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[3U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[4U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[4U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[5U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[5U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[6U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[6U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[7U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[7U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[8U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[8U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[9U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[9U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[10U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[10U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[11U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[11U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[12U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[12U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[13U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[13U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[14U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[14U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[15U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[15U]))));
    vlSelfRef.stream_matvec_int8__DOT__out_last = 0U;
    if ((1U & (~ (IData)(vlSelfRef.stream_matvec_int8__DOT__rst)))) {
        vlSelfRef.stream_matvec_int8__DOT__cmd_ready 
            = (0U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state));
        vlSelfRef.stream_matvec_int8__DOT__in_ready 
            = (((1U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state)) 
                | (3U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) 
               | (4U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state)));
        if ((7U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__out_valid = 1U;
            vlSelfRef.stream_matvec_int8__DOT__out_data 
                = vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank
                [vlSelfRef.stream_matvec_int8__DOT__lane_index];
            vlSelfRef.stream_matvec_int8__DOT__out_last 
                = (vlSelfRef.stream_matvec_int8__DOT__current_row 
                   == (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
                                      - (IData)(1U))));
        }
        if ((8U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__done_valid = 1U;
            vlSelfRef.stream_matvec_int8__DOT__done_error 
                = vlSelfRef.stream_matvec_int8__DOT__error_q;
        }
    }
    vlSelfRef.cmd_ready = vlSelfRef.stream_matvec_int8__DOT__cmd_ready;
    vlSelfRef.in_ready = vlSelfRef.stream_matvec_int8__DOT__in_ready;
    vlSelfRef.out_valid = vlSelfRef.stream_matvec_int8__DOT__out_valid;
    vlSelfRef.done_valid = vlSelfRef.stream_matvec_int8__DOT__done_valid;
    vlSelfRef.done_error = vlSelfRef.stream_matvec_int8__DOT__done_error;
    vlSelfRef.out_data = vlSelfRef.stream_matvec_int8__DOT__out_data;
    vlSelfRef.stream_matvec_int8__DOT__final_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__extended_product[0U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[0U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[0U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[1U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[1U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[1U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[2U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[2U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[2U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[3U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[3U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[3U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[4U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[4U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[4U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[5U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[5U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[5U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[6U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[6U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[6U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[7U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[7U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[7U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[8U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[8U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[8U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[9U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[9U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[9U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[10U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[10U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[10U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[11U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[11U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[11U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[12U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[12U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[12U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[13U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[13U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[13U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[14U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[14U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[14U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[15U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[15U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[15U]);
    vlSelfRef.out_last = vlSelfRef.stream_matvec_int8__DOT__out_last;
    vlSelfRef.stream_matvec_int8__DOT__mac_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[0U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[0U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[1U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[1U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[2U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[2U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[3U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[3U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[4U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[4U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[5U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[5U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[6U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[6U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[7U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[7U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[8U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[8U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[9U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[9U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[10U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[10U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[11U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[11U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[12U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[12U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[13U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[13U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[14U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[14U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[15U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[15U]);
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
    CData/*3:0*/ __Vdly__stream_matvec_int8__DOT__state;
    __Vdly__stream_matvec_int8__DOT__state = 0;
    CData/*0:0*/ __Vdly__stream_matvec_int8__DOT__bias_enable_q;
    __Vdly__stream_matvec_int8__DOT__bias_enable_q = 0;
    CData/*7:0*/ __Vdly__stream_matvec_int8__DOT__vector_write_index;
    __Vdly__stream_matvec_int8__DOT__vector_write_index = 0;
    CData/*7:0*/ __Vdly__stream_matvec_int8__DOT__column_index;
    __Vdly__stream_matvec_int8__DOT__column_index = 0;
    CData/*4:0*/ __Vdly__stream_matvec_int8__DOT__tile_height;
    __Vdly__stream_matvec_int8__DOT__tile_height = 0;
    CData/*3:0*/ __Vdly__stream_matvec_int8__DOT__lane_index;
    __Vdly__stream_matvec_int8__DOT__lane_index = 0;
    IData/*31:0*/ __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v0;
    __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v0 = 0;
    CData/*3:0*/ __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v0;
    __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v0 = 0;
    IData/*31:0*/ __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v1;
    __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v1 = 0;
    CData/*3:0*/ __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v1;
    __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v1 = 0;
    CData/*7:0*/ __VdlyVal__stream_matvec_int8__DOT__matrix_staging__v0;
    __VdlyVal__stream_matvec_int8__DOT__matrix_staging__v0 = 0;
    CData/*3:0*/ __VdlyDim0__stream_matvec_int8__DOT__matrix_staging__v0;
    __VdlyDim0__stream_matvec_int8__DOT__matrix_staging__v0 = 0;
    CData/*0:0*/ __VdlySet__stream_matvec_int8__DOT__matrix_staging__v0;
    __VdlySet__stream_matvec_int8__DOT__matrix_staging__v0 = 0;
    IData/*31:0*/ __VdlyVal__stream_matvec_int8__DOT__bias_staging__v0;
    __VdlyVal__stream_matvec_int8__DOT__bias_staging__v0 = 0;
    CData/*3:0*/ __VdlyDim0__stream_matvec_int8__DOT__bias_staging__v0;
    __VdlyDim0__stream_matvec_int8__DOT__bias_staging__v0 = 0;
    CData/*0:0*/ __VdlySet__stream_matvec_int8__DOT__bias_staging__v0;
    __VdlySet__stream_matvec_int8__DOT__bias_staging__v0 = 0;
    CData/*3:0*/ __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v2;
    __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v2 = 0;
    CData/*7:0*/ __VdlyVal__stream_matvec_int8__DOT__vector_store__v0;
    __VdlyVal__stream_matvec_int8__DOT__vector_store__v0 = 0;
    CData/*7:0*/ __VdlyDim0__stream_matvec_int8__DOT__vector_store__v0;
    __VdlyDim0__stream_matvec_int8__DOT__vector_store__v0 = 0;
    CData/*0:0*/ __VdlySet__stream_matvec_int8__DOT__vector_store__v0;
    __VdlySet__stream_matvec_int8__DOT__vector_store__v0 = 0;
    // Body
    __Vdly__stream_matvec_int8__DOT__vector_write_index 
        = vlSelfRef.stream_matvec_int8__DOT__vector_write_index;
    __Vdly__stream_matvec_int8__DOT__tile_height = vlSelfRef.stream_matvec_int8__DOT__tile_height;
    __Vdly__stream_matvec_int8__DOT__lane_index = vlSelfRef.stream_matvec_int8__DOT__lane_index;
    __Vdly__stream_matvec_int8__DOT__state = vlSelfRef.stream_matvec_int8__DOT__state;
    __VdlySet__stream_matvec_int8__DOT__matrix_staging__v0 = 0U;
    __VdlySet__stream_matvec_int8__DOT__vector_store__v0 = 0U;
    __Vdly__stream_matvec_int8__DOT__column_index = vlSelfRef.stream_matvec_int8__DOT__column_index;
    __Vdly__stream_matvec_int8__DOT__bias_enable_q 
        = vlSelfRef.stream_matvec_int8__DOT__bias_enable_q;
    __VdlySet__stream_matvec_int8__DOT__bias_staging__v0 = 0U;
    if (vlSelfRef.stream_matvec_int8__DOT__rst) {
        __Vdly__stream_matvec_int8__DOT__state = 0U;
        vlSelfRef.stream_matvec_int8__DOT__rows_q = 0U;
        vlSelfRef.stream_matvec_int8__DOT__cols_q = 0U;
        __Vdly__stream_matvec_int8__DOT__bias_enable_q = 0U;
        vlSelfRef.stream_matvec_int8__DOT__relu_enable_q = 0U;
        vlSelfRef.stream_matvec_int8__DOT__error_q = 0U;
        __Vdly__stream_matvec_int8__DOT__vector_write_index = 0U;
        __Vdly__stream_matvec_int8__DOT__column_index = 0U;
        vlSelfRef.stream_matvec_int8__DOT__tile_base = 0U;
        __Vdly__stream_matvec_int8__DOT__tile_height = 0U;
        __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
    } else if ((8U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
        if ((4U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            __Vdly__stream_matvec_int8__DOT__state = 0U;
        } else if ((2U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            __Vdly__stream_matvec_int8__DOT__state = 0U;
        } else if ((1U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            __Vdly__stream_matvec_int8__DOT__state = 0U;
        } else if (((IData)(vlSelfRef.stream_matvec_int8__DOT__done_valid) 
                    & (IData)(vlSelfRef.stream_matvec_int8__DOT__done_ready))) {
            __Vdly__stream_matvec_int8__DOT__state = 0U;
        }
    } else if ((4U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
        if ((2U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
                if (((IData)(vlSelfRef.stream_matvec_int8__DOT__out_valid) 
                     & (IData)(vlSelfRef.stream_matvec_int8__DOT__out_ready))) {
                    if (vlSelfRef.stream_matvec_int8__DOT__last_lane) {
                        __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
                        if (vlSelfRef.stream_matvec_int8__DOT__final_tile) {
                            __Vdly__stream_matvec_int8__DOT__state = 8U;
                        } else {
                            vlSelfRef.stream_matvec_int8__DOT__tile_base 
                                = (0x000000ffU & vlSelfRef.stream_matvec_int8__DOT__next_base);
                            __Vdly__stream_matvec_int8__DOT__state = 2U;
                        }
                    } else {
                        __Vdly__stream_matvec_int8__DOT__lane_index 
                            = (0x0000000fU & ((IData)(1U) 
                                              + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index)));
                    }
                }
            } else {
                vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i = 0U;
                while (VL_GTS_III(32, 0x00000010U, vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i)) {
                    if (((0x0000001fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i) 
                         < (IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height))) {
                        __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v0 
                            = vlSelfRef.stream_matvec_int8__DOT__final_value
                            [(0x0000000fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i)];
                        __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v0 
                            = (0x0000000fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i);
                        vlSelfRef.__VdlyCommitQueuestream_matvec_int8__DOT__accumulator_result_bank.enqueue(__VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v0, (IData)(__VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v0));
                    }
                    vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i 
                        = ((IData)(1U) + vlSelfRef.stream_matvec_int8__DOT__unnamedblk3__DOT__i);
                }
                __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
                __Vdly__stream_matvec_int8__DOT__state = 7U;
            }
        } else if ((1U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i = 0U;
            while (VL_GTS_III(32, 0x00000010U, vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i)) {
                if (((0x0000001fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i) 
                     < (IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height))) {
                    __VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v1 
                        = vlSelfRef.stream_matvec_int8__DOT__mac_value
                        [(0x0000000fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i)];
                    __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v1 
                        = (0x0000000fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i);
                    vlSelfRef.__VdlyCommitQueuestream_matvec_int8__DOT__accumulator_result_bank.enqueue(__VdlyVal__stream_matvec_int8__DOT__accumulator_result_bank__v1, (IData)(__VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v1));
                }
                vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i 
                    = ((IData)(1U) + vlSelfRef.stream_matvec_int8__DOT__unnamedblk2__DOT__i);
            }
            if ((vlSelfRef.stream_matvec_int8__DOT__column_ext 
                 == vlSelfRef.stream_matvec_int8__DOT__last_column)) {
                __Vdly__stream_matvec_int8__DOT__state = 6U;
            } else {
                __Vdly__stream_matvec_int8__DOT__column_index 
                    = (0x000000ffU & ((IData)(1U) + (IData)(vlSelfRef.stream_matvec_int8__DOT__column_index)));
                __Vdly__stream_matvec_int8__DOT__state = 4U;
            }
        } else if (((IData)(vlSelfRef.stream_matvec_int8__DOT__in_valid) 
                    & (IData)(vlSelfRef.stream_matvec_int8__DOT__in_ready))) {
            __VdlyVal__stream_matvec_int8__DOT__matrix_staging__v0 
                = (0x000000ffU & vlSelfRef.stream_matvec_int8__DOT__in_data);
            __VdlyDim0__stream_matvec_int8__DOT__matrix_staging__v0 
                = vlSelfRef.stream_matvec_int8__DOT__lane_index;
            __VdlySet__stream_matvec_int8__DOT__matrix_staging__v0 = 1U;
            if (vlSelfRef.stream_matvec_int8__DOT__last_lane) {
                __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
                __Vdly__stream_matvec_int8__DOT__state = 5U;
            } else {
                __Vdly__stream_matvec_int8__DOT__lane_index 
                    = (0x0000000fU & ((IData)(1U) + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index)));
            }
        }
    } else if ((2U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
        if ((1U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            if (((IData)(vlSelfRef.stream_matvec_int8__DOT__in_valid) 
                 & (IData)(vlSelfRef.stream_matvec_int8__DOT__in_ready))) {
                __VdlyVal__stream_matvec_int8__DOT__bias_staging__v0 
                    = vlSelfRef.stream_matvec_int8__DOT__in_data;
                __VdlyDim0__stream_matvec_int8__DOT__bias_staging__v0 
                    = vlSelfRef.stream_matvec_int8__DOT__lane_index;
                __VdlySet__stream_matvec_int8__DOT__bias_staging__v0 = 1U;
                if (vlSelfRef.stream_matvec_int8__DOT__last_lane) {
                    __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
                    __Vdly__stream_matvec_int8__DOT__state = 4U;
                } else {
                    __Vdly__stream_matvec_int8__DOT__lane_index 
                        = (0x0000000fU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index)));
                }
            }
        } else {
            vlSelfRef.stream_matvec_int8__DOT__unnamedblk1__DOT__i = 0U;
            while (VL_GTS_III(32, 0x00000010U, vlSelfRef.stream_matvec_int8__DOT__unnamedblk1__DOT__i)) {
                __VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v2 
                    = (0x0000000fU & vlSelfRef.stream_matvec_int8__DOT__unnamedblk1__DOT__i);
                vlSelfRef.__VdlyCommitQueuestream_matvec_int8__DOT__accumulator_result_bank.enqueue(0U, (IData)(__VdlyDim0__stream_matvec_int8__DOT__accumulator_result_bank__v2));
                vlSelfRef.stream_matvec_int8__DOT__unnamedblk1__DOT__i 
                    = ((IData)(1U) + vlSelfRef.stream_matvec_int8__DOT__unnamedblk1__DOT__i);
            }
            __Vdly__stream_matvec_int8__DOT__column_index = 0U;
            __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
            __Vdly__stream_matvec_int8__DOT__tile_height 
                = ((0x00000010U < vlSelfRef.stream_matvec_int8__DOT__remaining_rows)
                    ? 0x00000010U : (0x0000001fU & vlSelfRef.stream_matvec_int8__DOT__remaining_rows));
            __Vdly__stream_matvec_int8__DOT__state 
                = ((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q)
                    ? 3U : 4U);
        }
    } else if ((1U & (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
        if (((IData)(vlSelfRef.stream_matvec_int8__DOT__in_valid) 
             & (IData)(vlSelfRef.stream_matvec_int8__DOT__in_ready))) {
            __VdlyVal__stream_matvec_int8__DOT__vector_store__v0 
                = (0x000000ffU & vlSelfRef.stream_matvec_int8__DOT__in_data);
            __VdlyDim0__stream_matvec_int8__DOT__vector_store__v0 
                = vlSelfRef.stream_matvec_int8__DOT__vector_write_index;
            __VdlySet__stream_matvec_int8__DOT__vector_store__v0 = 1U;
            if ((vlSelfRef.stream_matvec_int8__DOT__vector_write_ext 
                 == vlSelfRef.stream_matvec_int8__DOT__last_column)) {
                __Vdly__stream_matvec_int8__DOT__state = 2U;
            } else {
                __Vdly__stream_matvec_int8__DOT__vector_write_index 
                    = (0x000000ffU & ((IData)(1U) + (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_write_index)));
            }
        }
    } else if (((IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_valid) 
                & (IData)(vlSelfRef.stream_matvec_int8__DOT__cmd_ready))) {
        vlSelfRef.stream_matvec_int8__DOT__rows_q = vlSelfRef.stream_matvec_int8__DOT__cmd_rows;
        vlSelfRef.stream_matvec_int8__DOT__cols_q = vlSelfRef.stream_matvec_int8__DOT__cmd_cols;
        __Vdly__stream_matvec_int8__DOT__bias_enable_q 
            = vlSelfRef.stream_matvec_int8__DOT__cmd_bias_enable;
        vlSelfRef.stream_matvec_int8__DOT__relu_enable_q 
            = vlSelfRef.stream_matvec_int8__DOT__cmd_relu_enable;
        vlSelfRef.stream_matvec_int8__DOT__error_q 
            = (1U & (~ (IData)(vlSelfRef.stream_matvec_int8__DOT__command_legal)));
        __Vdly__stream_matvec_int8__DOT__vector_write_index = 0U;
        __Vdly__stream_matvec_int8__DOT__column_index = 0U;
        vlSelfRef.stream_matvec_int8__DOT__tile_base = 0U;
        __Vdly__stream_matvec_int8__DOT__tile_height = 0U;
        __Vdly__stream_matvec_int8__DOT__lane_index = 0U;
        __Vdly__stream_matvec_int8__DOT__state = ((IData)(vlSelfRef.stream_matvec_int8__DOT__command_legal)
                                                   ? 1U
                                                   : 8U);
    }
    vlSelfRef.stream_matvec_int8__DOT__vector_write_index 
        = __Vdly__stream_matvec_int8__DOT__vector_write_index;
    vlSelfRef.stream_matvec_int8__DOT__tile_height 
        = __Vdly__stream_matvec_int8__DOT__tile_height;
    vlSelfRef.stream_matvec_int8__DOT__lane_index = __Vdly__stream_matvec_int8__DOT__lane_index;
    vlSelfRef.stream_matvec_int8__DOT__state = __Vdly__stream_matvec_int8__DOT__state;
    vlSelfRef.__VdlyCommitQueuestream_matvec_int8__DOT__accumulator_result_bank.commit(vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank);
    if (__VdlySet__stream_matvec_int8__DOT__matrix_staging__v0) {
        vlSelfRef.stream_matvec_int8__DOT__matrix_staging[__VdlyDim0__stream_matvec_int8__DOT__matrix_staging__v0] 
            = __VdlyVal__stream_matvec_int8__DOT__matrix_staging__v0;
    }
    if (__VdlySet__stream_matvec_int8__DOT__vector_store__v0) {
        vlSelfRef.stream_matvec_int8__DOT__vector_store[__VdlyDim0__stream_matvec_int8__DOT__vector_store__v0] 
            = __VdlyVal__stream_matvec_int8__DOT__vector_store__v0;
    }
    vlSelfRef.stream_matvec_int8__DOT__column_index 
        = __Vdly__stream_matvec_int8__DOT__column_index;
    vlSelfRef.stream_matvec_int8__DOT__bias_enable_q 
        = __Vdly__stream_matvec_int8__DOT__bias_enable_q;
    if (__VdlySet__stream_matvec_int8__DOT__bias_staging__v0) {
        vlSelfRef.stream_matvec_int8__DOT__bias_staging[__VdlyDim0__stream_matvec_int8__DOT__bias_staging__v0] 
            = __VdlyVal__stream_matvec_int8__DOT__bias_staging__v0;
    }
    vlSelfRef.stream_matvec_int8__DOT__vector_write_ext 
        = vlSelfRef.stream_matvec_int8__DOT__vector_write_index;
    vlSelfRef.stream_matvec_int8__DOT__cols_ext = vlSelfRef.stream_matvec_int8__DOT__cols_q;
    vlSelfRef.stream_matvec_int8__DOT__rows_ext = vlSelfRef.stream_matvec_int8__DOT__rows_q;
    vlSelfRef.stream_matvec_int8__DOT__last_lane = 
        ((IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height) 
         == (0x0000001fU & ((IData)(1U) + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index))));
    vlSelfRef.stream_matvec_int8__DOT__base_ext = vlSelfRef.stream_matvec_int8__DOT__tile_base;
    vlSelfRef.stream_matvec_int8__DOT__cmd_ready = 0U;
    vlSelfRef.stream_matvec_int8__DOT__in_ready = 0U;
    vlSelfRef.stream_matvec_int8__DOT__out_valid = 0U;
    vlSelfRef.stream_matvec_int8__DOT__done_valid = 0U;
    vlSelfRef.stream_matvec_int8__DOT__done_error = 0U;
    vlSelfRef.stream_matvec_int8__DOT__out_data = 0U;
    vlSelfRef.stream_matvec_int8__DOT__column_ext = vlSelfRef.stream_matvec_int8__DOT__column_index;
    vlSelfRef.stream_matvec_int8__DOT__vector_value 
        = vlSelfRef.stream_matvec_int8__DOT__vector_store
        [vlSelfRef.stream_matvec_int8__DOT__column_index];
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[0U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[1U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[2U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[3U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[4U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[5U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[6U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[7U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[8U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[9U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[10U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[11U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[12U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[13U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[14U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__selected_bias[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__bias_staging[15U] 
           & (- (IData)((IData)(vlSelfRef.stream_matvec_int8__DOT__bias_enable_q))));
    vlSelfRef.stream_matvec_int8__DOT__last_column 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__cols_ext 
                          - (IData)(1U)));
    vlSelfRef.stream_matvec_int8__DOT__next_base = 
        (0x0001ffffU & ((IData)(0x00000010U) + vlSelfRef.stream_matvec_int8__DOT__base_ext));
    vlSelfRef.stream_matvec_int8__DOT__remaining_rows 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
                          - vlSelfRef.stream_matvec_int8__DOT__base_ext));
    vlSelfRef.stream_matvec_int8__DOT__final_tile = 
        (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
         == (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__base_ext 
                            + (IData)(vlSelfRef.stream_matvec_int8__DOT__tile_height))));
    vlSelfRef.stream_matvec_int8__DOT__current_row 
        = (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__base_ext 
                          + (IData)(vlSelfRef.stream_matvec_int8__DOT__lane_index)));
    if ((1U & (~ (IData)(vlSelfRef.stream_matvec_int8__DOT__rst)))) {
        vlSelfRef.stream_matvec_int8__DOT__cmd_ready 
            = (0U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state));
        vlSelfRef.cmd_ready = vlSelfRef.stream_matvec_int8__DOT__cmd_ready;
        vlSelfRef.stream_matvec_int8__DOT__in_ready 
            = (((1U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state)) 
                | (3U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) 
               | (4U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state)));
        vlSelfRef.in_ready = vlSelfRef.stream_matvec_int8__DOT__in_ready;
        if ((7U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__out_valid = 1U;
            vlSelfRef.stream_matvec_int8__DOT__out_data 
                = vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank
                [vlSelfRef.stream_matvec_int8__DOT__lane_index];
        }
        vlSelfRef.out_valid = vlSelfRef.stream_matvec_int8__DOT__out_valid;
        if ((8U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__done_valid = 1U;
            vlSelfRef.stream_matvec_int8__DOT__done_error 
                = vlSelfRef.stream_matvec_int8__DOT__error_q;
        }
        vlSelfRef.done_valid = vlSelfRef.stream_matvec_int8__DOT__done_valid;
        vlSelfRef.done_error = vlSelfRef.stream_matvec_int8__DOT__done_error;
    } else {
        vlSelfRef.cmd_ready = vlSelfRef.stream_matvec_int8__DOT__cmd_ready;
        vlSelfRef.in_ready = vlSelfRef.stream_matvec_int8__DOT__in_ready;
        vlSelfRef.out_valid = vlSelfRef.stream_matvec_int8__DOT__out_valid;
        vlSelfRef.done_valid = vlSelfRef.stream_matvec_int8__DOT__done_valid;
        vlSelfRef.done_error = vlSelfRef.stream_matvec_int8__DOT__done_error;
    }
    vlSelfRef.out_data = vlSelfRef.stream_matvec_int8__DOT__out_data;
    vlSelfRef.stream_matvec_int8__DOT__product[0U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[0U])), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value)))));
    vlSelfRef.stream_matvec_int8__DOT__product[1U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[1U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[2U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[2U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[3U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[3U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[4U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[4U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[5U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[5U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[6U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[6U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[7U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[7U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[8U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[8U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[9U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[9U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[10U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[10U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[11U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[11U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[12U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[12U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[13U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[13U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[14U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[14U]))));
    vlSelfRef.stream_matvec_int8__DOT__product[15U] 
        = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.stream_matvec_int8__DOT__vector_value))), 
                                     (0x0000ffffU & 
                                      VL_EXTENDS_II(16,8, vlSelfRef.stream_matvec_int8__DOT__matrix_staging[15U]))));
    vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[0U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[0U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[1U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[1U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[2U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[2U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[3U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[3U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[4U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[4U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[5U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[5U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[6U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[6U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[7U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[7U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[8U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[8U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[9U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[9U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[10U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[10U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[11U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[11U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[12U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[12U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[13U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[13U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[14U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[14U]);
    vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[15U] 
           + vlSelfRef.stream_matvec_int8__DOT__selected_bias[15U]);
    vlSelfRef.stream_matvec_int8__DOT__out_last = 0U;
    if ((1U & (~ (IData)(vlSelfRef.stream_matvec_int8__DOT__rst)))) {
        if ((7U == (IData)(vlSelfRef.stream_matvec_int8__DOT__state))) {
            vlSelfRef.stream_matvec_int8__DOT__out_last 
                = (vlSelfRef.stream_matvec_int8__DOT__current_row 
                   == (0x0001ffffU & (vlSelfRef.stream_matvec_int8__DOT__rows_ext 
                                      - (IData)(1U))));
        }
    }
    vlSelfRef.stream_matvec_int8__DOT__extended_product[0U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[0U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[0U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[1U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[1U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[1U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[2U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[2U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[2U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[3U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[3U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[3U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[4U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[4U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[4U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[5U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[5U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[5U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[6U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[6U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[6U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[7U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[7U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[7U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[8U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[8U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[8U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[9U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[9U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[9U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[10U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[10U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[10U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[11U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[11U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[11U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[12U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[12U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[12U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[13U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[13U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[13U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[14U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[14U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[14U]);
    vlSelfRef.stream_matvec_int8__DOT__extended_product[15U] 
        = (((- (IData)((1U & (vlSelfRef.stream_matvec_int8__DOT__product[15U] 
                              >> 0x0000000fU)))) << 0x00000010U) 
           | vlSelfRef.stream_matvec_int8__DOT__product[15U]);
    vlSelfRef.stream_matvec_int8__DOT__final_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[0U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[1U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[2U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[3U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[4U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[5U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[6U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[7U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[8U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[9U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[10U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[11U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[12U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[13U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[14U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.stream_matvec_int8__DOT__final_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
           & (- (IData)((1U & (~ ((IData)(vlSelfRef.stream_matvec_int8__DOT__relu_enable_q) 
                                  & (vlSelfRef.stream_matvec_int8__DOT__biased_value[15U] 
                                     >> 0x0000001fU)))))));
    vlSelfRef.out_last = vlSelfRef.stream_matvec_int8__DOT__out_last;
    vlSelfRef.stream_matvec_int8__DOT__mac_value[0U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[0U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[0U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[1U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[1U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[1U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[2U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[2U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[2U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[3U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[3U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[3U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[4U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[4U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[4U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[5U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[5U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[5U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[6U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[6U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[6U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[7U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[7U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[7U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[8U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[8U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[8U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[9U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[9U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[9U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[10U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[10U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[10U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[11U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[11U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[11U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[12U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[12U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[12U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[13U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[13U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[13U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[14U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[14U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[14U]);
    vlSelfRef.stream_matvec_int8__DOT__mac_value[15U] 
        = (vlSelfRef.stream_matvec_int8__DOT__accumulator_result_bank[15U] 
           + vlSelfRef.stream_matvec_int8__DOT__extended_product[15U]);
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
                                                        ((IData)(vlSelfRef.stream_matvec_int8__DOT__clk) 
                                                         & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__stream_matvec_int8__DOT__clk__0)))));
        vlSelfRef.__Vtrigprevexpr___TOP__stream_matvec_int8__DOT__clk__0 
            = vlSelfRef.stream_matvec_int8__DOT__clk;
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
            if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
                Vtop___024root___nba_sequent__TOP__0(vlSelf);
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-205759-2ecda0/rtl/stream_matvec_int8.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-205759-2ecda0/rtl/stream_matvec_int8.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-205759-2ecda0/rtl/stream_matvec_int8.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
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
    if (VL_UNLIKELY(((vlSelfRef.rst & 0xfeU)))) {
        Verilated::overWidthError("rst");
    }
    if (VL_UNLIKELY(((vlSelfRef.cmd_valid & 0xfeU)))) {
        Verilated::overWidthError("cmd_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.cmd_bias_enable & 0xfeU)))) {
        Verilated::overWidthError("cmd_bias_enable");
    }
    if (VL_UNLIKELY(((vlSelfRef.cmd_relu_enable & 0xfeU)))) {
        Verilated::overWidthError("cmd_relu_enable");
    }
    if (VL_UNLIKELY(((vlSelfRef.in_valid & 0xfeU)))) {
        Verilated::overWidthError("in_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
    if (VL_UNLIKELY(((vlSelfRef.done_ready & 0xfeU)))) {
        Verilated::overWidthError("done_ready");
    }
}
#endif  // VL_DEBUG
