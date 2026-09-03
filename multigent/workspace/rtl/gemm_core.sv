module gemm_core #(
  parameter int TILE_N = 8,
  parameter int MAX_K = 64,
  parameter int MAX_N = 64
)(
  input  logic clk,
  input  logic rst_n,
  input  logic do_start,
  input  logic do_step,
  input  logic [15:0] cfg_k,
  input  logic [TILE_N-1:0] lane_active,
  input  logic signed [7:0] a_elem,
  input  logic signed [7:0] b_vec [0:TILE_N-1],
  output logic tile_done,
  output logic signed [31:0] lane_acc [0:TILE_N-1]
);
  logic [15:0] k_count;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      k_count <= 0;
      for (int i=0;i<TILE_N;i++) lane_acc[i] <= '0;
    end else begin
      if (do_start) begin
        k_count <= 0;
        for (int i=0;i<TILE_N;i++) lane_acc[i] <= '0;
      end else if (do_step) begin
        k_count <= k_count + 1;
        for (int i=0;i<TILE_N;i++) begin
          logic signed [15:0] p16;
          logic signed [31:0] p32;
          p16 = a_elem * b_vec[i];
          p32 = {{16{p16[15]}}, p16};
          if (lane_active[i]) lane_acc[i] <= lane_acc[i] + p32;
        end
      end
    end
  end
  always_comb tile_done = (do_step && (k_count + 1 >= cfg_k));
endmodule
