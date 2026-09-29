// Minimal, hand-authored, contract-driven reference RTL: sibling of
// ready_valid_tiny_gemm variant A (identical M=1/K=4/N=1 bias+ReLU
// arithmetic) with A_matrix read over a minimal AXI4-Lite manager port
// (a_ar/a_r) instead of a plain ready_valid channel. All 4 s8 A elements
// pack into one 32-bit word (elements_per_word=4, little-endian byte order,
// per the frozen contract's derived memory_mapping), so exactly one AR/R
// exchange fetches the whole A vector.
//
// Y = relu(sum_{k=0}^{3} A[k]*B[k] + bias).
//
// lifecycle_policy: job_acceptance=valid_ready_handshake, completion_style=pulse,
// completion_timing=next_cycle_after_retirement, error_style=pulse,
// error_timing=next_cycle_after_error_event, reset_behavior=abort_inflight.
module ready_valid_axi_error_gemm_top (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        cmd_valid,
    output reg         cmd_ready,
    input  wire        cmd_op,          // legal value: 1'b1 (start)
    input  wire [31:0] a_base,

    output reg  [31:0] a_araddr,
    output reg         a_arvalid,
    input  wire        a_arready,
    input  wire [31:0] a_rdata,
    input  wire [1:0]  a_rresp,
    input  wire        a_rvalid,
    output reg         a_rready,

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
    output reg         err
);
    localparam S_IDLE = 3'd0, S_READ_A = 3'd1, S_LOAD_B = 3'd2,
               S_LOAD_BIAS = 3'd3, S_OUTPUT = 3'd4;

    reg [2:0] state;
    reg [2:0] cnt;
    reg signed [7:0] a_mem [0:3];
    reg signed [15:0] acc;
    reg signed [15:0] bias_reg;
    reg ar_issued;

    wire signed [15:0] biased    = acc + bias_reg;
    wire signed [15:0] activated = biased[15] ? 16'sd0 : biased;

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            cnt        <= 3'd0;
            cmd_ready  <= 1'b1;
            a_araddr   <= 32'd0;
            a_arvalid  <= 1'b0;
            a_rready   <= 1'b0;
            ar_issued  <= 1'b0;
            b_ready    <= 1'b0;
            bias_ready <= 1'b0;
            y_valid    <= 1'b0;
            busy       <= 1'b0;
            done       <= 1'b0;
            err        <= 1'b0;
            acc        <= 16'sd0;
            bias_reg   <= 16'sd0;
        end else begin
            done <= 1'b0;
            err  <= 1'b0;
            case (state)
                S_IDLE: begin
                    y_valid    <= 1'b0;
                    cmd_ready  <= 1'b1;
                    a_rready   <= 1'b0;
                    b_ready    <= 1'b0;
                    bias_ready <= 1'b0;
                    busy       <= 1'b0;
                    if (cmd_valid && cmd_ready) begin
                        if (cmd_op == 1'b1) begin
                            busy      <= 1'b1;
                            cmd_ready <= 1'b0;
                            a_araddr  <= a_base;
                            a_arvalid <= 1'b1;
                            a_rready  <= 1'b1;
                            ar_issued <= 1'b0;
                            state     <= S_READ_A;
                        end else begin
                            err <= 1'b1;
                        end
                    end
                end
                S_READ_A: begin
                    if (a_arvalid && a_arready) begin
                        a_arvalid <= 1'b0;
                        ar_issued <= 1'b1;
                    end
                    if (a_rvalid && a_rready) begin
                        a_rready <= 1'b0;
                        if (a_rresp != 2'b00) begin
                            // A non-OKAY response aborts the job right here:
                            // the lifecycle checker's response_error_follows_
                            // nonokay handling marks the job inactive the
                            // instant it observes the bad response
                            // (lifecycle/assertion/assertion_checkers.py's
                            // error_responses loop sets current["active"] =
                            // False), so a compliant design must drop busy
                            // and return to idle immediately rather than
                            // continue on to load B/bias/output.
                            err   <= 1'b1;
                            busy  <= 1'b0;
                            state <= S_IDLE;
                        end else begin
                            a_mem[0] <= a_rdata[7:0];
                            a_mem[1] <= a_rdata[15:8];
                            a_mem[2] <= a_rdata[23:16];
                            a_mem[3] <= a_rdata[31:24];
                            b_ready  <= 1'b1;
                            cnt      <= 3'd0;
                            acc      <= 16'sd0;
                            state    <= S_LOAD_B;
                        end
                    end
                end
                S_LOAD_B: begin
                    if (b_valid && b_ready) begin
                        acc <= acc + a_mem[cnt] * b_data;
                        if (cnt == 3'd3) begin
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
                    y_data  <= activated;
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
