module gemm_core_seq #(
  parameter int M_MAX=8, N_MAX=8, K_MAX=32, A_ELEM_W=8, ACC_W=32
)(
  input logic clk,
  input logic rst,
  input logic start_compute,
  output logic [((M_MAX*K_MAX>1)?$clog2(M_MAX*K_MAX):1)-1:0] a_rd_addr,
  input  logic signed [A_ELEM_W-1:0] a_rd_data,
  output logic [((K_MAX*N_MAX>1)?$clog2(K_MAX*N_MAX):1)-1:0] b_rd_addr,
  input  logic signed [A_ELEM_W-1:0] b_rd_data,
  output logic acc_valid,
  output logic [((M_MAX>1)?$clog2(M_MAX):1)-1:0] acc_m,
  output logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] acc_n,
  output logic signed [ACC_W-1:0] acc_data,
  output logic compute_done
);
  int unsigned m,n,k;
  logic run;
  logic signed [ACC_W-1:0] acc;
  logic signed [15:0] prod16;
  always_ff @(posedge clk) begin
    if(rst) begin run<=0; m<=0;n<=0;k<=0; acc<=0; acc_valid<=0; compute_done<=0; end
    else begin
      acc_valid<=0; compute_done<=0;
      if(start_compute) begin run<=1; m<=0;n<=0;k<=0; acc<=0; end
      else if(run) begin
        a_rd_addr <= m*K_MAX + k;
        b_rd_addr <= k*N_MAX + n;
        prod16 = a_rd_data * b_rd_data;
        acc <= acc + $signed({{(ACC_W-16){prod16[15]}},prod16});
        if(k==K_MAX-1) begin
          acc_valid<=1; acc_m<=m; acc_n<=n; acc_data<=acc + $signed({{(ACC_W-16){prod16[15]}},prod16});
          acc<=0; k<=0;
          if(n==N_MAX-1) begin n<=0; if(m==M_MAX-1) begin run<=0; compute_done<=1; end else m<=m+1; end
          else n<=n+1;
        end else k<=k+1;
      end
    end
  end
endmodule
