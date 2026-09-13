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
    vlSelfRef.status_done = vlSelfRef.gemm_bias_relu_npu_top__DOT__status_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_busy 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_done_pulse 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_valid 
        = vlSelfRef.cmd_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__status_error 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr 
        = (0x00000fffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a);
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr 
        = (0x00000fffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b);
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr 
        = (0x0000003fU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias);
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute 
        = (4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit 
        = (5U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[0U] 
        = vlSelfRef.cmd_data[0U];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[1U] 
        = vlSelfRef.cmd_data[1U];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[2U] 
        = vlSelfRef.cmd_data[2U];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__out_valid 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__out_ready 
        = vlSelfRef.out_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__out_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_emit_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_data = vlSelfRef.a_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_data = vlSelfRef.b_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_data 
        = vlSelfRef.bias_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready 
        = ((~ (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error)) 
           & (0U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state)));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_m = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__clk = vlSelfRef.clk;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n = vlSelfRef.rst_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_m = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step 
        = (4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_valid 
        = vlSelfRef.a_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_valid 
        = vlSelfRef.b_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_bias;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_valid 
        = vlSelfRef.bias_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a 
        = (1U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b 
        = (2U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_acc 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias 
        = (3U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i)) {
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active 
            = (((~ ((IData)(1U) << (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i))) 
                & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active)) 
               | (0x00ffU & ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base) 
                               + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i) 
                              < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n)) 
                             << (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i))));
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i 
            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i);
    }
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_valid 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_valid;
    vlSelfRef.status_error = vlSelfRef.gemm_bias_relu_npu_top__DOT__status_error;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_addr 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_addr 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_addr 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_compute 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_emit 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U] 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[0U];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U] 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[1U];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[2U] 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_data[2U];
    vlSelfRef.out_valid = vlSelfRef.gemm_bias_relu_npu_top__DOT__out_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__out_ready;
    vlSelfRef.out_data = vlSelfRef.gemm_bias_relu_npu_top__DOT__out_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_emit_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__clk 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__clk;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__clk 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__clk;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__clk;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__clk;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__rst_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__rst_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__rst_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_step 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_valid;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_a 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_b 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_acc;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_bias 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_elem = vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_A
        [(0x00000fffU & ((0x0000ffffU & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k) 
                                         * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_m))) 
                         + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k)))];
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_data;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_data;
    vlSelfRef.cmd_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_step;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_bias;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)) {
        vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx 
            = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base) 
               + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i);
        vlSelfRef.gemm_bias_relu_npu_top__DOT__b_vec[(7U 
                                                      & vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)] 
            = ((1U & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active) 
                      >> (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)))
                ? vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_B
               [(0x00000fffU & (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k) 
                                 * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n)) 
                                + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx))]
                : 0U);
        vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i 
            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i);
    }
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_elem;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done 
        = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a 
           == ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m) 
               * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k)));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done 
        = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b 
           == ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n) 
               * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k)));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done 
        = (1U & ((~ (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable)) 
                 | (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias 
                    == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n))));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done 
        = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step) 
           & (((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count)) 
              >= (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k)));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en 
        = (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en 
        = (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready 
        = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en 
        = ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias) 
             & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable)) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_vec;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)) {
        if ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active) 
              >> (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)) 
             & (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base) 
                 + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i) 
                < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n)))) {
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t 
                = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc
                   [(7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] 
                   + ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable)
                       ? vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem
                      [(0x0000003fU & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base) 
                                       + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i))]
                       : 0U));
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out[(7U 
                                                                          & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] 
                = (VL_GTS_III(32, 0U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t)
                    ? 0U : vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t);
        } else {
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out[(7U 
                                                                          & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] = 0U;
        }
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i 
            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i);
    }
    vlSelfRef.gemm_bias_relu_npu_top__DOT__load_a_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__load_b_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__load_bias_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__compute_tile_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_post 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_a_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_b_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_bias_done;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__compute_tile_done;
    vlSelfRef.a_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_ready;
    vlSelfRef.b_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_ready;
    vlSelfRef.bias_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_post;
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
    SData/*15:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m = 0;
    CData/*0:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable = 0;
    CData/*2:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 0;
    SData/*15:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles = 0;
    SData/*15:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx = 0;
    CData/*5:0*/ __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = 0;
    // Body
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state;
    if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__rst_n) {
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse = 0U;
        if ((0U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_valid) 
                 & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready))) {
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m 
                    = (0x0000ffffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U]);
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n 
                    = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U] 
                       >> 0x00000010U);
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k 
                    = (0x0000ffffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U]);
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable 
                    = (1U & (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U] 
                             >> 0x00000010U));
                if ((((((((1U > (0x0000ffffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U])) 
                          | (0x0040U < (0x0000ffffU 
                                        & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U]))) 
                         | (1U > (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U] 
                                  >> 0x00000010U))) 
                        | (0x0040U < (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U] 
                                      >> 0x00000010U))) 
                       | (1U > (0x0000ffffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U]))) 
                      | (0x0040U < (0x0000ffffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U]))) 
                     | (0ULL != (0x00007fffffffffffULL 
                                 & (((QData)((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[2U])) 
                                     << 0x0000000fU) 
                                    | ((QData)((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[1U])) 
                                       >> 0x00000011U)))))) {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error = 1U;
                } else {
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 1U;
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles 
                        = (0x0000ffffU & (((IData)(7U) 
                                           + (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data[0U] 
                                              >> 0x00000010U)) 
                                          >> 3U));
                }
            }
        } else if ((1U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done) {
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 2U;
            }
        } else if ((2U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done) {
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state 
                    = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable)
                        ? 3U : 4U);
            }
        } else if ((3U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done) {
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 4U;
            }
        } else if ((4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if ((0U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k))) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start = 1U;
            }
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done) {
                __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 5U;
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start = 1U;
            }
        } else if ((5U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done) {
                if ((((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx)) 
                     < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles))) {
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx 
                        = (0x0000ffffU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx)));
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base 
                        = (0x0000003fU & (((IData)(1U) 
                                           + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx)) 
                                          << 3U));
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = 0U;
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 4U;
                } else if ((((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m)) 
                            < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m))) {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m 
                        = (0x0000003fU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m)));
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx = 0U;
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base = 0U;
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = 0U;
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 4U;
                } else {
                    __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 6U;
                }
            }
        } else if ((6U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state))) {
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m = 0U;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse = 1U;
            __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 0U;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base = 0U;
            __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = 0U;
            __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx = 0U;
        }
        if (((4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state)) 
             & (~ (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done)))) {
            __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k 
                = (0x0000003fU & ((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k)));
        }
    } else {
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx = 0U;
        __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start = 0U;
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse = 0U;
    }
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state 
        = __Vdly__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_done_pulse 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_emit_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_m = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__status_error 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_m = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i = 0U;
    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i)) {
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active 
            = (((~ ((IData)(1U) << (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i))) 
                & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active)) 
               | (0x00ffU & ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base) 
                               + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i) 
                              < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n)) 
                             << (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i))));
        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i 
            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i);
    }
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute 
        = (4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit 
        = (5U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready 
        = ((~ (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error)) 
           & (0U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state)));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step 
        = (4U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a 
        = (1U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b 
        = (2U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias 
        = (3U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_start;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_emit_start;
    vlSelfRef.status_error = vlSelfRef.gemm_bias_relu_npu_top__DOT__status_error;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_m;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_bias_enable;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_compute 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_emit 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_step 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_a 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_b 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_bias 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active;
    vlSelfRef.cmd_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__cmd_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__do_compute_step;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__st_load_bias;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en 
        = (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en 
        = (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready 
        = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en 
        = ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias) 
             & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable)) 
            & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid)) 
           & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready));
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__a_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__b_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_en 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en;
    vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_ready 
        = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready;
    vlSelfRef.a_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_ready;
    vlSelfRef.b_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_ready;
    vlSelfRef.bias_ready = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_ready;
}

