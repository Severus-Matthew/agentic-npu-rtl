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
    Verilated::stackCheck(322);
    // Setup sub module instances
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscopep_TOP = new VerilatedScope{this, "TOP", "TOP", "<null>", 0, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top = new VerilatedScope{this, "gemm_bias_relu_npu_top", "gemm_bias_relu_npu_top", "gemm_bias_relu_npu_top", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_core = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_core", "u_core", "gemm_core", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_core.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_core.unnamedblk2", "unnamedblk2", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_core.unnamedblk3", "unnamedblk3", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_core.unnamedblk3.unnamedblk4", "unnamedblk4", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_ctrl", "u_ctrl", "npu_control_fsm", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_ctrl.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_loader = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_loader", "u_loader", "input_loader", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_out = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_out", "u_out", "output_streamer", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_post = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_post", "u_post", "postproc_relu_bias", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_post.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2 = new VerilatedScope{this, "gemm_bias_relu_npu_top.u_post.unnamedblk1.unnamedblk2", "unnamedblk2", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__unnamedblk1 = new VerilatedScope{this, "gemm_bias_relu_npu_top.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2 = new VerilatedScope{this, "gemm_bias_relu_npu_top.unnamedblk1.unnamedblk2", "unnamedblk2", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_gemm_bias_relu_npu_top);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_core);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_ctrl);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_loader);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_out);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_post);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_ctrl, __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_post, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2);
    __Vhier.add(__Vscopep_gemm_bias_relu_npu_top__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("a_data", &(TOP.a_data), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_TOP->varInsert("a_ready", &(TOP.a_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("a_valid", &(TOP.a_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("b_data", &(TOP.b_data), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_TOP->varInsert("b_ready", &(TOP.b_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("b_valid", &(TOP.b_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("bias_data", &(TOP.bias_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("bias_ready", &(TOP.bias_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("bias_valid", &(TOP.bias_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_data", &(TOP.cmd_data), false, VLVT_WDATA, VLVD_IN|VLVF_PUB_RW, 0, 1 ,95,0);
    __Vscopep_TOP->varInsert("cmd_ready", &(TOP.cmd_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_valid", &(TOP.cmd_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst_n", &(TOP.rst_n), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_done", &(TOP.status_done), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_error", &(TOP.status_error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("A_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__A_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("B_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__B_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("TILE_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__TILE_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_data", &(TOP.gemm_bias_relu_npu_top__DOT__a_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_elem", &(TOP.gemm_bias_relu_npu_top__DOT__a_elem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_ready", &(TOP.gemm_bias_relu_npu_top__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_valid", &(TOP.gemm_bias_relu_npu_top__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__a_wr_addr), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("a_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_data", &(TOP.gemm_bias_relu_npu_top__DOT__b_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_ready", &(TOP.gemm_bias_relu_npu_top__DOT__b_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_valid", &(TOP.gemm_bias_relu_npu_top__DOT__b_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_vec", &(TOP.gemm_bias_relu_npu_top__DOT__b_vec), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__b_wr_addr), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("b_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("bias_data", &(TOP.gemm_bias_relu_npu_top__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("bias_ready", &(TOP.gemm_bias_relu_npu_top__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("bias_valid", &(TOP.gemm_bias_relu_npu_top__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("bias_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("bias_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("buf_A", &(TOP.gemm_bias_relu_npu_top__DOT__buf_A), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,4095 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("buf_B", &(TOP.gemm_bias_relu_npu_top__DOT__buf_B), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,4095 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("buf_bias", &(TOP.gemm_bias_relu_npu_top__DOT__buf_bias), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,63 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cfg_bias_enable", &(TOP.gemm_bias_relu_npu_top__DOT__cfg_bias_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cfg_k", &(TOP.gemm_bias_relu_npu_top__DOT__cfg_k), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cfg_m", &(TOP.gemm_bias_relu_npu_top__DOT__cfg_m), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cfg_n", &(TOP.gemm_bias_relu_npu_top__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("clk", &(TOP.gemm_bias_relu_npu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cmd_data", &(TOP.gemm_bias_relu_npu_top__DOT__cmd_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,95,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cmd_ready", &(TOP.gemm_bias_relu_npu_top__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("cmd_valid", &(TOP.gemm_bias_relu_npu_top__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("compute_tile_done", &(TOP.gemm_bias_relu_npu_top__DOT__compute_tile_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("do_compute_start", &(TOP.gemm_bias_relu_npu_top__DOT__do_compute_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("do_compute_step", &(TOP.gemm_bias_relu_npu_top__DOT__do_compute_step), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("do_done_pulse", &(TOP.gemm_bias_relu_npu_top__DOT__do_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("do_emit_start", &(TOP.gemm_bias_relu_npu_top__DOT__do_emit_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("emit_busy", &(TOP.gemm_bias_relu_npu_top__DOT__emit_busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("emit_done", &(TOP.gemm_bias_relu_npu_top__DOT__emit_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("idx_k", &(TOP.gemm_bias_relu_npu_top__DOT__idx_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("idx_m", &(TOP.gemm_bias_relu_npu_top__DOT__idx_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("idx_n_base", &(TOP.gemm_bias_relu_npu_top__DOT__idx_n_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("lane_acc", &(TOP.gemm_bias_relu_npu_top__DOT__lane_acc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("lane_active", &(TOP.gemm_bias_relu_npu_top__DOT__lane_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("lane_post", &(TOP.gemm_bias_relu_npu_top__DOT__lane_post), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("load_a_done", &(TOP.gemm_bias_relu_npu_top__DOT__load_a_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("load_b_done", &(TOP.gemm_bias_relu_npu_top__DOT__load_b_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("load_bias_done", &(TOP.gemm_bias_relu_npu_top__DOT__load_bias_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("out_data", &(TOP.gemm_bias_relu_npu_top__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("out_ready", &(TOP.gemm_bias_relu_npu_top__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("out_valid", &(TOP.gemm_bias_relu_npu_top__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("rst_n", &(TOP.gemm_bias_relu_npu_top__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("st_compute", &(TOP.gemm_bias_relu_npu_top__DOT__st_compute), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("st_emit", &(TOP.gemm_bias_relu_npu_top__DOT__st_emit), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("st_load_a", &(TOP.gemm_bias_relu_npu_top__DOT__st_load_a), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("st_load_b", &(TOP.gemm_bias_relu_npu_top__DOT__st_load_b), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("st_load_bias", &(TOP.gemm_bias_relu_npu_top__DOT__st_load_bias), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("status_done", &(TOP.gemm_bias_relu_npu_top__DOT__status_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top->varInsert("status_error", &(TOP.gemm_bias_relu_npu_top__DOT__status_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("TILE_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__TILE_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("a_elem", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("b_vec", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("cfg_k", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("clk", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("do_start", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("do_step", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("k_count", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("lane_acc", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("lane_active", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("rst_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core->varInsert("tile_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4->varInsert("p16", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4->varInsert("p32", &(TOP.gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p32), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("TILE_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__TILE_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cfg_bias_enable", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cfg_k", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cfg_m", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cfg_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("clk", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cmd_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data), false, VLVT_WDATA, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,95,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cmd_ready", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("cmd_valid", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("compute_tile_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("do_compute_start", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("do_compute_step", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("do_done_pulse", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("do_emit_start", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("emit_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("idx_k", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("idx_m", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("idx_n_base", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("lane_active", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("load_a_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("load_b_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("load_bias_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("n_tiles", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("rst_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("st_compute", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("st_emit", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("st_load_a", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("st_load_b", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("st_load_bias", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("state", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("status_error", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl->varInsert("t_idx", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_ready", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_valid", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_wr_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("a_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_ready", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_valid", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_wr_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("b_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_enable", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_ready", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_valid", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_wr_addr", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_wr_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("bias_wr_en", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cfg_k", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cfg_m", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cfg_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("clk", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cnt_a", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cnt_b", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("cnt_bias", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("load_a_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("load_b_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("load_bias_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("rst_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("st_load_a", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("st_load_b", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_loader->varInsert("st_load_bias", &(TOP.gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("TILE_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__TILE_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("clk", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("do_start", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("emit_busy", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("emit_done", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("lane_active", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("lane_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("lane_idx", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("out_data", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("out_ready", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("out_valid", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("rst_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_out->varInsert("started", &(TOP.gemm_bias_relu_npu_top__DOT__u_out__DOT__started), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("TILE_N", const_cast<void*>(static_cast<const void*>(&(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__TILE_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("bias_enable", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("bias_mem", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,63 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("cfg_n", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("idx_n_base", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,15,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("lane_acc", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("lane_active", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post->varInsert("lane_out", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2->varInsert("t", &(TOP.gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__unnamedblk1->varInsert("n_idx", &(TOP.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2->varInsert("i", &(TOP.gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_gemm_bias_relu_npu_top);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_core);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_ctrl);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_loader);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_out);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__u_post);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_ctrl, __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_post, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2);
    __Vhier.remove(__Vscopep_gemm_bias_relu_npu_top__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top, __Vscopep_gemm_bias_relu_npu_top = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_core, __Vscopep_gemm_bias_relu_npu_top__u_core = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4, __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_ctrl, __Vscopep_gemm_bias_relu_npu_top__u_ctrl = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_loader, __Vscopep_gemm_bias_relu_npu_top__u_loader = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_out, __Vscopep_gemm_bias_relu_npu_top__u_out = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_post, __Vscopep_gemm_bias_relu_npu_top__u_post = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2, __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__unnamedblk1, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1 = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2, __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2 = nullptr);
    // Tear down sub module instances
}
