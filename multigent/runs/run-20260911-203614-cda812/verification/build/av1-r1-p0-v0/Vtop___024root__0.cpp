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
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr 
        = vlSelfRef.mv_npu_top__DOT__vec_wr_addr;
    vlSelfRef.mv_npu_top__DOT__row_done_pulse = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_done_pulse;
    vlSelfRef.mv_npu_top__DOT__cfg_M = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M;
    vlSelfRef.mv_npu_top__DOT__cmd_data = vlSelfRef.cmd_data;
    vlSelfRef.mv_npu_top__DOT__vec_data = vlSelfRef.vec_data;
    vlSelfRef.mv_npu_top__DOT__pp_out_data = vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_data;
    vlSelfRef.mv_npu_top__DOT__cmd_valid = vlSelfRef.cmd_valid;
    vlSelfRef.mv_npu_top__DOT__vec_valid = vlSelfRef.vec_valid;
    vlSelfRef.mv_npu_top__DOT__bias_data = vlSelfRef.bias_data;
    vlSelfRef.mv_npu_top__DOT__row_accum_out = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_accum_out;
    vlSelfRef.mv_npu_top__DOT__cfg_relu_en = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en;
    vlSelfRef.mv_npu_top__DOT__clk = vlSelfRef.clk;
    vlSelfRef.mv_npu_top__DOT__rst_n = vlSelfRef.rst_n;
    vlSelfRef.mv_npu_top__DOT__bias_valid = vlSelfRef.bias_valid;
    vlSelfRef.mv_npu_top__DOT__pp_out_valid = vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row 
        = (0x0000ffffU & (((IData)(0x0000000fU) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N)) 
                          >> 4U));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem = (0x0fU 
                                                   & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask = 0xffffU;
    if ((((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt) 
          == ((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row) 
              - (IData)(1U))) & (0U != (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem)))) {
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask 
            = (0x0000ffffU & (((IData)(1U) << (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem)) 
                              - (IData)(1U)));
    }
    vlSelfRef.mv_npu_top__DOT__mat_data[0U] = vlSelfRef.mat_data[0U];
    vlSelfRef.mv_npu_top__DOT__mat_data[1U] = vlSelfRef.mat_data[1U];
    vlSelfRef.mv_npu_top__DOT__mat_data[2U] = vlSelfRef.mat_data[2U];
    vlSelfRef.mv_npu_top__DOT__mat_data[3U] = vlSelfRef.mat_data[3U];
    vlSelfRef.mv_npu_top__DOT__rd_chunk_base = (0x000000f0U 
                                                & ((IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx) 
                                                   << 4U));
    vlSelfRef.mv_npu_top__DOT__cfg_bias_en = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en;
    vlSelfRef.mv_npu_top__DOT__mat_valid = vlSelfRef.mat_valid;
    vlSelfRef.mv_npu_top__DOT__out_ready = vlSelfRef.out_ready;
    vlSelfRef.mv_npu_top__DOT__status_error = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_busy 
        = (0U != (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st));
    vlSelfRef.mv_npu_top__DOT__cfg_N = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
        = vlSelfRef.mv_npu_top__DOT__cmd_data;
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_data 
        = vlSelfRef.mv_npu_top__DOT__vec_data;
    vlSelfRef.mv_npu_top__DOT__out_data = vlSelfRef.mv_npu_top__DOT__pp_out_data;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_data 
        = vlSelfRef.mv_npu_top__DOT__bias_data;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data 
        = vlSelfRef.mv_npu_top__DOT__row_accum_out;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_relu_en;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__clk 
        = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk = vlSelfRef.mv_npu_top__DOT__clk;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rst_n 
        = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rst_n = vlSelfRef.mv_npu_top__DOT__rst_n;
    vlSelfRef.mv_npu_top__DOT__out_valid = vlSelfRef.mv_npu_top__DOT__pp_out_valid;
    vlSelfRef.mv_npu_top__DOT__lane_valid_mask = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask;
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[0U] 
        = vlSelfRef.mv_npu_top__DOT__mat_data[0U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[1U] 
        = vlSelfRef.mv_npu_top__DOT__mat_data[1U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[2U] 
        = vlSelfRef.mv_npu_top__DOT__mat_data[2U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[3U] 
        = vlSelfRef.mv_npu_top__DOT__mat_data[3U];
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base 
        = vlSelfRef.mv_npu_top__DOT__rd_chunk_base;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_bias_en;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_ready 
        = vlSelfRef.mv_npu_top__DOT__out_ready;
    vlSelfRef.status_error = vlSelfRef.mv_npu_top__DOT__status_error;
    vlSelfRef.mv_npu_top__DOT__status_busy = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_busy;
    vlSelfRef.out_data = vlSelfRef.mv_npu_top__DOT__out_data;
    vlSelfRef.out_valid = vlSelfRef.mv_npu_top__DOT__out_valid;
    vlSelfRef.mv_npu_top__DOT__out_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__out_valid) 
                                           & (IData)(vlSelfRef.mv_npu_top__DOT__out_ready));
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__lane_valid_mask 
        = vlSelfRef.mv_npu_top__DOT__lane_valid_mask;
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[0U] 
        = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[0U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[1U] 
        = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[1U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[2U] 
        = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[2U];
    vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[3U] 
        = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in[3U];
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j = 0U;
    while (VL_GTS_III(32, 0x00000010U, vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j)) {
        VL_ASSIGNSEL_WI(128, 8, (0x0000007fU & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j)), vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data, 
                        ((0x00000100U > ((IData)(vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base) 
                                         + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j))
                          ? vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__mem
                         [(0x000000ffU & ((IData)(vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base) 
                                          + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j))]
                          : 0U));
        vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j 
            = ((IData)(1U) + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j);
    }
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
        = vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data;
    if (vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en) {
        vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
            = (vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data 
               + vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_data);
    }
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__post_act 
        = vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act;
    if (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en) 
         & (vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
            >> 0x1fU))) {
        vlSelfRef.mv_npu_top__DOT__u_post__DOT__post_act = 0U;
    }
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_ready 
        = (1U & ((~ (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid)) 
                 | (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_ready)));
    vlSelfRef.status_busy = vlSelfRef.mv_npu_top__DOT__status_busy;
    vlSelfRef.mv_npu_top__DOT__cmd_ready = (1U & (~ 
                                                  ((IData)(vlSelfRef.mv_npu_top__DOT__status_busy) 
                                                   | (IData)(vlSelfRef.mv_npu_top__DOT__status_error))));
    vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1 = ((~ (IData)(vlSelfRef.mv_npu_top__DOT__status_error)) 
                                                & (IData)(vlSelfRef.mv_npu_top__DOT__status_busy));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_xfer 
        = vlSelfRef.mv_npu_top__DOT__out_xfer;
    vlSelfRef.mv_npu_top__DOT__mat_lanes[0U] = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[0U];
    vlSelfRef.mv_npu_top__DOT__mat_lanes[1U] = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[1U];
    vlSelfRef.mv_npu_top__DOT__mat_lanes[2U] = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[2U];
    vlSelfRef.mv_npu_top__DOT__mat_lanes[3U] = vlSelfRef.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out[3U];
    vlSelfRef.mv_npu_top__DOT__vec_lanes[0U] = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[0U];
    vlSelfRef.mv_npu_top__DOT__vec_lanes[1U] = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[1U];
    vlSelfRef.mv_npu_top__DOT__vec_lanes[2U] = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[2U];
    vlSelfRef.mv_npu_top__DOT__vec_lanes[3U] = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[3U];
    vlSelfRef.mv_npu_top__DOT__pp_in_ready = vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_ready;
    vlSelfRef.cmd_ready = vlSelfRef.mv_npu_top__DOT__cmd_ready;
    vlSelfRef.mv_npu_top__DOT__cmd_accept = ((IData)(vlSelfRef.mv_npu_top__DOT__cmd_valid) 
                                             & (IData)(vlSelfRef.mv_npu_top__DOT__cmd_ready));
    vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0 = ((0U 
                                                 != (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                                                & (IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1));
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data[0U] 
        = vlSelfRef.mv_npu_top__DOT__mat_lanes[0U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data[1U] 
        = vlSelfRef.mv_npu_top__DOT__mat_lanes[1U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data[2U] 
        = vlSelfRef.mv_npu_top__DOT__mat_lanes[2U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data[3U] 
        = vlSelfRef.mv_npu_top__DOT__mat_lanes[3U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[0U] 
        = vlSelfRef.mv_npu_top__DOT__vec_lanes[0U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[1U] 
        = vlSelfRef.mv_npu_top__DOT__vec_lanes[1U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[2U] 
        = vlSelfRef.mv_npu_top__DOT__vec_lanes[2U];
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[3U] 
        = vlSelfRef.mv_npu_top__DOT__vec_lanes[3U];
    vlSelfRef.mv_npu_top__DOT__bias_ready = ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1) 
                                             & ((IData)(vlSelfRef.mv_npu_top__DOT__pp_in_ready) 
                                                & (IData)(vlSelfRef.mv_npu_top__DOT__cfg_bias_en)));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_accept 
        = vlSelfRef.mv_npu_top__DOT__cmd_accept;
    vlSelfRef.mv_npu_top__DOT__vec_ready = ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0) 
                                            & ((0U 
                                                == (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx)) 
                                               & (((IData)(vlSelfRef.mv_npu_top__DOT__vec_wr_addr) 
                                                   < (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                                                  & (0U 
                                                     == (IData)(vlSelfRef.mv_npu_top__DOT__row_idx)))));
    vlSelfRef.mv_npu_top__DOT__mat_ready = ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0) 
                                            & ((IData)(vlSelfRef.mv_npu_top__DOT__pp_in_ready) 
                                               & ((IData)(vlSelfRef.mv_npu_top__DOT__cfg_N) 
                                                  == (IData)(vlSelfRef.mv_npu_top__DOT__vec_wr_addr))));
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 = 0U;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i = 0U;
    while (VL_GTS_III(32, 0x00000010U, vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)) {
        if ((1U & ((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__lane_valid_mask) 
                   >> (0x0000000fU & vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))) {
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__m_i 
                = (0x000000ffU & (((0U == (0x0000001fU 
                                           & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))
                                    ? 0U : (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data
                                            [(((IData)(7U) 
                                               + (0x0000007fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))) 
                                              >> 5U)] 
                                            << ((IData)(0x00000020U) 
                                                - (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))))) 
                                  | (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data
                                     [(3U & (VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i) 
                                             >> 5U))] 
                                     >> (0x0000001fU 
                                         & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))));
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__v_i 
                = (0x000000ffU & (((0U == (0x0000001fU 
                                           & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))
                                    ? 0U : (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data
                                            [(((IData)(7U) 
                                               + (0x0000007fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))) 
                                              >> 5U)] 
                                            << ((IData)(0x00000020U) 
                                                - (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))))) 
                                  | (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data
                                     [(3U & (VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i) 
                                             >> 5U))] 
                                     >> (0x0000001fU 
                                         & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))));
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i 
                = (0x0000ffffU & VL_MULS_III(16, (0x0000ffffU 
                                                  & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__m_i))), 
                                             (0x0000ffffU 
                                              & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__v_i)))));
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 
                = (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 
                   + (((- (IData)((1U & ((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i) 
                                         >> 0x0fU)))) 
                       << 0x00000010U) | (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i)));
        }
        vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i = 
            ((IData)(1U) + vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i);
    }
    vlSelfRef.bias_ready = vlSelfRef.mv_npu_top__DOT__bias_ready;
    vlSelfRef.mv_npu_top__DOT__bias_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__bias_valid) 
                                            & (IData)(vlSelfRef.mv_npu_top__DOT__bias_ready));
    vlSelfRef.vec_ready = vlSelfRef.mv_npu_top__DOT__vec_ready;
    vlSelfRef.mv_npu_top__DOT__vec_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__vec_valid) 
                                           & (IData)(vlSelfRef.mv_npu_top__DOT__vec_ready));
    vlSelfRef.mat_ready = vlSelfRef.mv_npu_top__DOT__mat_ready;
    vlSelfRef.mv_npu_top__DOT__mat_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_valid) 
                                           & (IData)(vlSelfRef.mv_npu_top__DOT__mat_ready));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__bias_xfer 
        = vlSelfRef.mv_npu_top__DOT__bias_xfer;
    vlSelfRef.mv_npu_top__DOT__pp_bias_valid = vlSelfRef.mv_npu_top__DOT__bias_xfer;
    vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_en 
        = vlSelfRef.mv_npu_top__DOT__vec_xfer;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_xfer 
        = vlSelfRef.mv_npu_top__DOT__vec_xfer;
    vlSelfRef.mv_npu_top__DOT__compute_en_core = vlSelfRef.mv_npu_top__DOT__mat_xfer;
    vlSelfRef.mv_npu_top__DOT__new_row_core = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_xfer) 
                                               & (0U 
                                                  == (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx)));
    vlSelfRef.mv_npu_top__DOT__chunks_per_row = (0x0000ffffU 
                                                 & (((IData)(0x0000000fU) 
                                                     + (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                                                    >> 4U));
    vlSelfRef.mv_npu_top__DOT__pp_in_valid = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_xfer) 
                                              & ((0x0000ffffU 
                                                  & ((IData)(1U) 
                                                     + (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx))) 
                                                 == (IData)(vlSelfRef.mv_npu_top__DOT__chunks_per_row)));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer 
        = vlSelfRef.mv_npu_top__DOT__mat_xfer;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_valid 
        = vlSelfRef.mv_npu_top__DOT__pp_bias_valid;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__compute_en 
        = vlSelfRef.mv_npu_top__DOT__compute_en_core;
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__new_row 
        = vlSelfRef.mv_npu_top__DOT__new_row_core;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_valid 
        = vlSelfRef.mv_npu_top__DOT__pp_in_valid;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__state_compute_en 
        = ((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer) 
           & (2U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st)));
    vlSelfRef.mv_npu_top__DOT__state_compute_en = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__state_compute_en;
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
    CData/*1:0*/ __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st;
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 0;
    SData/*15:0*/ __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt;
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt = 0;
    SData/*15:0*/ __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt;
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt = 0;
    // Body
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_cnt;
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt 
        = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt;
    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st;
    if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rst_n) {
        if ((2U & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st))) {
            if ((1U & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st))) {
                if (((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_xfer) 
                     & ((((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt)) 
                         == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M)) 
                        | (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error)))) {
                    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 0U;
                }
            } else {
                if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer) {
                    if ((((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt)) 
                         == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row))) {
                        __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt = 0U;
                        if ((((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt)) 
                             == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M))) {
                            __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 3U;
                        } else {
                            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt 
                                = (0x0000ffffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt)));
                        }
                    } else {
                        __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt 
                            = (0x0000ffffU & ((IData)(1U) 
                                              + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt)));
                    }
                }
                if (((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__bias_xfer) 
                     & (~ (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en)))) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error = 1U;
                }
            }
        } else if ((1U & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st))) {
            if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_xfer) {
                __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt 
                    = (0x0000ffffU & ((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_cnt)));
                if ((((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_cnt)) 
                     == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N))) {
                    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 2U;
                }
            }
        } else {
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt = 0U;
            __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt = 0U;
            __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt = 0U;
            if (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_accept) {
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M 
                    = (0x0000ffffU & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data));
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N 
                    = (0x0000ffffU & (IData)((vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
                                              >> 0x10U)));
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en 
                    = (1U & (IData)((vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
                                     >> 0x20U)));
                vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en 
                    = (1U & (IData)((vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
                                     >> 0x21U)));
                if (((((1U > (0x0000ffffU & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data))) 
                       | (0x0100U < (0x0000ffffU & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data)))) 
                      | (1U > (0x0000ffffU & (IData)(
                                                     (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
                                                      >> 0x10U))))) 
                     | (0x0100U < (0x0000ffffU & (IData)(
                                                         (vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_data 
                                                          >> 0x10U)))))) {
                    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error = 1U;
                    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 3U;
                } else {
                    __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 1U;
                }
            }
        }
    } else {
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__row_cnt = 0U;
        __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt = 0U;
        __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st = 0U;
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M = 0U;
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N = 0U;
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en = 0U;
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en = 0U;
        __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt = 0U;
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error = 0U;
    }
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_cnt 
        = __Vdly__mv_npu_top__DOT__u_ctrl__DOT__vec_cnt;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt 
        = __Vdly__mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st = __Vdly__mv_npu_top__DOT__u_ctrl__DOT__st;
    vlSelfRef.mv_npu_top__DOT__cfg_M = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_M;
    vlSelfRef.mv_npu_top__DOT__cfg_relu_en = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en;
    vlSelfRef.mv_npu_top__DOT__cfg_bias_en = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en;
    vlSelfRef.mv_npu_top__DOT__status_error = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_error;
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_busy 
        = (0U != (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row 
        = (0x0000ffffU & (((IData)(0x0000000fU) + (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N)) 
                          >> 4U));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem = (0x0fU 
                                                   & (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask = 0xffffU;
    if ((((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt) 
          == ((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row) 
              - (IData)(1U))) & (0U != (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem)))) {
        vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask 
            = (0x0000ffffU & (((IData)(1U) << (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__rem)) 
                              - (IData)(1U)));
    }
    vlSelfRef.mv_npu_top__DOT__cfg_N = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cfg_N;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_relu_en;
    vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en 
        = vlSelfRef.mv_npu_top__DOT__cfg_bias_en;
    vlSelfRef.status_error = vlSelfRef.mv_npu_top__DOT__status_error;
    vlSelfRef.mv_npu_top__DOT__status_busy = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__status_busy;
    vlSelfRef.mv_npu_top__DOT__lane_valid_mask = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask;
    vlSelfRef.status_busy = vlSelfRef.mv_npu_top__DOT__status_busy;
    vlSelfRef.mv_npu_top__DOT__cmd_ready = (1U & (~ 
                                                  ((IData)(vlSelfRef.mv_npu_top__DOT__status_busy) 
                                                   | (IData)(vlSelfRef.mv_npu_top__DOT__status_error))));
    vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1 = ((~ (IData)(vlSelfRef.mv_npu_top__DOT__status_error)) 
                                                & (IData)(vlSelfRef.mv_npu_top__DOT__status_busy));
    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__lane_valid_mask 
        = vlSelfRef.mv_npu_top__DOT__lane_valid_mask;
    vlSelfRef.cmd_ready = vlSelfRef.mv_npu_top__DOT__cmd_ready;
    vlSelfRef.mv_npu_top__DOT__cmd_accept = ((IData)(vlSelfRef.mv_npu_top__DOT__cmd_valid) 
                                             & (IData)(vlSelfRef.mv_npu_top__DOT__cmd_ready));
    vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0 = ((0U 
                                                 != (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                                                & (IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1));
    vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__cmd_accept 
        = vlSelfRef.mv_npu_top__DOT__cmd_accept;
}

void Vtop___024root___eval_nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((4ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__0
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out;
            __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out = 0;
            __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out 
                = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_accum_out;
            if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__rst_n) {
                if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__new_row) {
                    __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out = 0U;
                }
                vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_done_pulse = 0U;
                if (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__compute_en) {
                    __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out 
                        = (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_accum_out 
                           + vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32);
                    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_done_pulse = 1U;
                }
            } else {
                __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out = 0U;
                vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_done_pulse = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_accum_out 
                = __Vinline_0__nba_sequent__TOP__0___Vdly__mv_npu_top__DOT__u_mac__DOT__row_accum_out;
            vlSelfRef.mv_npu_top__DOT__row_accum_out 
                = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_accum_out;
            vlSelfRef.mv_npu_top__DOT__row_done_pulse 
                = vlSelfRef.mv_npu_top__DOT__u_mac__DOT__row_done_pulse;
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data 
                = vlSelfRef.mv_npu_top__DOT__row_accum_out;
        }
    }
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__1
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyVal__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyVal__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyDim0__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyDim0__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___VdlySet__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 = 0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 = 0U;
            if (vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_en) {
                __Vinline_0__nba_sequent__TOP__1___VdlyVal__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 
                    = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_data;
                __Vinline_0__nba_sequent__TOP__1___VdlyDim0__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 
                    = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr;
                __Vinline_0__nba_sequent__TOP__1___VdlySet__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0 = 1U;
            }
            if (__Vinline_0__nba_sequent__TOP__1___VdlySet__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0) {
                vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__mem[__Vinline_0__nba_sequent__TOP__1___VdlyDim0__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0] 
                    = __Vinline_0__nba_sequent__TOP__1___VdlyVal__mv_npu_top__DOT__u_vec_buffer__DOT__mem__v0;
            }
        }
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__2
            SData/*15:0*/ __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx;
            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx = 0;
            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx 
                = vlSelfRef.mv_npu_top__DOT__k_chunk_idx;
            if (vlSelfRef.mv_npu_top__DOT__rst_n) {
                if (vlSelfRef.mv_npu_top__DOT__status_busy) {
                    if (vlSelfRef.mv_npu_top__DOT__vec_xfer) {
                        vlSelfRef.mv_npu_top__DOT__vec_wr_addr 
                            = (0x000000ffU & ((IData)(1U) 
                                              + (IData)(vlSelfRef.mv_npu_top__DOT__vec_wr_addr)));
                    }
                    if (vlSelfRef.mv_npu_top__DOT__mat_xfer) {
                        if (((0x0000ffffU & ((IData)(1U) 
                                             + (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx))) 
                             == (IData)(vlSelfRef.mv_npu_top__DOT__chunks_per_row))) {
                            if (((0x0000ffffU & ((IData)(1U) 
                                                 + (IData)(vlSelfRef.mv_npu_top__DOT__row_idx))) 
                                 < (IData)(vlSelfRef.mv_npu_top__DOT__cfg_M))) {
                                vlSelfRef.mv_npu_top__DOT__row_idx 
                                    = (0x0000ffffU 
                                       & ((IData)(1U) 
                                          + (IData)(vlSelfRef.mv_npu_top__DOT__row_idx)));
                            }
                            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx = 0U;
                        } else {
                            __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx 
                                = (0x0000ffffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx)));
                        }
                    }
                } else {
                    vlSelfRef.mv_npu_top__DOT__vec_wr_addr = 0U;
                    vlSelfRef.mv_npu_top__DOT__row_idx = 0U;
                    __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx = 0U;
                }
            } else {
                vlSelfRef.mv_npu_top__DOT__vec_wr_addr = 0U;
                vlSelfRef.mv_npu_top__DOT__row_idx = 0U;
                __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__k_chunk_idx 
                = __Vinline_0__nba_sequent__TOP__2___Vdly__mv_npu_top__DOT__k_chunk_idx;
            vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr 
                = vlSelfRef.mv_npu_top__DOT__vec_wr_addr;
            vlSelfRef.mv_npu_top__DOT__rd_chunk_base 
                = (0x000000f0U & ((IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx) 
                                  << 4U));
            vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base 
                = vlSelfRef.mv_npu_top__DOT__rd_chunk_base;
        }
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__3
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid;
            __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid = 0;
            __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid;
            if (vlSelfRef.mv_npu_top__DOT__u_post__DOT__rst_n) {
                if (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_valid) 
                     & (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_ready))) {
                    if ((1U & ((~ (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en)) 
                               | (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_valid)))) {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid = 1U;
                        vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_data 
                            = vlSelfRef.mv_npu_top__DOT__u_post__DOT__post_act;
                    }
                } else if (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid) 
                            & (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_ready))) {
                    __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid = 0U;
                }
            } else {
                __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid = 0U;
                vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_data = 0U;
            }
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__mv_npu_top__DOT__u_post__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__pp_out_valid 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_ready 
                = (1U & ((~ (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_valid)) 
                         | (IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_ready)));
            vlSelfRef.mv_npu_top__DOT__pp_out_data 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__out_data;
            vlSelfRef.mv_npu_top__DOT__out_valid = vlSelfRef.mv_npu_top__DOT__pp_out_valid;
            vlSelfRef.mv_npu_top__DOT__pp_in_ready 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_ready;
            vlSelfRef.mv_npu_top__DOT__out_data = vlSelfRef.mv_npu_top__DOT__pp_out_data;
            vlSelfRef.out_valid = vlSelfRef.mv_npu_top__DOT__out_valid;
            vlSelfRef.mv_npu_top__DOT__out_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__out_valid) 
                                                   & (IData)(vlSelfRef.mv_npu_top__DOT__out_ready));
            vlSelfRef.out_data = vlSelfRef.mv_npu_top__DOT__out_data;
        }
    }
    if ((0x0000000000000010ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtop___024root___nba_sequent__TOP__4(vlSelf);
    }
    if ((9ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__0
            vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j = 0U;
            while (VL_GTS_III(32, 0x00000010U, vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j)) {
                VL_ASSIGNSEL_WI(128, 8, (0x0000007fU 
                                         & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j)), vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data, 
                                ((0x00000100U > ((IData)(vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base) 
                                                 + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j))
                                  ? vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__mem
                                 [(0x000000ffU & ((IData)(vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base) 
                                                  + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j))]
                                  : 0U));
                vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j 
                    = ((IData)(1U) + vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__j);
            }
            vlSelfRef.mv_npu_top__DOT__vec_lanes[0U] 
                = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[0U];
            vlSelfRef.mv_npu_top__DOT__vec_lanes[1U] 
                = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[1U];
            vlSelfRef.mv_npu_top__DOT__vec_lanes[2U] 
                = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[2U];
            vlSelfRef.mv_npu_top__DOT__vec_lanes[3U] 
                = vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data[3U];
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[0U] 
                = vlSelfRef.mv_npu_top__DOT__vec_lanes[0U];
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[1U] 
                = vlSelfRef.mv_npu_top__DOT__vec_lanes[1U];
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[2U] 
                = vlSelfRef.mv_npu_top__DOT__vec_lanes[2U];
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data[3U] 
                = vlSelfRef.mv_npu_top__DOT__vec_lanes[3U];
        }
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__5
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__out_xfer 
                = vlSelfRef.mv_npu_top__DOT__out_xfer;
        }
    }
    if ((0x0000000000000014ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__1
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data;
            if (vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_en) {
                vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
                    = (vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_data 
                       + vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_data);
            }
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__post_act 
                = vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act;
            if (((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__relu_en) 
                 & (vlSelfRef.mv_npu_top__DOT__u_post__DOT__pre_act 
                    >> 0x1fU))) {
                vlSelfRef.mv_npu_top__DOT__u_post__DOT__post_act = 0U;
            }
        }
    }
    if ((0x0000000000000012ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__2
            vlSelfRef.mv_npu_top__DOT__bias_ready = 
                ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_1) 
                 & ((IData)(vlSelfRef.mv_npu_top__DOT__pp_in_ready) 
                    & (IData)(vlSelfRef.mv_npu_top__DOT__cfg_bias_en)));
            vlSelfRef.bias_ready = vlSelfRef.mv_npu_top__DOT__bias_ready;
            vlSelfRef.mv_npu_top__DOT__bias_xfer = 
                ((IData)(vlSelfRef.mv_npu_top__DOT__bias_valid) 
                 & (IData)(vlSelfRef.mv_npu_top__DOT__bias_ready));
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__bias_xfer 
                = vlSelfRef.mv_npu_top__DOT__bias_xfer;
            vlSelfRef.mv_npu_top__DOT__pp_bias_valid 
                = vlSelfRef.mv_npu_top__DOT__bias_xfer;
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__bias_valid 
                = vlSelfRef.mv_npu_top__DOT__pp_bias_valid;
        }
    }
    if ((0x0000000000000011ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__3
            vlSelfRef.mv_npu_top__DOT__vec_ready = 
                ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0) 
                 & ((0U == (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx)) 
                    & (((IData)(vlSelfRef.mv_npu_top__DOT__vec_wr_addr) 
                        < (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                       & (0U == (IData)(vlSelfRef.mv_npu_top__DOT__row_idx)))));
            vlSelfRef.vec_ready = vlSelfRef.mv_npu_top__DOT__vec_ready;
            vlSelfRef.mv_npu_top__DOT__vec_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__vec_valid) 
                                                   & (IData)(vlSelfRef.mv_npu_top__DOT__vec_ready));
            vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__wr_en 
                = vlSelfRef.mv_npu_top__DOT__vec_xfer;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__vec_xfer 
                = vlSelfRef.mv_npu_top__DOT__vec_xfer;
        }
    }
    if ((0x0000000000000013ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__4
            vlSelfRef.mv_npu_top__DOT__mat_ready = 
                ((IData)(vlSelfRef.__VdfgRegularize_h6e95ff9d_0_0) 
                 & ((IData)(vlSelfRef.mv_npu_top__DOT__pp_in_ready) 
                    & ((IData)(vlSelfRef.mv_npu_top__DOT__cfg_N) 
                       == (IData)(vlSelfRef.mv_npu_top__DOT__vec_wr_addr))));
            vlSelfRef.mat_ready = vlSelfRef.mv_npu_top__DOT__mat_ready;
            vlSelfRef.mv_npu_top__DOT__mat_xfer = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_valid) 
                                                   & (IData)(vlSelfRef.mv_npu_top__DOT__mat_ready));
            vlSelfRef.mv_npu_top__DOT__compute_en_core 
                = vlSelfRef.mv_npu_top__DOT__mat_xfer;
            vlSelfRef.mv_npu_top__DOT__new_row_core 
                = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_xfer) 
                   & (0U == (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx)));
            vlSelfRef.mv_npu_top__DOT__chunks_per_row 
                = (0x0000ffffU & (((IData)(0x0000000fU) 
                                   + (IData)(vlSelfRef.mv_npu_top__DOT__cfg_N)) 
                                  >> 4U));
            vlSelfRef.mv_npu_top__DOT__pp_in_valid 
                = ((IData)(vlSelfRef.mv_npu_top__DOT__mat_xfer) 
                   & ((0x0000ffffU & ((IData)(1U) + (IData)(vlSelfRef.mv_npu_top__DOT__k_chunk_idx))) 
                      == (IData)(vlSelfRef.mv_npu_top__DOT__chunks_per_row)));
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer 
                = vlSelfRef.mv_npu_top__DOT__mat_xfer;
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__compute_en 
                = vlSelfRef.mv_npu_top__DOT__compute_en_core;
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__new_row 
                = vlSelfRef.mv_npu_top__DOT__new_row_core;
            vlSelfRef.mv_npu_top__DOT__u_post__DOT__in_valid 
                = vlSelfRef.mv_npu_top__DOT__pp_in_valid;
            vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__state_compute_en 
                = ((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer) 
                   & (2U == (IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__st)));
            vlSelfRef.mv_npu_top__DOT__state_compute_en 
                = vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__state_compute_en;
        }
    }
    if ((0x0000000000000019ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__5
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 = 0U;
            vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i = 0U;
            while (VL_GTS_III(32, 0x00000010U, vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)) {
                if ((1U & ((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__lane_valid_mask) 
                           >> (0x0000000fU & vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))) {
                    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__m_i 
                        = (0x000000ffU & (((0U == (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))
                                            ? 0U : 
                                           (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data
                                            [(((IData)(7U) 
                                               + (0x0000007fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))) 
                                              >> 5U)] 
                                            << ((IData)(0x00000020U) 
                                                - (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))))) 
                                          | (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__mat_lane_data
                                             [(3U & 
                                               (VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i) 
                                                >> 5U))] 
                                             >> (0x0000001fU 
                                                 & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))));
                    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__v_i 
                        = (0x000000ffU & (((0U == (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))
                                            ? 0U : 
                                           (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data
                                            [(((IData)(7U) 
                                               + (0x0000007fU 
                                                  & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))) 
                                              >> 5U)] 
                                            << ((IData)(0x00000020U) 
                                                - (0x0000001fU 
                                                   & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i))))) 
                                          | (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__vec_lane_data
                                             [(3U & 
                                               (VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i) 
                                                >> 5U))] 
                                             >> (0x0000001fU 
                                                 & VL_MULS_III(32, (IData)(8U), vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i)))));
                    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i 
                        = (0x0000ffffU & VL_MULS_III(16, 
                                                     (0x0000ffffU 
                                                      & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__m_i))), 
                                                     (0x0000ffffU 
                                                      & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__v_i)))));
                    vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 
                        = (vlSelfRef.mv_npu_top__DOT__u_mac__DOT__sum32 
                           + (((- (IData)((1U & ((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i) 
                                                 >> 0x0fU)))) 
                               << 0x00000010U) | (IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__p_i)));
                }
                vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i 
                    = ((IData)(1U) + vlSelfRef.mv_npu_top__DOT__u_mac__DOT__i);
            }
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
                                                        ((((IData)(vlSelfRef.mv_npu_top__DOT__u_ctrl__DOT__clk) 
                                                           & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_ctrl__DOT__clk__0))) 
                                                          << 4U) 
                                                         | (((((IData)(vlSelfRef.mv_npu_top__DOT__u_vec_buffer__DOT__clk) 
                                                               & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_vec_buffer__DOT__clk__0))) 
                                                              << 3U) 
                                                             | (((IData)(vlSelfRef.mv_npu_top__DOT__u_mac__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_mac__DOT__clk__0))) 
                                                                << 2U)) 
                                                            | ((((IData)(vlSelfRef.mv_npu_top__DOT__u_post__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__u_post__DOT__clk__0))) 
                                                                << 1U) 
                                                               | ((IData)(vlSelfRef.mv_npu_top__DOT__clk) 
                                                                  & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__mv_npu_top__DOT__clk__0))))))));
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-203614-cda812/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-203614-cda812/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/runs/run-20260911-203614-cda812/rtl/mv_npu_top.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
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
    if (VL_UNLIKELY(((vlSelfRef.vec_valid & 0xfeU)))) {
        Verilated::overWidthError("vec_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.mat_valid & 0xfeU)))) {
        Verilated::overWidthError("mat_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bias_valid & 0xfeU)))) {
        Verilated::overWidthError("bias_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
}
#endif  // VL_DEBUG
