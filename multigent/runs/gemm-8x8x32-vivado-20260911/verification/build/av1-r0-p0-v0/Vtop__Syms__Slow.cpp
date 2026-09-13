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
    Verilated::stackCheck(252);
    // Setup sub module instances
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscopep_TOP = new VerilatedScope{this, "TOP", "TOP", "<null>", 0, VerilatedScope::SCOPE_OTHER};
    __Vscopep_gemm8x8x32_bias_relu_top = new VerilatedScope{this, "gemm8x8x32_bias_relu_top", "gemm8x8x32_bias_relu_top", "gemm8x8x32_bias_relu_top", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_core = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_core", "u_core", "gemm_core_seq", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_loader", "u_loader", "input_loader", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_mem", "u_mem", "local_memories", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_out = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_out", "u_out", "output_streamer", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_post = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_post", "u_post", "postproc_relu_bias", -12, VerilatedScope::SCOPE_MODULE};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_gemm8x8x32_bias_relu_top);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_core);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_loader);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_mem);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_out);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_post);
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
    __Vscopep_TOP->varInsert("done", &(TOP.done), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("error", &(TOP.error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("rst", &(TOP.rst), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("y_data", &(TOP.y_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("y_ready", &(TOP.y_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("y_valid", &(TOP.y_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("ACC_ELEMS", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__ACC_ELEMS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("A_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__A_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("B_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__B_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("K_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__K_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("M_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__M_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("N_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__N_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("Y_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__Y_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("compute_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__compute_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("compute_start", &(TOP.gemm8x8x32_bias_relu_top__DOT__compute_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("done", &(TOP.gemm8x8x32_bias_relu_top__DOT__done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("emit_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__emit_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("emit_start", &(TOP.gemm8x8x32_bias_relu_top__DOT__emit_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("error", &(TOP.gemm8x8x32_bias_relu_top__DOT__error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("error_sticky", &(TOP.gemm8x8x32_bias_relu_top__DOT__error_sticky), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("finalize_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__finalize_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("finalize_start", &(TOP.gemm8x8x32_bias_relu_top__DOT__finalize_start), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_a_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_a_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_a_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_a_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_b_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_b_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_b_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_b_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_bias_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_bias_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_bias_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_err", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_err), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("state", &(TOP.gemm8x8x32_bias_relu_top__DOT__state), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,3,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("y_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__y_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_core->varInsert("K_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_core__DOT__K_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_core->varInsert("M_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_core__DOT__M_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_core->varInsert("N_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_core__DOT__N_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("A_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("B_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__B_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("N_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__N_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_a_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_a_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_a_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_b_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_b_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_b_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_bias_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_bias_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_bias_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_err", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_err), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("K_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__K_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("M_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__M_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("N_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__N_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("Y_ELEMS_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__Y_ELEMS_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("M_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__M_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("N_FIXED", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__N_FIXED))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_gemm8x8x32_bias_relu_top);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_core);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_loader);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_mem);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_out);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_post);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_core, __Vscopep_gemm8x8x32_bias_relu_top__u_core = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_loader, __Vscopep_gemm8x8x32_bias_relu_top__u_loader = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_mem, __Vscopep_gemm8x8x32_bias_relu_top__u_mem = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_out, __Vscopep_gemm8x8x32_bias_relu_top__u_out = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_post, __Vscopep_gemm8x8x32_bias_relu_top__u_post = nullptr);
    // Tear down sub module instances
}
