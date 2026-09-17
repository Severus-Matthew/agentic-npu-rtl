module mac_sequencer #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic enable_compute,
  output logic [7:0] raddr_a,
  input  logic signed [7:0] rdata_a,
  output logic [7:0] raddr_b,
  input  logic signed [7:0] rdata_b,
  output logic [2:0] raddr_bias,
  input  logic signed [31:0] rdata_bias,
  output logic we_c,
  output logic [5:0] waddr_c,
  output logic signed [31:0] wdata_c,
  output logic compute_done
);
  typedef enum logic [1:0] {PH_BIAS_ISSUE=2'd0, PH_BIAS_CAPTURE=2'd1, PH_MAC_ISSUE=2'd2, PH_MAC_UPDATE=2'd3} ph_t;
  ph_t ph_q;

  logic [2:0] i_q, j_q;
  logic [5:0] k_q;
  logic signed [31:0] acc_q;
  logic signed [7:0] a_hold_q, b_hold_q;

  logic [7:0] a_addr_calc, b_addr_calc;
  logic [5:0] c_addr_calc;
  logic signed [15:0] prod16;
  logic signed [31:0] prod32;
  logic signed [31:0] sum32;

  always_comb begin
    a_addr_calc = (i_q * K_FIXED) + k_q;
    b_addr_calc = (k_q * N_FIXED) + j_q;
    c_addr_calc = (i_q * N_FIXED) + j_q;
    prod16 = a_hold_q * b_hold_q;
    prod32 = {{16{prod16[15]}}, prod16};
    sum32 = acc_q + prod32;
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      ph_q <= PH_BIAS_ISSUE;
      i_q <= '0;
      j_q <= '0;
      k_q <= '0;
      acc_q <= '0;
      a_hold_q <= '0;
      b_hold_q <= '0;
      raddr_a <= '0;
      raddr_b <= '0;
      raddr_bias <= '0;
      we_c <= 1'b0;
      waddr_c <= '0;
      wdata_c <= '0;
      compute_done <= 1'b0;
    end else begin
      we_c <= 1'b0;
      compute_done <= 1'b0;

      if (!enable_compute) begin
        ph_q <= PH_BIAS_ISSUE;
        i_q <= '0;
        j_q <= '0;
        k_q <= '0;
        acc_q <= '0;
        raddr_a <= '0;
        raddr_b <= '0;
        raddr_bias <= '0;
      end else begin
        unique case (ph_q)
          PH_BIAS_ISSUE: begin
            raddr_bias <= j_q;
            ph_q <= PH_BIAS_CAPTURE;
          end
          PH_BIAS_CAPTURE: begin
            acc_q <= rdata_bias;
            k_q <= '0;
            ph_q <= PH_MAC_ISSUE;
          end
          PH_MAC_ISSUE: begin
            raddr_a <= a_addr_calc;
            raddr_b <= b_addr_calc;
            ph_q <= PH_MAC_UPDATE;
          end
          PH_MAC_UPDATE: begin
            a_hold_q <= rdata_a;
            b_hold_q <= rdata_b;
            acc_q <= sum32;
            if (k_q == K_FIXED-1) begin
              waddr_c <= c_addr_calc;
              wdata_c <= sum32[31] ? 32'sd0 : sum32;
              we_c <= 1'b1;
              if ((i_q == M_FIXED-1) && (j_q == N_FIXED-1)) begin
                compute_done <= 1'b1;
              end
              if (j_q == N_FIXED-1) begin
                j_q <= '0;
                i_q <= i_q + 1'b1;
              end else begin
                j_q <= j_q + 1'b1;
              end
              ph_q <= PH_BIAS_ISSUE;
            end else begin
              k_q <= k_q + 1'b1;
              ph_q <= PH_MAC_ISSUE;
            end
          end
          default: ph_q <= PH_BIAS_ISSUE;
        endcase
      end
    end
  end
endmodule
