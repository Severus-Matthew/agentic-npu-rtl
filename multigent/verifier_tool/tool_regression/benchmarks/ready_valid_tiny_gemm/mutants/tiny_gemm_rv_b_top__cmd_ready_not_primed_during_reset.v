// Minimal, hand-authored, contract-driven reference RTL for the ready_valid
// protocol profile plus a bias+affine_quantize GEMM operation (variant B).
//
// Y = quantize(sum_{k=0}^{K-1} A[k]*B[k] + bias), M=1, N=1, K=4.
// quantize: q = clamp(round_nearest_even(value * 1 / 2^2) + (-1), -128, 127)
// (scale_multiplier=1, scale_shift=2, zero_point=-1, rounding=nearest_ties_to_even,
// saturation=clamp, granularity=per_tensor, output data_type=s8).
// Unlike variant A there is deliberately no relu stage before the quantizer,
// so the pre-quantize value can be either sign and both negative_saturation
// and positive_saturation are reachable (confirmed empirically: chaining
// relu directly before affine_quantize makes negative_saturation provably
// unreachable, since relu's output is always >= 0 and zero_point must itself
// be representable in the output dtype -- verifier_tool's own
// generate_canonical_stimulus_for_bin already detects that specific case and
// raises "unreachable", so it is not required there; this variant exists so
// negative_saturation has a contract where it genuinely is required).
//
// lifecycle_policy: job_acceptance=valid_ready_handshake, completion_style=pulse,
// completion_timing=next_cycle_after_retirement, error_style=pulse,
// error_timing=next_cycle_after_error_event, reset_behavior=abort_inflight.
module tiny_gemm_rv_b_top #(
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
    // regardless of summation grouping (modular addition is associative).
    wire signed [15:0] acc_sum = products[0] + products[1] + products[2] + products[3];
    wire signed [15:0] biased  = acc_sum + bias_reg;

    // affine_quantize: scale_multiplier=1, scale_shift=2, zero_point=-1,
    // rounding=nearest_ties_to_even, saturation=clamp, output s8.
    // round_nearest_even(biased / 4): quotient = biased >>> 2 (arithmetic
    // shift, correct floor-toward-negative-infinity for a right shift of a
    // two's-complement value), remainder = biased mod 4 in [0,3] taken from
    // the low two bits reinterpreted as the *distance above* that floored
    // quotient (always non-negative for a floor division).
    wire signed [15:0] quot_floor = biased >>> 2;
    wire [1:0]         rem        = biased[1:0];
    wire               round_up   = (rem == 2'b11) || (rem == 2'b10 && quot_floor[0]);
    wire signed [15:0] rounded    = quot_floor + {15'b0, round_up};
    wire signed [15:0] q_full     = rounded + (-16'sd1);
    wire signed [15:0] q_clamped  = (q_full > 16'sd127)  ? 16'sd127
                                   : (q_full < -16'sd128) ? -16'sd128
                                   : q_full;

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            cnt        <= 3'd0;
            cmd_ready  <= 1'b0;
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
                    y_data  <= q_clamped[7:0];
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
