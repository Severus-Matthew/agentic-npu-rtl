module output_streamer #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic enable_output,
  input  logic out_ready,
  output logic out_valid,
  output logic signed [31:0] out_payload,
  output logic out_last,
  output logic out_hs,
  output logic [5:0] raddr_c,
  input  logic signed [31:0] rdata_c
);
  localparam int C_COUNT = M_FIXED*N_FIXED;
  logic [6:0] count_q;
  logic active_q;
  logic [5:0] addr_pipe_q;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      out_valid <= 1'b0;
      out_payload <= '0;
      out_last <= 1'b0;
      out_hs <= 1'b0;
      raddr_c <= '0;
      addr_pipe_q <= '0;
      count_q <= '0;
      active_q <= 1'b0;
    end else begin
      out_hs <= 1'b0;
      if (!enable_output) begin
        out_valid <= 1'b0;
        out_payload <= '0;
        out_last <= 1'b0;
        raddr_c <= '0;
        addr_pipe_q <= '0;
        count_q <= '0;
        active_q <= 1'b0;
      end else begin
        if (!active_q) begin
          raddr_c <= 6'd0;
          addr_pipe_q <= 6'd0;
          active_q <= 1'b1;
          count_q <= 7'd0;
        end

        if (!out_valid) begin
          out_valid <= 1'b1;
          out_payload <= rdata_c;
          out_last <= (count_q == C_COUNT-1);
        end else if (out_ready) begin
          out_hs <= 1'b1;
          if (count_q == C_COUNT-1) begin
            out_valid <= 1'b0;
            out_last <= 1'b0;
          end else begin
            count_q <= count_q + 1'b1;
            raddr_c <= count_q + 1'b1;
            addr_pipe_q <= count_q + 1'b1;
            out_payload <= rdata_c;
            out_last <= (count_q + 1'b1 == C_COUNT-1);
          end
        end
      end
    end
  end
endmodule
