module input_router #(
  parameter int MAX_N = 256,
  parameter int LANES = 16
) (
  input  logic                        clk,
  input  logic                        rst_n,
  input  logic                        in_valid,
  output logic                        in_ready,
  input  logic [31:0]                 in_data,
  input  logic [1:0]                  in_type,
  output logic                        cfg_valid,
  output logic [63:0]                 cfg_word,
  output logic                        x_we,
  output logic [$clog2(MAX_N)-1:0]    x_waddr,
  output logic signed [7:0]           x_wdata,
  output logic                        a_lane_valid,
  output logic [LANES*8-1:0]          a_lane_data,
  output logic                        bias_valid,
  output logic signed [31:0]          bias_data
);
  logic [$clog2(MAX_N)-1:0] x_count;
  assign in_ready = 1'b1;

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      cfg_valid <= 1'b0;
      cfg_word <= '0;
      x_we <= 1'b0;
      x_waddr <= '0;
      x_wdata <= '0;
      a_lane_valid <= 1'b0;
      a_lane_data <= '0;
      bias_valid <= 1'b0;
      bias_data <= '0;
      x_count <= '0;
    end else begin
      cfg_valid <= 1'b0;
      x_we <= 1'b0;
      a_lane_valid <= 1'b0;
      bias_valid <= 1'b0;
      if (in_valid && in_ready) begin
        case (in_type)
          2'b00: begin cfg_valid <= 1'b1; cfg_word <= {32'd0, in_data}; x_count <= '0; end
          2'b01: begin x_we <= 1'b1; x_waddr <= x_count; x_wdata <= $signed(in_data[7:0]); x_count <= x_count + 1'b1; end
          2'b10: begin a_lane_valid <= 1'b1; a_lane_data <= '0; a_lane_data[7:0] <= in_data[7:0]; end
          2'b11: begin bias_valid <= 1'b1; bias_data <= $signed(in_data); end
          default: begin end
        endcase
      end
    end
  end
endmodule
