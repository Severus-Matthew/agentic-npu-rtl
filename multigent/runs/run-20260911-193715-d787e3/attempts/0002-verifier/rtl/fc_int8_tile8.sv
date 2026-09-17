module fc_int8_tile8 #(
    parameter int unsigned MAX_M = 64,
    parameter int unsigned MAX_N = 64,
    parameter int unsigned MAX_K = 64
) (
    input  logic clk,
    input  logic rst,
    input  logic cmd_valid,
    output logic cmd_ready,
    input  logic [((($clog2(MAX_M+1)) < 1) ? 1 : $clog2(MAX_M+1))-1:0] cmd_m,
    input  logic [((($clog2(MAX_N+1)) < 1) ? 1 : $clog2(MAX_N+1))-1:0] cmd_n,
    input  logic [((($clog2(MAX_K+1)) < 1) ? 1 : $clog2(MAX_K+1))-1:0] cmd_k,
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
    localparam int unsigned MW = ($clog2(MAX_M+1) < 1) ? 1 : $clog2(MAX_M+1);
    localparam int unsigned NW = ($clog2(MAX_N+1) < 1) ? 1 : $clog2(MAX_N+1);
    localparam int unsigned KW = ($clog2(MAX_K+1) < 1) ? 1 : $clog2(MAX_K+1);
    localparam int unsigned MT = (MAX_M + 7) / 8;
    localparam int unsigned NT = (MAX_N + 7) / 8;
    localparam int unsigned TRW = ($clog2(MT) < 1) ? 1 : $clog2(MT);
    localparam int unsigned TCW = ($clog2(NT) < 1) ? 1 : $clog2(NT);
    localparam int unsigned A_DEPTH = MT * MAX_K;
    localparam int unsigned B_DEPTH = MAX_K * NT;
    localparam int unsigned AAW = ($clog2(A_DEPTH) < 1) ? 1 : $clog2(A_DEPTH);
    localparam int unsigned BAW = ($clog2(B_DEPTH) < 1) ? 1 : $clog2(B_DEPTH);
    localparam int unsigned BIAS_AW = ($clog2(MAX_N) < 1) ? 1 : $clog2(MAX_N);

    typedef enum logic [2:0] {
        IDLE, LOAD_A, LOAD_B, LOAD_BIAS, INIT, MAC, EMIT
    } state_t;
    state_t state;

    logic [MW-1:0] dim_m, load_a_m;
    logic [NW-1:0] dim_n, load_b_n, load_bias_n;
    logic [KW-1:0] dim_k, load_a_k, load_b_k, mac_k;
    logic [TRW-1:0] tr;
    logic [TCW-1:0] tc;
    logic [2:0] emit_i, emit_j;
    logic [3:0] extent_r, extent_c;
    logic done_q, error_q;
    logic command_legal;

    logic signed [7:0] activation_banks [0:7][0:A_DEPTH-1];
    logic signed [7:0] weight_banks [0:7][0:B_DEPTH-1];
    logic signed [31:0] bias_store [0:MAX_N-1];

    logic [31:0] base_r, base_c, current_r, current_c;
    logic [31:0] a_wr_calc, b_wr_calc, a_rd_calc, b_rd_calc;
    logic [AAW-1:0] a_wr_addr, a_rd_addr;
    logic [BAW-1:0] b_wr_addr, b_rd_addr;
    logic [BIAS_AW-1:0] bias_wr_addr, bias_rd_addr;
    logic [2:0] a_wr_bank, b_wr_bank;
    logic tile_active;
    logic array_clear, array_step;
    logic [63:0] act_lanes, weight_lanes;
    logic [7:0] row_mask, col_mask;
    logic [2:0] read_row, read_col;
    logic signed [31:0] tile_sum;
    logic signed [32:0] biased_wide;
    logic signed [31:0] biased_wrap;

    assign cmd_ready = !rst && (state == IDLE);
    assign in_ready = !rst && ((state == LOAD_A) || (state == LOAD_B) || (state == LOAD_BIAS));
    assign out_valid = !rst && (state == EMIT);
    assign busy = !rst && (state != IDLE);
    assign done = !rst && done_q;
    assign error = !rst && error_q;
    assign command_legal = (32'(cmd_m) >= 32'd1) && (32'(cmd_m) <= MAX_M) &&
                           (32'(cmd_n) >= 32'd1) && (32'(cmd_n) <= MAX_N) &&
                           (32'(cmd_k) >= 32'd1) && (32'(cmd_k) <= MAX_K);

    // All base/address arithmetic is unsigned and widened before operations.
    assign base_r = 32'(tr) << 3;
    assign base_c = 32'(tc) << 3;
    assign current_r = base_r + 32'(emit_i);
    assign current_c = base_c + 32'(emit_j);
    assign a_wr_calc = (32'(load_a_m) >> 3) * MAX_K + 32'(load_a_k);
    assign b_wr_calc = 32'(load_b_k) * NT + (32'(load_b_n) >> 3);
    assign a_rd_calc = 32'(tr) * MAX_K + 32'(mac_k);
    assign b_rd_calc = 32'(mac_k) * NT + 32'(tc);
    assign a_wr_addr = AAW'(a_wr_calc);
    assign b_wr_addr = BAW'(b_wr_calc);
    assign a_rd_addr = AAW'(a_rd_calc);
    assign b_rd_addr = BAW'(b_rd_calc);
    assign a_wr_bank = 3'(32'(load_a_m) & 32'd7);
    assign b_wr_bank = 3'(32'(load_b_n) & 32'd7);
    assign bias_wr_addr = BIAS_AW'(load_bias_n);
    assign bias_rd_addr = BIAS_AW'(current_c);

    assign tile_active = !rst && ((state == INIT) || (state == MAC) || (state == EMIT));
    assign array_clear = !rst && (state == INIT);
    assign array_step = !rst && (state == MAC);
    assign read_row = out_valid ? emit_i : 3'd0;
    assign read_col = out_valid ? emit_j : 3'd0;
    assign out_last = out_valid &&
                      ((current_r + 32'd1) == 32'(dim_m)) &&
                      ((current_c + 32'd1) == 32'(dim_n));

    always_comb begin
        extent_r = 4'd0;
        extent_c = 4'd0;
        if (tile_active) begin
            if ((32'(dim_m) - base_r) >= 32'd8)
                extent_r = 4'd8;
            else
                extent_r = 4'(32'(dim_m) - base_r);
            if ((32'(dim_n) - base_c) >= 32'd8)
                extent_c = 4'd8;
            else
                extent_c = 4'(32'(dim_n) - base_c);
        end
    end

    always_comb begin
        row_mask = 8'd0;
        col_mask = 8'd0;
        act_lanes = 64'd0;
        weight_lanes = 64'd0;
        for (int unsigned lane = 0; lane < 8; lane = lane + 1) begin
            if (tile_active) begin
                row_mask[lane] = (lane < 32'(extent_r));
                col_mask[lane] = (lane < 32'(extent_c));
            end
            // Each loop iteration accesses a distinct asynchronous-read bank.
            // Invalid lanes do not read unwritten padding.
            if (array_step && row_mask[lane])
                act_lanes[8*lane +: 8] = activation_banks[lane][a_rd_addr];
            if (array_step && col_mask[lane])
                weight_lanes[8*lane +: 8] = weight_banks[lane][b_rd_addr];
        end
    end

    // Separate synchronous write ports; memories are deliberately not reset.
    generate
        for (genvar bank = 0; bank < 8; bank = bank + 1) begin : g_operand_bank
            always_ff @(posedge clk) begin
                if (!rst && in_valid && in_ready && (state == LOAD_A) &&
                    (a_wr_bank == 3'(bank)))
                    activation_banks[bank][a_wr_addr] <= $signed(in_data[7:0]);
                if (!rst && in_valid && in_ready && (state == LOAD_B) &&
                    (b_wr_bank == 3'(bank)))
                    weight_banks[bank][b_wr_addr] <= $signed(in_data[7:0]);
            end
        end
    endgenerate

    always_ff @(posedge clk) begin
        if (!rst && in_valid && in_ready && (state == LOAD_BIAS))
            bias_store[bias_wr_addr] <= $signed(in_data);
    end

    mac_tile8x8 u_mac_tile8x8 (
        .clk(clk),
        .rst(rst),
        .clear(array_clear),
        .step(array_step),
        .act_lanes(act_lanes),
        .weight_lanes(weight_lanes),
        .row_mask(row_mask),
        .col_mask(col_mask),
        .read_row(read_row),
        .read_col(read_col),
        .sum(tile_sum)
    );

    // Sign-extend both INT32 operands, explicitly wrap, then apply signed ReLU.
    always_comb begin
        biased_wide = 33'sd0;
        biased_wrap = 32'sd0;
        out_data = 32'sd0;
        if (out_valid) begin
            biased_wide = $signed({tile_sum[31], tile_sum}) +
                          $signed({bias_store[bias_rd_addr][31], bias_store[bias_rd_addr]});
            biased_wrap = $signed(biased_wide[31:0]);
            if (!biased_wrap[31])
                out_data = biased_wrap;
        end
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            dim_m <= '0;
            dim_n <= '0;
            dim_k <= '0;
            load_a_m <= '0;
            load_a_k <= '0;
            load_b_k <= '0;
            load_b_n <= '0;
            load_bias_n <= '0;
            tr <= '0;
            tc <= '0;
            mac_k <= '0;
            emit_i <= '0;
            emit_j <= '0;
            done_q <= 1'b0;
            error_q <= 1'b0;
        end else begin
            done_q <= 1'b0;
            error_q <= 1'b0;
            case (state)
                IDLE: begin
                    if (cmd_valid && cmd_ready) begin
                        if (command_legal) begin
                            dim_m <= cmd_m;
                            dim_n <= cmd_n;
                            dim_k <= cmd_k;
                            load_a_m <= '0;
                            load_a_k <= '0;
                            load_b_k <= '0;
                            load_b_n <= '0;
                            load_bias_n <= '0;
                            tr <= '0;
                            tc <= '0;
                            mac_k <= '0;
                            emit_i <= '0;
                            emit_j <= '0;
                            state <= LOAD_A;
                        end else begin
                            error_q <= 1'b1;
                        end
                    end
                end
                LOAD_A: begin
                    if (in_valid && in_ready) begin
                        if ((32'(load_a_k) + 32'd1) == 32'(dim_k)) begin
                            load_a_k <= '0;
                            if ((32'(load_a_m) + 32'd1) == 32'(dim_m)) begin
                                state <= LOAD_B;
                            end else begin
                                load_a_m <= load_a_m + MW'(1);
                            end
                        end else begin
                            load_a_k <= load_a_k + KW'(1);
                        end
                    end
                end
                LOAD_B: begin
                    if (in_valid && in_ready) begin
                        if ((32'(load_b_n) + 32'd1) == 32'(dim_n)) begin
                            load_b_n <= '0;
                            if ((32'(load_b_k) + 32'd1) == 32'(dim_k)) begin
                                state <= LOAD_BIAS;
                            end else begin
                                load_b_k <= load_b_k + KW'(1);
                            end
                        end else begin
                            load_b_n <= load_b_n + NW'(1);
                        end
                    end
                end
                LOAD_BIAS: begin
                    if (in_valid && in_ready) begin
                        if ((32'(load_bias_n) + 32'd1) == 32'(dim_n)) begin
                            state <= INIT;
                        end else begin
                            load_bias_n <= load_bias_n + NW'(1);
                        end
                    end
                end
                INIT: begin
                    // The child clears on this edge; MAC begins next cycle.
                    mac_k <= '0;
                    emit_i <= '0;
                    emit_j <= '0;
                    state <= MAC;
                end
                MAC: begin
                    if ((32'(mac_k) + 32'd1) == 32'(dim_k)) begin
                        state <= EMIT;
                    end else begin
                        mac_k <= mac_k + KW'(1);
                    end
                end
                EMIT: begin
                    if (out_valid && out_ready) begin
                        if ((32'(emit_j) + 32'd1) == 32'(extent_c)) begin
                            emit_j <= '0;
                            if ((32'(emit_i) + 32'd1) == 32'(extent_r)) begin
                                emit_i <= '0;
                                if (out_last) begin
                                    state <= IDLE;
                                    done_q <= 1'b1;
                                end else begin
                                    if ((base_c + 32'd8) >= 32'(dim_n)) begin
                                        tc <= '0;
                                        tr <= tr + TRW'(1);
                                    end else begin
                                        tc <= tc + TCW'(1);
                                    end
                                    state <= INIT;
                                end
                            end else begin
                                emit_i <= emit_i + 3'd1;
                            end
                        end else begin
                            emit_j <= emit_j + 3'd1;
                        end
                    end
                end
                default: begin
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
