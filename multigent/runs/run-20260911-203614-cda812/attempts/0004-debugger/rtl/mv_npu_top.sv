module mv_npu_top #(
  parameter int MAX_M = 256,
  parameter int MAX_N = 256,
  parameter int LANES = 16,
  parameter int CMD_W = 64,
  parameter int MAT_DATA_W = 128,
  parameter int VEC_DATA_W = 8,
  parameter int BIAS_DATA_W = 32,
  parameter int OUT_DATA_W = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic [CMD_W-1:0] cmd_data,
  input  logic vec_valid,
  output logic vec_ready,
  input  logic signed [VEC_DATA_W-1:0] vec_data,
  input  logic mat_valid,
  output logic mat_ready,
  input  logic [MAT_DATA_W-1:0] mat_data,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic signed [BIAS_DATA_W-1:0] bias_data,
  output logic out_valid,
  input  logic out_ready,
  output logic signed [OUT_DATA_W-1:0] out_data,
  output logic status_busy,
  output logic status_error
);
  initial begin
    if (LANES != 16) $error("LANES must be 16");
    if (MAT_DATA_W != LANES*8) $error("MAT_DATA_W mismatch");
    if (VEC_DATA_W != 8) $error("VEC_DATA_W must be 8");
    if (BIAS_DATA_W != 32) $error("BIAS_DATA_W must be 32");
    if (OUT_DATA_W != 32) $error("OUT_DATA_W must be 32");
  end
endmodule
