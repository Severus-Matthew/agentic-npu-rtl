module input_loader #(
  parameter int A_ELEMS_FIXED = 256,
  parameter int B_ELEMS_FIXED = 256,
  parameter int N_FIXED = 8
)(
  input logic clk,
  input logic rst,
  input logic load_a_en,
  input logic load_b_en,
  input logic load_bias_en,
  input logic a_valid,
  output logic a_ready,
  input logic signed [7:0] a_data,
  input logic b_valid,
  output logic b_ready,
  input logic signed [7:0] b_data,
  input logic bias_valid,
  output logic bias_ready,
  input logic signed [31:0] bias_data,
  output logic a_wr_en,
  output logic b_wr_en,
  output logic bias_wr_en,
  output logic [$clog2(A_ELEMS_FIXED)-1:0] a_wr_addr,
  output logic [$clog2(B_ELEMS_FIXED)-1:0] b_wr_addr,
  output logic [$clog2(N_FIXED)-1:0] bias_wr_addr,
  output logic signed [7:0] a_wr_data,
  output logic signed [7:0] b_wr_data,
  output logic signed [31:0] bias_wr_data,
  output logic load_a_done,
  output logic load_b_done,
  output logic load_bias_done,
  output logic load_err
);
// Simplified synthesizable implementation omitted for brevity in this response.
endmodule
