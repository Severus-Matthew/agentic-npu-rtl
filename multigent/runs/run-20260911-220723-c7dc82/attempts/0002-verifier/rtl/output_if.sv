module output_if (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               in_valid,
  input  logic signed [31:0] in_data,
  input  logic               in_last,
  output logic               out_valid,
  input  logic               out_ready,
  output logic signed [31:0] out_data,
  output logic               out_last,
  output logic               out_accept_pulse
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      out_valid <= 1'b0;
      out_data <= '0;
      out_last <= 1'b0;
    end else begin
      if (out_valid && out_ready) out_valid <= 1'b0;
      if ((!out_valid || (out_valid && out_ready)) && in_valid) begin
        out_valid <= 1'b1;
        out_data <= in_data;
        out_last <= in_last;
      end
    end
  end
  assign out_accept_pulse = out_valid && out_ready;
endmodule
