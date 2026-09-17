module tiled_int8_fc #(
    parameter integer MAX_M = 64,
    parameter integer MAX_N = 64,
    parameter integer MAX_K = 64
) (
    input  logic clk,
    input  logic rst,
    input  logic cmd_valid,
    output logic cmd_ready,
    input  logic [((MAX_M < 2) ? 1 : $clog2(MAX_M+1))-1:0] cmd_m,
    input  logic [((MAX_N < 2) ? 1 : $clog2(MAX_N+1))-1:0] cmd_n,
    input  logic [((MAX_K < 2) ? 1 : $clog2(MAX_K+1))-1:0] cmd_k,
    input  logic in_valid,
    output logic in_ready,
    input  logic [31:0] in_data,
    output logic out_valid,
    input  logic out_ready,
    output logic signed [31:0] out_data,
    output logic out_last,
    output logic busy,
    output logic done,
    output logic error
);
    localparam integer MW = (MAX_M < 2) ? 1 : $clog2(MAX_M+1);
    localparam integer NW = (MAX_N < 2) ? 1 : $clog2(MAX_N+1);
    localparam integer KW = (MAX_K < 2) ? 1 : $clog2(MAX_K+1);
    localparam integer AD = MAX_M*MAX_K;
    localparam integer WD = MAX_K*MAX_N;
    localparam integer AIW = (AD < 2) ? 1 : $clog2(AD+1);
    localparam integer WIW = (WD < 2) ? 1 : $clog2(WD+1);
    localparam integer AAW = (AD < 2) ? 1 : $clog2(AD);
    localparam integer WAW = (WD < 2) ? 1 : $clog2(WD);
    localparam integer BAW = (MAX_N < 2) ? 1 : $clog2(MAX_N);
    localparam integer TMW = (((MAX_M+7)/8) < 2) ? 1 : $clog2((MAX_M+7)/8);
    localparam integer TNW = (((MAX_N+7)/8) < 2) ? 1 : $clog2((MAX_N+7)/8);

    // Static elaboration diagnostic; no functional initialization is used.
    generate
        if ((MAX_M < 1) || (MAX_M > 1024) ||
            (MAX_N < 1) || (MAX_N > 1024) ||
            (MAX_K < 1) || (MAX_K > 1024)) begin : g_illegal_parameters
            $error("MAX_M, MAX_N and MAX_K must each be in 1..1024");
        end
    endgenerate

    typedef enum logic [3:0] {
        IDLE, LOAD_A, LOAD_W, LOAD_B, CLEAR_TILE,
        GATHER_REQ, GATHER_CAPTURE, MAC, BIAS_REQ, FINALIZE, EMIT
    } state_t;
    state_t state;

    logic [MW-1:0] m_reg;
    logic [NW-1:0] n_reg;
    logic [KW-1:0] k_reg, k_index;
    logic [AIW-1:0] a_index;
    logic [WIW-1:0] w_index;
    logic [NW-1:0] b_index;
    logic [TMW-1:0] tm;
    logic [TNW-1:0] tn;
    logic [2:0] lane, out_row, out_col;
    logic valid_reg, done_reg, error_reg;

    logic signed [7:0] activation_memory [0:AD-1];
    logic signed [7:0] weight_memory [0:WD-1];
    logic signed [31:0] bias_memory [0:MAX_N-1];
    logic signed [7:0] a_read_data, w_read_data;
    logic signed [31:0] b_read_data;
    logic signed [7:0] activation_lanes [0:7];
    logic signed [7:0] weight_lanes [0:7];
    logic signed [31:0] accumulator_tile [0:7][0:7];

    logic [31:0] m_u, n_u, k_u, ki_u, lane_u;
    logic [31:0] m_base, n_base, a_count, w_count;
    logic [31:0] gather_row, gather_col;
    logic [3:0] rows_in_tile, cols_in_tile;
    logic a_lane_valid, w_lane_valid;
    logic tile_element_last, job_element_last;
    logic [AAW-1:0] a_read_addr;
    logic [WAW-1:0] w_read_addr;
    logic [BAW-1:0] b_read_addr;
    logic signed [32:0] bias_sum_wide;
    logic signed [31:0] biased_value;

    assign cmd_ready = !rst && (state == IDLE);
    assign in_ready = !rst && ((state == LOAD_A) || (state == LOAD_W) || (state == LOAD_B));
    assign out_valid = !rst && valid_reg;
    assign busy = !rst && (state != IDLE);
    assign done = !rst && done_reg;
    assign error = !rst && error_reg;

    always_comb begin
        m_u = 32'(m_reg);
        n_u = 32'(n_reg);
        k_u = 32'(k_reg);
        ki_u = 32'(k_index);
        lane_u = 32'(lane);
        m_base = 32'(tm) * 32'd8;
        n_base = 32'(tn) * 32'd8;
        a_count = m_u * k_u;
        w_count = k_u * n_u;
        gather_row = m_base + lane_u;
        gather_col = n_base + lane_u;
        a_lane_valid = gather_row < m_u;
        w_lane_valid = gather_col < n_u;
        rows_in_tile = 4'd0;
        cols_in_tile = 4'd0;
        if (m_u > m_base)
            rows_in_tile = ((m_u-m_base) >= 32'd8) ? 4'd8 : 4'(m_u-m_base);
        if (n_u > n_base)
            cols_in_tile = ((n_u-n_base) >= 32'd8) ? 4'd8 : 4'(n_u-n_base);
        a_read_addr = AAW'(gather_row*k_u + ki_u);
        w_read_addr = WAW'(ki_u*n_u + gather_col);
        b_read_addr = BAW'(n_base + 32'(out_col));
        tile_element_last = ((32'(out_row)+32'd1) == 32'(rows_in_tile)) &&
                            ((32'(out_col)+32'd1) == 32'(cols_in_tile));
        job_element_last = tile_element_last &&
                           ((m_base+32'd8) >= m_u) &&
                           ((n_base+32'd8) >= n_u);
        bias_sum_wide = $signed({accumulator_tile[out_row][out_col][31],
                                accumulator_tile[out_row][out_col]}) +
                        $signed({b_read_data[31], b_read_data});
        biased_value = $signed(bias_sum_wide[31:0]);
    end

    // Independent single synchronous ports. RAM and read outputs are not reset.
    always_ff @(posedge clk) begin
        if (!rst) begin
            if ((state == LOAD_A) && in_valid && in_ready)
                activation_memory[AAW'(a_index)] <= $signed(in_data[7:0]);
            else if ((state == GATHER_REQ) && a_lane_valid)
                a_read_data <= activation_memory[a_read_addr];
        end
    end
    always_ff @(posedge clk) begin
        if (!rst) begin
            if ((state == LOAD_W) && in_valid && in_ready)
                weight_memory[WAW'(w_index)] <= $signed(in_data[7:0]);
            else if ((state == GATHER_REQ) && w_lane_valid)
                w_read_data <= weight_memory[w_read_addr];
        end
    end
    always_ff @(posedge clk) begin
        if (!rst) begin
            if ((state == LOAD_B) && in_valid && in_ready)
                bias_memory[BAW'(b_index)] <= $signed(in_data);
            else if (state == BIAS_REQ)
                b_read_data <= bias_memory[b_read_addr];
        end
    end

    always_ff @(posedge clk) begin
        if (!rst && (state == GATHER_CAPTURE)) begin
            activation_lanes[lane] <= a_lane_valid ? a_read_data : 8'sd0;
            weight_lanes[lane] <= w_lane_valid ? w_read_data : 8'sd0;
        end
    end

    // All 64 cells update together. Explicit 33-bit sums expose wrap32 truncation.
    generate
        for (genvar i = 0; i < 8; i = i+1) begin : g_row
            for (genvar j = 0; j < 8; j = j+1) begin : g_col
                wire signed [15:0] product;
                wire signed [32:0] sum_wide;
                assign product = $signed(activation_lanes[i]) * $signed(weight_lanes[j]);
                assign sum_wide = $signed({accumulator_tile[i][j][31], accumulator_tile[i][j]}) +
                                  $signed({{17{product[15]}}, product});
                always_ff @(posedge clk) begin
                    if (!rst) begin
                        if (state == CLEAR_TILE)
                            accumulator_tile[i][j] <= 32'sd0;
                        else if (state == MAC)
                            accumulator_tile[i][j] <= $signed(sum_wide[31:0]);
                    end
                end
            end
        end
    endgenerate

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            m_reg <= '0;
            n_reg <= '0;
            k_reg <= '0;
            k_index <= '0;
            a_index <= '0;
            w_index <= '0;
            b_index <= '0;
            tm <= '0;
            tn <= '0;
            lane <= '0;
            out_row <= '0;
            out_col <= '0;
            valid_reg <= 1'b0;
            out_last <= 1'b0;
            out_data <= 32'sd0;
            done_reg <= 1'b0;
            error_reg <= 1'b0;
        end else begin
            done_reg <= 1'b0;
            error_reg <= 1'b0;
            case (state)
                IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        if ((cmd_m == '0) || (cmd_n == '0) || (cmd_k == '0) ||
                            (32'(cmd_m) > $unsigned(MAX_M)) ||
                            (32'(cmd_n) > $unsigned(MAX_N)) ||
                            (32'(cmd_k) > $unsigned(MAX_K))) begin
                            error_reg <= 1'b1;
                        end else begin
                            m_reg <= cmd_m;
                            n_reg <= cmd_n;
                            k_reg <= cmd_k;
                            a_index <= '0;
                            w_index <= '0;
                            b_index <= '0;
                            tm <= '0;
                            tn <= '0;
                            k_index <= '0;
                            lane <= '0;
                            out_row <= '0;
                            out_col <= '0;
                            state <= LOAD_A;
                        end
                    end
                end
                LOAD_A: begin
                    if (in_valid && in_ready) begin
                        if (32'(a_index) == (a_count-32'd1))
                            state <= LOAD_W;
                        else
                            a_index <= a_index + AIW'(1);
                    end
                end
                LOAD_W: begin
                    if (in_valid && in_ready) begin
                        if (32'(w_index) == (w_count-32'd1))
                            state <= LOAD_B;
                        else
                            w_index <= w_index + WIW'(1);
                    end
                end
                LOAD_B: begin
                    if (in_valid && in_ready) begin
                        if (32'(b_index) == (n_u-32'd1))
                            state <= CLEAR_TILE;
                        else
                            b_index <= b_index + NW'(1);
                    end
                end
                CLEAR_TILE: begin
                    k_index <= '0;
                    lane <= '0;
                    out_row <= '0;
                    out_col <= '0;
                    state <= GATHER_REQ;
                end
                GATHER_REQ: state <= GATHER_CAPTURE;
                GATHER_CAPTURE: begin
                    if (lane == 3'd7)
                        state <= MAC;
                    else begin
                        lane <= lane + 3'd1;
                        state <= GATHER_REQ;
                    end
                end
                MAC: begin
                    if (ki_u == (k_u-32'd1))
                        state <= BIAS_REQ;
                    else begin
                        k_index <= k_index + KW'(1);
                        lane <= '0;
                        state <= GATHER_REQ;
                    end
                end
                BIAS_REQ: state <= FINALIZE;
                FINALIZE: begin
                    out_data <= biased_value[31] ? 32'sd0 : biased_value;
                    out_last <= job_element_last;
                    valid_reg <= 1'b1;
                    state <= EMIT;
                end
                EMIT: begin
                    if (out_valid && out_ready) begin
                        valid_reg <= 1'b0;
                        if (out_last) begin
                            done_reg <= 1'b1;
                            state <= IDLE;
                        end else if (tile_element_last) begin
                            if ((n_base+32'd8) < n_u)
                                tn <= tn + TNW'(1);
                            else begin
                                tn <= '0;
                                tm <= tm + TMW'(1);
                            end
                            state <= CLEAR_TILE;
                        end else begin
                            if ((32'(out_col)+32'd1) < 32'(cols_in_tile))
                                out_col <= out_col + 3'd1;
                            else begin
                                out_col <= '0;
                                out_row <= out_row + 3'd1;
                            end
                            state <= BIAS_REQ;
                        end
                    end
                end
                default: begin
                    state <= IDLE;
                    valid_reg <= 1'b0;
                end
            endcase
        end
    end
endmodule
