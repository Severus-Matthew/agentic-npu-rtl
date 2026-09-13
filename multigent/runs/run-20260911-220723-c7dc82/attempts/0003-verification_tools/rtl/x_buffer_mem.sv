module x_buffer_mem #(
  parameter int MAX_N = 256
) (
  input  logic                     clk,
  input  logic                     we,
  input  logic [$clog2(MAX_N)-1:0] waddr,
  input  logic signed [7:0]        wdata,
  input  logic [$clog2(MAX_N)-1:0] raddr,
  output logic signed [7:0]        rdata
);
  logic signed [7:0] mem [0:MAX_N-1];
  always_ff @(posedge clk) begin
    if (we) mem[waddr] <= wdata;
    rdata <= mem[raddr];
  end
endmodule
