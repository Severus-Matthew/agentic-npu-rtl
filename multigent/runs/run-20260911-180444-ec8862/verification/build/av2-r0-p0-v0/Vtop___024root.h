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
        VL_IN8(w_valid,0,0);
        VL_OUT8(w_ready,0,0);
        VL_IN8(bias_valid,0,0);
        VL_OUT8(bias_ready,0,0);
        VL_OUT8(out_valid,0,0);
        VL_IN8(out_ready,0,0);
        VL_OUT8(status_valid,0,0);
        VL_IN8(status_ready,0,0);
        VL_OUT8(status_code,1,0);
        CData/*0:0*/ fc_accelerator__DOT__clk;
        CData/*0:0*/ fc_accelerator__DOT__rst_n;
        CData/*0:0*/ fc_accelerator__DOT__cmd_valid;
        CData/*0:0*/ fc_accelerator__DOT__cmd_ready;
        CData/*0:0*/ fc_accelerator__DOT__a_valid;
        CData/*0:0*/ fc_accelerator__DOT__a_ready;
        CData/*0:0*/ fc_accelerator__DOT__w_valid;
        CData/*0:0*/ fc_accelerator__DOT__w_ready;
        CData/*0:0*/ fc_accelerator__DOT__bias_valid;
        CData/*0:0*/ fc_accelerator__DOT__bias_ready;
        CData/*0:0*/ fc_accelerator__DOT__out_valid;
        CData/*0:0*/ fc_accelerator__DOT__out_ready;
        CData/*0:0*/ fc_accelerator__DOT__status_valid;
        CData/*0:0*/ fc_accelerator__DOT__status_ready;
        CData/*1:0*/ fc_accelerator__DOT__status_code;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__clk;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__rst_n;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_ready;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__a_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__a_ready;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__w_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__w_ready;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__bias_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__bias_ready;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__out_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__out_ready;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__status_valid;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__status_ready;
        CData/*1:0*/ fc_accelerator__DOT__u_controller__DOT__status_code;
        CData/*3:0*/ fc_accelerator__DOT__u_controller__DOT__state;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cfg_m;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cfg_n;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cfg_k;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__tile_m_base;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__tile_n_base;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__compute_k;
        CData/*4:0*/ fc_accelerator__DOT__u_controller__DOT__finalize_pair;
        CData/*1:0*/ fc_accelerator__DOT__u_controller__DOT__status_code_reg;
        CData/*7:0*/ fc_accelerator__DOT__u_controller__DOT__a_we;
        CData/*7:0*/ fc_accelerator__DOT__u_controller__DOT__w_we;
        CData/*1:0*/ fc_accelerator__DOT__u_controller__DOT__bias_we;
        CData/*5:0*/ fc_accelerator__DOT__u_controller__DOT__bias_wbase;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__tile_init;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__compute_step;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__finalize_we;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_m;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_n;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_k;
    };
    struct {
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__rst_n;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_m;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_n;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__cfg_k;
        CData/*7:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_we;
        CData/*7:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_we;
        CData/*1:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_we;
        CData/*5:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wbase;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_m_base;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_n_base;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__tile_init;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_step;
        CData/*6:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__compute_k;
        CData/*0:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_we;
        CData/*4:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__finalize_pair;
        CData/*1:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_valid;
        CData/*0:0*/ __VstlFirstIteration;
        CData/*0:0*/ __VstlPhaseResult;
        CData/*0:0*/ __VicoFirstIteration;
        CData/*0:0*/ __VicoPhaseResult;
        CData/*0:0*/ __Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__clk__0;
        CData/*0:0*/ __Vtrigprevexpr___TOP__fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__clk__0;
        CData/*0:0*/ __VactPhaseResult;
        CData/*0:0*/ __VnbaPhaseResult;
        SData/*10:0*/ fc_accelerator__DOT__u_controller__DOT__result_rpair;
        SData/*11:0*/ fc_accelerator__DOT__u_controller__DOT__a_wbase;
        SData/*11:0*/ fc_accelerator__DOT__u_controller__DOT__w_wbase;
        SData/*11:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wbase;
        SData/*11:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wbase;
        SData/*10:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rpair;
        VL_IN(cmd_data,20,0);
        IData/*20:0*/ fc_accelerator__DOT__cmd_data;
        IData/*20:0*/ fc_accelerator__DOT__u_controller__DOT__cmd_data;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__activation_beat;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__weight_beat;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__bias_beat;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__output_beat;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__a_total;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__w_total;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__b_total;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__out_total;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__lane;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__r;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__c;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__l;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ai;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__wi;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_index;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_row;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__local_col;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_row;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_col;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__global_index;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__read_index;
        IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_total;
        IData/*31:0*/ __VactIterCount;
        VL_IN64(a_data,63,0);
        VL_IN64(w_data,63,0);
        VL_IN64(bias_data,63,0);
        VL_OUT64(out_data,63,0);
        QData/*63:0*/ fc_accelerator__DOT__a_data;
        QData/*63:0*/ fc_accelerator__DOT__w_data;
        QData/*63:0*/ fc_accelerator__DOT__bias_data;
    };
    struct {
        QData/*63:0*/ fc_accelerator__DOT__out_data;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__a_data;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__w_data;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__bias_data;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__out_data;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__result_rdata;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__a_wdata;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__w_wdata;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_wdata;
        QData/*63:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_rdata;
        VlUnpacked<CData/*7:0*/, 4096> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem;
        VlUnpacked<CData/*7:0*/, 4096> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem;
        VlUnpacked<IData/*31:0*/, 64> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__bias_mem;
        VlUnpacked<VlUnpacked<IData/*31:0*/, 8>, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator;
        VlUnpacked<IData/*31:0*/, 4096> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__result_mem;
        VlUnpacked<CData/*7:0*/, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_a;
        VlUnpacked<CData/*7:0*/, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__active_w;
        VlUnpacked<VlUnpacked<SData/*15:0*/, 8>, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product;
        VlUnpacked<VlUnpacked<IData/*31:0*/, 8>, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__product_ext;
        VlUnpacked<CData/*0:0*/, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__row_active;
        VlUnpacked<CData/*0:0*/, 8> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__col_active;
        VlUnpacked<SData/*11:0*/, 2> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_addr;
        VlUnpacked<IData/*31:0*/, 2> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_sum;
        VlUnpacked<IData/*31:0*/, 2> fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__fin_data;
        VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VicoTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
        VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    };
    VlNBACommitQueue<VlUnpacked<CData/*7:0*/, 4096>, false, CData/*7:0*/, 1> __VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__activation_mem;
    VlNBACommitQueue<VlUnpacked<CData/*7:0*/, 4096>, false, CData/*7:0*/, 1> __VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__weight_mem;
    VlNBACommitQueue<VlUnpacked<VlUnpacked<IData/*31:0*/, 8>, 8>, false, IData/*31:0*/, 2> __VdlyCommitQueuefc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__accumulator;

    // INTERNAL VARIABLES
    Vtop__Syms* vlSymsp;
    const char* vlNamep;

    // PARAMETERS
    static constexpr IData/*31:0*/ fc_accelerator__DOT__ARRAY_ROWS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__ARRAY_COLS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__ARRAY_ROWS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__ARRAY_COLS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__M_W = 7U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__N_W = 7U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__K_W = 7U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__A_AW = 0x0000000cU;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__W_AW = 0x0000000cU;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__B_AW = 6U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__TILE_PAIRS = 0x00000020U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__FP_W = 5U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__RESULT_PAIRS = 0x00000800U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__RP_W = 0x0000000bU;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_ROWS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__ARRAY_COLS = 8U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_M = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_N = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__MAX_K = 0x00000040U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RESULT_CAP = 0x00001000U;
    static constexpr IData/*31:0*/ fc_accelerator__DOT__u_controller__DOT__u_datapath__DOT__RES_AW = 0x0000000cU;

    // CONSTRUCTORS
    Vtop___024root(Vtop__Syms* symsp, const char* namep);
    ~Vtop___024root();
    VL_UNCOPYABLE(Vtop___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
