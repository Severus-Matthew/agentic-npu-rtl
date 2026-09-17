module rv_uadd8_top (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       in_valid,
    output logic       in_ready,
    input  logic [7:0] in_op_a,
    input  logic [7:0] in_op_b,
    output logic       out_valid,
    input  logic       out_ready,
    output logic [8:0] out_sum
);

    logic       out_valid_r;
    logic [8:0] out_sum_r;

    logic       pop;
    logic       push;
    logic [8:0] sum_candidate;

    always_comb begin
        in_ready      = rst_n && (!out_valid_r || out_ready);
        out_valid     = out_valid_r;
        out_sum       = out_sum_r;

        pop           = out_valid_r && out_ready;
        push          = in_valid && in_ready;
        sum_candidate = {1'b0, in_op_a} + {1'b0, in_op_b};
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            out_valid_r <= 1'b0;
            out_sum_r   <= 9'd0;
        end else begin
            case ({push, pop})
                2'b10: begin
                    out_valid_r <= 1'b1;
                    out_sum_r   <= sum_candidate;
                end
                2'b01: begin
                    out_valid_r <= 1'b0;
                    out_sum_r   <= out_sum_r;
                end
                2'b11: begin
                    out_valid_r <= 1'b1;
                    out_sum_r   <= sum_candidate;
                end
                default: begin
                    out_valid_r <= out_valid_r;
                    out_sum_r   <= out_sum_r;
                end
            endcase
        end
    end

endmodule
