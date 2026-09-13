// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtop.h for the primary calling header

#include "Vtop__pch.h"

// Parameter definitions for Vtop___024root
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__ARRAY_ROWS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__ARRAY_COLS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__ARRAY_ROWS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__ARRAY_COLS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__M_W;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__N_W;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__K_W;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__A_AW;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__W_AW;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__B_AW;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__TILE_PAIRS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__FP_W;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__RESULT_PAIRS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__RP_W;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_ROWS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_COLS;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_M;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_N;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_K;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RESULT_CAP;
constexpr IData/*31:0*/ Vtop___024root::fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RES_AW;


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
