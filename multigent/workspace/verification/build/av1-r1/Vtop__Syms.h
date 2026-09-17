// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VTOP__SYMS_H_
#define VERILATED_VTOP__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "Vtop.h"

// INCLUDE MODULE CLASSES
#include "Vtop___024root.h"

// DPI TYPES for DPI Export callbacks (Internal use)

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES) Vtop__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    Vtop* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    Vtop___024root                 TOP;

    // SCOPE NAMES
    VerilatedScope* __Vscopep_TOP;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_core;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk1;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk2;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_core__unnamedblk3__unnamedblk4;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_ctrl;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_ctrl__unnamedblk1;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_loader;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_out;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_post;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__u_post__unnamedblk1__unnamedblk2;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__unnamedblk1;
    VerilatedScope* __Vscopep_gemm_bias_relu_npu_top__unnamedblk1__unnamedblk2;

    // SCOPE HIERARCHY
    VerilatedHierarchy __Vhier;

    // CONSTRUCTORS
    Vtop__Syms(VerilatedContext* contextp, const char* namep, Vtop* modelp);
    ~Vtop__Syms();

    // METHODS
    const char* name() const { return TOP.vlNamep; }
};

#endif  // guard
