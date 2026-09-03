module output_streamer #(
  parameter int TILE_N = 8,
  parameter int MAX_N = 64
)(
  input  logic clk,
  input  logic rst_n,
  input  logic do_start,
  input  logic [TILE_N-1:0] lane_active,
  input  logic signed [31:0] lane_data [0:TILE_N-1],
  output logic out_valid,
  input  logic out_ready,
  output logic signed [31:0] out_data,
  output logic emit_busy,
  output logic emit_done
);
  logic [$clog2(TILE_N)-1:0] lane_idx;
  logic started;
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      out_valid<=0; out_data<=0; emit_busy<=0; emit_done<=0; lane_idx<=0; started<=0;
    end else begin
      emit_done <= 0;
      if (do_start) begin
        emit_busy <= 1;
        lane_idx <= 0;
        started <= 1;
      end
      if (emit_busy && started) begin
        if (lane_active[lane_idx]) begin
          out_valid <= 1;
          out_data <= lane_data[lane_idx];
          if (out_valid && out_ready) begin
            if (lane_idx == TILE_N-1) begin
              emit_busy <= 0;
              emit_done <= 1;
              out_valid <= 0;
              started <= 0;
            end
            lane_idx <= lane_idx + 1;
          end
        end else begin
          if (lane_idx == TILE_N-1) begin
            emit_busy <= 0;
            emit_done <= 1;
            out_valid <= 0;
            started <= 0;
          end else lane_idx <= lane_idx + 1;
        end
      end else begin
        out_valid <= 0;
      end
    end
  end
endmodule
