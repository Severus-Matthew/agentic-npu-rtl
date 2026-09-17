module operand_buffer_bank #(
  parameter int M_FIXED = 8,
  parameter int N_FIXED = 8,
  parameter int K_FIXED = 32
) (
  input  logic                  clk,
  input  logic                  we_a,
  input  logic [7:0]            waddr_a,
  input  logic signed [7:0]     wdata_a,
  input  logic                  we_b,
  input  logic [7:0]            waddr_b,
  input  logic signed [7:0]     wdata_b,
  input  logic                  we_bias,
  input  logic [2:0]            waddr_bias,
  input  logic signed [31:0]    wdata_bias,
  input  logic [7:0]            raddr_a,
  output logic signed [7:0]     rdata_a,
  input  logic [7:0]            raddr_b,
  output logic signed [7:0]     rdata_b,
  input  logic [2:0]            raddr_bias,
  output logic signed [31:0]    rdata_bias,
  input  logic                  we_c,
  input  logic [5:0]            waddr_c,
  input  logic signed [31:0]    wdata_c,
  input  logic [5:0]            raddr_c,
  output logic signed [31:0]    rdata_c
);
  localparam int A_COUNT    = M_FIXED*K_FIXED;
  localparam int B_COUNT    = K_FIXED*N_FIXED;
  localparam int BIAS_COUNT = N_FIXED;
  localparam int C_COUNT    = M_FIXED*N_FIXED;

  logic signed [7:0]  a_buf [0:A_COUNT-1];
  logic signed [7:0]  b_buf [0:B_COUNT-1];
  logic signed [31:0] bias_buf [0:BIAS_COUNT-1];
  logic signed [31:0] c_buf [0:C_COUNT-1];

  always_ff @(posedge clk) begin
    if (we_a) a_buf[waddr_a] <= wdata_a;
    if (we_b) b_buf[waddr_b] <= wdata_b;
    if (we_bias) bias_buf[waddr_bias] <= wdata_bias;
    if (we_c) c_buf[waddr_c] <= wdata_c;

    rdata_a    <= a_buf[raddr_a];
    rdata_b    <= b_buf[raddr_b];
    rdata_bias <= bias_buf[raddr_bias];
    rdata_c    <= c_buf[raddr_c];
  end
endmodule
