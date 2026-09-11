module postproc_relu_bias #(
  parameter int M_MAX=8, N_MAX=8, ACC_W=32
)(
  input logic clk,
  input logic rst,
  input logic start_post,
  input logic acc_valid,
  input logic [((M_MAX>1)?$clog2(M_MAX):1)-1:0] acc_m,
  input logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] acc_n,
  input logic signed [ACC_W-1:0] acc_data,
  output logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] bias_rd_addr,
  input  logic signed [ACC_W-1:0] bias_rd_data,
  output logic out_wr_en,
  output logic [((M_MAX*N_MAX>1)?$clog2(M_MAX*N_MAX):1)-1:0] out_wr_addr,
  output logic signed [ACC_W-1:0] out_wr_data,
  output logic post_done
);
  logic pending;
  logic [((M_MAX>1)?$clog2(M_MAX):1)-1:0] pm;
  logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] pn;
  logic signed [ACC_W-1:0] pdata;
  always_ff @(posedge clk) begin
    if(rst) begin out_wr_en<=0; post_done<=0; pending<=0; end
    else begin
      out_wr_en<=0; post_done<=0;
      if(start_post && acc_valid) begin
        bias_rd_addr<=acc_n; pm<=acc_m; pn<=acc_n; pdata<=acc_data; pending<=1;
      end
      if(pending) begin
        logic signed [ACC_W-1:0] sum;
        sum = pdata + bias_rd_data;
        out_wr_en<=1;
        out_wr_addr<=pm*N_MAX + pn;
        out_wr_data<=sum[ACC_W-1] ? '0 : sum;
        if(pm==M_MAX-1 && pn==N_MAX-1) post_done<=1;
        pending<=0;
      end
    end
  end
endmodule
