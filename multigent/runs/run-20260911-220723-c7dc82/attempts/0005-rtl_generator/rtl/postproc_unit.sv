module postproc_unit (
  input  logic signed [31:0] acc_in,
  input  logic signed [31:0] bias_in,
  input  logic               bias_en,
  input  logic               relu_en,
  output logic signed [31:0] y_out
);
  logic signed [31:0] y_pre;
  always_comb begin
    y_pre = bias_en ? (acc_in + bias_in) : acc_in;
    if (relu_en && y_pre[31]) y_out = 32'sd0;
    else y_out = y_pre;
  end
endmodule
