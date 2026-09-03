module npu_control_fsm #(
  parameter int MAX_M = 64,
  parameter int MAX_N = 64,
  parameter int MAX_K = 64,
  parameter int TILE_N = 8
)(
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic [95:0] cmd_data,
  input  logic load_a_done,
  input  logic load_b_done,
  input  logic load_bias_done,
  input  logic compute_tile_done,
  input  logic emit_done,
  output logic [15:0] cfg_m,
  output logic [15:0] cfg_n,
  output logic [15:0] cfg_k,
  output logic        cfg_bias_enable,
  output logic st_load_a,
  output logic st_load_b,
  output logic st_load_bias,
  output logic st_compute,
  output logic st_emit,
  output logic do_compute_start,
  output logic do_compute_step,
  output logic do_emit_start,
  output logic do_done_pulse,
  output logic [$clog2(MAX_M)-1:0] idx_m,
  output logic [$clog2(MAX_N)-1:0] idx_n_base,
  output logic [$clog2(MAX_K)-1:0] idx_k,
  output logic [TILE_N-1:0] lane_active,
  output logic status_error
);
  typedef enum logic [2:0] {IDLE, LOAD_A, LOAD_B, LOAD_BIAS, COMPUTE, EMIT, DONE} state_t;
  state_t state;
  logic [15:0] n_tiles;
  logic [15:0] t_idx;

  always_comb begin
    st_load_a = (state==LOAD_A); st_load_b = (state==LOAD_B); st_load_bias = (state==LOAD_BIAS);
    st_compute = (state==COMPUTE); st_emit = (state==EMIT);
    cmd_ready = (state==IDLE) && !status_error;
    do_compute_step = (state==COMPUTE);
  end

  always_comb begin
    for (int i=0;i<TILE_N;i++) begin
      if ((idx_n_base + i) < cfg_n) lane_active[i]=1'b1; else lane_active[i]=1'b0;
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state <= IDLE; cfg_m<=0; cfg_n<=0; cfg_k<=0; cfg_bias_enable<=0; status_error<=0;
      idx_m<=0; idx_n_base<=0; idx_k<=0; t_idx<=0; n_tiles<=0;
      do_compute_start<=0; do_emit_start<=0; do_done_pulse<=0;
    end else begin
      do_compute_start<=0; do_emit_start<=0; do_done_pulse<=0;
      case (state)
        IDLE: begin
          if (cmd_valid && cmd_ready) begin
            cfg_m <= cmd_data[15:0]; cfg_n <= cmd_data[31:16]; cfg_k <= cmd_data[47:32]; cfg_bias_enable <= cmd_data[48];
            if ((cmd_data[15:0]<1)||(cmd_data[15:0]>MAX_M)||(cmd_data[31:16]<1)||(cmd_data[31:16]>MAX_N)||(cmd_data[47:32]<1)||(cmd_data[47:32]>MAX_K)||(cmd_data[95:49]!=0)) begin
              status_error <= 1'b1;
            end else begin
              state <= LOAD_A;
              n_tiles <= (cmd_data[31:16] + TILE_N - 1)/TILE_N;
            end
          end
        end
        LOAD_A: if (load_a_done) state <= LOAD_B;
        LOAD_B: if (load_b_done) state <= cfg_bias_enable ? LOAD_BIAS : COMPUTE;
        LOAD_BIAS: if (load_bias_done) state <= COMPUTE;
        COMPUTE: begin
          if (idx_k==0) do_compute_start <= 1'b1;
          if (compute_tile_done) begin
            state <= EMIT;
            do_emit_start <= 1'b1;
          end
        end
        EMIT: if (emit_done) begin
          if (t_idx + 1 < n_tiles) begin
            t_idx <= t_idx + 1;
            idx_n_base <= (t_idx + 1)*TILE_N;
            idx_k <= 0;
            state <= COMPUTE;
          end else if (idx_m + 1 < cfg_m) begin
            idx_m <= idx_m + 1;
            t_idx <= 0;
            idx_n_base <= 0;
            idx_k <= 0;
            state <= COMPUTE;
          end else begin
            state <= DONE;
          end
        end
        DONE: begin
          do_done_pulse <= 1'b1;
          state <= IDLE;
          idx_m<=0; idx_n_base<=0; idx_k<=0; t_idx<=0;
        end
      endcase
      if (state==COMPUTE && !compute_tile_done) idx_k <= idx_k + 1;
    end
  end
endmodule
