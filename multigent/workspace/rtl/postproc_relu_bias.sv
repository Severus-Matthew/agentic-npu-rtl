module postproc_relu_bias #(
  parameter int TILE_N = 8
)(
  input  logic bias_enable,
  input  logic [TILE_N-1:0] lane_active,
  input  logic [15:0] idx_n_base,
  input  logic [15:0] cfg_n,
  input  logic signed [31:0] lane_acc [0:TILE_N-1],
  input  logic signed [31:0] bias_mem [0:cfg_n-1],
  output logic signed [31:0] lane_out [0:TILE_N-1]
);
  always_comb begin
    for (int i=0;i<TILE_N;i++) begin
      logic signed [31:0] t;
      if (lane_active[i]) begin
        t = lane_acc[i] + (bias_enable ? bias_mem[idx_n_base+i] : 32'sd0);
        lane_out[i] = (t < 0) ? 32'sd0 : t;
      end else lane_out[i] = 32'sd0;
    end
  end
endmodule
