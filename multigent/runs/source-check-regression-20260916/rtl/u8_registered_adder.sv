module u8_registered_adder (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        in_valid,
    output logic        in_ready,
    input  logic [15:0] in_payload,
    output logic        out_valid,
    input  logic        out_ready,
    output logic [8:0]  out_payload
);

    logic [8:0] operand_a_ext;
    logic [8:0] operand_b_ext;
    logic [8:0] sum_next;

    always_comb begin
        in_ready     = rst_n && (!out_valid || out_ready);
        operand_a_ext = {1'b0, in_payload[7:0]};
        operand_b_ext = {1'b0, in_payload[15:8]};
        sum_next      = operand_a_ext + operand_b_ext;
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid   <= 1'b0;
            out_payload <= 9'b0;
        end else if (in_valid && in_ready) begin
            out_valid   <= 1'b1;
            out_payload <= sum_next;
        end else if (out_valid && out_ready) begin
            out_valid <= 1'b0;
        end
    end

endmodule
