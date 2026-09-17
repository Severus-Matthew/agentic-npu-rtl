module mv_npu_top #(
  parameter int LANES = 16,
  parameter int MAX_M = 256,
  parameter int MAX_N = 256
) (
  input  logic                 clk,
  input  logic                 rst_n,
  input  logic                 in_valid,
  output logic                 in_ready,
  input  logic [31:0]          in_data,
  input  logic [1:0]           in_type,
  input  logic                 in_last,
  output logic                 out_valid,
  input  logic                 out_ready,
  output logic signed [31:0]   out_data,
  output logic                 out_last,
  output logic                 busy,
  output logic                 status_err
);
  localparam int MW = $clog2(MAX_M+1);
  localparam int NW = $clog2(MAX_N+1);
  localparam int XAW = (MAX_N <= 1) ? 1 : $clog2(MAX_N);

  logic                 cfg_valid;
  logic [63:0]          cfg_word;
  logic                 x_we;
  logic [XAW-1:0]       x_waddr;
  logic signed [7:0]    x_wdata;
  logic                 a_lane_valid;
  logic [LANES*8-1:0]   a_lane_data;
  logic                 bias_valid;
  logic signed [31:0]   bias_data;

  logic [MW-1:0]        cfg_m;
  logic [NW-1:0]        cfg_n;
  logic                 cfg_bias_en;
  logic                 cfg_relu_en;

  logic                 compute_step_pulse;
  logic                 row_finalize_pulse;
  logic                 job_done_pulse;

  logic signed [7:0]    x_rdata;
  logic [XAW-1:0]       x_raddr;

  logic                 start_row;
  logic                 step_valid;
  logic signed [7:0]    a_val;
  logic signed [7:0]    x_val;
  logic signed [31:0]   acc_out;

  logic signed [31:0]   bias_hold;
  logic signed [31:0]   y_post;

  logic                 out_in_valid;
  logic signed [31:0]   out_in_data;
  logic                 out_in_last;
  logic                 out_accept_pulse;

  logic [MW-1:0]        m_runtime;
  logic [NW-1:0]        n_runtime;
  logic                 bias_en_runtime;
  logic                 relu_en_runtime;

  logic [MW-1:0]        row_idx;
  logic [NW-1:0]        col_idx;
  logic                 compute_active;

  assign cfg_m       = cfg_word[15:8];
  assign cfg_n       = cfg_word[23:16];
  assign cfg_bias_en = cfg_word[0];
  assign cfg_relu_en = cfg_word[1];

  input_router #(
    .MAX_N(MAX_N),
    .LANES(LANES)
  ) u_input_router (
    .clk(clk), .rst_n(rst_n),
    .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_type(in_type),
    .cfg_valid(cfg_valid), .cfg_word(cfg_word),
    .x_we(x_we), .x_waddr(x_waddr), .x_wdata(x_wdata),
    .a_lane_valid(a_lane_valid), .a_lane_data(a_lane_data),
    .bias_valid(bias_valid), .bias_data(bias_data)
  );

  ctrl_fsm #(.LANES(LANES), .MAX_M(MAX_M), .MAX_N(MAX_N)) u_ctrl (
    .clk(clk), .rst_n(rst_n),
    .cfg_valid(cfg_valid), .cfg_m(cfg_m), .cfg_n(cfg_n), .cfg_bias_en(cfg_bias_en), .cfg_relu_en(cfg_relu_en),
    .in_beat_accepted(in_valid && in_ready),
    .out_beat_accepted(out_accept_pulse),
    .compute_step_pulse(compute_step_pulse),
    .row_finalize_pulse(row_finalize_pulse),
    .job_done_pulse(job_done_pulse),
    .busy(busy), .status_err(status_err)
  );

  x_buffer_mem #(.MAX_N(MAX_N)) u_xmem (
    .clk(clk),
    .we(x_we), .waddr(x_waddr), .wdata(x_wdata),
    .raddr(x_raddr), .rdata(x_rdata)
  );

  mac16_core #(.LANES(LANES), .MAX_N(MAX_N)) u_mac (
    .clk(clk), .rst_n(rst_n),
    .start_row(start_row), .step_valid(step_valid),
    .a_val(a_val), .x_val(x_val),
    .acc_out(acc_out)
  );

  postproc_unit u_post (
    .acc_in(acc_out), .bias_in(bias_hold), .bias_en(bias_en_runtime), .relu_en(relu_en_runtime), .y_out(y_post)
  );

  output_if u_out (
    .clk(clk), .rst_n(rst_n),
    .in_valid(out_in_valid), .in_data(out_in_data), .in_last(out_in_last),
    .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
    .out_accept_pulse(out_accept_pulse)
  );

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      m_runtime <= '0;
      n_runtime <= '0;
      bias_en_runtime <= 1'b0;
      relu_en_runtime <= 1'b0;
      row_idx <= '0;
      col_idx <= '0;
      compute_active <= 1'b0;
      x_raddr <= '0;
      start_row <= 1'b0;
      step_valid <= 1'b0;
      a_val <= '0;
      x_val <= '0;
      bias_hold <= '0;
      out_in_valid <= 1'b0;
      out_in_data <= '0;
      out_in_last <= 1'b0;
    end else begin
      start_row <= 1'b0;
      step_valid <= 1'b0;
      out_in_valid <= 1'b0;

      if (cfg_valid) begin
        m_runtime <= cfg_m;
        n_runtime <= cfg_n;
        bias_en_runtime <= cfg_bias_en;
        relu_en_runtime <= cfg_relu_en;
        row_idx <= '0;
        col_idx <= '0;
        compute_active <= 1'b1;
        start_row <= 1'b1;
      end

      if (compute_active && a_lane_valid) begin
        a_val <= $signed(a_lane_data[7:0]);
        x_raddr <= col_idx[XAW-1:0];
        x_val <= x_rdata;
        step_valid <= 1'b1;
        if (col_idx == n_runtime - 1'b1) begin
          col_idx <= '0;
          if (bias_valid) bias_hold <= bias_data;
          out_in_valid <= 1'b1;
          out_in_data <= y_post;
          out_in_last <= (row_idx == m_runtime - 1'b1);
          if (row_idx == m_runtime - 1'b1) begin
            compute_active <= 1'b0;
          end else begin
            row_idx <= row_idx + 1'b1;
            start_row <= 1'b1;
          end
        end else begin
          col_idx <= col_idx + 1'b1;
        end
      end
    end
  end
endmodule
