module fc_controller #(
  parameter integer ARRAY_ROWS = 8,
  parameter integer ARRAY_COLS = 8,
  parameter integer MAX_M = 64,
  parameter integer MAX_N = 64,
  parameter integer MAX_K = 64
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cmd_valid,
  output logic cmd_ready,
  input  logic [(((MAX_M <= 1) ? 1 : $clog2(MAX_M+1)) +
                ((MAX_N <= 1) ? 1 : $clog2(MAX_N+1)) +
                ((MAX_K <= 1) ? 1 : $clog2(MAX_K+1)))-1:0] cmd_data,
  input  logic a_valid,
  output logic a_ready,
  input  logic [63:0] a_data,
  input  logic w_valid,
  output logic w_ready,
  input  logic [63:0] w_data,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic [63:0] bias_data,
  output logic out_valid,
  input  logic out_ready,
  output logic [63:0] out_data,
  output logic status_valid,
  input  logic status_ready,
  output logic [1:0] status_code
);
  localparam integer M_W = (MAX_M <= 1) ? 1 : $clog2(MAX_M+1);
  localparam integer N_W = (MAX_N <= 1) ? 1 : $clog2(MAX_N+1);
  localparam integer K_W = (MAX_K <= 1) ? 1 : $clog2(MAX_K+1);
  localparam integer A_AW = (MAX_M*MAX_K <= 1) ? 1 : $clog2(MAX_M*MAX_K);
  localparam integer W_AW = (MAX_K*MAX_N <= 1) ? 1 : $clog2(MAX_K*MAX_N);
  localparam integer B_AW = (MAX_N <= 1) ? 1 : $clog2(MAX_N);
  localparam integer TILE_PAIRS = (ARRAY_ROWS*ARRAY_COLS+1)/2;
  localparam integer FP_W = (TILE_PAIRS <= 1) ? 1 : $clog2(TILE_PAIRS);
  localparam integer RESULT_PAIRS = (MAX_M*MAX_N+1)/2;
  localparam integer RP_W = (RESULT_PAIRS <= 1) ? 1 : $clog2(RESULT_PAIRS);

  typedef enum logic [3:0] {
    IDLE, LOAD_A, LOAD_W, LOAD_BIAS, TILE_INIT,
    COMPUTE, FINALIZE, OUTPUT, STATUS
  } state_t;

  state_t state;
  logic [M_W-1:0] cfg_m;
  logic [N_W-1:0] cfg_n;
  logic [K_W-1:0] cfg_k;
  logic [M_W-1:0] tile_m_base;
  logic [N_W-1:0] tile_n_base;
  logic [K_W-1:0] compute_k;
  logic [FP_W-1:0] finalize_pair;
  logic [RP_W-1:0] result_rpair;
  logic [1:0] status_code_reg;
  integer unsigned activation_beat;
  integer unsigned weight_beat;
  integer unsigned bias_beat;
  integer unsigned output_beat;
  integer unsigned a_total;
  integer unsigned w_total;
  integer unsigned b_total;
  integer unsigned out_total;
  integer lane;

  logic [7:0] a_we;
  logic [A_AW-1:0] a_wbase;
  logic [7:0] w_we;
  logic [W_AW-1:0] w_wbase;
  logic [1:0] bias_we;
  logic [B_AW-1:0] bias_wbase;
  logic tile_init;
  logic compute_step;
  logic finalize_we;
  logic [63:0] result_rdata;

  wire [M_W-1:0] cmd_m = cmd_data[M_W-1:0];
  wire [N_W-1:0] cmd_n = cmd_data[M_W +: N_W];
  wire [K_W-1:0] cmd_k = cmd_data[M_W+N_W +: K_W];

  always_comb begin
    a_total = cfg_m * cfg_k;
    w_total = cfg_k * cfg_n;
    b_total = cfg_n;
    out_total = cfg_m * cfg_n;

    cmd_ready = (state == IDLE);
    a_ready = (state == LOAD_A);
    w_ready = (state == LOAD_W);
    bias_ready = (state == LOAD_BIAS);
    out_valid = (state == OUTPUT);
    status_valid = (state == STATUS);
    status_code = status_code_reg;
    out_data = (state == OUTPUT) ? result_rdata : 64'b0;

    a_we = 8'b0;
    w_we = 8'b0;
    bias_we = 2'b0;
    a_wbase = A_AW'(activation_beat * 8);
    w_wbase = W_AW'(weight_beat * 8);
    bias_wbase = B_AW'(bias_beat * 2);
    tile_init = (state == TILE_INIT);
    compute_step = (state == COMPUTE);
    finalize_we = (state == FINALIZE);
    result_rpair = RP_W'(output_beat);

    if ((state == LOAD_A) && a_valid) begin
      for (lane = 0; lane < 8; lane = lane + 1)
        if ((activation_beat*8 + lane) < a_total)
          a_we[lane] = 1'b1;
    end
    if ((state == LOAD_W) && w_valid) begin
      for (lane = 0; lane < 8; lane = lane + 1)
        if ((weight_beat*8 + lane) < w_total)
          w_we[lane] = 1'b1;
    end
    if ((state == LOAD_BIAS) && bias_valid) begin
      if ((bias_beat*2) < b_total) bias_we[0] = 1'b1;
      if ((bias_beat*2 + 1) < b_total) bias_we[1] = 1'b1;
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state <= IDLE;
      cfg_m <= '0; cfg_n <= '0; cfg_k <= '0;
      tile_m_base <= '0; tile_n_base <= '0; compute_k <= '0;
      finalize_pair <= '0;
      activation_beat <= 0; weight_beat <= 0; bias_beat <= 0;
      output_beat <= 0;
      status_code_reg <= 2'b00;
    end else begin
      case (state)
        IDLE: begin
          activation_beat <= 0; weight_beat <= 0; bias_beat <= 0;
          output_beat <= 0; finalize_pair <= '0; compute_k <= '0;
          tile_m_base <= '0; tile_n_base <= '0;
          if (cmd_valid) begin
            if ((cmd_m == 0) || (cmd_n == 0) || (cmd_k == 0) ||
                (cmd_m > MAX_M) || (cmd_n > MAX_N) || (cmd_k > MAX_K)) begin
              status_code_reg <= 2'b01;
              state <= STATUS;
            end else begin
              cfg_m <= cmd_m; cfg_n <= cmd_n; cfg_k <= cmd_k;
              status_code_reg <= 2'b00;
              state <= LOAD_A;
            end
          end
        end
        LOAD_A: if (a_valid) begin
          if (((activation_beat+1)*8) >= a_total) begin
            weight_beat <= 0;
            state <= LOAD_W;
          end else activation_beat <= activation_beat + 1;
        end
        LOAD_W: if (w_valid) begin
          if (((weight_beat+1)*8) >= w_total) begin
            bias_beat <= 0;
            state <= LOAD_BIAS;
          end else weight_beat <= weight_beat + 1;
        end
        LOAD_BIAS: if (bias_valid) begin
          if (((bias_beat+1)*2) >= b_total) begin
            tile_m_base <= '0; tile_n_base <= '0;
            state <= TILE_INIT;
          end else bias_beat <= bias_beat + 1;
        end
        TILE_INIT: begin
          compute_k <= '0;
          state <= COMPUTE;
        end
        COMPUTE: begin
          if ((compute_k + 1) >= cfg_k) begin
            finalize_pair <= '0;
            state <= FINALIZE;
          end else compute_k <= compute_k + 1'b1;
        end
        FINALIZE: begin
          if ((finalize_pair + 1) >= TILE_PAIRS) begin
            finalize_pair <= '0;
            if ((tile_n_base + ARRAY_COLS) < cfg_n) begin
              tile_n_base <= tile_n_base + ARRAY_COLS;
              state <= TILE_INIT;
            end else if ((tile_m_base + ARRAY_ROWS) < cfg_m) begin
              tile_m_base <= tile_m_base + ARRAY_ROWS;
              tile_n_base <= '0;
              state <= TILE_INIT;
            end else begin
              output_beat <= 0;
              state <= OUTPUT;
            end
          end else finalize_pair <= finalize_pair + 1'b1;
        end
        OUTPUT: if (out_ready) begin
          if (((output_beat+1)*2) >= out_total) begin
            status_code_reg <= 2'b00;
            state <= STATUS;
          end else output_beat <= output_beat + 1;
        end
        STATUS: if (status_ready) begin
          state <= IDLE;
          status_code_reg <= 2'b00;
        end
        default: state <= IDLE;
      endcase
    end
  end

  fc_datapath #(
    .ARRAY_ROWS(ARRAY_ROWS), .ARRAY_COLS(ARRAY_COLS),
    .MAX_M(MAX_M), .MAX_N(MAX_N), .MAX_K(MAX_K)
  ) u_datapath (
    .clk(clk), .rst_n(rst_n),
    .cfg_m(cfg_m), .cfg_n(cfg_n), .cfg_k(cfg_k),
    .a_we(a_we), .a_wbase(a_wbase), .a_wdata(a_data),
    .w_we(w_we), .w_wbase(w_wbase), .w_wdata(w_data),
    .bias_we(bias_we), .bias_wbase(bias_wbase), .bias_wdata(bias_data),
    .tile_m_base(tile_m_base), .tile_n_base(tile_n_base),
    .tile_init(tile_init), .compute_step(compute_step), .compute_k(compute_k),
    .finalize_we(finalize_we), .finalize_pair(finalize_pair),
    .result_rpair(result_rpair), .result_rdata(result_rdata)
  );
endmodule
