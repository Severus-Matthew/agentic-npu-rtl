module gemm8x8x32_bias_relu_top #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32,
  parameter int A_ELEMS_FIXED = 256,
  parameter int B_ELEMS_FIXED = 256,
  parameter int Y_ELEMS_FIXED = 64
)(
  input  logic clk,
  input  logic rst,
  input  logic a_valid,
  output logic a_ready,
  input  logic signed [7:0] a_data,
  input  logic b_valid,
  output logic b_ready,
  input  logic signed [7:0] b_data,
  input  logic bias_valid,
  output logic bias_ready,
  input  logic signed [31:0] bias_data,
  output logic y_valid,
  input  logic y_ready,
  output logic signed [31:0] y_data,
  output logic done,
  output logic error
);

  localparam int ACC_ELEMS = M_FIXED*N_FIXED;
  typedef enum logic [3:0] {
    ST_RESET=4'd0, ST_IDLE=4'd1, ST_LOAD_A=4'd2, ST_LOAD_B=4'd3, ST_LOAD_BIAS=4'd4,
    ST_COMPUTE=4'd5, ST_FINALIZE=4'd6, ST_EMIT=4'd7, ST_DONE=4'd8
  } state_t;

  state_t state;
  logic error_sticky;

  logic load_a_en, load_b_en, load_bias_en;
  logic load_a_done, load_b_done, load_bias_done;
  logic load_err;

  logic compute_start, compute_done;
  logic finalize_start, finalize_done;
  logic emit_start, emit_done;

  logic [31:0] acc_rd_data;
  logic [31:0] bias_rd_data;
  logic [7:0]  a_rd_data;
  logic [7:0]  b_rd_data;
  logic [31:0] y_rd_data;

  logic a_wr_en, b_wr_en, bias_wr_en, y_wr_en, acc_wr_en;
  logic [$clog2(A_ELEMS_FIXED)-1:0] a_wr_addr, a_rd_addr;
  logic [$clog2(B_ELEMS_FIXED)-1:0] b_wr_addr, b_rd_addr;
  logic [$clog2(N_FIXED)-1:0] bias_wr_addr, bias_rd_addr;
  logic [$clog2(Y_ELEMS_FIXED)-1:0] y_wr_addr, y_rd_addr;
  logic [$clog2(ACC_ELEMS)-1:0] acc_wr_addr, acc_rd_addr;

  logic signed [7:0]  a_wr_data, b_wr_data;
  logic signed [31:0] bias_wr_data, y_wr_data, acc_wr_data;

  input_loader #(.A_ELEMS_FIXED(A_ELEMS_FIXED), .B_ELEMS_FIXED(B_ELEMS_FIXED), .N_FIXED(N_FIXED)) u_loader (.*);
  gemm_core_seq #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_core (.*);
  postproc_relu_bias #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED)) u_post (.*);
  output_streamer #(.Y_ELEMS_FIXED(Y_ELEMS_FIXED)) u_out (.*);
  local_memories #(.M_FIXED(M_FIXED), .N_FIXED(N_FIXED), .K_FIXED(K_FIXED)) u_mem (.*);

  always_ff @(posedge clk) begin
    if (rst) begin
      state <= ST_RESET;
      error_sticky <= 1'b0;
      done <= 1'b0;
    end else begin
      done <= 1'b0;
      if (load_err) error_sticky <= 1'b1;
      case (state)
        ST_RESET: state <= ST_IDLE;
        ST_IDLE: if (!error_sticky) state <= ST_LOAD_A;
        ST_LOAD_A: if (load_a_done) state <= ST_LOAD_B;
        ST_LOAD_B: if (load_b_done) state <= ST_LOAD_BIAS;
        ST_LOAD_BIAS: if (load_bias_done) state <= ST_COMPUTE;
        ST_COMPUTE: if (compute_done) state <= ST_FINALIZE;
        ST_FINALIZE: if (finalize_done) state <= ST_EMIT;
        ST_EMIT: if (emit_done) state <= ST_DONE;
        ST_DONE: begin done <= 1'b1; state <= ST_IDLE; end
        default: state <= ST_RESET;
      endcase
    end
  end

  assign error = error_sticky;
  assign load_a_en = (state==ST_LOAD_A) && !error_sticky;
  assign load_b_en = (state==ST_LOAD_B) && !error_sticky;
  assign load_bias_en = (state==ST_LOAD_BIAS) && !error_sticky;
  assign compute_start = (state==ST_COMPUTE) && !error_sticky;
  assign finalize_start = (state==ST_FINALIZE) && !error_sticky;
  assign emit_start = (state==ST_EMIT) && !error_sticky;

endmodule