void Vtop___024root___eval_nba(Vtop___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtop___024root___eval_nba\n"); );
    Vtop__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((4ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__0
            SData/*15:0*/ __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count;
            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v0;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v0 = 0;
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1;
            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1 = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1 = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v2;
            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v2 = 0;
            __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count;
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n) {
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start) {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i = 0U;
                    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i)) {
                        __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v0 
                            = (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i);
                        vlSelfRef.__VdlyCommitQueuegemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc.enqueue(0U, __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v0);
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i 
                            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i);
                    }
                } else if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step) {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i = 0U;
                    while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i)) {
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16 
                            = (0x0000ffffU & VL_MULS_III(16, 
                                                         (0x0000ffffU 
                                                          & VL_EXTENDS_II(16,8, (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem))), 
                                                         (0x0000ffffU 
                                                          & VL_EXTENDS_II(16,8, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec
                                                                          [
                                                                          (7U 
                                                                           & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i)]))));
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p32 
                            = (((- (IData)((1U & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16) 
                                                  >> 0x0fU)))) 
                                << 0x00000010U) | (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16));
                        if ((1U & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active) 
                                   >> (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i)))) {
                            __Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1 
                                = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc
                                   [(7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i)] 
                                   + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p32);
                            __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1 
                                = (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i);
                            vlSelfRef.__VdlyCommitQueuegemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc.enqueue(__Vinline_0__nba_sequent__TOP__0___VdlyVal__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1, __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v1);
                        }
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i 
                            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i);
                    }
                }
            } else {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i = 0U;
                while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i)) {
                    __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v2 
                        = (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i);
                    vlSelfRef.__VdlyCommitQueuegemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc.enqueue(0U, __Vinline_0__nba_sequent__TOP__0___VdlyDim0__gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc__v2);
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i 
                        = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i);
                }
            }
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n) {
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start) {
                    __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count = 0U;
                } else if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step) {
                    __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count 
                        = (0x0000ffffU & ((IData)(1U) 
                                          + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count)));
                }
            } else {
                __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count = 0U;
            }
            vlSelfRef.__VdlyCommitQueuegemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc.commit(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc);
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count 
                = __Vinline_0__nba_sequent__TOP__0___Vdly__gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_acc 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_acc;
        }
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__1
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_A__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_A__v0 = 0;
            SData/*11:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_A__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_A__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_A__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_A__v0 = 0;
            CData/*7:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_B__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_B__v0 = 0;
            SData/*11:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_B__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_B__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_B__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_B__v0 = 0;
            IData/*31:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_bias__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_bias__v0 = 0;
            CData/*5:0*/ __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_bias__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_bias__v0 = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_bias__v0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_bias__v0 = 0;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_A__v0 = 0U;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_B__v0 = 0U;
            __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_bias__v0 = 0U;
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_en) {
                __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_A__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_data;
                __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_A__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_addr;
                __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_A__v0 = 1U;
            }
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_en) {
                __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_B__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_data;
                __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_B__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_addr;
                __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_B__v0 = 1U;
            }
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_en) {
                __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_bias__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_data;
                __Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_bias__v0 
                    = vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_addr;
                __Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_bias__v0 = 1U;
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__status_done 
                = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__rst_n) 
                   & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__do_done_pulse));
            if (__Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_A__v0) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_A[__Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_A__v0] 
                    = __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_A__v0;
            }
            if (__Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_B__v0) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_B[__Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_B__v0] 
                    = __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_B__v0;
            }
            if (__Vinline_0__nba_sequent__TOP__1___VdlySet__gemm_bias_relu_npu_top__DOT__buf_bias__v0) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_bias[__Vinline_0__nba_sequent__TOP__1___VdlyDim0__gemm_bias_relu_npu_top__DOT__buf_bias__v0] 
                    = __Vinline_0__nba_sequent__TOP__1___VdlyVal__gemm_bias_relu_npu_top__DOT__buf_bias__v0;
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_bias;
            vlSelfRef.status_done = vlSelfRef.gemm_bias_relu_npu_top__DOT__status_done;
        }
    }
    if ((8ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__2
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__rst_n) {
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a) {
                    if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en) {
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a 
                            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a);
                    }
                } else {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a = 0U;
                }
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b) {
                    if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en) {
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b 
                            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b);
                    }
                } else {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b = 0U;
                }
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias) {
                    if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en) {
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias 
                            = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias);
                    }
                } else {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias = 0U;
                }
            } else {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a = 0U;
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b = 0U;
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias = 0U;
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr 
                = (0x00000fffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a);
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr 
                = (0x00000fffU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b);
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr 
                = (0x0000003fU & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias);
            vlSelfRef.gemm_bias_relu_npu_top__DOT__a_wr_addr 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__b_wr_addr 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__bias_wr_addr 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr;
        }
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__3
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = 0;
            CData/*2:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started = 0;
            CData/*0:0*/ __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 0;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__started;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
            if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__rst_n) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done = 0U;
                if (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start) {
                    __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = 1U;
                    __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx = 0U;
                    __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started = 1U;
                }
                if (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy) 
                     & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__started))) {
                    if ((1U & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active) 
                               >> (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx)))) {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 1U;
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data 
                            = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data
                            [vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx];
                        if (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid) 
                             & (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_ready))) {
                            if ((7U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx))) {
                                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = 0U;
                                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done = 1U;
                                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 0U;
                                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started = 0U;
                            }
                            __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx 
                                = (7U & ((IData)(1U) 
                                         + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx)));
                        }
                    } else if ((7U == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx))) {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 0U;
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = 0U;
                        vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done = 1U;
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started = 0U;
                    } else {
                        __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx 
                            = (7U & ((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx)));
                    }
                } else {
                    __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 0U;
                }
            } else {
                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid = 0U;
                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy = 0U;
                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx = 0U;
                __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started = 0U;
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data = 0U;
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done = 0U;
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__started 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__started;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid 
                = __Vinline_0__nba_sequent__TOP__3___Vdly__gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_busy 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__out_valid 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__out_data 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data;
            vlSelfRef.out_valid = vlSelfRef.gemm_bias_relu_npu_top__DOT__out_valid;
            vlSelfRef.out_data = vlSelfRef.gemm_bias_relu_npu_top__DOT__out_data;
        }
    }
    if ((0x0000000000000010ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtop___024root___nba_sequent__TOP__4(vlSelf);
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_sequent__TOP__5
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__emit_done;
        }
    }
    if ((0x0000000000000011ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__0
            vlSelfRef.gemm_bias_relu_npu_top__DOT__a_elem 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_A
                [(0x00000fffU & ((0x0000ffffU & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_k) 
                                                 * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_m))) 
                                 + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k)))];
            vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i = 0U;
            while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)) {
                vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx 
                    = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_n_base) 
                       + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i);
                vlSelfRef.gemm_bias_relu_npu_top__DOT__b_vec[(7U 
                                                              & vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)] 
                    = ((1U & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_active) 
                              >> (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i)))
                        ? vlSelfRef.gemm_bias_relu_npu_top__DOT__buf_B
                       [(0x00000fffU & (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__idx_k) 
                                         * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__cfg_n)) 
                                        + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx))]
                        : 0U);
                vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i 
                    = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i);
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__a_elem;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__b_vec;
        }
    }
    if ((0x0000000000000018ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__1
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done 
                = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a 
                   == ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m) 
                       * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k)));
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done 
                = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b 
                   == ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n) 
                       * (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k)));
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done 
                = (1U & ((~ (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable)) 
                         | (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias 
                            == (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n))));
            vlSelfRef.gemm_bias_relu_npu_top__DOT__load_a_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__load_b_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__load_bias_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_a_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_b_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__load_bias_done;
        }
    }
    if ((0x0000000000000015ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__2
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i = 0U;
            while (VL_GTS_III(32, 8U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)) {
                if ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active) 
                      >> (7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)) 
                     & (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base) 
                         + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i) 
                        < (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n)))) {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t 
                        = (vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc
                           [(7U & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] 
                           + ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable)
                               ? vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem
                              [(0x0000003fU & ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base) 
                                               + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i))]
                               : 0U));
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out[(7U 
                                                                                & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] 
                        = (VL_GTS_III(32, 0U, vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t)
                            ? 0U : vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t);
                } else {
                    vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out[(7U 
                                                                                & vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i)] = 0U;
                }
                vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i 
                    = ((IData)(1U) + vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i);
            }
            vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_post 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__lane_post;
        }
    }
    if ((0x0000000000000014ULL & vlSelfRef.__VnbaTriggered[0U])) {
        {
            // Inlined CFunc: _nba_comb__TOP__3
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done 
                = ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step) 
                   & (((IData)(1U) + (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count)) 
                      >= (IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k)));
            vlSelfRef.gemm_bias_relu_npu_top__DOT__compute_tile_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done;
            vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done 
                = vlSelfRef.gemm_bias_relu_npu_top__DOT__compute_tile_done;
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
                                                        ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk) 
                                                           & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk__0))) 
                                                          << 4U) 
                                                         | (((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk) 
                                                               & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk__0))) 
                                                              << 3U) 
                                                             | (((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_core__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_core__DOT__clk__0))) 
                                                                << 2U)) 
                                                            | ((((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__u_out__DOT__clk) 
                                                                 & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_out__DOT__clk__0))) 
                                                                << 1U) 
                                                               | ((IData)(vlSelfRef.gemm_bias_relu_npu_top__DOT__clk) 
                                                                  & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__clk__0))))))));
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/workspace/rtl/gemm_bias_relu_npu_top.sv", 1, "", "DIDNOTCONVERGE: Input combinational region did not converge after '--converge-limit' of 10000 tries");
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
            VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/workspace/rtl/gemm_bias_relu_npu_top.sv", 1, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtop___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("/u/mjha1/agentic-npu-rtl/multigent/workspace/rtl/gemm_bias_relu_npu_top.sv", 1, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
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
    if (VL_UNLIKELY(((vlSelfRef.a_valid & 0xfeU)))) {
        Verilated::overWidthError("a_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.b_valid & 0xfeU)))) {
        Verilated::overWidthError("b_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.bias_valid & 0xfeU)))) {
        Verilated::overWidthError("bias_valid");
    }
    if (VL_UNLIKELY(((vlSelfRef.out_ready & 0xfeU)))) {
        Verilated::overWidthError("out_ready");
    }
}
#endif  // VL_DEBUG
