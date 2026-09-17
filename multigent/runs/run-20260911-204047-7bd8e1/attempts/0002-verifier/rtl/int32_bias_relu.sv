module int32_bias_relu (
  input  logic signed [31:0] dot_value,
  input  logic signed [31:0] bias_value,
  input  logic bias_enable,
  input  logic relu_enable,
  output logic signed [31:0] result_value
);
  logic signed [32:0] sum_extended;
  logic signed [31:0] adjusted;

  always_comb begin
    sum_extended = $signed({dot_value[31], dot_value}) +
                   $signed({bias_value[31], bias_value});
    adjusted = dot_value;
    if (bias_enable)
      adjusted = $signed(sum_extended[31:0]);
    // Test the sign only after truncation to the wrapped INT32 value.
    if (relu_enable && adjusted[31])
      result_value = 32'sd0;
    else
      result_value = adjusted;
  end
endmodule
