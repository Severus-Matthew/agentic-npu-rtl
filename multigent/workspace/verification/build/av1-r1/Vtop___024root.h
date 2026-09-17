// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtop.h for the primary calling header

#ifndef VERILATED_VTOP___024ROOT_H_
#define VERILATED_VTOP___024ROOT_H_  // guard

#include "verilated.h"


class Vtop__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtop___024root final {
  public:

    // DESIGN SPECIFIC STATE
    // Anonymous structures to workaround compiler member-count bugs
    struct {
        VL_IN8(clk,0,0);
        VL_IN8(rst_n,0,0);
        VL_IN8(cmd_valid,0,0);
        VL_OUT8(cmd_ready,0,0);
        VL_IN8(a_valid,0,0);
        VL_OUT8(a_ready,0,0);
        VL_IN8(a_data,7,0);
        VL_IN8(b_valid,0,0);
        VL_OUT8(b_ready,0,0);
        VL_IN8(b_data,7,0);
        VL_IN8(bias_valid,0,0);
        VL_OUT8(bias_ready,0,0);
        VL_OUT8(out_valid,0,0);
        VL_IN8(out_ready,0,0);
        VL_OUT8(status_done,0,0);
        VL_OUT8(status_error,0,0);
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__clk;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__rst_n;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__cmd_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__cmd_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__a_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__a_ready;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__a_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__b_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__b_ready;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__b_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__bias_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__bias_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__out_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__out_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__status_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__status_error;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__cfg_bias_enable;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__st_load_a;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__st_load_b;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__st_load_bias;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__st_compute;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__st_emit;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__do_compute_start;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__do_compute_step;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__do_emit_start;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__do_done_pulse;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__load_a_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__load_b_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__load_bias_done;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__bias_wr_addr;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__a_wr_en;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__b_wr_en;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__bias_wr_en;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__idx_m;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__idx_n_base;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__idx_k;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__lane_active;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__a_elem;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__compute_tile_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__emit_busy;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__emit_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__clk;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__rst_n;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__do_start;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_active;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__out_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__out_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_busy;
    };
    struct {
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__emit_done;
        CData/*2:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_idx;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__started;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_enable;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_active;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__clk;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__rst_n;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__do_start;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__do_step;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_active;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__a_elem;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__tile_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__rst_n;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_a;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_b;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__st_load_bias;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_enable;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_ready;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_ready;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_en;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_en;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_data;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_en;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_addr;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_a_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_b_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__load_bias_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__rst_n;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_valid;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_ready;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_a_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_b_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__load_bias_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__compute_tile_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__emit_done;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_bias_enable;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_a;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_b;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_load_bias;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_compute;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__st_emit;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_start;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_compute_step;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_emit_start;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__do_done_pulse;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_m;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_n_base;
        CData/*5:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__idx_k;
        CData/*7:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__lane_active;
        CData/*0:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__status_error;
        CData/*2:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__state;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
    };
    struct {
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_out__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_core__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_loader__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__cfg_m;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__cfg_n;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__cfg_k;
        SData/*11:0*/ gemm_bias_relu_npu_top__DOT__a_wr_addr;
        SData/*11:0*/ gemm_bias_relu_npu_top__DOT__b_wr_addr;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__idx_n_base;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__cfg_n;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__cfg_k;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__k_count;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p16;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_m;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_n;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cfg_k;
        SData/*11:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__a_wr_addr;
        SData/*11:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__b_wr_addr;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_m;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_n;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cfg_k;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__n_tiles;
        SData/*15:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__t_idx;
        VL_INW(cmd_data,95,0,3);
        VL_IN(bias_data,31,0);
        VL_OUT(out_data,31,0);
        VlWide<3>/*95:0*/ gemm_bias_relu_npu_top__DOT__cmd_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__bias_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__out_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__n_idx;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__unnamedblk1__DOT__unnamedblk2__DOT__i;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__out_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__i;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__unnamedblk1__DOT__unnamedblk2__DOT__t;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk2__DOT__i;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__i;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk3__DOT__unnamedblk4__DOT__p32;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__unnamedblk1__DOT__i;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__bias_wr_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_a;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_b;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__cnt_bias;
        VlWide<3>/*95:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__cmd_data;
        IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__unnamedblk1__DOT__i;
        IData/*31:0*/ __VactIterCount;
        VlUnpacked<CData/*7:0*/, 4096> gemm_bias_relu_npu_top__DOT__buf_A;
        VlUnpacked<CData/*7:0*/, 4096> gemm_bias_relu_npu_top__DOT__buf_B;
        VlUnpacked<IData/*31:0*/, 64> gemm_bias_relu_npu_top__DOT__buf_bias;
        VlUnpacked<CData/*7:0*/, 8> gemm_bias_relu_npu_top__DOT__b_vec;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__lane_acc;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__lane_post;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__u_out__DOT__lane_data;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_acc;
        VlUnpacked<IData/*31:0*/, 64> gemm_bias_relu_npu_top__DOT__u_post__DOT__bias_mem;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__u_post__DOT__lane_out;
        VlUnpacked<CData/*7:0*/, 8> gemm_bias_relu_npu_top__DOT__u_core__DOT__b_vec;
        VlUnpacked<IData/*31:0*/, 8> gemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
    };
    struct {
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };
    VlNBACommitQueue<VlUnpacked<IData/*31:0*/, 8>, false, IData/*31:0*/, 1> __VdlyCommitQueuegemm_bias_relu_npu_top__DOT__u_core__DOT__lane_acc;

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__TILE_N = 8U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__A_DEPTH = 0x00001000U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__B_DEPTH = 0x00001000U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__TILE_N = 8U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_out__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__TILE_N = 8U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_post__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__TILE_N = 8U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_core__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_loader__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ gemm_bias_relu_npu_top__DOT__u_ctrl__DOT__TILE_N = 8U;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
