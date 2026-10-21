// Local qualification copy of the upstream QK systolic MAC.
// Source pin and local-only purpose are documented in ../README.md.
`timescale 1ns/1ps

module mac_pe #(
    parameter int DATA_WIDTH = 16,
    parameter int ACC_WIDTH  = 32
)(
    input  logic                         clk,
    input  logic                         reset,
    input  logic                         valid_in,
    input  logic signed [DATA_WIDTH-1:0] a_in,
    input  logic signed [DATA_WIDTH-1:0] b_in,
    output logic signed [ACC_WIDTH-1:0]  sum_out,
    output logic                         valid_out
);

    logic signed [DATA_WIDTH-1:0]   reg_a;
    logic signed [DATA_WIDTH-1:0]   reg_b;
    logic signed [2*DATA_WIDTH-1:0] reg_product;
    logic signed [ACC_WIDTH-1:0]    acc;
    logic [2:0]                     valid_pipe;

    always_ff @(posedge clk) begin
        if (reset) begin
            reg_a       <= '0;
            reg_b       <= '0;
            reg_product <= '0;
            acc         <= '0;
            sum_out     <= '0;
            valid_pipe  <= 3'b0;
        end else begin
            reg_a       <= a_in;
            reg_b       <= b_in;
            reg_product <= reg_a * reg_b;
            acc         <= acc + ACC_WIDTH'(reg_product);
            sum_out     <= acc + ACC_WIDTH'(reg_product);
            valid_pipe  <= {valid_pipe[1:0], valid_in};
        end
    end

    assign valid_out = valid_pipe[2];

endmodule
