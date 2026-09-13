module mv_vec_buffer #(
  parameter int MAX_N = 256,
  parameter int LANES = 16
) (
  input  logic                          clk,
  input  logic                          rst_n,
  input  logic                          wr_en,
  input  logic [$clog2(MAX_N)-1:0]      wr_addr,
  input  logic signed [7:0]             wr_data,
  input  logic [$clog2(MAX_N)-1:0]      rd_chunk_base,
  output logic signed [LANES*8-1:0]     rd_data
);
  logic signed [7:0] mem [0:MAX_N-1];

  always_ff @(posedge clk) begin
    if (wr_en) mem[wr_addr] <= wr_data;
  end

  integer j;
  always_comb begin
    for (j = 0; j < LANES; j++) begin
      if ((rd_chunk_base + j) < MAX_N)
        rd_data[j*8 +: 8] = mem[rd_chunk_base + j];
      else
        rd_data[j*8 +: 8] = '0;
    end
  end
endmodule
