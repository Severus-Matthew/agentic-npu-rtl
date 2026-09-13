// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table implementation internals

#include "Vtop__pch.h"

Vtop__Syms::Vtop__Syms(VerilatedContext* contextp, const char* namep, Vtop* modelp)
    : VerilatedSyms{contextp}
    // Setup internal state of the Syms class
    , __Vm_modelp{modelp}
    // Setup top module instance
    , TOP{this, namep}
{
    // Check resources
    Verilated::stackCheck(308);
    // Setup sub module instances
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscopep_TOP = new VerilatedScope{this, "TOP", "TOP", "<null>", 0, VerilatedScope::SCOPE_OTHER};
    __Vscopep_stream_matvec_int8 = new VerilatedScope{this, "stream_matvec_int8", "stream_matvec_int8", "stream_matvec_int8", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_stream_matvec_int8__unnamedblk1 = new VerilatedScope{this, "stream_matvec_int8.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_stream_matvec_int8__unnamedblk2 = new VerilatedScope{this, "stream_matvec_int8.unnamedblk2", "unnamedblk2", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_stream_matvec_int8__unnamedblk3 = new VerilatedScope{this, "stream_matvec_int8.unnamedblk3", "unnamedblk3", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_stream_matvec_int8);
    __Vhier.add(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk1);
    __Vhier.add(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk2);
    __Vhier.add(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk3);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_bias_enable", &(TOP.cmd_bias_enable), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_cols", &(TOP.cmd_cols), false, VLVT_UINT16, VLVD_IN|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_TOP->varInsert("cmd_ready", &(TOP.cmd_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_relu_enable", &(TOP.cmd_relu_enable), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_rows", &(TOP.cmd_rows), false, VLVT_UINT16, VLVD_IN|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_TOP->varInsert("cmd_valid", &(TOP.cmd_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("done_error", &(TOP.done_error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("done_ready", &(TOP.done_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("done_valid", &(TOP.done_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("in_data", &(TOP.in_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("in_ready", &(TOP.in_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("in_valid", &(TOP.in_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("out_last", &(TOP.out_last), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst", &(TOP.rst), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("COL_LIMIT", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__COL_LIMIT))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("COL_W", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__COL_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("MAX_COLS", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__MAX_COLS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("MAX_ROWS", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__MAX_ROWS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("ROW_LIMIT", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__ROW_LIMIT))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("ROW_W", const_cast<void*>(static_cast<const void*>(&(TOP.stream_matvec_int8__DOT__ROW_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("accumulator_result_bank", &(TOP.stream_matvec_int8__DOT__accumulator_result_bank), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("base_ext", &(TOP.stream_matvec_int8__DOT__base_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("bias_enable_q", &(TOP.stream_matvec_int8__DOT__bias_enable_q), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("bias_staging", &(TOP.stream_matvec_int8__DOT__bias_staging), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("biased_value", &(TOP.stream_matvec_int8__DOT__biased_value), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("clk", &(TOP.stream_matvec_int8__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_bias_enable", &(TOP.stream_matvec_int8__DOT__cmd_bias_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_cols", &(TOP.stream_matvec_int8__DOT__cmd_cols), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_ready", &(TOP.stream_matvec_int8__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_relu_enable", &(TOP.stream_matvec_int8__DOT__cmd_relu_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_rows", &(TOP.stream_matvec_int8__DOT__cmd_rows), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_stream_matvec_int8->varInsert("cmd_valid", &(TOP.stream_matvec_int8__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("cols_ext", &(TOP.stream_matvec_int8__DOT__cols_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("cols_q", &(TOP.stream_matvec_int8__DOT__cols_q), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_stream_matvec_int8->varInsert("column_ext", &(TOP.stream_matvec_int8__DOT__column_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("column_index", &(TOP.stream_matvec_int8__DOT__column_index), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_stream_matvec_int8->varInsert("command_legal", &(TOP.stream_matvec_int8__DOT__command_legal), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("current_row", &(TOP.stream_matvec_int8__DOT__current_row), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("done_error", &(TOP.stream_matvec_int8__DOT__done_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("done_ready", &(TOP.stream_matvec_int8__DOT__done_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("done_valid", &(TOP.stream_matvec_int8__DOT__done_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("error_q", &(TOP.stream_matvec_int8__DOT__error_q), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("extended_product", &(TOP.stream_matvec_int8__DOT__extended_product), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("final_tile", &(TOP.stream_matvec_int8__DOT__final_tile), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("final_value", &(TOP.stream_matvec_int8__DOT__final_value), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("in_data", &(TOP.stream_matvec_int8__DOT__in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("in_ready", &(TOP.stream_matvec_int8__DOT__in_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("in_valid", &(TOP.stream_matvec_int8__DOT__in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("lane_index", &(TOP.stream_matvec_int8__DOT__lane_index), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,3,0);
    __Vscopep_stream_matvec_int8->varInsert("last_column", &(TOP.stream_matvec_int8__DOT__last_column), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("last_lane", &(TOP.stream_matvec_int8__DOT__last_lane), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("mac_value", &(TOP.stream_matvec_int8__DOT__mac_value), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("matrix_staging", &(TOP.stream_matvec_int8__DOT__matrix_staging), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,15 ,7,0);
    __Vscopep_stream_matvec_int8->varInsert("next_base", &(TOP.stream_matvec_int8__DOT__next_base), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("out_data", &(TOP.stream_matvec_int8__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("out_last", &(TOP.stream_matvec_int8__DOT__out_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("out_ready", &(TOP.stream_matvec_int8__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("out_valid", &(TOP.stream_matvec_int8__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("product", &(TOP.stream_matvec_int8__DOT__product), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,15,0);
    __Vscopep_stream_matvec_int8->varInsert("relu_enable_q", &(TOP.stream_matvec_int8__DOT__relu_enable_q), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("remaining_rows", &(TOP.stream_matvec_int8__DOT__remaining_rows), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("rows_ext", &(TOP.stream_matvec_int8__DOT__rows_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("rows_q", &(TOP.stream_matvec_int8__DOT__rows_q), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_stream_matvec_int8->varInsert("rst", &(TOP.stream_matvec_int8__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_stream_matvec_int8->varInsert("selected_bias", &(TOP.stream_matvec_int8__DOT__selected_bias), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED|VLVF_NET, 1, 1 ,0,15 ,31,0);
    __Vscopep_stream_matvec_int8->varInsert("state", &(TOP.stream_matvec_int8__DOT__state), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,3,0);
    __Vscopep_stream_matvec_int8->varInsert("tile_base", &(TOP.stream_matvec_int8__DOT__tile_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_stream_matvec_int8->varInsert("tile_height", &(TOP.stream_matvec_int8__DOT__tile_height), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,4,0);
    __Vscopep_stream_matvec_int8->varInsert("vector_store", &(TOP.stream_matvec_int8__DOT__vector_store), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,255 ,7,0);
    __Vscopep_stream_matvec_int8->varInsert("vector_value", &(TOP.stream_matvec_int8__DOT__vector_value), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_stream_matvec_int8->varInsert("vector_write_ext", &(TOP.stream_matvec_int8__DOT__vector_write_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,16,0);
    __Vscopep_stream_matvec_int8->varInsert("vector_write_index", &(TOP.stream_matvec_int8__DOT__vector_write_index), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_stream_matvec_int8__unnamedblk1->varInsert("i", &(TOP.stream_matvec_int8__DOT__unnamedblk1__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8__unnamedblk2->varInsert("i", &(TOP.stream_matvec_int8__DOT__unnamedblk2__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_stream_matvec_int8__unnamedblk3->varInsert("i", &(TOP.stream_matvec_int8__DOT__unnamedblk3__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_stream_matvec_int8);
    __Vhier.remove(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk1);
    __Vhier.remove(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk2);
    __Vhier.remove(__Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8__unnamedblk3);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_stream_matvec_int8, __Vscopep_stream_matvec_int8 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_stream_matvec_int8__unnamedblk1, __Vscopep_stream_matvec_int8__unnamedblk1 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_stream_matvec_int8__unnamedblk2, __Vscopep_stream_matvec_int8__unnamedblk2 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_stream_matvec_int8__unnamedblk3, __Vscopep_stream_matvec_int8__unnamedblk3 = nullptr);
    // Tear down sub module instances
}
