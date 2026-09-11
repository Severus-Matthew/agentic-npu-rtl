module local_memories #(
  parameter int M_MAX=8, N_MAX=8, K_MAX=32, A_ELEM_W=8, ACC_W=32
)(
  input logic clk,
  input logic a_wr_en,
  input logic [((M_MAX*K_MAX>1)?$clog2(M_MAX*K_MAX):1)-1:0] a_wr_addr,
  input logic signed [A_ELEM_W-1:0] a_wr_data,
  input logic [((M_MAX*K_MAX>1)?$clog2(M_MAX*K_MAX):1)-1:0] a_rd_addr,
  output logic signed [A_ELEM_W-1:0] a_rd_data,
  input logic b_wr_en,
  input logic [((K_MAX*N_MAX>1)?$clog2(K_MAX*N_MAX):1)-1:0] b_wr_addr,
  input logic signed [A_ELEM_W-1:0] b_wr_data,
  input logic [((K_MAX*N_MAX>1)?$clog2(K_MAX*N_MAX):1)-1:0] b_rd_addr,
  output logic signed [A_ELEM_W-1:0] b_rd_data,
  input logic bias_wr_en,
  input logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] bias_wr_addr,
  input logic signed [ACC_W-1:0] bias_wr_data,
  input logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] bias_rd_addr,
  output logic signed [ACC_W-1:0] bias_rd_data,
  input logic out_wr_en,
  input logic [((M_MAX*N_MAX>1)?$clog2(M_MAX*N_MAX):1)-1:0] out_wr_addr,
  input logic signed [ACC_W-1:0] out_wr_data,
  input logic [((M_MAX*N_MAX>1)?$clog2(M_MAX*N_MAX):1)-1:0] out_rd_addr,
  output logic signed [ACC_W-1:0] out_rd_data
);
  logic signed [A_ELEM_W-1:0] memA [0:M_MAX*K_MAX-1];
  logic signed [A_ELEM_W-1:0] memB [0:K_MAX*N_MAX-1];
  logic signed [ACC_W-1:0] memBias [0:N_MAX-1];
  logic signed [ACC_W-1:0] memOut [0:M_MAX*N_MAX-1];
  always_ff @(posedge clk) begin
    if(a_wr_en) memA[a_wr_addr] <= a_wr_data;
    a_rd_data <= memA[a_rd_addr];
    if(b_wr_en) memB[b_wr_addr] <= b_wr_data;
    b_rd_data <= memB[b_rd_addr];
    if(bias_wr_en) memBias[bias_wr_addr] <= bias_wr_data;
    bias_rd_data <= memBias[bias_rd_addr];
    if(out_wr_en) memOut[out_wr_addr] <= out_wr_data;
    out_rd_data <= memOut[out_rd_addr];
  end
endmodule
