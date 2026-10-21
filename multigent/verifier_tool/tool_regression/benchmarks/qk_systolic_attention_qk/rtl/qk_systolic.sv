// Local qualification copy of the upstream output-stationary Q*K^T array.
// The qualification harness uses FRAC_BITS=0, N=4, D=4, DATA_WIDTH=16,
// and ACC_WIDTH=16 so its arithmetic exactly matches the frozen QK contract.
// Source pin and local-only purpose are documented in ../README.md.
`timescale 1ns/1ps

module qk_systolic #(
    parameter int N          = 64,
    parameter int D          = 64,
    parameter int DATA_WIDTH = 16,
    parameter int ACC_WIDTH  = 32,
    parameter int FRAC_BITS  = 8
)(
    input  logic                  clk,
    input  logic                  rst_n,
    input  logic                  start,
    input  logic [DATA_WIDTH-1:0] q_in [0:N-1],
    input  logic [DATA_WIDTH-1:0] k_in [0:N-1],
    output logic [DATA_WIDTH-1:0] s_out [0:N-1][0:N-1],
    output logic                  done
);

    localparam int LAT       = 2*N + D;
    localparam int CNT_WIDTH = $clog2(LAT + 1);

    logic                 busy;
    logic [CNT_WIDTH-1:0] cnt;
    logic                 capture;

    assign capture = busy && (cnt == CNT_WIDTH'(LAT));

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            busy <= 1'b0;
            cnt  <= '0;
            done <= 1'b0;
        end else begin
            done <= capture;
            if (start) begin
                busy <= 1'b1;
                cnt  <= '0;
            end else if (busy) begin
                if (capture) busy <= 1'b0;
                else         cnt  <= cnt + 1'b1;
            end
        end
    end

    logic clr;
    assign clr = !rst_n || !busy;

    logic [DATA_WIDTH-1:0] a_wire [0:N-1][0:N];
    logic [DATA_WIDTH-1:0] b_wire [0:N][0:N-1];

    genvar i, j;
    generate
        for (i = 0; i < N; i++) begin : edge_connect
            assign a_wire[i][0] = q_in[i];
            assign b_wire[0][i] = k_in[i];
        end
    endgenerate

    generate
        for (i = 0; i < N; i++) begin : a_shift_row
            for (j = 0; j < N; j++) begin : a_shift_col
                always_ff @(posedge clk) begin
                    if (clr) a_wire[i][j+1] <= '0;
                    else     a_wire[i][j+1] <= a_wire[i][j];
                end
            end
        end
    endgenerate

    generate
        for (j = 0; j < N; j++) begin : b_shift_col
            for (i = 0; i < N; i++) begin : b_shift_row
                always_ff @(posedge clk) begin
                    if (clr) b_wire[i+1][j] <= '0;
                    else     b_wire[i+1][j] <= b_wire[i][j];
                end
            end
        end
    endgenerate

    logic [ACC_WIDTH-1:0] pe_out [0:N-1][0:N-1];

    generate
        for (i = 0; i < N; i++) begin : pe_row
            for (j = 0; j < N; j++) begin : pe_col
                mac_pe #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .ACC_WIDTH (ACC_WIDTH)
                ) pe_inst (
                    .clk      (clk),
                    .reset    (clr),
                    .valid_in (1'b1),
                    .a_in     (a_wire[i][j]),
                    .b_in     (b_wire[i][j]),
                    .sum_out  (pe_out[i][j]),
                    .valid_out()
                );
            end
        end
    endgenerate

    always_ff @(posedge clk) begin
        if (capture) begin
            for (int r = 0; r < N; r++)
                for (int c = 0; c < N; c++)
                    s_out[r][c] <= pe_out[r][c][FRAC_BITS +: DATA_WIDTH];
        end
    end

endmodule
