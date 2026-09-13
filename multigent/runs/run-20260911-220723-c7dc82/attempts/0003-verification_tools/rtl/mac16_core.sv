module mac16_core #(
  parameter int LANES = 16,
  parameter int MAX_N = 256
) (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               start_row,
  input  logic               step_valid,
  input  logic signed [7:0]  a_val,
  input  logic signed [7:0]  x_val,
  output logic signed [31:0] acc_out
);
  logic signed [31:0] acc;
  logic signed [15:0] prod;
  assign prod = a_val * x_val;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      acc <= '0;
    end else begin
      if (start_row) acc <= '0;
      else if (step_valid) acc <= acc + {{16{prod[15]}}, prod};
    end
  end
  assign acc_out = acc;
endmodule
