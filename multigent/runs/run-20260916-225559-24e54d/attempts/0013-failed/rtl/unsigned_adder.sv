module unsigned_adder (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       in_valid,
    output logic       in_ready,
    input  logic [7:0] in_a,
    input  logic [7:0] in_b,
    output logic       out_valid,
    input  logic       out_ready,
    output logic [8:0] out_sum
);

    logic [8:0] operand_a_ext;
    logic [8:0] operand_b_ext;
    logic [8:0] sum_next;

    assign operand_a_ext = {1'b0, in_a};
    assign operand_b_ext = {1'b0, in_b};
    assign sum_next = operand_a_ext + operand_b_ext;
    assign in_ready = rst_n && (!out_valid || out_ready);

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_sum   <= 9'd0;
        end else if (in_valid && in_ready) begin
            out_valid <= 1'b1;
            out_sum   <= sum_next;
        end else if (out_valid && out_ready) begin
            out_valid <= 1'b0;
        end
    end

endmodule
