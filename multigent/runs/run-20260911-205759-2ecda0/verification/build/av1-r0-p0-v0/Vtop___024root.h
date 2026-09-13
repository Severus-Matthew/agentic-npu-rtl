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
    // Anonymous structures to workaround compiler member-count bugs
    struct {
        VL_IN8(clk,0,0);
        VL_IN8(rst,0,0);
        VL_IN8(cmd_valid,0,0);
        VL_OUT8(cmd_ready,0,0);
        VL_IN8(cmd_bias_enable,0,0);
        VL_IN8(cmd_relu_enable,0,0);
        VL_IN8(in_valid,0,0);
        VL_OUT8(in_ready,0,0);
        VL_OUT8(out_valid,0,0);
        VL_IN8(out_ready,0,0);
        VL_OUT8(out_last,0,0);
        VL_OUT8(done_valid,0,0);
        VL_IN8(done_ready,0,0);
        VL_OUT8(done_error,0,0);
        CData/*0:0*/ stream_matvec_int8__DOT__clk;
        CData/*0:0*/ stream_matvec_int8__DOT__rst;
        CData/*0:0*/ stream_matvec_int8__DOT__cmd_valid;
        CData/*0:0*/ stream_matvec_int8__DOT__cmd_ready;
        CData/*0:0*/ stream_matvec_int8__DOT__cmd_bias_enable;
        CData/*0:0*/ stream_matvec_int8__DOT__cmd_relu_enable;
        CData/*0:0*/ stream_matvec_int8__DOT__in_valid;
        CData/*0:0*/ stream_matvec_int8__DOT__in_ready;
        CData/*0:0*/ stream_matvec_int8__DOT__out_valid;
        CData/*0:0*/ stream_matvec_int8__DOT__out_ready;
        CData/*0:0*/ stream_matvec_int8__DOT__out_last;
        CData/*0:0*/ stream_matvec_int8__DOT__done_valid;
        CData/*0:0*/ stream_matvec_int8__DOT__done_ready;
        CData/*0:0*/ stream_matvec_int8__DOT__done_error;
        CData/*3:0*/ stream_matvec_int8__DOT__state;
        CData/*0:0*/ stream_matvec_int8__DOT__bias_enable_q;
        CData/*0:0*/ stream_matvec_int8__DOT__relu_enable_q;
        CData/*0:0*/ stream_matvec_int8__DOT__error_q;
        CData/*7:0*/ stream_matvec_int8__DOT__vector_write_index;
        CData/*7:0*/ stream_matvec_int8__DOT__column_index;
        CData/*7:0*/ stream_matvec_int8__DOT__tile_base;
        CData/*4:0*/ stream_matvec_int8__DOT__tile_height;
        CData/*3:0*/ stream_matvec_int8__DOT__lane_index;
        CData/*7:0*/ stream_matvec_int8__DOT__vector_value;
        CData/*0:0*/ stream_matvec_int8__DOT__last_lane;
        CData/*0:0*/ stream_matvec_int8__DOT__final_tile;
        CData/*0:0*/ stream_matvec_int8__DOT__command_legal;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__stream_matvec_int8__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        VL_IN16(cmd_rows,15,0);
        VL_IN16(cmd_cols,15,0);
        SData/*15:0*/ stream_matvec_int8__DOT__cmd_rows;
        SData/*15:0*/ stream_matvec_int8__DOT__cmd_cols;
        SData/*15:0*/ stream_matvec_int8__DOT__rows_q;
        SData/*15:0*/ stream_matvec_int8__DOT__cols_q;
        VL_IN(in_data,31,0);
        VL_OUT(out_data,31,0);
        IData/*31:0*/ stream_matvec_int8__DOT__in_data;
        IData/*31:0*/ stream_matvec_int8__DOT__out_data;
        IData/*16:0*/ stream_matvec_int8__DOT__rows_ext;
        IData/*16:0*/ stream_matvec_int8__DOT__cols_ext;
        IData/*16:0*/ stream_matvec_int8__DOT__base_ext;
        IData/*16:0*/ stream_matvec_int8__DOT__vector_write_ext;
        IData/*16:0*/ stream_matvec_int8__DOT__column_ext;
        IData/*16:0*/ stream_matvec_int8__DOT__remaining_rows;
    };
    struct {
        IData/*16:0*/ stream_matvec_int8__DOT__next_base;
        IData/*16:0*/ stream_matvec_int8__DOT__current_row;
        IData/*16:0*/ stream_matvec_int8__DOT__last_column;
        IData/*31:0*/ stream_matvec_int8__DOT__unnamedblk1__DOT__i;
        IData/*31:0*/ stream_matvec_int8__DOT__unnamedblk2__DOT__i;
        IData/*31:0*/ stream_matvec_int8__DOT__unnamedblk3__DOT__i;
        IData/*31:0*/ __VactIterCount;
        VlUnpacked<CData/*7:0*/, 256> stream_matvec_int8__DOT__vector_store;
        VlUnpacked<CData/*7:0*/, 16> stream_matvec_int8__DOT__matrix_staging;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__bias_staging;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__accumulator_result_bank;
        VlUnpacked<SData/*15:0*/, 16> stream_matvec_int8__DOT__product;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__extended_product;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__mac_value;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__selected_bias;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__biased_value;
        VlUnpacked<IData/*31:0*/, 16> stream_matvec_int8__DOT__final_value;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };
    VlNBACommitQueue<VlUnpacked<IData/*31:0*/, 16>, false, IData/*31:0*/, 1> __VdlyCommitQueuestream_matvec_int8__DOT__accumulator_result_bank;

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ stream_matvec_int8__DOT__MAX_ROWS = 0x00000100U;
    static constexpr IData/*31:0*/ stream_matvec_int8__DOT__MAX_COLS = 0x00000100U;
    static constexpr IData/*31:0*/ stream_matvec_int8__DOT__COL_W = 8U;
    static constexpr IData/*31:0*/ stream_matvec_int8__DOT__ROW_W = 8U;
    static constexpr IData/*16:0*/ stream_matvec_int8__DOT__ROW_LIMIT = 0x00000100U;
    static constexpr IData/*16:0*/ stream_matvec_int8__DOT__COL_LIMIT = 0x00000100U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
