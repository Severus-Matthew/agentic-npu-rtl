module stream_matvec_int8 #(
    parameter int MAX_ROWS = 256,
    parameter int MAX_COLS = 256
) (
    input  logic               clk,
    input  logic               rst,
    input  logic               cmd_valid,
    output logic               cmd_ready,
    input  logic [15:0]        cmd_rows,
    input  logic [15:0]        cmd_cols,
    input  logic               cmd_bias_enable,
    input  logic               cmd_relu_enable,
    input  logic               in_valid,
    output logic               in_ready,
    input  logic [31:0]        in_data,
    output logic               out_valid,
    input  logic               out_ready,
    output logic signed [31:0] out_data,
    output logic               out_last,
    output logic               done_valid,
    input  logic               done_ready,
    output logic               done_error
);

    localparam int COL_W = (MAX_COLS > 1) ? $clog2(MAX_COLS) : 1;
    localparam int ROW_W = (MAX_ROWS > 1) ? $clog2(MAX_ROWS) : 1;
    localparam logic [16:0] ROW_LIMIT = 17'(MAX_ROWS);
    localparam logic [16:0] COL_LIMIT = 17'(MAX_COLS);

    // Elaboration-only parameter checks; no functional initialization.
    generate
        if ((MAX_ROWS < 16) || (MAX_ROWS > 65535) ||
            (MAX_COLS < 1) || (MAX_COLS > 65535)) begin : g_invalid_parameters
            $error("MAX_ROWS must be 16..65535; MAX_COLS must be 1..65535");
        end
    endgenerate

    typedef enum logic [3:0] {
        IDLE, LOAD_X, TILE_INIT, LOAD_BIAS, LOAD_W,
        MAC, FINALIZE, EMIT, DONE
    } state_t;
    state_t state;

    logic [15:0] rows_q, cols_q;
    logic bias_enable_q, relu_enable_q, error_q;
    logic [COL_W-1:0] vector_write_index, column_index;
    logic [ROW_W-1:0] tile_base;
    logic [4:0] tile_height;
    logic [3:0] lane_index;

    logic signed [7:0] vector_store [0:MAX_COLS-1];
    logic signed [7:0] matrix_staging [0:15];
    logic signed [31:0] bias_staging [0:15];
    logic signed [31:0] accumulator_result_bank [0:15];

    logic signed [7:0] vector_value;
    wire signed [15:0] product [0:15];
    wire signed [31:0] extended_product [0:15];
    wire signed [31:0] mac_value [0:15];
    wire signed [31:0] selected_bias [0:15];
    wire signed [31:0] biased_value [0:15];
    wire signed [31:0] final_value [0:15];

    logic [16:0] rows_ext, cols_ext, base_ext;
    logic [16:0] vector_write_ext, column_ext;
    logic [16:0] remaining_rows, next_base, current_row;
    logic [16:0] last_column;
    logic last_lane, final_tile, command_legal;

    assign rows_ext = {1'b0, rows_q};
    assign cols_ext = {1'b0, cols_q};
    assign base_ext = {{(17-ROW_W){1'b0}}, tile_base};
    assign vector_write_ext = {{(17-COL_W){1'b0}}, vector_write_index};
    assign column_ext = {{(17-COL_W){1'b0}}, column_index};
    assign remaining_rows = rows_ext - base_ext;
    assign next_base = base_ext + 17'd16;
    assign current_row = base_ext + {13'b0, lane_index};
    assign last_column = cols_ext - 17'd1;
    assign last_lane = ({1'b0, lane_index} + 5'd1) == tile_height;
    assign final_tile = (base_ext + {12'b0, tile_height}) == rows_ext;
    assign command_legal = (cmd_rows != 16'd0) &&
                           (cmd_cols != 16'd0) &&
                           ({1'b0, cmd_rows} <= ROW_LIMIT) &&
                           ({1'b0, cmd_cols} <= COL_LIMIT);

    // Asynchronous scalar read: no extra memory-read stage.
    assign vector_value = vector_store[column_index];

    generate
        for (genvar g = 0; g < 16; g = g + 1) begin : g_lane
            // Both operands are signed INT8; the exact product fits INT16.
            assign product[g] = $signed(matrix_staging[g]) * $signed(vector_value);
            assign extended_product[g] = {{16{product[g][15]}}, product[g]};
            // Explicit 32-bit paths retain the low 32 bits of every addition.
            assign mac_value[g] = accumulator_result_bank[g] + extended_product[g];
            assign selected_bias[g] = bias_enable_q ? bias_staging[g] : 32'sd0;
            assign biased_value[g] = accumulator_result_bank[g] + selected_bias[g];
            assign final_value[g] = (relu_enable_q && biased_value[g][31])
                                 ? 32'sd0 : biased_value[g];
        end
    endgenerate

    always_comb begin
        cmd_ready = 1'b0;
        in_ready = 1'b0;
        out_valid = 1'b0;
        out_data = 32'sd0;
        out_last = 1'b0;
        done_valid = 1'b0;
        done_error = 1'b0;
        if (!rst) begin
            cmd_ready = (state == IDLE);
            in_ready = (state == LOAD_X) || (state == LOAD_BIAS) || (state == LOAD_W);
            if (state == EMIT) begin
                out_valid = 1'b1;
                out_data = accumulator_result_bank[lane_index];
                out_last = (current_row == (rows_ext - 17'd1));
            end
            if (state == DONE) begin
                done_valid = 1'b1;
                done_error = error_q;
            end
        end
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            rows_q <= 16'd0;
            cols_q <= 16'd0;
            bias_enable_q <= 1'b0;
            relu_enable_q <= 1'b0;
            error_q <= 1'b0;
            vector_write_index <= '0;
            column_index <= '0;
            tile_base <= '0;
            tile_height <= 5'd0;
            lane_index <= 4'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        rows_q <= cmd_rows;
                        cols_q <= cmd_cols;
                        bias_enable_q <= cmd_bias_enable;
                        relu_enable_q <= cmd_relu_enable;
                        error_q <= !command_legal;
                        vector_write_index <= '0;
                        column_index <= '0;
                        tile_base <= '0;
                        tile_height <= 5'd0;
                        lane_index <= 4'd0;
                        if (command_legal)
                            state <= LOAD_X;
                        else
                            state <= DONE;
                    end
                end

                LOAD_X: begin
                    if (in_valid && in_ready) begin
                        vector_store[vector_write_index] <= $signed(in_data[7:0]);
                        if (vector_write_ext == last_column) begin
                            state <= TILE_INIT;
                        end else begin
                            vector_write_index <= vector_write_index + COL_W'(1);
                        end
                    end
                end

                TILE_INIT: begin
                    for (int i = 0; i < 16; i = i + 1)
                        accumulator_result_bank[i] <= 32'sd0;
                    column_index <= '0;
                    lane_index <= 4'd0;
                    if (remaining_rows > 17'd16)
                        tile_height <= 5'd16;
                    else
                        tile_height <= remaining_rows[4:0];
                    if (bias_enable_q)
                        state <= LOAD_BIAS;
                    else
                        state <= LOAD_W;
                end

                LOAD_BIAS: begin
                    if (in_valid && in_ready) begin
                        bias_staging[lane_index] <= $signed(in_data);
                        if (last_lane) begin
                            lane_index <= 4'd0;
                            state <= LOAD_W;
                        end else begin
                            lane_index <= lane_index + 4'd1;
                        end
                    end
                end

                LOAD_W: begin
                    if (in_valid && in_ready) begin
                        matrix_staging[lane_index] <= $signed(in_data[7:0]);
                        if (last_lane) begin
                            lane_index <= 4'd0;
                            state <= MAC;
                        end else begin
                            lane_index <= lane_index + 4'd1;
                        end
                    end
                end

                MAC: begin
                    for (int i = 0; i < 16; i = i + 1) begin
                        if (5'(i) < tile_height)
                            accumulator_result_bank[i] <= mac_value[i];
                    end
                    if (column_ext == last_column) begin
                        state <= FINALIZE;
                    end else begin
                        column_index <= column_index + COL_W'(1);
                        state <= LOAD_W;
                    end
                end

                FINALIZE: begin
                    for (int i = 0; i < 16; i = i + 1) begin
                        if (5'(i) < tile_height)
                            accumulator_result_bank[i] <= final_value[i];
                    end
                    lane_index <= 4'd0;
                    state <= EMIT;
                end

                EMIT: begin
                    if (out_valid && out_ready) begin
                        if (last_lane) begin
                            lane_index <= 4'd0;
                            if (final_tile) begin
                                state <= DONE;
                            end else begin
                                // Narrow only after establishing another tile exists.
                                tile_base <= next_base[ROW_W-1:0];
                                state <= TILE_INIT;
                            end
                        end else begin
                            lane_index <= lane_index + 4'd1;
                        end
                    end
                end

                DONE: begin
                    if (done_valid && done_ready)
                        state <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end
endmodule
