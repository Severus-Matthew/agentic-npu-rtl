// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

// Parameter definitions for Vtop___024root
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__LANES;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__CMD_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__MAT_DATA_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__VEC_DATA_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__BIAS_DATA_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__OUT_DATA_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__AW;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_mac__DOT__LANES;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_vec_buffer__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_vec_buffer__DOT__LANES;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_stream_if__DOT__LANES;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_stream_if__DOT__MAT_DATA_W;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_ctrl__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_ctrl__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_ctrl__DOT__LANES;
constexpr IData/*31:0*/ Vtop___024root::mv_npu_top__DOT__u_ctrl__DOT__CMD_W;


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
