module fc_datapath #(
  parameter integer ARRAY_ROWS = 8,
  parameter integer ARRAY_COLS = 8,
  parameter integer MAX_M = 64,
  parameter integer MAX_N = 64,
  parameter integer MAX_K = 64
) (
  input logic clk,
  input logic rst_n,
  input logic [((MAX_M <= 1) ? 1 : $clog2(MAX_M+1))-1:0] cfg_m,
  input logic [((MAX_N <= 1) ? 1 : $clog2(MAX_N+1))-1:0] cfg_n,
  input logic [((MAX_K <= 1) ? 1 : $clog2(MAX_K+1))-1:0] cfg_k,
  input logic [7:0] a_we,
  input logic [((MAX_M*MAX_K <= 1) ? 1 : $clog2(MAX_M*MAX_K))-1:0] a_wbase,
  input logic [63:0] a_wdata,
  input logic [7:0] w_we,
  input logic [((MAX_K*MAX_N <= 1) ? 1 : $clog2(MAX_K*MAX_N))-1:0] w_wbase,
  input logic [63:0] w_wdata,
  input logic [1:0] bias_we,
  input logic [((MAX_N <= 1) ? 1 : $clog2(MAX_N))-1:0] bias_wbase,
  input logic [63:0] bias_wdata,
  input logic [((MAX_M <= 1) ? 1 : $clog2(MAX_M+1))-1:0] tile_m_base,
  input logic [((MAX_N <= 1) ? 1 : $clog2(MAX_N+1))-1:0] tile_n_base,
  input logic tile_init,
  input logic compute_step,
  input logic [((MAX_K <= 1) ? 1 : $clog2(MAX_K+1))-1:0] compute_k,
  input logic finalize_we,
  input logic [((((ARRAY_ROWS*ARRAY_COLS+1)/2) <= 1) ? 1 :
               $clog2((ARRAY_ROWS*ARRAY_COLS+1)/2))-1:0] finalize_pair,
  input logic [((((MAX_M*MAX_N+1)/2) <= 1) ? 1 :
               $clog2((MAX_M*MAX_N+1)/2))-1:0] result_rpair,
  output logic [63:0] result_rdata
);
  localparam integer RESULT_CAP = MAX_M*MAX_N;
  localparam integer RES_AW = (RESULT_CAP <= 1) ? 1 : $clog2(RESULT_CAP);

  logic signed [7:0] activation_mem [0:MAX_M*MAX_K-1];
  logic signed [7:0] weight_mem [0:MAX_K*MAX_N-1];
  logic signed [31:0] bias_mem [0:MAX_N-1];
  logic signed [31:0] accumulator [0:ARRAY_ROWS-1][0:ARRAY_COLS-1];
  logic signed [31:0] result_mem [0:RESULT_CAP-1];

  logic signed [7:0] active_a [0:ARRAY_ROWS-1];
  logic signed [7:0] active_w [0:ARRAY_COLS-1];
  logic signed [15:0] product [0:ARRAY_ROWS-1][0:ARRAY_COLS-1];
  logic signed [31:0] product_ext [0:ARRAY_ROWS-1][0:ARRAY_COLS-1];
  logic row_active [0:ARRAY_ROWS-1];
  logic col_active [0:ARRAY_COLS-1];

  logic [1:0] fin_valid;
  logic [RES_AW-1:0] fin_addr [0:1];
  logic signed [31:0] fin_sum [0:1];
  logic signed [31:0] fin_data [0:1];

  integer r, c, l;
  integer ai, wi;
  integer local_index, local_row, local_col;
  integer global_row, global_col, global_index;
  integer read_index, result_total;

  always_comb begin
    for (r = 0; r < ARRAY_ROWS; r = r + 1) begin
      row_active[r] = ((tile_m_base + r) < cfg_m);
      active_a[r] = 8'sd0;
      ai = (tile_m_base + r) * cfg_k + compute_k;
      if (row_active[r]) active_a[r] = activation_mem[ai];
    end
    for (c = 0; c < ARRAY_COLS; c = c + 1) begin
      col_active[c] = ((tile_n_base + c) < cfg_n);
      active_w[c] = 8'sd0;
      wi = compute_k * cfg_n + tile_n_base + c;
      if (col_active[c]) active_w[c] = weight_mem[wi];
    end
    for (r = 0; r < ARRAY_ROWS; r = r + 1)
      for (c = 0; c < ARRAY_COLS; c = c + 1) begin
        product[r][c] = active_a[r] * active_w[c];
        product_ext[r][c] = {{16{product[r][c][15]}}, product[r][c]};
      end
  end

  always_comb begin
    fin_valid = 2'b00;
    for (l = 0; l < 2; l = l + 1) begin
      fin_addr[l] = '0;
      fin_sum[l] = 32'sd0;
      fin_data[l] = 32'sd0;
      local_index = finalize_pair*2 + l;
      local_row = local_index / ARRAY_COLS;
      local_col = local_index % ARRAY_COLS;
      global_row = tile_m_base + local_row;
      global_col = tile_n_base + local_col;
      global_index = global_row * cfg_n + global_col;
      if ((local_row < ARRAY_ROWS) && (local_col < ARRAY_COLS) &&
          (global_row < cfg_m) && (global_col < cfg_n)) begin
        fin_valid[l] = 1'b1;
        fin_addr[l] = RES_AW'(global_index);
        fin_sum[l] = accumulator[local_row][local_col] + bias_mem[global_col];
        if (fin_sum[l][31]) fin_data[l] = 32'sd0;
        else fin_data[l] = fin_sum[l];
      end
    end
  end

  always_comb begin
    result_rdata = 64'b0;
    read_index = result_rpair * 2;
    result_total = cfg_m * cfg_n;
    if (read_index < result_total)
      result_rdata[31:0] = result_mem[read_index];
    if ((read_index + 1) < result_total)
      result_rdata[63:32] = result_mem[read_index+1];
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      for (r = 0; r < ARRAY_ROWS; r = r + 1)
        for (c = 0; c < ARRAY_COLS; c = c + 1)
          accumulator[r][c] <= 32'sd0;
    end else begin
      for (l = 0; l < 8; l = l + 1) begin
        if (a_we[l]) activation_mem[a_wbase+l] <= a_wdata[8*l +: 8];
        if (w_we[l]) weight_mem[w_wbase+l] <= w_wdata[8*l +: 8];
      end
      if (bias_we[0]) bias_mem[bias_wbase] <= bias_wdata[31:0];
      if (bias_we[1]) bias_mem[bias_wbase+1] <= bias_wdata[63:32];

      if (tile_init) begin
        for (r = 0; r < ARRAY_ROWS; r = r + 1)
          for (c = 0; c < ARRAY_COLS; c = c + 1)
            accumulator[r][c] <= 32'sd0;
      end else if (compute_step) begin
        for (r = 0; r < ARRAY_ROWS; r = r + 1)
          for (c = 0; c < ARRAY_COLS; c = c + 1)
            if (row_active[r] && col_active[c])
              accumulator[r][c] <= accumulator[r][c] + product_ext[r][c];
      end

      if (finalize_we) begin
        if (fin_valid[0]) result_mem[fin_addr[0]] <= fin_data[0];
        if (fin_valid[1]) result_mem[fin_addr[1]] <= fin_data[1];
      end
    end
  end
endmodule
