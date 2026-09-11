module gemm8x8x32_bias_relu_top #(
  parameter int M_MAX    = 8,
  parameter int N_MAX    = 8,
  parameter int K_MAX    = 32,
  parameter int A_ELEM_W = 8,
  parameter int ACC_W    = 32
)(
  input  logic                      clk,
  input  logic                      rst,
  input  logic                      s_valid,
  output logic                      s_ready,
  input  logic signed [31:0]        s_data,
  input  logic        [1:0]         s_type,
  output logic                      m_valid,
  input  logic                      m_ready,
  output logic signed [31:0]        m_data,
  output logic                      busy,
  output logic                      done,
  output logic                      error
);
  localparam int A_DEPTH = M_MAX*K_MAX;
  localparam int B_DEPTH = K_MAX*N_MAX;
  localparam int O_DEPTH = M_MAX*N_MAX;
  localparam int A_AW = (A_DEPTH > 1) ? $clog2(A_DEPTH) : 1;
  localparam int B_AW = (B_DEPTH > 1) ? $clog2(B_DEPTH) : 1;
  localparam int N_AW = (N_MAX   > 1) ? $clog2(N_MAX)   : 1;
  localparam int O_AW = (O_DEPTH > 1) ? $clog2(O_DEPTH) : 1;

  typedef enum logic [2:0] {
    ST_IDLE,
    ST_LOAD,
    ST_COMPUTE,
    ST_POST,
    ST_OUTPUT,
    ST_DONE
  } state_t;

  state_t state;

  logic start_load, start_compute, start_post, start_out;
  logic load_done, load_error;
  logic compute_done, acc_valid;
  logic [((M_MAX>1)?$clog2(M_MAX):1)-1:0] acc_m;
  logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] acc_n;
  logic signed [ACC_W-1:0] acc_data;
  logic post_done;
  logic out_done;

  logic a_wr_en, b_wr_en, bias_wr_en, out_wr_en;
  logic [A_AW-1:0] a_wr_addr, a_rd_addr;
  logic [B_AW-1:0] b_wr_addr, b_rd_addr;
  logic [N_AW-1:0] bias_wr_addr, bias_rd_addr;
  logic [O_AW-1:0] out_wr_addr, out_rd_addr;
  logic signed [A_ELEM_W-1:0] a_wr_data, b_wr_data, a_rd_data, b_rd_data;
  logic signed [ACC_W-1:0] bias_wr_data, bias_rd_data, out_wr_data, out_rd_data;

  logic sticky_error;

  always_ff @(posedge clk) begin
    if (rst) begin
      state <= ST_IDLE;
      sticky_error <= 1'b0;
      done <= 1'b0;
      start_load <= 1'b0;
      start_compute <= 1'b0;
      start_post <= 1'b0;
      start_out <= 1'b0;
    end else begin
      done <= 1'b0;
      start_load <= 1'b0;
      start_compute <= 1'b0;
      start_post <= 1'b0;
      start_out <= 1'b0;

      if (load_error) sticky_error <= 1'b1;

      case (state)
        ST_IDLE: begin
          if (!sticky_error) begin
            start_load <= 1'b1;
            state <= ST_LOAD;
          end
        end
        ST_LOAD: begin
          if (load_done) begin
            start_compute <= 1'b1;
            start_post <= 1'b1;
            state <= ST_COMPUTE;
          end
        end
        ST_COMPUTE: begin
          if (compute_done) state <= ST_POST;
        end
        ST_POST: begin
          if (post_done) begin
            start_out <= 1'b1;
            state <= ST_OUTPUT;
          end
        end
        ST_OUTPUT: begin
          if (out_done) begin
            done <= 1'b1;
            state <= ST_DONE;
          end
        end
        ST_DONE: state <= ST_IDLE;
        default: state <= ST_IDLE;
      endcase
    end
  end

  input_loader #(.M_MAX(M_MAX),.N_MAX(N_MAX),.K_MAX(K_MAX),.A_ELEM_W(A_ELEM_W),.ACC_W(ACC_W)) u_loader (
    .clk(clk),.rst(rst),.start_load(start_load),.s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),.s_type(s_type),
    .a_wr_en(a_wr_en),.a_wr_addr(a_wr_addr),.a_wr_data(a_wr_data),
    .b_wr_en(b_wr_en),.b_wr_addr(b_wr_addr),.b_wr_data(b_wr_data),
    .bias_wr_en(bias_wr_en),.bias_wr_addr(bias_wr_addr),.bias_wr_data(bias_wr_data),
    .load_done(load_done),.error_flag(load_error)
  );

  gemm_core_seq #(.M_MAX(M_MAX),.N_MAX(N_MAX),.K_MAX(K_MAX),.A_ELEM_W(A_ELEM_W),.ACC_W(ACC_W)) u_gemm (
    .clk(clk),.rst(rst),.start_compute(start_compute),
    .a_rd_addr(a_rd_addr),.a_rd_data(a_rd_data),.b_rd_addr(b_rd_addr),.b_rd_data(b_rd_data),
    .acc_valid(acc_valid),.acc_m(acc_m),.acc_n(acc_n),.acc_data(acc_data),.compute_done(compute_done)
  );

  postproc_relu_bias #(.M_MAX(M_MAX),.N_MAX(N_MAX),.ACC_W(ACC_W)) u_post (
    .clk(clk),.rst(rst),.start_post(start_post),.acc_valid(acc_valid),.acc_m(acc_m),.acc_n(acc_n),.acc_data(acc_data),
    .bias_rd_addr(bias_rd_addr),.bias_rd_data(bias_rd_data),
    .out_wr_en(out_wr_en),.out_wr_addr(out_wr_addr),.out_wr_data(out_wr_data),.post_done(post_done)
  );

  output_streamer #(.M_MAX(M_MAX),.N_MAX(N_MAX),.ACC_W(ACC_W)) u_out (
    .clk(clk),.rst(rst),.start_out(start_out),.out_rd_addr(out_rd_addr),.out_rd_data(out_rd_data),
    .m_valid(m_valid),.m_ready(m_ready),.m_data(m_data),.out_done(out_done)
  );

  local_memories #(.M_MAX(M_MAX),.N_MAX(N_MAX),.K_MAX(K_MAX),.A_ELEM_W(A_ELEM_W),.ACC_W(ACC_W)) u_mem (
    .clk(clk),
    .a_wr_en(a_wr_en),.a_wr_addr(a_wr_addr),.a_wr_data(a_wr_data),.a_rd_addr(a_rd_addr),.a_rd_data(a_rd_data),
    .b_wr_en(b_wr_en),.b_wr_addr(b_wr_addr),.b_wr_data(b_wr_data),.b_rd_addr(b_rd_addr),.b_rd_data(b_rd_data),
    .bias_wr_en(bias_wr_en),.bias_wr_addr(bias_wr_addr),.bias_wr_data(bias_wr_data),.bias_rd_addr(bias_rd_addr),.bias_rd_data(bias_rd_data),
    .out_wr_en(out_wr_en),.out_wr_addr(out_wr_addr),.out_wr_data(out_wr_data),.out_rd_addr(out_rd_addr),.out_rd_data(out_rd_data)
  );

  assign busy  = (state != ST_IDLE);
  assign error = sticky_error;
endmodule
