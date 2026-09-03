module input_loader #(
  parameter int MAX_M = 64,
  parameter int MAX_N = 64,
  parameter int MAX_K = 64
)(
  input  logic clk,
  input  logic rst_n,
  input  logic st_load_a,
  input  logic st_load_b,
  input  logic st_load_bias,
  input  logic bias_enable,
  input  logic [15:0] cfg_m,
  input  logic [15:0] cfg_n,
  input  logic [15:0] cfg_k,
  input  logic a_valid,
  output logic a_ready,
  input  logic signed [7:0] a_data,
  input  logic b_valid,
  output logic b_ready,
  input  logic signed [7:0] b_data,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic signed [31:0] bias_data,
  output logic a_wr_en,
  output logic [$clog2(MAX_M*MAX_K)-1:0] a_wr_addr,
  output logic signed [7:0] a_wr_data,
  output logic b_wr_en,
  output logic [$clog2(MAX_K*MAX_N)-1:0] b_wr_addr,
  output logic signed [7:0] b_wr_data,
  output logic bias_wr_en,
  output logic [$clog2(MAX_N)-1:0] bias_wr_addr,
  output logic signed [31:0] bias_wr_data,
  output logic load_a_done,
  output logic load_b_done,
  output logic load_bias_done
);
  logic [31:0] cnt_a, cnt_b, cnt_bias;
  always_comb begin
    a_ready = st_load_a;
    b_ready = st_load_b;
    bias_ready = st_load_bias && bias_enable;
    a_wr_en = st_load_a && a_valid && a_ready;
    b_wr_en = st_load_b && b_valid && b_ready;
    bias_wr_en = st_load_bias && bias_enable && bias_valid && bias_ready;
    a_wr_addr = cnt_a[$clog2(MAX_M*MAX_K)-1:0];
    b_wr_addr = cnt_b[$clog2(MAX_K*MAX_N)-1:0];
    bias_wr_addr = cnt_bias[$clog2(MAX_N)-1:0];
    a_wr_data = a_data;
    b_wr_data = b_data;
    bias_wr_data = bias_data;
    load_a_done = (cnt_a == (cfg_m*cfg_k));
    load_b_done = (cnt_b == (cfg_k*cfg_n));
    load_bias_done = (!bias_enable) || (cnt_bias == cfg_n);
  end
  always_ff @(posedge clk) begin
    if (!rst_n) begin cnt_a<=0; cnt_b<=0; cnt_bias<=0; end
    else begin
      if (!st_load_a) cnt_a<=0; else if (a_wr_en) cnt_a<=cnt_a+1;
      if (!st_load_b) cnt_b<=0; else if (b_wr_en) cnt_b<=cnt_b+1;
      if (!st_load_bias) cnt_bias<=0; else if (bias_wr_en) cnt_bias<=cnt_bias+1;
    end
  end
endmodule
