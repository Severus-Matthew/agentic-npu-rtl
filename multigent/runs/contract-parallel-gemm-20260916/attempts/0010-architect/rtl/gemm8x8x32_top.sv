module gemm8x8x32_top #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic cmd_payload,
  input  logic a_valid,
  output logic a_ready,
  input  logic signed [7:0] a_payload,
  input  logic b_valid,
  output logic b_ready,
  input  logic signed [7:0] b_payload,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic signed [31:0] bias_payload,
  output logic out_valid,
  input  logic out_ready,
  output logic signed [31:0] out_payload,
  output logic out_last,
  output logic busy,
  output logic completion,
  output logic error
);
  logic cmd_hs, a_hs, b_hs, bias_hs, out_hs;
  logic state_load_a, state_load_b, state_load_bias, state_compute, state_output;
  logic compute_done;

  logic we_a, we_b, we_bias;
  logic [7:0] waddr_a, waddr_b;
  logic [2:0] waddr_bias;

  logic [7:0] raddr_a, raddr_b;
  logic [2:0] raddr_bias;
  logic signed [7:0] rdata_a, rdata_b;
  logic signed [31:0] rdata_bias;

  logic we_c;
  logic [5:0] waddr_c, raddr_c;
  logic signed [31:0] wdata_c, rdata_c;

  logic [8:0] a_load_idx_q;
  logic [8:0] b_load_idx_q;
  logic [3:0] bias_load_idx_q;

  assign cmd_hs  = cmd_valid  & cmd_ready;
  assign a_hs    = a_valid    & a_ready;
  assign b_hs    = b_valid    & b_ready;
  assign bias_hs = bias_valid & bias_ready;

  assign we_a = a_hs;
  assign we_b = b_hs;
  assign we_bias = bias_hs;

  assign waddr_a = a_load_idx_q[7:0];
  assign waddr_b = b_load_idx_q[7:0];
  assign waddr_bias = bias_load_idx_q[2:0];

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      a_load_idx_q <= '0;
      b_load_idx_q <= '0;
      bias_load_idx_q <= '0;
    end else begin
      if (!state_load_a) a_load_idx_q <= '0;
      else if (a_hs) a_load_idx_q <= a_load_idx_q + 1'b1;

      if (!state_load_b) b_load_idx_q <= '0;
      else if (b_hs) b_load_idx_q <= b_load_idx_q + 1'b1;

      if (!state_load_bias) bias_load_idx_q <= '0;
      else if (bias_hs) bias_load_idx_q <= bias_load_idx_q + 1'b1;
    end
  end

  gemm_ctrl_fsm #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_ctrl (
    .clk(clk), .rst_n(rst_n), .cmd_hs(cmd_hs), .cmd_payload(cmd_payload), .a_hs(a_hs), .b_hs(b_hs), .bias_hs(bias_hs),
    .compute_done(compute_done), .out_hs(out_hs), .state_load_a(state_load_a), .state_load_b(state_load_b), .state_load_bias(state_load_bias),
    .state_compute(state_compute), .state_output(state_output), .cmd_ready(cmd_ready), .a_ready(a_ready), .b_ready(b_ready), .bias_ready(bias_ready),
    .busy(busy), .completion(completion), .error(error)
  );

  mac_sequencer #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_mac (
    .clk(clk), .rst_n(rst_n), .enable_compute(state_compute), .raddr_a(raddr_a), .rdata_a(rdata_a), .raddr_b(raddr_b), .rdata_b(rdata_b),
    .raddr_bias(raddr_bias), .rdata_bias(rdata_bias), .we_c(we_c), .waddr_c(waddr_c), .wdata_c(wdata_c), .compute_done(compute_done)
  );

  output_streamer #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_out (
    .clk(clk), .rst_n(rst_n), .enable_output(state_output), .out_ready(out_ready), .out_valid(out_valid), .out_payload(out_payload),
    .out_last(out_last), .out_hs(out_hs), .raddr_c(raddr_c), .rdata_c(rdata_c)
  );

  operand_buffer_bank #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_buf (
    .clk(clk), .we_a(we_a), .waddr_a(waddr_a), .wdata_a(a_payload), .we_b(we_b), .waddr_b(waddr_b), .wdata_b(b_payload),
    .we_bias(we_bias), .waddr_bias(waddr_bias), .wdata_bias(bias_payload), .raddr_a(raddr_a), .rdata_a(rdata_a), .raddr_b(raddr_b), .rdata_b(rdata_b),
    .raddr_bias(raddr_bias), .rdata_bias(rdata_bias), .we_c(we_c), .waddr_c(waddr_c), .wdata_c(wdata_c), .raddr_c(raddr_c), .rdata_c(rdata_c)
  );
endmodule
