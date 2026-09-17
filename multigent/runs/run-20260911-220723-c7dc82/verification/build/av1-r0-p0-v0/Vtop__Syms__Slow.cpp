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
    Verilated::stackCheck(276);
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
    __Vscopep_mv_npu_top__u_ctrl = new VerilatedScope{this, "mv_npu_top.u_ctrl", "u_ctrl", "ctrl_fsm", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_input_router = new VerilatedScope{this, "mv_npu_top.u_input_router", "u_input_router", "input_router", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_mac = new VerilatedScope{this, "mv_npu_top.u_mac", "u_mac", "mac16_core", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_out = new VerilatedScope{this, "mv_npu_top.u_out", "u_out", "output_if", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_post = new VerilatedScope{this, "mv_npu_top.u_post", "u_post", "postproc_unit", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_mv_npu_top__u_xmem = new VerilatedScope{this, "mv_npu_top.u_xmem", "u_xmem", "x_buffer_mem", -12, VerilatedScope::SCOPE_MODULE};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_mv_npu_top);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_ctrl);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_input_router);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_mac);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_out);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_post);
    __Vhier.add(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_xmem);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("busy", &(TOP.busy), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("in_data", &(TOP.in_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("in_last", &(TOP.in_last), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("in_ready", &(TOP.in_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("in_type", &(TOP.in_type), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_TOP->varInsert("in_valid", &(TOP.in_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("out_last", &(TOP.out_last), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst_n", &(TOP.rst_n), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_err", &(TOP.status_err), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("MW", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__MW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("NW", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__NW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("XAW", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__XAW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("a_lane_data", &(TOP.mv_npu_top__DOT__a_lane_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_mv_npu_top->varInsert("a_lane_valid", &(TOP.mv_npu_top__DOT__a_lane_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("a_val", &(TOP.mv_npu_top__DOT__a_val), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("acc_out", &(TOP.mv_npu_top__DOT__acc_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_data", &(TOP.mv_npu_top__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_en_runtime", &(TOP.mv_npu_top__DOT__bias_en_runtime), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("bias_hold", &(TOP.mv_npu_top__DOT__bias_hold), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("bias_valid", &(TOP.mv_npu_top__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("busy", &(TOP.mv_npu_top__DOT__busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_bias_en", &(TOP.mv_npu_top__DOT__cfg_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_m", &(TOP.mv_npu_top__DOT__cfg_m), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("cfg_n", &(TOP.mv_npu_top__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("cfg_relu_en", &(TOP.mv_npu_top__DOT__cfg_relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_valid", &(TOP.mv_npu_top__DOT__cfg_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("cfg_word", &(TOP.mv_npu_top__DOT__cfg_word), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_mv_npu_top->varInsert("clk", &(TOP.mv_npu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("col_idx", &(TOP.mv_npu_top__DOT__col_idx), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("compute_active", &(TOP.mv_npu_top__DOT__compute_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("compute_step_pulse", &(TOP.mv_npu_top__DOT__compute_step_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("in_data", &(TOP.mv_npu_top__DOT__in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("in_last", &(TOP.mv_npu_top__DOT__in_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("in_ready", &(TOP.mv_npu_top__DOT__in_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("in_type", &(TOP.mv_npu_top__DOT__in_type), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_mv_npu_top->varInsert("in_valid", &(TOP.mv_npu_top__DOT__in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("job_done_pulse", &(TOP.mv_npu_top__DOT__job_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("m_runtime", &(TOP.mv_npu_top__DOT__m_runtime), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("n_runtime", &(TOP.mv_npu_top__DOT__n_runtime), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("out_accept_pulse", &(TOP.mv_npu_top__DOT__out_accept_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_data", &(TOP.mv_npu_top__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("out_in_data", &(TOP.mv_npu_top__DOT__out_in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top->varInsert("out_in_last", &(TOP.mv_npu_top__DOT__out_in_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_in_valid", &(TOP.mv_npu_top__DOT__out_in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_last", &(TOP.mv_npu_top__DOT__out_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_ready", &(TOP.mv_npu_top__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("out_valid", &(TOP.mv_npu_top__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("relu_en_runtime", &(TOP.mv_npu_top__DOT__relu_en_runtime), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("row_finalize_pulse", &(TOP.mv_npu_top__DOT__row_finalize_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("row_idx", &(TOP.mv_npu_top__DOT__row_idx), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top->varInsert("rst_n", &(TOP.mv_npu_top__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("start_row", &(TOP.mv_npu_top__DOT__start_row), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("status_err", &(TOP.mv_npu_top__DOT__status_err), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("step_valid", &(TOP.mv_npu_top__DOT__step_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("x_raddr", &(TOP.mv_npu_top__DOT__x_raddr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("x_rdata", &(TOP.mv_npu_top__DOT__x_rdata), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("x_val", &(TOP.mv_npu_top__DOT__x_val), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("x_waddr", &(TOP.mv_npu_top__DOT__x_waddr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("x_wdata", &(TOP.mv_npu_top__DOT__x_wdata), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top->varInsert("x_we", &(TOP.mv_npu_top__DOT__x_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top->varInsert("y_post", &(TOP.mv_npu_top__DOT__y_post), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_ctrl__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("busy", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_bias_en", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_m", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_m), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_n", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,8,0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_relu_en", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("cfg_valid", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__cfg_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("clk", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("compute_step_pulse", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__compute_step_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("in_beat_accepted", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__in_beat_accepted), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("job_done_pulse", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__job_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("out_beat_accepted", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__out_beat_accepted), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("row_finalize_pulse", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__row_finalize_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_ctrl->varInsert("status_err", &(TOP.mv_npu_top__DOT__u_ctrl__DOT__status_err), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_input_router__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_input_router__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("a_lane_data", &(TOP.mv_npu_top__DOT__u_input_router__DOT__a_lane_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,127,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("a_lane_valid", &(TOP.mv_npu_top__DOT__u_input_router__DOT__a_lane_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("bias_data", &(TOP.mv_npu_top__DOT__u_input_router__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("bias_valid", &(TOP.mv_npu_top__DOT__u_input_router__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("cfg_valid", &(TOP.mv_npu_top__DOT__u_input_router__DOT__cfg_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("cfg_word", &(TOP.mv_npu_top__DOT__u_input_router__DOT__cfg_word), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("clk", &(TOP.mv_npu_top__DOT__u_input_router__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("in_data", &(TOP.mv_npu_top__DOT__u_input_router__DOT__in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("in_ready", &(TOP.mv_npu_top__DOT__u_input_router__DOT__in_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("in_type", &(TOP.mv_npu_top__DOT__u_input_router__DOT__in_type), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("in_valid", &(TOP.mv_npu_top__DOT__u_input_router__DOT__in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_input_router__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("x_count", &(TOP.mv_npu_top__DOT__u_input_router__DOT__x_count), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("x_waddr", &(TOP.mv_npu_top__DOT__u_input_router__DOT__x_waddr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("x_wdata", &(TOP.mv_npu_top__DOT__u_input_router__DOT__x_wdata), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_input_router->varInsert("x_we", &(TOP.mv_npu_top__DOT__u_input_router__DOT__x_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("LANES", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_mac__DOT__LANES))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_mac__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("a_val", &(TOP.mv_npu_top__DOT__u_mac__DOT__a_val), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("acc", &(TOP.mv_npu_top__DOT__u_mac__DOT__acc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("acc_out", &(TOP.mv_npu_top__DOT__u_mac__DOT__acc_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("clk", &(TOP.mv_npu_top__DOT__u_mac__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("prod", &(TOP.mv_npu_top__DOT__u_mac__DOT__prod), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_SIGNED, 0, 1 ,15,0);
    __Vscopep_mv_npu_top__u_mac->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_mac__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("start_row", &(TOP.mv_npu_top__DOT__u_mac__DOT__start_row), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("step_valid", &(TOP.mv_npu_top__DOT__u_mac__DOT__step_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_mac->varInsert("x_val", &(TOP.mv_npu_top__DOT__u_mac__DOT__x_val), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_out->varInsert("clk", &(TOP.mv_npu_top__DOT__u_out__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("in_data", &(TOP.mv_npu_top__DOT__u_out__DOT__in_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_out->varInsert("in_last", &(TOP.mv_npu_top__DOT__u_out__DOT__in_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("in_valid", &(TOP.mv_npu_top__DOT__u_out__DOT__in_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("out_accept_pulse", &(TOP.mv_npu_top__DOT__u_out__DOT__out_accept_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("out_data", &(TOP.mv_npu_top__DOT__u_out__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_out->varInsert("out_last", &(TOP.mv_npu_top__DOT__u_out__DOT__out_last), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("out_ready", &(TOP.mv_npu_top__DOT__u_out__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("out_valid", &(TOP.mv_npu_top__DOT__u_out__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_out->varInsert("rst_n", &(TOP.mv_npu_top__DOT__u_out__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("acc_in", &(TOP.mv_npu_top__DOT__u_post__DOT__acc_in), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("bias_en", &(TOP.mv_npu_top__DOT__u_post__DOT__bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("bias_in", &(TOP.mv_npu_top__DOT__u_post__DOT__bias_in), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("relu_en", &(TOP.mv_npu_top__DOT__u_post__DOT__relu_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_post->varInsert("y_out", &(TOP.mv_npu_top__DOT__u_post__DOT__y_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_post->varInsert("y_pre", &(TOP.mv_npu_top__DOT__u_post__DOT__y_pre), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.mv_npu_top__DOT__u_xmem__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("clk", &(TOP.mv_npu_top__DOT__u_xmem__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("mem", &(TOP.mv_npu_top__DOT__u_xmem__DOT__mem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,255 ,7,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("raddr", &(TOP.mv_npu_top__DOT__u_xmem__DOT__raddr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("rdata", &(TOP.mv_npu_top__DOT__u_xmem__DOT__rdata), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("waddr", &(TOP.mv_npu_top__DOT__u_xmem__DOT__waddr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("wdata", &(TOP.mv_npu_top__DOT__u_xmem__DOT__wdata), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_mv_npu_top__u_xmem->varInsert("we", &(TOP.mv_npu_top__DOT__u_xmem__DOT__we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_mv_npu_top);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_ctrl);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_input_router);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_mac);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_out);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_post);
    __Vhier.remove(__Vscopep_mv_npu_top, __Vscopep_mv_npu_top__u_xmem);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top, __Vscopep_mv_npu_top = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_ctrl, __Vscopep_mv_npu_top__u_ctrl = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_input_router, __Vscopep_mv_npu_top__u_input_router = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_mac, __Vscopep_mv_npu_top__u_mac = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_out, __Vscopep_mv_npu_top__u_out = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_post, __Vscopep_mv_npu_top__u_post = nullptr);
    VL_DO_CLEAR(delete __Vscopep_mv_npu_top__u_xmem, __Vscopep_mv_npu_top__u_xmem = nullptr);
    // Tear down sub module instances
}
