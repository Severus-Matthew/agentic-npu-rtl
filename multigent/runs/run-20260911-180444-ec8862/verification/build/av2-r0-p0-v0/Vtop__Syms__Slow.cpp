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
    Verilated::stackCheck(338);
    // Setup sub module instances
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscopep_TOP = new VerilatedScope{this, "TOP", "TOP", "<null>", 0, VerilatedScope::SCOPE_OTHER};
    __Vscopep_fc_accelerator = new VerilatedScope{this, "fc_accelerator", "fc_accelerator", "fc_accelerator", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_fc_accelerator__u_controller = new VerilatedScope{this, "fc_accelerator.u_controller", "u_controller", "fc_controller", -12, VerilatedScope::SCOPE_MODULE};
    __Vscopep_fc_accelerator__u_controller__u_datapath = new VerilatedScope{this, "fc_accelerator.u_controller.u_datapath", "u_datapath", "fc_datapath", -12, VerilatedScope::SCOPE_MODULE};
    // Set up scope hierarchy
    __Vhier.add(0, __Vscopep_fc_accelerator);
    __Vhier.add(__Vscopep_fc_accelerator, __Vscopep_fc_accelerator__u_controller);
    __Vhier.add(__Vscopep_fc_accelerator__u_controller, __Vscopep_fc_accelerator__u_controller__u_datapath);
    // Setup export functions - final: 0
    // Setup export functions - final: 1
    // Setup public variables
    __Vscopep_TOP->varInsert("a_data", &(TOP.a_data), false, VLVT_UINT64, VLVD_IN|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("a_ready", &(TOP.a_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("a_valid", &(TOP.a_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("bias_data", &(TOP.bias_data), false, VLVT_UINT64, VLVD_IN|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("bias_ready", &(TOP.bias_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("bias_valid", &(TOP.bias_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("clk", &(TOP.clk), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_data", &(TOP.cmd_data), false, VLVT_UINT32, VLVD_IN|VLVF_PUB_RW, 0, 1 ,20,0);
    __Vscopep_TOP->varInsert("cmd_ready", &(TOP.cmd_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("cmd_valid", &(TOP.cmd_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_data", &(TOP.out_data), false, VLVT_UINT64, VLVD_OUT|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("out_ready", &(TOP.out_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("out_valid", &(TOP.out_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("rst_n", &(TOP.rst_n), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_code", &(TOP.status_code), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_TOP->varInsert("status_ready", &(TOP.status_ready), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("status_valid", &(TOP.status_valid), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("w_data", &(TOP.w_data), false, VLVT_UINT64, VLVD_IN|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_TOP->varInsert("w_ready", &(TOP.w_ready), false, VLVT_UINT8, VLVD_OUT|VLVF_PUB_RW, 0, 0);
    __Vscopep_TOP->varInsert("w_valid", &(TOP.w_valid), false, VLVT_UINT8, VLVD_IN|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("ARRAY_COLS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__ARRAY_COLS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator->varInsert("ARRAY_ROWS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__ARRAY_ROWS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator->varInsert("a_data", &(TOP.fc_accelerator__DOT__a_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator->varInsert("a_ready", &(TOP.fc_accelerator__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("a_valid", &(TOP.fc_accelerator__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("bias_data", &(TOP.fc_accelerator__DOT__bias_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator->varInsert("bias_ready", &(TOP.fc_accelerator__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("bias_valid", &(TOP.fc_accelerator__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("clk", &(TOP.fc_accelerator__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("cmd_data", &(TOP.fc_accelerator__DOT__cmd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,20,0);
    __Vscopep_fc_accelerator->varInsert("cmd_ready", &(TOP.fc_accelerator__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("cmd_valid", &(TOP.fc_accelerator__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("out_data", &(TOP.fc_accelerator__DOT__out_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator->varInsert("out_ready", &(TOP.fc_accelerator__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("out_valid", &(TOP.fc_accelerator__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("rst_n", &(TOP.fc_accelerator__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("status_code", &(TOP.fc_accelerator__DOT__status_code), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator->varInsert("status_ready", &(TOP.fc_accelerator__DOT__status_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("status_valid", &(TOP.fc_accelerator__DOT__status_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("w_data", &(TOP.fc_accelerator__DOT__w_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator->varInsert("w_ready", &(TOP.fc_accelerator__DOT__w_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator->varInsert("w_valid", &(TOP.fc_accelerator__DOT__w_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("ARRAY_COLS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__ARRAY_COLS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("ARRAY_ROWS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__ARRAY_ROWS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("A_AW", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__A_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("B_AW", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__B_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("FP_W", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__FP_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("K_W", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__K_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("M_W", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__M_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("N_W", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__N_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("RESULT_PAIRS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__RESULT_PAIRS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("RP_W", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__RP_W))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("TILE_PAIRS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__TILE_PAIRS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("W_AW", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__W_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_total", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_total), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_wbase), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("a_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__a_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("activation_beat", &(TOP.fc_accelerator__DOT__u_controller__DOT__activation_beat), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("b_total", &(TOP.fc_accelerator__DOT__u_controller__DOT__b_total), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_beat", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_beat), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_wbase), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("bias_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__bias_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cfg_k", &(TOP.fc_accelerator__DOT__u_controller__DOT__cfg_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cfg_m", &(TOP.fc_accelerator__DOT__u_controller__DOT__cfg_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cfg_n", &(TOP.fc_accelerator__DOT__u_controller__DOT__cfg_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("clk", &(TOP.fc_accelerator__DOT__u_controller__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,20,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_k", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_NET, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_m", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_NET, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_n", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_CONTINUOUSLY|VLVF_NET, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("cmd_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__cmd_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("compute_k", &(TOP.fc_accelerator__DOT__u_controller__DOT__compute_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("compute_step", &(TOP.fc_accelerator__DOT__u_controller__DOT__compute_step), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("finalize_pair", &(TOP.fc_accelerator__DOT__u_controller__DOT__finalize_pair), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,4,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("finalize_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__finalize_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("lane", &(TOP.fc_accelerator__DOT__u_controller__DOT__lane), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("out_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__out_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("out_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__out_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("out_total", &(TOP.fc_accelerator__DOT__u_controller__DOT__out_total), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("out_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__out_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("output_beat", &(TOP.fc_accelerator__DOT__u_controller__DOT__output_beat), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("result_rdata", &(TOP.fc_accelerator__DOT__u_controller__DOT__result_rdata), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("result_rpair", &(TOP.fc_accelerator__DOT__u_controller__DOT__result_rpair), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,10,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("rst_n", &(TOP.fc_accelerator__DOT__u_controller__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("state", &(TOP.fc_accelerator__DOT__u_controller__DOT__state), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,3,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("status_code", &(TOP.fc_accelerator__DOT__u_controller__DOT__status_code), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("status_code_reg", &(TOP.fc_accelerator__DOT__u_controller__DOT__status_code_reg), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("status_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__status_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("status_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__status_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("tile_init", &(TOP.fc_accelerator__DOT__u_controller__DOT__tile_init), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("tile_m_base", &(TOP.fc_accelerator__DOT__u_controller__DOT__tile_m_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("tile_n_base", &(TOP.fc_accelerator__DOT__u_controller__DOT__tile_n_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_data), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_ready", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_ready), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_total", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_total), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_wbase), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("w_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__w_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_fc_accelerator__u_controller->varInsert("weight_beat", &(TOP.fc_accelerator__DOT__u_controller__DOT__weight_beat), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("ARRAY_COLS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_COLS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("ARRAY_ROWS", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_ROWS))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("MAX_K", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_K))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("MAX_M", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_M))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("MAX_N", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_N))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("RESULT_CAP", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RESULT_CAP))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("RES_AW", const_cast<void*>(static_cast<const void*>(&(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RES_AW))), true, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("a_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("a_wdata", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wdata), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("a_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("accumulator", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 2, 1 ,0,7 ,0,7 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("activation_mem", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,4095 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("active_a", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("active_w", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,7 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("ai", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("bias_mem", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,63 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("bias_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,5,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("bias_wdata", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("bias_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("c", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("cfg_k", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("cfg_m", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("cfg_n", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("clk", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("col_active", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 1, 0 ,0,7);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("compute_k", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("compute_step", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("fin_addr", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 1, 1 ,0,1 ,11,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("fin_data", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("fin_sum", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("fin_valid", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,1,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("finalize_pair", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,4,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("finalize_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("global_col", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("global_index", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("global_row", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("l", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("local_col", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("local_index", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("local_row", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("product", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 2, 1 ,0,7 ,0,7 ,15,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("product_ext", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 2, 1 ,0,7 ,0,7 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("r", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("read_index", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("result_mem", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,4095 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("result_rdata", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("result_rpair", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,10,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("result_total", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("row_active", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 1, 0 ,0,7);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("rst_n", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("tile_init", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("tile_m_base", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("tile_n_base", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,6,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("w_wbase", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase), false, VLVT_UINT16, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,11,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("w_wdata", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wdata), false, VLVT_UINT64, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,63,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("w_we", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW, 0, 1 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("weight_mem", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem), false, VLVT_UINT8, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 1, 1 ,0,4095 ,7,0);
    __Vscopep_fc_accelerator__u_controller__u_datapath->varInsert("wi", &(TOP.fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi), false, VLVT_UINT32, VLVD_NODIR|VLVF_PUB_RW|VLVF_SIGNED, 0, 1 ,31,0);
}

Vtop__Syms::~Vtop__Syms() {
    // Tear down scope hierarchy
    __Vhier.remove(0, __Vscopep_fc_accelerator);
    __Vhier.remove(__Vscopep_fc_accelerator, __Vscopep_fc_accelerator__u_controller);
    __Vhier.remove(__Vscopep_fc_accelerator__u_controller, __Vscopep_fc_accelerator__u_controller__u_datapath);
    // Clear keys from hierarchy map after values have been removed
    __Vhier.clear();
    // Tear down scopes
    VL_DO_CLEAR(delete __Vscopep_TOP, __Vscopep_TOP = nullptr);
    VL_DO_CLEAR(delete __Vscopep_fc_accelerator, __Vscopep_fc_accelerator = nullptr);
    VL_DO_CLEAR(delete __Vscopep_fc_accelerator__u_controller, __Vscopep_fc_accelerator__u_controller = nullptr);
    VL_DO_CLEAR(delete __Vscopep_fc_accelerator__u_controller__u_datapath, __Vscopep_fc_accelerator__u_controller__u_datapath = nullptr);
    // Tear down sub module instances
}
