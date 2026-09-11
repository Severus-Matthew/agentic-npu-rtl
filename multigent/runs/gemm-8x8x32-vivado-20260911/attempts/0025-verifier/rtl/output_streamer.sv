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
  localparam int O_DEPTH=M_MAX*N_MAX;
  int unsigned idx;
  logic active;
  always_ff @(posedge clk) begin
    if(rst) begin idx<=0; active<=0; m_valid<=0; m_data<=0; out_done<=0; end
    else begin
      out_done<=0;
      if(start_out) begin active<=1; idx<=0; out_rd_addr<=0; m_valid<=1; m_data<=out_rd_data; end
      else if(active) begin
        if(m_valid && m_ready) begin
          if(idx==O_DEPTH-1) begin out_done<=1; active<=0; m_valid<=0; end
          else begin idx<=idx+1; out_rd_addr<=idx+1; m_data<=out_rd_data; m_valid<=1; end
        end
      end
    end
  end
endmodule
