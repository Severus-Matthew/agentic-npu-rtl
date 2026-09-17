module mv_mac16_core #(
  parameter int LANES = 16
) (
  input  logic                         clk,
  input  logic                         rst_n,
  input  logic                         compute_en,
  input  logic                         new_row,
  input  logic [LANES-1:0]             lane_valid_mask,
  input  logic signed [LANES*8-1:0]    mat_lane_data,
  input  logic signed [LANES*8-1:0]    vec_lane_data,
  output logic signed [31:0]           row_accum_out,
  output logic                         row_done_pulse
);
  logic signed [31:0] sum32;
  integer i;
  logic signed [7:0] m_i, v_i;
  logic signed [15:0] p_i;

  always_comb begin
    sum32 = 32'sd0;
    for (i = 0; i < LANES; i++) begin
      if (lane_valid_mask[i]) begin
        m_i = mat_lane_data[i*8 +: 8];
        v_i = vec_lane_data[i*8 +: 8];
        p_i = m_i * v_i;
        sum32 = sum32 + {{16{p_i[15]}}, p_i};
      end
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      row_accum_out  <= 32'sd0;
      row_done_pulse <= 1'b0;
    end else begin
      row_done_pulse <= 1'b0;
      if (new_row) row_accum_out <= 32'sd0;
      if (compute_en) begin
        row_accum_out <= row_accum_out + sum32;
        row_done_pulse <= 1'b1;
      end
    end
  end
endmodule
