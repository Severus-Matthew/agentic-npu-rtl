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
    Verilated::stackCheck(362);
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
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_gemm", "u_gemm", "gemm_core_seq", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_loader", "u_loader", "input_loader", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_mem", "u_mem", "local_memories", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_out = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_out", "u_out", "output_streamer", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_post = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_post", "u_post", "postproc_relu_bias", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1 = new VerilatedScope{this, "gemm8x8x32_bias_relu_top.u_post.unnamedblk1", "unnamedblk1", "<null>", -12, VerilatedScope::SCOPE_OTHER};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_gemm8x8x32_bias_relu_top);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_gemm);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_loader);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_mem);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_out);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_post);
    __Vhier.add(__Vscopep_gemm8x8x32_bias_relu_top__u_post, __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("busy", &(TOP.busy), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("done", &(TOP.done), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("error", &(TOP.error), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_TOP->varInsert("m_data", &(TOP.m_data), false, VLVT_UINT32, VLVD_OUT|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("m_ready", &(TOP.m_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("m_valid", &(TOP.m_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst", &(TOP.rst), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("s_data", &(TOP.s_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_TOP->varInsert("s_ready", &(TOP.s_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("s_type", &(TOP.s_type), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_TOP->varInsert("s_valid", &(TOP.s_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("A_AW", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__A_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("A_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__A_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("A_ELEM_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__A_ELEM_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("B_AW", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__B_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("B_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__B_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("K_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__K_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("N_AW", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__N_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("O_AW", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__O_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("O_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__O_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("a_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_m", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_n", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("acc_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__acc_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("b_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("bias_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("busy", &(TOP.gemm8x8x32_bias_relu_top__DOT__busy), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("compute_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__compute_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("done", &(TOP.gemm8x8x32_bias_relu_top__DOT__done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("error", &(TOP.gemm8x8x32_bias_relu_top__DOT__error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("load_error", &(TOP.gemm8x8x32_bias_relu_top__DOT__load_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("m_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__m_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("m_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__m_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("m_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__m_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("out_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__out_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("post_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__post_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("s_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__s_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("s_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__s_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("s_type", &(TOP.gemm8x8x32_bias_relu_top__DOT__s_type), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("s_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__s_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("start_compute", &(TOP.gemm8x8x32_bias_relu_top__DOT__start_compute), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("start_load", &(TOP.gemm8x8x32_bias_relu_top__DOT__start_load), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("start_out", &(TOP.gemm8x8x32_bias_relu_top__DOT__start_out), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("start_post", &(TOP.gemm8x8x32_bias_relu_top__DOT__start_post), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("state", &(TOP.gemm8x8x32_bias_relu_top__DOT__state), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top->varInsert("sticky_error", &(TOP.gemm8x8x32_bias_relu_top__DOT__sticky_error), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("A_ELEM_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__A_ELEM_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("K_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__K_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("a_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("a_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__a_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("acc", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("acc_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("acc_m", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("acc_n", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("acc_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__acc_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("b_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("b_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__b_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("compute_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__compute_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("k", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__k), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("m", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__m), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("n", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__n), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("prod16", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__prod16), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,15,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("run", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__run), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_gemm->varInsert("start_compute", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_gemm__DOT__start_compute), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("A_CNT_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_CNT_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("A_ELEM_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__A_ELEM_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("B_CNT_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__B_CNT_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("C_CNT_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__C_CNT_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("K_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__K_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("a_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("b_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("bias_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("ca", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__ca), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("cb", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cb), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("cc", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__cc), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("error_flag", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__error_flag), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("load_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__load_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("s_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("s_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("s_type", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_type), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("s_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__s_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("st", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__st), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_loader->varInsert("start_load", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_loader__DOT__start_load), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("A_ELEM_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__A_ELEM_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("K_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__K_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("a_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("a_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("a_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("a_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("a_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__a_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("b_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("b_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_rd_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("b_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("b_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_data), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("b_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__b_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("bias_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("bias_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("bias_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("bias_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("bias_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__bias_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("memA", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memA), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,255 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("memB", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memB), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,255 ,7,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("memBias", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memBias), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("memOut", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__memOut), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,63 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("out_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("out_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("out_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("out_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_mem->varInsert("out_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_mem__DOT__out_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("O_DEPTH", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__O_DEPTH))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("active", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("idx", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__idx), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("m_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("m_ready", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("m_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__m_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("out_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("out_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("out_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__out_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_out->varInsert("start_out", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_out__DOT__start_out), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("ACC_W", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__ACC_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("M_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__M_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("N_MAX", const_cast<void*>(static_cast<const void*>(&(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__N_MAX))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_DPI_CLAY|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("acc_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("acc_m", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("acc_n", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("acc_valid", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__acc_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("bias_rd_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("bias_rd_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__bias_rd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("clk", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("out_wr_addr", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_addr), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("out_wr_data", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("out_wr_en", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__out_wr_en), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("pdata", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pdata), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("pending", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pending), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("pm", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pm), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("pn", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__pn), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,2,0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("post_done", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__post_done), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("rst", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__rst), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post->varInsert("start_post", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__start_post), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1->varInsert("sum", &(TOP.gemm8x8x32_bias_relu_top__DOT__u_post__DOT__unnamedblk1__DOT__sum), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_gemm8x8x32_bias_relu_top);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_gemm);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_loader);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_mem);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_out);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top__u_post);
    __Vhier.remove(__Vscopep_gemm8x8x32_bias_relu_top__u_post, __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top, __Vscopep_gemm8x8x32_bias_relu_top = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_gemm, __Vscopep_gemm8x8x32_bias_relu_top__u_gemm = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_loader, __Vscopep_gemm8x8x32_bias_relu_top__u_loader = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_mem, __Vscopep_gemm8x8x32_bias_relu_top__u_mem = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_out, __Vscopep_gemm8x8x32_bias_relu_top__u_out = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_post, __Vscopep_gemm8x8x32_bias_relu_top__u_post = nullptr);
    VL_DO_CLEAR(delete __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1, __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1 = nullptr);
    // Tear down sub module instances
}
