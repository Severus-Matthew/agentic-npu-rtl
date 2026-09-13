module ctrl_fsm #(
  parameter int LANES = 16,
  parameter int MAX_M = 256,
  parameter int MAX_N = 256
) (
  input  logic                           clk,
  input  logic                           rst_n,
  input  logic                           cfg_valid,
  input  logic [$clog2(MAX_M+1)-1:0]     cfg_m,
  input  logic [$clog2(MAX_N+1)-1:0]     cfg_n,
  input  logic                           cfg_bias_en,
  input  logic                           cfg_relu_en,
  input  logic                           in_beat_accepted,
  input  logic                           out_beat_accepted,
  output logic                           compute_step_pulse,
  output logic                           row_finalize_pulse,
  output logic                           job_done_pulse,
  output logic                           busy,
  output logic                           status_err
);
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      compute_step_pulse <= 1'b0;
      row_finalize_pulse <= 1'b0;
      job_done_pulse <= 1'b0;
      busy <= 1'b0;
      status_err <= 1'b0;
    end else begin
      compute_step_pulse <= 1'b0;
      row_finalize_pulse <= 1'b0;
      job_done_pulse <= 1'b0;
      if (cfg_valid) begin
        if ((cfg_m == 0) || (cfg_n == 0) || (cfg_m > MAX_M) || (cfg_n > MAX_N)) begin
          status_err <= 1'b1;
          busy <= 1'b0;
        end else begin
          status_err <= 1'b0;
          busy <= 1'b1;
        end
      end
      if (in_beat_accepted) compute_step_pulse <= 1'b1;
      if (out_beat_accepted) row_finalize_pulse <= 1'b1;
      if (busy && out_beat_accepted) job_done_pulse <= 1'b0;
    end
  end
endmodule
