module fc_accelerator #(
  parameter integer ARRAY_ROWS = 8,
  parameter integer ARRAY_COLS = 8,
  parameter integer MAX_M = 64,
  parameter integer MAX_N = 64,
  parameter integer MAX_K = 64
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic [(((MAX_M <= 1) ? 1 : $clog2(MAX_M+1)) +
                ((MAX_N <= 1) ? 1 : $clog2(MAX_N+1)) +
                ((MAX_K <= 1) ? 1 : $clog2(MAX_K+1)))-1:0] cmd_data,
  input  logic a_valid,
  output logic a_ready,
  input  logic [63:0] a_data,
  input  logic w_valid,
  output logic w_ready,
  input  logic [63:0] w_data,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic [63:0] bias_data,
  output logic out_valid,
  input  logic out_ready,
  output logic [63:0] out_data,
  output logic status_valid,
  input  logic status_ready,
  output logic [1:0] status_code
);

  fc_controller #(
    .ARRAY_ROWS(ARRAY_ROWS), .ARRAY_COLS(ARRAY_COLS),
    .MAX_M(MAX_M), .MAX_N(MAX_N), .MAX_K(MAX_K)
  ) u_controller (
    .clk(clk), .rst_n(rst_n),
    .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_data(cmd_data),
    .a_valid(a_valid), .a_ready(a_ready), .a_data(a_data),
    .w_valid(w_valid), .w_ready(w_ready), .w_data(w_data),
    .bias_valid(bias_valid), .bias_ready(bias_ready), .bias_data(bias_data),
    .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data),
    .status_valid(status_valid), .status_ready(status_ready),
    .status_code(status_code)
  );
endmodule
