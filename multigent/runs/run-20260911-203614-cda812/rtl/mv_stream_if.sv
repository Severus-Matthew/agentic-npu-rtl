module mv_stream_if #(
  parameter int LANES = 16,
  parameter int MAT_DATA_W = 128
) (
  input  logic [MAT_DATA_W-1:0]      mat_data_in,
  output logic signed [LANES*8-1:0]  mat_lanes_out
);
  genvar i;
  generate
    for (i = 0; i < LANES; i++) begin : g_unpack
      assign mat_lanes_out[i*8 +: 8] = mat_data_in[i*8 +: 8];
    end
  endgenerate
endmodule
