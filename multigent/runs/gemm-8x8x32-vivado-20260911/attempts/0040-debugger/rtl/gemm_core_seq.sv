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
  localparam int M_W = (M_MAX>1)?$clog2(M_MAX):1;
  localparam int N_W = (N_MAX>1)?$clog2(N_MAX):1;
  localparam int K_W = (K_MAX>1)?$clog2(K_MAX):1;

  logic run;
  logic [M_W-1:0] m;
  logic [N_W-1:0] n;
  logic [K_W-1:0] k_issue;
  logic [K_W-1:0] k_resp;
  logic signed [ACC_W-1:0] acc;
  logic req_valid;
  logic resp_valid;
  logic signed [15:0] prod16;
  logic signed [ACC_W-1:0] prod32;
  logic signed [ACC_W-1:0] sum32;

  always_ff @(posedge clk) begin
    if(rst) begin
      run <= 1'b0;
      m <= '0;
      n <= '0;
      k_issue <= '0;
      k_resp <= '0;
      acc <= '0;
      req_valid <= 1'b0;
      resp_valid <= 1'b0;
      acc_valid <= 1'b0;
      acc_m <= '0;
      acc_n <= '0;
      acc_data <= '0;
      compute_done <= 1'b0;
      a_rd_addr <= '0;
      b_rd_addr <= '0;
    end else begin
      acc_valid <= 1'b0;
      compute_done <= 1'b0;

      resp_valid <= req_valid;
      k_resp <= k_issue;

      if (start_compute) begin
        run <= 1'b1;
        m <= '0;
        n <= '0;
        k_issue <= '0;
        acc <= '0;
        req_valid <= 1'b1;
        a_rd_addr <= '0;
        b_rd_addr <= '0;
      end else if (run) begin
        if (req_valid) begin
          a_rd_addr <= m*K_MAX + k_issue;
          b_rd_addr <= k_issue*N_MAX + n;
          if (k_issue == K_MAX-1) req_valid <= 1'b0;
          else k_issue <= k_issue + 1'b1;
        end

        if (resp_valid) begin
          prod16 = a_rd_data * b_rd_data;
          prod32 = $signed({{(ACC_W-16){prod16[15]}}, prod16});
          sum32 = acc + prod32;

          if (k_resp == K_MAX-1) begin
            acc_valid <= 1'b1;
            acc_m <= m;
            acc_n <= n;
            acc_data <= sum32;
            acc <= '0;

            if ((m == M_MAX-1) && (n == N_MAX-1)) begin
              run <= 1'b0;
              compute_done <= 1'b1;
              req_valid <= 1'b0;
            end else begin
              if (n == N_MAX-1) begin n <= '0; m <= m + 1'b1; end
              else n <= n + 1'b1;
              k_issue <= '0;
              req_valid <= 1'b1;
            end
          end else begin
            acc <= sum32;
          end
        end
      end else begin
        req_valid <= 1'b0;
      end
    end
  end
endmodule
