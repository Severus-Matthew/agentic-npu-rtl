module observed_adder4 (
    input logic clk,
    input logic [3:0] left,
    input logic [3:0] right,
    output logic [3:0] result
);
    assign result = left + right;
endmodule
