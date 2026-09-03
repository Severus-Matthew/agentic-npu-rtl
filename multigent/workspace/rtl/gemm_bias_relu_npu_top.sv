module gemm_bias_relu_npu_top #(
  parameter int MAX_M = 64,
  parameter int MAX_N = 64,
  parameter int MAX_K = 64,
  parameter int TILE_N = 8
) (
  input  logic                     clk,
  input  logic                     rst_n,
  input  logic                     cmd_valid,
  output logic                     cmd_ready,
  input  logic [95:0]              cmd_data,
  input  logic                     a_valid,
  output logic                     a_ready,
  input  logic signed [7:0]        a_data,
  input  logic                     b_valid,
  output logic                     b_ready,
  input  logic signed [7:0]        b_data,
  input  logic                     bias_valid,
  output logic                     bias_ready,
  input  logic signed [31:0]       bias_data,
  output logic                     out_valid,
  input  logic                     out_ready,
  output logic signed [31:0]       out_data,
  output logic                     status_done,
  output logic                     status_error
);
  localparam int A_DEPTH = MAX_M*MAX_K;
  localparam int B_DEPTH = MAX_K*MAX_N;

  logic [15:0] cfg_m, cfg_n, cfg_k;
  logic        cfg_bias_enable;

  logic st_load_a, st_load_b, st_load_bias, st_compute, st_emit;
  logic do_compute_start, do_compute_step, do_emit_start, do_done_pulse;

  logic load_a_done, load_b_done, load_bias_done;

  logic [$clog2(A_DEPTH)-1:0] a_wr_addr;
  logic [$clog2(B_DEPTH)-1:0] b_wr_addr;
  logic [$clog2(MAX_N)-1:0]   bias_wr_addr;
  logic                       a_wr_en, b_wr_en, bias_wr_en;

  logic signed [7:0]   buf_A [0:A_DEPTH-1];
  logic signed [7:0]   buf_B [0:B_DEPTH-1];
  logic signed [31:0]  buf_bias [0:MAX_N-1];

  logic [$clog2(MAX_M)-1:0] idx_m;
  logic [$clog2(MAX_N)-1:0] idx_n_base;
  logic [$clog2(MAX_K)-1:0] idx_k;
  logic [TILE_N-1:0]        lane_active;

  logic signed [7:0] a_elem;
  logic signed [7:0] b_vec [0:TILE_N-1];

  logic compute_tile_done;
  logic signed [31:0] lane_acc [0:TILE_N-1];

  logic signed [31:0] lane_post [0:TILE_N-1];

  logic emit_busy;
  logic emit_done;

  npu_control_fsm #(.MAX_M(MAX_M), .MAX_N(MAX_N), .MAX_K(MAX_K), .TILE_N(TILE_N)) u_ctrl (
    .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_data(cmd_data),
    .load_a_done(load_a_done), .load_b_done(load_b_done), .load_bias_done(load_bias_done),
    .compute_tile_done(compute_tile_done), .emit_done(emit_done),
    .cfg_m(cfg_m), .cfg_n(cfg_n), .cfg_k(cfg_k), .cfg_bias_enable(cfg_bias_enable),
    .st_load_a(st_load_a), .st_load_b(st_load_b), .st_load_bias(st_load_bias), .st_compute(st_compute), .st_emit(st_emit),
    .do_compute_start(do_compute_start), .do_compute_step(do_compute_step), .do_emit_start(do_emit_start), .do_done_pulse(do_done_pulse),
    .idx_m(idx_m), .idx_n_base(idx_n_base), .idx_k(idx_k), .lane_active(lane_active),
    .status_error(status_error)
  );

  input_loader #(.MAX_M(MAX_M), .MAX_N(MAX_N), .MAX_K(MAX_K)) u_loader (
    .clk(clk), .rst_n(rst_n), .st_load_a(st_load_a), .st_load_b(st_load_b), .st_load_bias(st_load_bias), .bias_enable(cfg_bias_enable),
    .cfg_m(cfg_m), .cfg_n(cfg_n), .cfg_k(cfg_k),
    .a_valid(a_valid), .a_ready(a_ready), .a_data(a_data),
    .b_valid(b_valid), .b_ready(b_ready), .b_data(b_data),
    .bias_valid(bias_valid), .bias_ready(bias_ready), .bias_data(bias_data),
    .a_wr_en(a_wr_en), .a_wr_addr(a_wr_addr), .a_wr_data(),
    .b_wr_en(b_wr_en), .b_wr_addr(b_wr_addr), .b_wr_data(),
    .bias_wr_en(bias_wr_en), .bias_wr_addr(bias_wr_addr), .bias_wr_data(),
    .load_a_done(load_a_done), .load_b_done(load_b_done), .load_bias_done(load_bias_done)
  );

  always_ff @(posedge clk) begin
    if (a_wr_en) buf_A[a_wr_addr] <= a_data;
    if (b_wr_en) buf_B[b_wr_addr] <= b_data;
    if (bias_wr_en) buf_bias[bias_wr_addr] <= bias_data;
  end

  always_comb begin
    int n_idx;
    a_elem = buf_A[(idx_m*cfg_k)+idx_k];
    for (int i = 0; i < TILE_N; i++) begin
      n_idx = idx_n_base + i;
      if (lane_active[i]) b_vec[i] = buf_B[(idx_k*cfg_n)+n_idx];
      else                b_vec[i] = '0;
    end
  end

  gemm_core #(.TILE_N(TILE_N), .MAX_K(MAX_K), .MAX_N(MAX_N)) u_core (
    .clk(clk), .rst_n(rst_n), .do_start(do_compute_start), .do_step(do_compute_step), .cfg_k(cfg_k), .lane_active(lane_active),
    .a_elem(a_elem), .b_vec(b_vec), .tile_done(compute_tile_done), .lane_acc(lane_acc)
  );

  postproc_relu_bias #(.TILE_N(TILE_N)) u_post (
    .bias_enable(cfg_bias_enable), .lane_active(lane_active), .idx_n_base(idx_n_base), .cfg_n(cfg_n), .lane_acc(lane_acc), .bias_mem(buf_bias), .lane_out(lane_post)
  );

  output_streamer #(.TILE_N(TILE_N), .MAX_N(MAX_N)) u_out (
    .clk(clk), .rst_n(rst_n), .do_start(do_emit_start), .lane_active(lane_active), .lane_data(lane_post),
    .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .emit_busy(emit_busy), .emit_done(emit_done)
  );

  always_ff @(posedge clk) begin
    if (!rst_n) status_done <= 1'b0;
    else        status_done <= do_done_pulse;
  end
endmodule
