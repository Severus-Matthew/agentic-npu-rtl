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
    Verilated::stackCheck(124);
    // Setup sub module instances
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscopep_TOP = new VerilatedScope{this, "TOP", "TOP", "<null>", 0, VerilatedScope::SCOPE_OTHER};
    __Vscopep_mv_npu_top = new VerilatedScope{this, "mv_npu_top", "mv_npu_top", "mv_npu_top", -12, VerilatedScope::SCOPE_MODULE};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_mv_npu_top);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("bias_data", &(TOP.bias_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("bias_ready", &(TOP.bias_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("bias_valid", &(TOP.bias_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_data", &(TOP.cmd_data), false, VLVT_UINT64, VLVD_IN|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("cmd_ready", &(TOP.cmd_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_valid", &(TOP.cmd_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("mat_data", &(TOP.mat_data), false, VLVT_WDATA, VLVD_IN|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_TOP->varInsert("mat_ready", &(TOP.mat_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("mat_valid", &(TOP.mat_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst_n", &(TOP.rst_n), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_busy", &(TOP.status_busy), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_error", &(TOP.status_error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("vec_data", &(TOP.vec_data), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_TOP->varInsert("vec_ready", &(TOP.vec_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("vec_valid", &(TOP.vec_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("BIAS_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__BIAS_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("CMD_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__CMD_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAT_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAT_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("OUT_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__OUT_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("VEC_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__VEC_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_data", &(TOP.mv_npu_top__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_ready", &(TOP.mv_npu_top__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("bias_valid", &(TOP.mv_npu_top__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("clk", &(TOP.mv_npu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cmd_data", &(TOP.mv_npu_top__DOT__cmd_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_mv_npu_top->varInsert("cmd_ready", &(TOP.mv_npu_top__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cmd_valid", &(TOP.mv_npu_top__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("mat_data", &(TOP.mv_npu_top__DOT__mat_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_mv_npu_top->varInsert("mat_ready", &(TOP.mv_npu_top__DOT__mat_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("mat_valid", &(TOP.mv_npu_top__DOT__mat_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_data", &(TOP.mv_npu_top__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("out_ready", &(TOP.mv_npu_top__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_valid", &(TOP.mv_npu_top__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("rst_n", &(TOP.mv_npu_top__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("status_busy", &(TOP.mv_npu_top__DOT__status_busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("status_error", &(TOP.mv_npu_top__DOT__status_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("vec_data", &(TOP.mv_npu_top__DOT__vec_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("vec_ready", &(TOP.mv_npu_top__DOT__vec_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("vec_valid", &(TOP.mv_npu_top__DOT__vec_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_mv_npu_top);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top, __Vscopep_mv_npu_top = nullptr);
    // Tear down sub module instances
}
