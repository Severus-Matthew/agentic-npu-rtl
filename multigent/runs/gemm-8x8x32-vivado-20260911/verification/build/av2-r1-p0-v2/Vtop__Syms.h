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
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_gemm;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_loader;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_mem;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_out;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_post;
    VerilatedScope* __Vscopep_gemm8x8x32_bias_relu_top__u_post__unnamedblk1;

    // SCOPE HIERARCHY
    VerilatedHierarchy __Vhier;

    // CONSTRUCTORS
    Vtop__Syms(VerilatedContext* contextp, const char* namep, Vtop* modelp);
    ~Vtop__Syms();

    // METHODS
    const char* name() const { return TOP.vlNamep; }
};

#endif  // guard
