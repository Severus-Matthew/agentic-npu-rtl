module stream_matvec_int8_16 #(
  parameter integer MAX_ROWS = 256,
  parameter integer MAX_COLS = 256
) (
  input  logic clk,
  input  logic rst_n,
  input  logic cfg_valid,
  output logic cfg_ready,
  input  logic [((MAX_ROWS < 2) ? 1 : $clog2(MAX_ROWS+1))-1:0] cfg_rows,
  input  logic [((MAX_COLS < 2) ? 1 : $clog2(MAX_COLS+1))-1:0] cfg_cols,
  input  logic cfg_bias_enable,
  input  logic cfg_relu_enable,
  input  logic in_valid,
  output logic in_ready,
  input  logic [127:0] in_data,
  output logic out_valid,
  input  logic out_ready,
  output logic signed [31:0] out_data,
  output logic out_last,
  output logic out_error
);
  localparam integer RW = (MAX_ROWS < 2) ? 1 : $clog2(MAX_ROWS+1);
  localparam integer CW = (MAX_COLS < 2) ? 1 : $clog2(MAX_COLS+1);
  // For small configurations there can only be one tile. This bound
  // keeps all row-boundary arithmetic representable in RW+1 bits.
  localparam logic [RW:0] TILE_SPAN = (RW+1)'((MAX_ROWS < 16) ? MAX_ROWS : 16);
  localparam logic [RW-1:0] ROW_BOUND = RW'(MAX_ROWS);
  localparam logic [CW-1:0] COL_BOUND = CW'(MAX_COLS);

  generate
    if ((MAX_ROWS < 1) || (MAX_ROWS > 65535) ||
        (MAX_COLS < 1) || (MAX_COLS > 65535)) begin : g_invalid_parameters
      // Static configuration diagnostic; no functional initialization.
      initial $fatal(1, "MAX_ROWS and MAX_COLS must be in 1..65535");
    end
  endgenerate

  typedef enum logic [2:0] {IDLE, VECTOR, BIAS, MAC, EMIT, ERROR} state_t;
  state_t state;
  logic [RW-1:0] rows, base;
  logic [CW-1:0] cols, k;
  logic [3:0] j;
  logic bias_enable, relu_enable;
  logic signed [7:0] vector_store [0:MAX_COLS-1];
  logic signed [31:0] bias_store [0:15];
  logic signed [7:0] vector_value;
  logic signed [31:0] dot_value, bias_value, result_value;
  logic [511:0] accumulators;
  logic cfg_fire, in_fire, out_fire;
  logic command_legal, active_job;
  logic [RW:0] remaining_rows, next_base;
  logic [4:0] lane_count;
  logic column_last, lane_last, final_tile;
  logic mac_clear, mac_step;

  assign cfg_ready = rst_n && (state == IDLE);
  assign in_ready = rst_n && ((state == VECTOR) || (state == BIAS) || (state == MAC));
  assign out_valid = rst_n && ((state == EMIT) || (state == ERROR));
  assign cfg_fire = cfg_valid && cfg_ready;
  assign in_fire = in_valid && in_ready;
  assign out_fire = out_valid && out_ready;
  assign command_legal = (cfg_rows != '0) && (cfg_rows <= ROW_BOUND) &&
                         (cfg_cols != '0) && (cfg_cols <= COL_BOUND);
  assign active_job = (state == VECTOR) || (state == BIAS) ||
                      (state == MAC) || (state == EMIT);
  assign column_last = active_job && (k == (cols - CW'(1)));

  always_comb begin
    remaining_rows = '0;
    next_base = {1'b0, base};
    lane_count = 5'd0;
    final_tile = 1'b0;
    if (active_job) begin
      remaining_rows = {1'b0, rows} - {1'b0, base};
      final_tile = (remaining_rows <= TILE_SPAN);
      if (remaining_rows > TILE_SPAN)
        lane_count = 5'd16;
      else
        lane_count = 5'(remaining_rows);
      // Whenever another tile exists, TILE_SPAN is exactly 16.
      if (!final_tile)
        next_base = {1'b0, base} + TILE_SPAN;
    end
  end

  assign lane_last = active_job && (({1'b0, j} + 5'd1) == lane_count);
  assign mac_clear = ((state == VECTOR) && in_fire && column_last) ||
                     ((state == EMIT) && out_fire && lane_last && !final_tile);
  assign mac_step = (state == MAC) && in_fire;

  // Reads are asynchronous and are enabled only after the relevant loads.
  always_comb begin
    vector_value = 8'sd0;
    bias_value = 32'sd0;
    dot_value = 32'sd0;
    if (rst_n && (state == MAC))
      vector_value = vector_store[k];
    if (rst_n && (state == EMIT)) begin
      dot_value = $signed(accumulators[32*j +: 32]);
      if (bias_enable)
        bias_value = bias_store[j];
    end
  end

  // Neither staging memory is reset or initialized.
  always_ff @(posedge clk) begin
    if (rst_n && in_fire) begin
      if (state == VECTOR)
        vector_store[k] <= $signed(in_data[7:0]);
      if (state == BIAS)
        bias_store[j] <= $signed(in_data[31:0]);
    end
  end

  int8_mac16_bank u_mac_bank (
    .clk(clk),
    .rst_n(rst_n),
    .clear(mac_clear),
    .step(mac_step),
    .vector_value(vector_value),
    .matrix_values(in_data),
    .accumulators(accumulators)
  );

  int32_bias_relu u_finalizer (
    .dot_value(dot_value),
    .bias_value(bias_value),
    .bias_enable(bias_enable),
    .relu_enable(relu_enable),
    .result_value(result_value)
  );

  always_comb begin
    out_data = 32'sd0;
    out_last = 1'b0;
    out_error = 1'b0;
    if (out_valid) begin
      if (state == EMIT) begin
        out_data = result_value;
        out_last = final_tile && lane_last;
      end else if (state == ERROR) begin
        out_last = 1'b1;
        out_error = 1'b1;
      end
    end
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      state <= IDLE;
      rows <= '0;
      cols <= '0;
      base <= '0;
      k <= '0;
      j <= '0;
      bias_enable <= 1'b0;
      relu_enable <= 1'b0;
    end else begin
      case (state)
        IDLE: begin
          if (cfg_fire) begin
            rows <= cfg_rows;
            cols <= cfg_cols;
            bias_enable <= cfg_bias_enable;
            relu_enable <= cfg_relu_enable;
            base <= '0;
            k <= '0;
            j <= '0;
            if (command_legal)
              state <= VECTOR;
            else
              state <= ERROR;
          end
        end
        VECTOR: begin
          if (in_fire) begin
            if (column_last) begin
              k <= '0;
              j <= '0;
              if (bias_enable)
                state <= BIAS;
              else
                state <= MAC;
            end else begin
              k <= k + CW'(1);
            end
          end
        end
        BIAS: begin
          if (in_fire) begin
            if (lane_last) begin
              j <= '0;
              k <= '0;
              state <= MAC;
            end else begin
              j <= j + 4'd1;
            end
          end
        end
        MAC: begin
          if (in_fire) begin
            if (column_last) begin
              k <= '0;
              j <= '0;
              state <= EMIT;
            end else begin
              k <= k + CW'(1);
            end
          end
        end
        EMIT: begin
          if (out_fire) begin
            if (lane_last) begin
              if (final_tile) begin
                state <= IDLE;
              end else begin
                base <= next_base[RW-1:0];
                k <= '0;
                j <= '0;
                if (bias_enable)
                  state <= BIAS;
                else
                  state <= MAC;
              end
            end else begin
              j <= j + 4'd1;
            end
          end
        end
        ERROR: begin
          if (out_fire)
            state <= IDLE;
        end
        default: begin
          // Unreachable after the required reset; retain state.
        end
      endcase
    end
  end
endmodule
