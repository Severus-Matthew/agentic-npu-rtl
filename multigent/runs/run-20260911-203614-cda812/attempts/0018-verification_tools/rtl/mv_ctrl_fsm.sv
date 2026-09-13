module mv_ctrl_fsm #(
  parameter int MAX_M = 256,
  parameter int MAX_N = 256,
  parameter int LANES = 16,
  parameter int CMD_W = 64
) (
  input  logic                     clk,
  input  logic                     rst_n,
  input  logic                     cmd_accept,
  input  logic [CMD_W-1:0]         cmd_data,
  input  logic                     vec_xfer,
  input  logic                     mat_xfer,
  input  logic                     bias_xfer,
  input  logic                     out_xfer,
  output logic [15:0]              cfg_M,
  output logic [15:0]              cfg_N,
  output logic                     cfg_bias_en,
  output logic                     cfg_relu_en,
  output logic                     state_compute_en,
  output logic [LANES-1:0]         lane_valid_mask,
  output logic                     status_busy,
  output logic                     status_error
);
  typedef enum logic [1:0] {IDLE, LOAD_VEC, COMPUTE_ROWS, DONE} st_t;
  st_t st;
  logic [15:0] vec_cnt, row_cnt, chunk_cnt;
  logic [15:0] chunks_per_row;
  logic [4:0]  rem;

  always_comb begin
    chunks_per_row = (cfg_N + LANES - 1) / LANES;
    rem = cfg_N % LANES;
    lane_valid_mask = {LANES{1'b1}};
    if ((chunk_cnt == chunks_per_row - 1) && (rem != 0)) lane_valid_mask = (16'h0001 << rem) - 1;
    state_compute_en = (st == COMPUTE_ROWS) && mat_xfer;
    status_busy = (st != IDLE);
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      st <= IDLE;
      cfg_M <= 16'd0;
      cfg_N <= 16'd0;
      cfg_bias_en <= 1'b0;
      cfg_relu_en <= 1'b0;
      vec_cnt <= 16'd0;
      row_cnt <= 16'd0;
      chunk_cnt <= 16'd0;
      status_error <= 1'b0;
    end else begin
      case (st)
        IDLE: begin
          vec_cnt <= 16'd0; row_cnt <= 16'd0; chunk_cnt <= 16'd0;
          if (cmd_accept) begin
            cfg_M <= cmd_data[15:0];
            cfg_N <= cmd_data[31:16];
            cfg_bias_en <= cmd_data[32];
            cfg_relu_en <= cmd_data[33];
            if ((cmd_data[15:0] < 1) || (cmd_data[15:0] > MAX_M) || (cmd_data[31:16] < 1) || (cmd_data[31:16] > MAX_N)) begin
              status_error <= 1'b1;
              st <= DONE;
            end else st <= LOAD_VEC;
          end
        end
        LOAD_VEC: begin
          if (vec_xfer) begin
            vec_cnt <= vec_cnt + 1;
            if (vec_cnt + 1 == cfg_N) st <= COMPUTE_ROWS;
          end
        end
        COMPUTE_ROWS: begin
          if (mat_xfer) begin
            if (chunk_cnt + 1 == chunks_per_row) begin
              chunk_cnt <= 16'd0;
              if (row_cnt + 1 == cfg_M) st <= DONE;
              else row_cnt <= row_cnt + 1;
            end else chunk_cnt <= chunk_cnt + 1;
          end
          if (bias_xfer && !cfg_bias_en) status_error <= 1'b1;
        end
        DONE: begin
          if (out_xfer && (row_cnt + 1 == cfg_M || status_error)) st <= IDLE;
        end
      endcase
    end
  end
endmodule
