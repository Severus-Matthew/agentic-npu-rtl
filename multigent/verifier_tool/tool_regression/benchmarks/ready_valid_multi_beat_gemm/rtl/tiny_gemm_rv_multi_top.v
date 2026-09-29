// Minimal, hand-authored, contract-driven reference RTL for the ready_valid
// protocol profile plus a bias+ReLU GEMM operation, M=1/K=4/N=2 -- the
// sibling of ready_valid_tiny_gemm's variant A with a genuinely two-beat Y
// output (N=2 instead of N=1) and a sticky (not pulsed) error indication.
//
// Y[n] = relu(sum_{k=0}^{K-1} A[k]*B[k,n] + bias[n]), M=1, N=2, K=4.
// Same s16 product/accumulator/bias/result semantics as variant A, just two
// independent accumulations (one per output column) instead of one.
//
// lifecycle_policy: job_acceptance=valid_ready_handshake, completion_style=pulse,
// completion_timing=next_cycle_after_retirement, error_style=sticky_until_reset,
// error_timing=next_cycle_after_error_event, reset_behavior=abort_inflight.
module tiny_gemm_rv_multi_top #(
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
    output reg signed [15:0] y_data,

    output reg         busy,
    output reg         done,
    output wire        err
);
    localparam S_IDLE = 3'd0, S_LOAD_A = 3'd1, S_LOAD_B = 3'd2,
               S_LOAD_BIAS = 3'd3, S_OUTPUT = 3'd4;

    reg [2:0] state;
    reg [2:0] cnt;
    reg [1:0] k;
    reg       n_sub;
    reg       out_idx;
    reg signed [7:0] a_mem [0:K-1];
    reg signed [15:0] acc0, acc1;
    reg signed [15:0] bias0, bias1;
    // Sticky error latch: set on an illegal command, cleared only by reset --
    // never auto-cleared, unlike variant A's plain pulsed `err` register.
    reg err_latch;
    assign err = err_latch;

    wire signed [15:0] biased0 = acc0 + bias0;
    wire signed [15:0] biased1 = acc1 + bias1;
    wire signed [15:0] activated0 = biased0[15] ? 16'sd0 : biased0;
    wire signed [15:0] activated1 = biased1[15] ? 16'sd0 : biased1;

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            cnt        <= 3'd0;
            k          <= 2'd0;
            n_sub      <= 1'b0;
            out_idx    <= 1'b0;
            cmd_ready  <= 1'b1;
            a_ready    <= 1'b0;
            b_ready    <= 1'b0;
            bias_ready <= 1'b0;
            y_valid    <= 1'b0;
            busy       <= 1'b0;
            done       <= 1'b0;
            err_latch  <= 1'b0;
            acc0       <= 16'sd0;
            acc1       <= 16'sd0;
            bias0      <= 16'sd0;
            bias1      <= 16'sd0;
        end else begin
            done <= 1'b0;
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
                            acc0      <= 16'sd0;
                            acc1      <= 16'sd0;
                            state     <= S_LOAD_A;
                        end else begin
                            err_latch <= 1'b1;
                        end
                    end
                end
                S_LOAD_A: begin
                    if (a_valid && a_ready) begin
                        a_mem[cnt] <= a_data;
                        if (cnt == K-1) begin
                            a_ready <= 1'b0;
                            b_ready <= 1'b1;
                            k       <= 2'd0;
                            n_sub   <= 1'b0;
                            state   <= S_LOAD_B;
                        end else begin
                            cnt <= cnt + 3'd1;
                        end
                    end
                end
                S_LOAD_B: begin
                    if (b_valid && b_ready) begin
                        if (n_sub == 1'b0) begin
                            acc0  <= acc0 + a_mem[k] * b_data;
                            n_sub <= 1'b1;
                        end else begin
                            acc1  <= acc1 + a_mem[k] * b_data;
                            n_sub <= 1'b0;
                            if (k == K-1) begin
                                b_ready    <= 1'b0;
                                bias_ready <= 1'b1;
                                state      <= S_LOAD_BIAS;
                            end else begin
                                k <= k + 2'd1;
                            end
                        end
                    end
                end
                S_LOAD_BIAS: begin
                    if (bias_valid && bias_ready) begin
                        if (n_sub == 1'b0) begin
                            bias0 <= bias_data;
                            n_sub <= 1'b1;
                        end else begin
                            bias1      <= bias_data;
                            bias_ready <= 1'b0;
                            out_idx    <= 1'b0;
                            y_data     <= activated0;
                            state      <= S_OUTPUT;
                        end
                    end
                end
                S_OUTPUT: begin
                    // y_data is set explicitly at each transition point below
                    // (entry into S_OUTPUT, and the out_idx flip), never
                    // recomputed from out_idx unconditionally every cycle --
                    // doing so raced against out_idx's own same-cycle update
                    // and presented the first beat's value twice.
                    y_valid <= 1'b1;
                    if (y_valid && y_ready) begin
                        if (out_idx == 1'b0) begin
                            out_idx <= 1'b1;
                            y_data  <= activated1;
                        end else begin
                            y_valid <= 1'b0;
                            busy    <= 1'b0;
                            done    <= 1'b1;
                            state   <= S_IDLE;
                        end
                    end
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
