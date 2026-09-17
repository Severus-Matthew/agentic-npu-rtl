module int8_mac16_bank (
  input  logic clk,
  input  logic rst_n,
  input  logic clear,
  input  logic step,
  input  logic signed [7:0] vector_value,
  input  logic [127:0] matrix_values,
  output wire [511:0] accumulators
);
  generate
    for (genvar lane = 0; lane < 16; lane = lane + 1) begin : g_lane
      logic signed [31:0] accumulator;
      wire signed [7:0] matrix_value;
      wire signed [15:0] product;
      wire signed [31:0] product_extended;
      wire signed [32:0] sum_extended;

      assign matrix_value = $signed(matrix_values[8*lane +: 8]);
      // The 16-bit signed destination retains the exact INT8 product.
      assign product = matrix_value * vector_value;
      assign product_extended = $signed({{16{product[15]}}, product});
      assign sum_extended = $signed({accumulator[31], accumulator}) +
                            $signed({product_extended[31], product_extended});
      assign accumulators[32*lane +: 32] = accumulator;

      always_ff @(posedge clk) begin
        if (!rst_n)
          accumulator <= 32'sd0;
        else if (clear)
          accumulator <= 32'sd0;
        else if (step)
          // Discard carry/sign overflow: modulo 2^32, without saturation.
          accumulator <= $signed(sum_extended[31:0]);
      end
    end
  endgenerate
endmodule
