module gemm_ctrl_fsm #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_hs,
  input  logic cmd_payload,
  input  logic a_hs,
  input  logic b_hs,
  input  logic bias_hs,
  input  logic compute_done,
  input  logic out_hs,
  output logic state_load_a,
  output logic state_load_b,
  output logic state_load_bias,
  output logic state_compute,
  output logic state_output,
  output logic cmd_ready,
  output logic a_ready,
  output logic b_ready,
  output logic bias_ready,
  output logic busy,
  output logic completion,
  output logic error
);
  localparam int A_COUNT    = M_FIXED*K_FIXED;
  localparam int B_COUNT    = K_FIXED*N_FIXED;
  localparam int BIAS_COUNT = N_FIXED;
  localparam int C_COUNT    = M_FIXED*N_FIXED;

  localparam int AW_A    = (A_COUNT    <= 1) ? 1 : $clog2(A_COUNT+1);
  localparam int AW_B    = (B_COUNT    <= 1) ? 1 : $clog2(B_COUNT+1);
  localparam int AW_BIAS = (BIAS_COUNT <= 1) ? 1 : $clog2(BIAS_COUNT+1);
  localparam int AW_C    = (C_COUNT    <= 1) ? 1 : $clog2(C_COUNT+1);

  typedef enum logic [2:0] {
    ST_IDLE      = 3'd0,
    ST_LOAD_A    = 3'd1,
    ST_LOAD_B    = 3'd2,
    ST_LOAD_BIAS = 3'd3,
    ST_COMPUTE   = 3'd4,
    ST_OUTPUT    = 3'd5,
    ST_DONE      = 3'd6
  } state_t;

  state_t state_q, state_d;
  logic [AW_A-1:0]    a_count_q;
  logic [AW_B-1:0]    b_count_q;
  logic [AW_BIAS-1:0] bias_count_q;
  logic [AW_C-1:0]    out_count_q;

  always_comb begin
    state_load_a    = (state_q == ST_LOAD_A);
    state_load_b    = (state_q == ST_LOAD_B);
    state_load_bias = (state_q == ST_LOAD_BIAS);
    state_compute   = (state_q == ST_COMPUTE);
    state_output    = (state_q == ST_OUTPUT);

    cmd_ready  = rst_n && (state_q == ST_IDLE);
    a_ready    = rst_n && (state_q == ST_LOAD_A);
    b_ready    = rst_n && (state_q == ST_LOAD_B);
    bias_ready = rst_n && (state_q == ST_LOAD_BIAS);

    state_d = state_q;
    unique case (state_q)
      ST_IDLE:      if (cmd_hs && (cmd_payload == 1'b1)) state_d = ST_LOAD_A;
      ST_LOAD_A:    if (a_hs    && (a_count_q    == A_COUNT-1)) state_d = ST_LOAD_B;
      ST_LOAD_B:    if (b_hs    && (b_count_q    == B_COUNT-1)) state_d = ST_LOAD_BIAS;
      ST_LOAD_BIAS: if (bias_hs && (bias_count_q == BIAS_COUNT-1)) state_d = ST_COMPUTE;
      ST_COMPUTE:   if (compute_done) state_d = ST_OUTPUT;
      ST_OUTPUT:    if (out_hs && (out_count_q == C_COUNT-1)) state_d = ST_DONE;
      ST_DONE:      state_d = ST_IDLE;
      default:      state_d = ST_IDLE;
    endcase
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state_q      <= ST_IDLE;
      a_count_q    <= '0;
      b_count_q    <= '0;
      bias_count_q <= '0;
      out_count_q  <= '0;
      busy         <= 1'b0;
      completion   <= 1'b0;
      error        <= 1'b0;
    end else begin
      state_q <= state_d;
      completion <= 1'b0;
      error <= 1'b0;

      if ((state_q == ST_IDLE) && cmd_hs && (cmd_payload == 1'b1)) busy <= 1'b1;
      if ((state_q == ST_OUTPUT) && out_hs && (out_count_q == C_COUNT-1)) busy <= 1'b0;
      if (state_q == ST_DONE) completion <= 1'b1;

      if (cmd_hs && ((state_q != ST_IDLE) || (cmd_payload != 1'b1))) error <= 1'b1;
      if (a_hs    && (state_q != ST_LOAD_A))    error <= 1'b1;
      if (b_hs    && (state_q != ST_LOAD_B))    error <= 1'b1;
      if (bias_hs && (state_q != ST_LOAD_BIAS)) error <= 1'b1;

      if (state_q != ST_LOAD_A) a_count_q <= '0;
      else if (a_hs) a_count_q <= a_count_q + 1'b1;

      if (state_q != ST_LOAD_B) b_count_q <= '0;
      else if (b_hs) b_count_q <= b_count_q + 1'b1;

      if (state_q != ST_LOAD_BIAS) bias_count_q <= '0;
      else if (bias_hs) bias_count_q <= bias_count_q + 1'b1;

      if (state_q != ST_OUTPUT) out_count_q <= '0;
      else if (out_hs) out_count_q <= out_count_q + 1'b1;
    end
  end
endmodule
