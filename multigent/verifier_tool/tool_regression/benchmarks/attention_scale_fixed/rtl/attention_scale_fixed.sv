// Standalone signed attention-score scale stage extracted from the fixed-point
// scale equation embedded in softmax_unit.sv at upstream commit
// 3054e9a5324da438a78937049f656abc413c2750:
//   SCALE_CONST = round((1/sqrt(D)) * 2^FRAC_BITS)
//   scaled      = exact_product >>> FRAC_BITS
//
// The upstream implementation applies the equation to a nonnegative max-score
// delta inside softmax.  This adapter deliberately exposes the same equation as
// an independent signed QK-score stage, before mask and softmax.

`timescale 1ns/1ps

module attention_scale_fixed #(
    parameter int DATA_WIDTH  = 16,
    parameter int FRAC_BITS   = 8,
    parameter int SCALE_CONST = 32
)(
    input  logic                         clk,
    input  logic                         rst_n,
    input  logic                         in_valid,
    output logic                         in_ready,
    input  logic signed [DATA_WIDTH-1:0] score_in,
    output logic                         out_valid,
    input  logic                         out_ready,
    output logic signed [DATA_WIDTH-1:0] score_out
);
    logic signed [2*DATA_WIDTH-1:0] scaled_product;

    assign in_ready = !out_valid || out_ready;
    assign scaled_product = $signed(score_in) * SCALE_CONST;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            score_out <= '0;
        end else if (in_ready) begin
            out_valid <= in_valid;
            if (in_valid) begin
                score_out <= scaled_product >>> FRAC_BITS;
            end
        end
    end
endmodule
