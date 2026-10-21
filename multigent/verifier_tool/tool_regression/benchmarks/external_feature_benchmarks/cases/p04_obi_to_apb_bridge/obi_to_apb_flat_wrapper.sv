// Transparent benchmark wrapper for the pinned PULP obi_to_apb module.
// It fixes only the upstream default type/configuration parameters and exposes
// packed struct fields as ordinary ports for simulator-independent cocotb use.
`include "obi/typedef.svh"

module obi_to_apb_flat_wrapper (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        obi_req,
  input  logic [31:0] obi_addr,
  input  logic        obi_we,
  input  logic [3:0]  obi_be,
  input  logic [31:0] obi_wdata,
  input  logic        obi_aid,
  output logic        obi_gnt,
  output logic        obi_rvalid,
  output logic [31:0] obi_rdata,
  output logic        obi_rid,
  output logic        obi_err,
  output logic [31:0] apb_paddr,
  output logic        apb_pwrite,
  output logic [3:0]  apb_pstrb,
  output logic [31:0] apb_pwdata,
  output logic [2:0]  apb_pprot,
  output logic        apb_psel,
  output logic        apb_penable,
  input  logic        apb_pready,
  input  logic [31:0] apb_prdata,
  input  logic        apb_pslverr
);
  localparam obi_pkg::obi_cfg_t ObiCfg = obi_pkg::ObiDefaultConfig;

  `OBI_TYPEDEF_DEFAULT_ALL(flat_obi, ObiCfg)

  typedef struct packed {
    logic [31:0] paddr;
    logic        pwrite;
    logic [3:0]  pstrb;
    logic [2:0]  pprot;
    logic [31:0] pwdata;
    logic        psel;
    logic        penable;
  } flat_apb_req_t;

  typedef struct packed {
    logic [31:0] prdata;
    logic        pready;
    logic        pslverr;
  } flat_apb_rsp_t;

  flat_obi_req_t obi_req_s;
  flat_obi_rsp_t obi_rsp_s;
  flat_apb_req_t apb_req_s;
  flat_apb_rsp_t apb_rsp_s;

  always_comb begin
    obi_req_s = '0;
    obi_req_s.req = obi_req;
    obi_req_s.a.addr = obi_addr;
    obi_req_s.a.we = obi_we;
    obi_req_s.a.be = obi_be;
    obi_req_s.a.wdata = obi_wdata;
    obi_req_s.a.aid = obi_aid;

    apb_rsp_s = '0;
    apb_rsp_s.pready = apb_pready;
    apb_rsp_s.prdata = apb_prdata;
    apb_rsp_s.pslverr = apb_pslverr;
  end

  assign obi_gnt = obi_rsp_s.gnt;
  assign obi_rvalid = obi_rsp_s.rvalid;
  assign obi_rdata = obi_rsp_s.r.rdata;
  assign obi_rid = obi_rsp_s.r.rid;
  assign obi_err = obi_rsp_s.r.err;
  assign apb_paddr = apb_req_s.paddr;
  assign apb_pwrite = apb_req_s.pwrite;
  assign apb_pstrb = apb_req_s.pstrb;
  assign apb_pwdata = apb_req_s.pwdata;
  assign apb_pprot = apb_req_s.pprot;
  assign apb_psel = apb_req_s.psel;
  assign apb_penable = apb_req_s.penable;

  obi_to_apb #(
    .ObiCfg(ObiCfg),
    .obi_req_t(flat_obi_req_t),
    .obi_rsp_t(flat_obi_rsp_t),
    .apb_req_t(flat_apb_req_t),
    .apb_rsp_t(flat_apb_rsp_t),
    .EnableSameCycleRsp(1'b0)
  ) i_dut (
    .clk_i,
    .rst_ni,
    .obi_req_i(obi_req_s),
    .obi_rsp_o(obi_rsp_s),
    .apb_req_o(apb_req_s),
    .apb_rsp_i(apb_rsp_s)
  );
endmodule
