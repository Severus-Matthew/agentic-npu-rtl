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
  localparam int M_W = (M_MAX>1)?$clog2(M_MAX):1;
  localparam int N_W = (N_MAX>1)?$clog2(N_MAX):1;
  localparam int O_W = ((M_MAX*N_MAX)>1)?$clog2(M_MAX*N_MAX):1;

  logic active;
  logic pend;
  logic [M_W-1:0] pm;
  logic [N_W-1:0] pn;
  logic signed [ACC_W-1:0] pdata;
  logic signed [ACC_W-1:0] sum;
  logic [O_W-1:0] wr_addr_calc;

  always_ff @(posedge clk) begin
    if(rst) begin
      active <= 1'b0;
      pend <= 1'b0;
      out_wr_en <= 1'b0;
      out_wr_addr <= '0;
      out_wr_data <= '0;
      bias_rd_addr <= '0;
      pm <= '0;
      pn <= '0;
      pdata <= '0;
      post_done <= 1'b0;
    end else begin
      out_wr_en <= 1'b0;
      post_done <= 1'b0;

      if (start_post) active <= 1'b1;

      if (active) begin
        if (pend) begin
          sum = pdata + bias_rd_data;
          wr_addr_calc = O_W'((pm * N_MAX) + pn);
          out_wr_en <= 1'b1;
          out_wr_addr <= wr_addr_calc;
          out_wr_data <= sum[ACC_W-1] ? '0 : sum;
          if ((pm == M_W'(M_MAX-1)) && (pn == N_W'(N_MAX-1))) begin
            post_done <= 1'b1;
            active <= 1'b0;
          end
          pend <= 1'b0;
        end

        if (acc_valid) begin
          bias_rd_addr <= acc_n;
          pm <= acc_m;
          pn <= acc_n;
          pdata <= acc_data;
          pend <= 1'b1;
        end
      end
    end
  end
endmodule
