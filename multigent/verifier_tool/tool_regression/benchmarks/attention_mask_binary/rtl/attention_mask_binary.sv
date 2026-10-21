// Standalone binary-keep mask stage for the restricted integer sparse-attention
// composition.  The score and mask streams are buffered independently so a
// stall on either producer cannot misalign Q-by-S coordinates.
//
// Contract: mask_keep == 1 preserves the signed scaled score; zero emits zero.
// This stage intentionally does not implement softmax's -infinity sentinel.

`timescale 1ns/1ps

module attention_mask_binary #(
    parameter int DATA_WIDTH = 16
)(
    input  logic                         clk,
    input  logic                         rst_n,

    input  logic                         score_valid,
    output logic                         score_ready,
    input  logic signed [DATA_WIDTH-1:0] score_in,

    input  logic                         mask_valid,
    output logic                         mask_ready,
    input  logic                         mask_keep,

    output logic                         out_valid,
    input  logic                         out_ready,
    output logic signed [DATA_WIDTH-1:0] score_out
);
    logic                         score_pending;
    logic signed [DATA_WIDTH-1:0] score_buffer;
    logic                         mask_pending;
    logic                         mask_buffer;
    logic                         output_slot_ready;
    logic                         consume_pair;

    assign output_slot_ready = !out_valid || out_ready;
    assign consume_pair = score_pending && mask_pending && output_slot_ready;
    assign score_ready = !score_pending || consume_pair;
    assign mask_ready  = !mask_pending  || consume_pair;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            score_pending <= 1'b0;
            score_buffer  <= '0;
            mask_pending  <= 1'b0;
            mask_buffer   <= 1'b0;
            out_valid     <= 1'b0;
            score_out     <= '0;
        end else begin
            if (output_slot_ready) begin
                out_valid <= score_pending && mask_pending;
                if (score_pending && mask_pending) begin
                    score_out <= mask_buffer ? score_buffer : '0;
                end
            end

            if (consume_pair) begin
                score_pending <= score_valid && score_ready;
                mask_pending  <= mask_valid && mask_ready;
            end else begin
                if (score_valid && score_ready) begin
                    score_pending <= 1'b1;
                end
                if (mask_valid && mask_ready) begin
                    mask_pending <= 1'b1;
                end
            end

            if (score_valid && score_ready) begin
                score_buffer <= score_in;
            end
            if (mask_valid && mask_ready) begin
                mask_buffer <= mask_keep;
            end
        end
    end
endmodule
