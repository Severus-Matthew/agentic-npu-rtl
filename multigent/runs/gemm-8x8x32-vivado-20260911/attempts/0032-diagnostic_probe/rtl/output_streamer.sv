module output_streamer #(
  parameter int M_MAX=8, N_MAX=8, ACC_W=32
)(
  input logic clk,
  input logic rst,
  input logic start_out,
  output logic [((M_MAX*N_MAX>1)?$clog2(M_MAX*N_MAX):1)-1:0] out_rd_addr,
  input  logic signed [ACC_W-1:0] out_rd_data,
  output logic m_valid,
  input  logic m_ready,
  output logic signed [ACC_W-1:0] m_data,
  output logic out_done
);
  localparam int O_DEPTH = M_MAX*N_MAX;
  localparam int O_W = (O_DEPTH>1)?$clog2(O_DEPTH):1;

  logic active;
  logic [O_W-1:0] rd_issue_idx;
  logic [O_W-1:0] sent_cnt;
  logic pending_data;

  always_ff @(posedge clk) begin
    if(rst) begin
      active <= 1'b0;
      rd_issue_idx <= '0;
      sent_cnt <= '0;
      pending_data <= 1'b0;
      out_rd_addr <= '0;
      m_valid <= 1'b0;
      m_data <= '0;
      out_done <= 1'b0;
    end else begin
      out_done <= 1'b0;

      if (start_out) begin
        active <= 1'b1;
        rd_issue_idx <= '0;
        sent_cnt <= '0;
        pending_data <= 1'b1;
        out_rd_addr <= '0;
        m_valid <= 1'b0;
      end else begin
        if (pending_data) begin
          m_data <= out_rd_data;
          m_valid <= 1'b1;
          pending_data <= 1'b0;
        end

        if (active && m_valid && m_ready) begin
          if (sent_cnt == O_DEPTH-1) begin
            out_done <= 1'b1;
            active <= 1'b0;
            m_valid <= 1'b0;
          end else begin
            sent_cnt <= sent_cnt + 1'b1;
            rd_issue_idx <= rd_issue_idx + 1'b1;
            out_rd_addr <= rd_issue_idx + 1'b1;
            m_valid <= 1'b0;
            pending_data <= 1'b1;
          end
        end
      end
    end
  end
endmodule
