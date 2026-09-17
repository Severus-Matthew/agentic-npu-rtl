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
    Verilated::stackCheck(280);
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
    __Vscopep_mv_npu_top__u_ctrl = new VerilatedScope{this, "mv_npu_top.u_ctrl", "u_ctrl", "mv_ctrl_fsm", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_mac = new VerilatedScope{this, "mv_npu_top.u_mac", "u_mac", "mv_mac16_core", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_post = new VerilatedScope{this, "mv_npu_top.u_post", "u_post", "mv_postproc", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_stream_if = new VerilatedScope{this, "mv_npu_top.u_stream_if", "u_stream_if", "mv_stream_if", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_vec_buffer = new VerilatedScope{this, "mv_npu_top.u_vec_buffer", "u_vec_buffer", "mv_vec_buffer", -12, VerilatedScope::SCOPE_MODULE};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_mv_npu_top);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_ctrl);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_mac);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_post);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_stream_if);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_vec_buffer);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("bias_data", &(TOP.bias_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("bias_ready", &(TOP.bias_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("bias_valid", &(TOP.bias_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_data", &(TOP.cmd_data), false, VLVT_UINT64, VLVD_IN|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("cmd_ready", &(TOP.cmd_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("cmd_valid", &(TOP.cmd_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("mat_data", &(TOP.mat_data), false, VLVT_WDATA, VLVD_IN|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_TOP->varInsert("mat_ready", &(TOP.mat_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("mat_valid", &(TOP.mat_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("rst_n", &(TOP.rst_n), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_busy", &(TOP.status_busy), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_error", &(TOP.status_error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("vec_data", &(TOP.vec_data), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_TOP->varInsert("vec_ready", &(TOP.vec_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("vec_valid", &(TOP.vec_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("AW", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("BIAS_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__BIAS_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("CMD_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__CMD_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAT_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAT_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("OUT_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__OUT_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("VEC_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__VEC_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_data", &(TOP.mv_npu_top__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_ready", &(TOP.mv_npu_top__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("bias_valid", &(TOP.mv_npu_top__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("bias_xfer", &(TOP.mv_npu_top__DOT__bias_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_M", &(TOP.mv_npu_top__DOT__cfg_M), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("cfg_N", &(TOP.mv_npu_top__DOT__cfg_N), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("cfg_bias_en", &(TOP.mv_npu_top__DOT__cfg_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_relu_en", &(TOP.mv_npu_top__DOT__cfg_relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("chunks_per_row", &(TOP.mv_npu_top__DOT__chunks_per_row), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("clk", &(TOP.mv_npu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cmd_accept", &(TOP.mv_npu_top__DOT__cmd_accept), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cmd_data", &(TOP.mv_npu_top__DOT__cmd_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_mv_npu_top->varInsert("cmd_ready", &(TOP.mv_npu_top__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cmd_valid", &(TOP.mv_npu_top__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("compute_en_core", &(TOP.mv_npu_top__DOT__compute_en_core), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("k_chunk_idx", &(TOP.mv_npu_top__DOT__k_chunk_idx), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("lane_valid_mask", &(TOP.mv_npu_top__DOT__lane_valid_mask), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("mat_data", &(TOP.mv_npu_top__DOT__mat_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_mv_npu_top->varInsert("mat_lanes", &(TOP.mv_npu_top__DOT__mat_lanes), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top->varInsert("mat_ready", &(TOP.mv_npu_top__DOT__mat_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("mat_valid", &(TOP.mv_npu_top__DOT__mat_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("mat_xfer", &(TOP.mv_npu_top__DOT__mat_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("new_row_core", &(TOP.mv_npu_top__DOT__new_row_core), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_data", &(TOP.mv_npu_top__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("out_ready", &(TOP.mv_npu_top__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_valid", &(TOP.mv_npu_top__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_xfer", &(TOP.mv_npu_top__DOT__out_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("pp_bias_valid", &(TOP.mv_npu_top__DOT__pp_bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("pp_in_ready", &(TOP.mv_npu_top__DOT__pp_in_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("pp_in_valid", &(TOP.mv_npu_top__DOT__pp_in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("pp_out_data", &(TOP.mv_npu_top__DOT__pp_out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("pp_out_valid", &(TOP.mv_npu_top__DOT__pp_out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("rd_chunk_base", &(TOP.mv_npu_top__DOT__rd_chunk_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("row_accum_out", &(TOP.mv_npu_top__DOT__row_accum_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("row_done_pulse", &(TOP.mv_npu_top__DOT__row_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("row_idx", &(TOP.mv_npu_top__DOT__row_idx), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top->varInsert("rst_n", &(TOP.mv_npu_top__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("state_compute_en", &(TOP.mv_npu_top__DOT__state_compute_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("status_busy", &(TOP.mv_npu_top__DOT__status_busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("status_error", &(TOP.mv_npu_top__DOT__status_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("vec_data", &(TOP.mv_npu_top__DOT__vec_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("vec_lanes", &(TOP.mv_npu_top__DOT__vec_lanes), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top->varInsert("vec_ready", &(TOP.mv_npu_top__DOT__vec_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("vec_valid", &(TOP.mv_npu_top__DOT__vec_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("vec_wr_addr", &(TOP.mv_npu_top__DOT__vec_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("vec_xfer", &(TOP.mv_npu_top__DOT__vec_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("CMD_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__CMD_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("bias_xfer", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__bias_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_M", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_M), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_N", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_N), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_bias_en", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_relu_en", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("chunk_cnt", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__chunk_cnt), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("chunks_per_row", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__chunks_per_row), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("clk", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cmd_accept", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cmd_accept), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cmd_data", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cmd_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("lane_valid_mask", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__lane_valid_mask), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("mat_xfer", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__mat_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("out_xfer", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__out_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("rem", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__rem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,4,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("row_cnt", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__row_cnt), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("st", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__st), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("state_compute_en", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__state_compute_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("status_busy", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__status_busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("status_error", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__status_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("vec_cnt", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__vec_cnt), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("vec_xfer", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__vec_xfer), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_mac__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("clk", &(TOP.mv_npu_top__DOT__u_mac__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("compute_en", &(TOP.mv_npu_top__DOT__u_mac__DOT__compute_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("i", &(TOP.mv_npu_top__DOT__u_mac__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("lane_valid_mask", &(TOP.mv_npu_top__DOT__u_mac__DOT__lane_valid_mask), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("m_i", &(TOP.mv_npu_top__DOT__u_mac__DOT__m_i), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("mat_lane_data", &(TOP.mv_npu_top__DOT__u_mac__DOT__mat_lane_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("new_row", &(TOP.mv_npu_top__DOT__u_mac__DOT__new_row), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("p_i", &(TOP.mv_npu_top__DOT__u_mac__DOT__p_i), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("row_accum_out", &(TOP.mv_npu_top__DOT__u_mac__DOT__row_accum_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("row_done_pulse", &(TOP.mv_npu_top__DOT__u_mac__DOT__row_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_mac__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("sum32", &(TOP.mv_npu_top__DOT__u_mac__DOT__sum32), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("v_i", &(TOP.mv_npu_top__DOT__u_mac__DOT__v_i), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("vec_lane_data", &(TOP.mv_npu_top__DOT__u_mac__DOT__vec_lane_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_post->varInsert("bias_data", &(TOP.mv_npu_top__DOT__u_post__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("bias_en", &(TOP.mv_npu_top__DOT__u_post__DOT__bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("bias_valid", &(TOP.mv_npu_top__DOT__u_post__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("clk", &(TOP.mv_npu_top__DOT__u_post__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("in_data", &(TOP.mv_npu_top__DOT__u_post__DOT__in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("in_ready", &(TOP.mv_npu_top__DOT__u_post__DOT__in_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("in_valid", &(TOP.mv_npu_top__DOT__u_post__DOT__in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("out_data", &(TOP.mv_npu_top__DOT__u_post__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("out_ready", &(TOP.mv_npu_top__DOT__u_post__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("out_valid", &(TOP.mv_npu_top__DOT__u_post__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("post_act", &(TOP.mv_npu_top__DOT__u_post__DOT__post_act), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("pre_act", &(TOP.mv_npu_top__DOT__u_post__DOT__pre_act), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("relu_en", &(TOP.mv_npu_top__DOT__u_post__DOT__relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_post__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_stream_if->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_stream_if__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_stream_if->varInsert("MAT_DATA_W", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_stream_if__DOT__MAT_DATA_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_stream_if->varInsert("mat_data_in", &(TOP.mv_npu_top__DOT__u_stream_if__DOT__mat_data_in), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_stream_if->varInsert("mat_lanes_out", &(TOP.mv_npu_top__DOT__u_stream_if__DOT__mat_lanes_out), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("clk", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("j", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__j), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("mem", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__mem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,255 ,7,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("rd_chunk_base", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__rd_chunk_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("rd_data", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__rd_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("wr_addr", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("wr_data", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_vec_buffer->varInsert("wr_en", &(TOP.mv_npu_top__DOT__u_vec_buffer__DOT__wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_mv_npu_top);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_ctrl);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_mac);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_post);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_stream_if);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_vec_buffer);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top, __Vscopep_mv_npu_top = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_ctrl, __Vscopep_mv_npu_top__u_ctrl = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_mac, __Vscopep_mv_npu_top__u_mac = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_post, __Vscopep_mv_npu_top__u_post = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_stream_if, __Vscopep_mv_npu_top__u_stream_if = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_vec_buffer, __Vscopep_mv_npu_top__u_vec_buffer = nullptr);
    // Tear down sub module instances
}
