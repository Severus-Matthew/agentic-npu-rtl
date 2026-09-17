// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

// Parameter definitions for Vtop___024root
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__TILE_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__A_DEPTH;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__B_DEPTH;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_out__DOT__TILE_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_out__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_post__DOT__TILE_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_post__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_core__DOT__TILE_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__TILE_N;


void Vtop___024root___ctor_var_reset(Vtop___024root* vlSelf);

Vtop___024root::Vtop___024root(Vtop__Syms* symsp, const char* namep)
 {
    vlSymsp = symsp;
    vlNamep = strdup(namep);
    // Reset structure values
    Vtop___024root___ctor_var_reset(this);
}

void Vtop___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

Vtop___024root::~Vtop___024root() {
    VL_DO_DANGLING(std::free(const_cast<char*>(vlNamep)), vlNamep);
}
