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
  localparam int AW = (MAX_N <= 1) ? 1 : $clog2(MAX_N);

  initial begin
    if (LANES != 16) $error("LANES must be 16");
    if (MAT_DATA_W != LANES*8) $error("MAT_DATA_W mismatch");
    if (VEC_DATA_W != 8) $error("VEC_DATA_W must be 8");
    if (BIAS_DATA_W != 32) $error("BIAS_DATA_W must be 32");
    if (OUT_DATA_W != 32) $error("OUT_DATA_W must be 32");
    if (CMD_W < 56) $error("CMD_W must be >=56");
  end

  logic [15:0] cfg_M, cfg_N;
  logic        cfg_bias_en, cfg_relu_en;
  logic        state_compute_en;
  logic [LANES-1:0] lane_valid_mask;

  logic cmd_accept, vec_xfer, mat_xfer, bias_xfer, out_xfer;

  logic [AW-1:0] vec_wr_addr;
  logic [AW-1:0] rd_chunk_base;
  logic [15:0]   row_idx;
  logic [15:0]   k_chunk_idx;
  logic [15:0]   chunks_per_row;

  logic signed [LANES*8-1:0] mat_lanes;
  logic signed [LANES*8-1:0] vec_lanes;

  logic compute_en_core;
  logic new_row_core;
  logic signed [31:0] row_accum_out;
  logic row_done_pulse;

  logic pp_in_valid;
  logic pp_in_ready;
  logic pp_bias_valid;
  logic pp_out_valid;
  logic signed [31:0] pp_out_data;

  logic row_buf_valid;
  logic signed [31:0] row_buf_data;
  logic mat_is_last_chunk;
  logic signed [31:0] chunk_sum32;
  logic signed [31:0] final_row_sum;
  logic row_buf_pop;
  logic row_buf_push;

  integer li;
  logic signed [7:0] m_i, v_i;
  logic signed [15:0] p_i;

  assign cmd_ready  = (!status_busy) && (!status_error);
  assign vec_ready  = status_busy && (!status_error) && (cfg_N != 16'd0) && (vec_wr_addr < cfg_N) && (k_chunk_idx == 16'd0) && (row_idx == 16'd0);
  assign mat_is_last_chunk = (k_chunk_idx + 16'd1 == chunks_per_row);
  assign mat_ready  = status_busy && (!status_error) && (cfg_N != 16'd0) && (vec_wr_addr == cfg_N) && (!row_buf_valid);
  assign bias_ready = status_busy && (!status_error) && cfg_bias_en && pp_in_ready;

  assign cmd_accept = cmd_valid && cmd_ready;
  assign vec_xfer   = vec_valid && vec_ready;
  assign mat_xfer   = mat_valid && mat_ready;
  assign bias_xfer  = bias_valid && bias_ready;
  assign out_xfer   = out_valid && out_ready;

  always_comb begin
    chunks_per_row = (cfg_N + LANES - 1) / LANES;
    rd_chunk_base  = k_chunk_idx * LANES;
    new_row_core   = mat_xfer && (k_chunk_idx == 16'd0);
    compute_en_core = mat_xfer;

    chunk_sum32 = 32'sd0;
    m_i = 8'sd0;
    v_i = 8'sd0;
    p_i = 16'sd0;
    for (li = 0; li < LANES; li++) begin
      if (lane_valid_mask[li]) begin
        m_i = mat_lanes[li*8 +: 8];
        v_i = vec_lanes[li*8 +: 8];
        p_i = m_i * v_i;
        chunk_sum32 = chunk_sum32 + {{16{p_i[15]}}, p_i};
      end
    end
    final_row_sum = row_accum_out + chunk_sum32;

    pp_in_valid = row_buf_valid;
    pp_bias_valid = bias_xfer;

    row_buf_pop  = row_buf_valid && pp_in_ready;
    row_buf_push = mat_xfer && mat_is_last_chunk;
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      vec_wr_addr   <= '0;
      row_idx       <= 16'd0;
      k_chunk_idx   <= 16'd0;
      row_buf_valid <= 1'b0;
      row_buf_data  <= 32'sd0;
    end else begin
      if (!status_busy) begin
        vec_wr_addr   <= '0;
        row_idx       <= 16'd0;
        k_chunk_idx   <= 16'd0;
        row_buf_valid <= 1'b0;
      end else begin
        if (vec_xfer) begin
          vec_wr_addr <= vec_wr_addr + 1'b1;
        end

        if (row_buf_pop) begin
          row_buf_valid <= 1'b0;
        end

        if (mat_xfer) begin
          if (mat_is_last_chunk) begin
            row_buf_valid <= 1'b1;
            row_buf_data  <= final_row_sum;
            k_chunk_idx   <= 16'd0;
            if (row_idx + 16'd1 < cfg_M) row_idx <= row_idx + 16'd1;
          end else begin
            k_chunk_idx <= k_chunk_idx + 16'd1;
          end
        end
      end
    end
  end

  mv_ctrl_fsm #(
    .MAX_M(MAX_M),
    .MAX_N(MAX_N),
    .LANES(LANES),
    .CMD_W(CMD_W)
  ) u_ctrl (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_accept(cmd_accept),
    .cmd_data(cmd_data),
    .vec_xfer(vec_xfer),
    .mat_xfer(mat_xfer),
    .bias_xfer(bias_xfer),
    .out_xfer(out_xfer),
    .cfg_M(cfg_M),
    .cfg_N(cfg_N),
    .cfg_bias_en(cfg_bias_en),
    .cfg_relu_en(cfg_relu_en),
    .state_compute_en(state_compute_en),
    .lane_valid_mask(lane_valid_mask),
    .status_busy(status_busy),
    .status_error(status_error)
  );

  mv_stream_if #(
    .LANES(LANES),
    .MAT_DATA_W(MAT_DATA_W)
  ) u_stream_if (
    .mat_data_in(mat_data),
    .mat_lanes_out(mat_lanes)
  );

  mv_vec_buffer #(
    .MAX_N(MAX_N),
    .LANES(LANES)
  ) u_vec_buffer (
    .clk(clk),
    .rst_n(rst_n),
    .wr_en(vec_xfer),
    .wr_addr(vec_wr_addr),
    .wr_data(vec_data),
    .rd_chunk_base(rd_chunk_base[AW-1:0]),
    .rd_data(vec_lanes)
  );

  mv_mac16_core #(
    .LANES(LANES)
  ) u_mac (
    .clk(clk),
    .rst_n(rst_n),
    .compute_en(compute_en_core),
    .new_row(new_row_core),
    .lane_valid_mask(lane_valid_mask),
    .mat_lane_data(mat_lanes),
    .vec_lane_data(vec_lanes),
    .row_accum_out(row_accum_out),
    .row_done_pulse(row_done_pulse)
  );

  mv_postproc u_post (
    .clk(clk),
    .rst_n(rst_n),
    .in_valid(pp_in_valid),
    .in_data(row_buf_data),
    .bias_en(cfg_bias_en),
    .relu_en(cfg_relu_en),
    .bias_valid(pp_bias_valid),
    .bias_data(bias_data[31:0]),
    .out_ready(out_ready),
    .out_valid(pp_out_valid),
    .out_data(pp_out_data),
    .in_ready(pp_in_ready)
  );

  assign out_valid = pp_out_valid;
  assign out_data  = pp_out_data;

endmodule
