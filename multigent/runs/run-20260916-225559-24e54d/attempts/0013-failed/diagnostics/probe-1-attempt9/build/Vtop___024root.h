// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtop.h for the primary calling header

#ifndef VERILATED_VTOP___024ROOT_H_
#define VERILATED_VTOP___024ROOT_H_  // guard

#include "verilated.h"


class Vtop__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtop___024root final {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(rst_n,0,0);
    VL_IN8(in_valid,0,0);
    VL_OUT8(in_ready,0,0);
    VL_IN8(in_a,7,0);
    VL_IN8(in_b,7,0);
    VL_OUT8(out_valid,0,0);
    VL_IN8(out_ready,0,0);
    CData/*0:0*/ unsigned_adder__DOT__clk;
    CData/*0:0*/ unsigned_adder__DOT__rst_n;
    CData/*0:0*/ unsigned_adder__DOT__in_valid;
    CData/*0:0*/ unsigned_adder__DOT__in_ready;
    CData/*7:0*/ unsigned_adder__DOT__in_a;
    CData/*7:0*/ unsigned_adder__DOT__in_b;
    CData/*0:0*/ unsigned_adder__DOT__out_valid;
    CData/*0:0*/ unsigned_adder__DOT__out_ready;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VstlPhaseResult;
    CData/*0:0*/ __VicoFirstIteration;
    CData/*0:0*/ __VicoPhaseResult;
    CData/*0:0*/ __Vtrigprevexpr___TOP__unsigned_adder__DOT__clk__0;
    CData/*0:0*/ __VactPhaseResult;
    CData/*0:0*/ __VnbaPhaseResult;
    VL_OUT16(out_sum,8,0);
    SData/*8:0*/ unsigned_adder__DOT__out_sum;
    SData/*8:0*/ unsigned_adder__DOT__operand_a_ext;
    SData/*8:0*/ unsigned_adder__DOT__operand_b_ext;
    SData/*8:0*/ unsigned_adder__DOT__sum_next;
    IData/*31:0*/ __VactIterCount;
    VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
