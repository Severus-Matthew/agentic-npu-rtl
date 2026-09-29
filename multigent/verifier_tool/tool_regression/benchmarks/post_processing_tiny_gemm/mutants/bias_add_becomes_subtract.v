// Minimal, hand-authored, contract-driven reference RTL for the ready_valid
// protocol profile plus a full bias+affine_quantize+ReLU GEMM post-processing
// DAG (M=1, N=1, K=4). Directly adapted from
// ../../ready_valid_tiny_gemm/rtl_a/tiny_gemm_rv_a_top.v (same FSM, same
// 5-channel ready/valid protocol), replacing that fixture's plain
// bias+ReLU final stage with bias -> affine_quantize -> ReLU, in that order
// (quantize BEFORE relu, not after) so a negative biased accumulator can
// still reach affine_quantize's negative_saturation bin -- relu after
// quantize still guarantees the final s8 result is non-negative.
//
// Y = relu(quantize(sum_{k=0}^{K-1} A[k]*B[k] + bias)).
// product_data_type=s16 (exact), accumulator_data_type=s16
// (reduction_conversion/bias_conversion=wrap_twos_complement_after_*  -- a
// plain 16-bit signed adder wraps mod 2^16 for free, bit-identical to
// wrap-after-each-add by associativity of modular addition).
// affine_quantize: scale_multiplier=1, scale_shift=4, zero_point=5,
// rounding=nearest_ties_to_even, saturation=clamp, result_data_type=s8.
//
// lifecycle_policy: job_acceptance=valid_ready_handshake, completion_style=pulse,
// completion_timing=next_cycle_after_retirement, error_style=pulse,
// error_timing=next_cycle_after_error_event, reset_behavior=abort_inflight.
module post_processing_tiny_gemm_top #(
    parameter K = 4
)(
    input  wire        clk,
    input  wire        rst_n,

    input  wire        cmd_valid,
    output reg         cmd_ready,
    input  wire        cmd_op,          // legal value: 1'b1 (start)

    input  wire        a_valid,
    output reg         a_ready,
    input  wire signed [7:0] a_data,

    input  wire        b_valid,
    output reg         b_ready,
    input  wire signed [7:0] b_data,

    input  wire        bias_valid,
    output reg         bias_ready,
    input  wire signed [15:0] bias_data,

    output reg         y_valid,
    input  wire        y_ready,
    output reg signed [7:0] y_data,

    output reg         busy,
    output reg         done,
    output reg         err
);
    localparam S_IDLE = 3'd0, S_LOAD_A = 3'd1, S_LOAD_B = 3'd2,
               S_LOAD_BIAS = 3'd3, S_OUTPUT = 3'd4;

    reg [2:0] state;
    reg [2:0] cnt;
    reg signed [7:0] a_mem [0:K-1];
    reg signed [7:0] b_mem [0:K-1];
    reg signed [15:0] bias_reg;

    wire signed [15:0] products [0:K-1];
    genvar gi;
    generate
        for (gi = 0; gi < K; gi = gi + 1) begin : PROD
            assign products[gi] = a_mem[gi] * b_mem[gi];
        end
    endgenerate

    // Natural 16-bit wraparound: matches wrap_twos_complement_after_each_add
    // (accumulation) and wrap_twos_complement_after_add (bias) regardless of
    // summation grouping (modular addition is associative).
    wire signed [15:0] acc_sum = products[0] + products[1] + products[2] + products[3];
    wire signed [15:0] biased  = acc_sum - bias_reg;

    // affine_quantize(biased): scale_multiplier=1, scale_shift=4 (divide by
    // 16), zero_point=5, rounding=nearest_ties_to_even, then clamp to s8.
    // Bit-exact match to canonical.py::_round_divide_nearest_even for a
    // positive multiplier and a power-of-two denominator: quotient/remainder
    // come from a plain unsigned shift/mask of the magnitude, and the
    // round-to-even tie-break only ever looks at the quotient's own LSB.
    wire               biased_neg   = biased[15];
    wire [15:0]        biased_abs   = biased_neg ? (~biased + 16'd1) : biased;
    wire [11:0]        quantize_quotient  = biased_abs[15:4];
    wire [3:0]         quantize_remainder = biased_abs[3:0];
    wire               quantize_round_up  = (quantize_remainder > 4'd8)
                                           || (quantize_remainder == 4'd8 && quantize_quotient[0]);
    wire [12:0]        scaled_magnitude   = quantize_quotient + quantize_round_up;
    wire signed [13:0] scaled             = biased_neg ? -$signed({1'b0, scaled_magnitude})
                                                        : $signed({1'b0, scaled_magnitude});
    wire signed [13:0] raw_quantized      = scaled + 14'sd5;
    wire signed [7:0]  quantized          = (raw_quantized > 14'sd127)    ? 8'sd127
                                           : (raw_quantized < -14'sd128)  ? -8'sd128
                                           : raw_quantized[7:0];
    // relu applied AFTER quantize (not before): clamps the final s8 result
    // to be non-negative without ever touching affine_quantize's own
    // negative_saturation reachability.
    wire signed [7:0]  post_processed     = quantized[7] ? 8'sd0 : quantized;

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            cnt        <= 3'd0;
            // Primed to the S_IDLE steady-state value so a command can be
            // accepted on the very first post-reset accepting edge, not one
            // cycle later.
            cmd_ready  <= 1'b1;
            a_ready    <= 1'b0;
            b_ready    <= 1'b0;
            bias_ready <= 1'b0;
            y_valid    <= 1'b0;
            busy       <= 1'b0;
            done       <= 1'b0;
            err        <= 1'b0;
        end else begin
            done <= 1'b0;
            err  <= 1'b0;
            case (state)
                S_IDLE: begin
                    y_valid    <= 1'b0;
                    cmd_ready  <= 1'b1;
                    a_ready    <= 1'b0;
                    b_ready    <= 1'b0;
                    bias_ready <= 1'b0;
                    busy       <= 1'b0;
                    if (cmd_valid && cmd_ready) begin
                        if (cmd_op == 1'b1) begin
                            busy      <= 1'b1;
                            cmd_ready <= 1'b0;
                            a_ready   <= 1'b1;
                            cnt       <= 3'd0;
                            state     <= S_LOAD_A;
                        end else begin
                            err <= 1'b1;
                        end
                    end
                end
                S_LOAD_A: begin
                    if (a_valid && a_ready) begin
                        a_mem[cnt] <= a_data;
                        if (cnt == K-1) begin
                            a_ready <= 1'b0;
                            b_ready <= 1'b1;
                            cnt     <= 3'd0;
                            state   <= S_LOAD_B;
                        end else begin
                            cnt <= cnt + 3'd1;
                        end
                    end
                end
                S_LOAD_B: begin
                    if (b_valid && b_ready) begin
                        b_mem[cnt] <= b_data;
                        if (cnt == K-1) begin
                            b_ready    <= 1'b0;
                            bias_ready <= 1'b1;
                            state      <= S_LOAD_BIAS;
                        end else begin
                            cnt <= cnt + 3'd1;
                        end
                    end
                end
                S_LOAD_BIAS: begin
                    if (bias_valid && bias_ready) begin
                        bias_reg   <= bias_data;
                        bias_ready <= 1'b0;
                        state      <= S_OUTPUT;
                    end
                end
                S_OUTPUT: begin
                    y_valid <= 1'b1;
                    y_data  <= post_processed;
                    if (y_valid && y_ready) begin
                        y_valid <= 1'b0;
                        busy    <= 1'b0;
                        done    <= 1'b1;
                        state   <= S_IDLE;
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
