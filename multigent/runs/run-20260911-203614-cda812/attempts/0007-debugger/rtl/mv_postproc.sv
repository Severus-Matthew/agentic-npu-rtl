module mv_postproc (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               in_valid,
  input  logic signed [31:0] in_data,
  input  logic               bias_en,
  input  logic               relu_en,
  input  logic               bias_valid,
  input  logic signed [31:0] bias_data,
  input  logic               out_ready,
  output logic               out_valid,
  output logic signed [31:0] out_data,
  output logic               in_ready
);
  logic signed [31:0] pre_act;
  logic signed [31:0] post_act;

  always_comb begin
    in_ready = (~out_valid) | out_ready;
    pre_act = in_data;
    if (bias_en) pre_act = in_data + bias_data;
    post_act = pre_act;
    if (relu_en && pre_act[31]) post_act = 32'sd0;
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      out_valid <= 1'b0;
      out_data  <= 32'sd0;
    end else begin
      if (in_valid && in_ready) begin
        if (!bias_en || bias_valid) begin
          out_data  <= post_act;
          out_valid <= 1'b1;
        end
      end else if (out_valid && out_ready) begin
        out_valid <= 1'b0;
      end
    end
  end
endmodule
