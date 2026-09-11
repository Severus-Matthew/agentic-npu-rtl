module input_loader #(
  parameter int M_MAX=8, N_MAX=8, K_MAX=32, A_ELEM_W=8, ACC_W=32
)(
  input  logic clk,
  input  logic rst,
  input  logic start_load,
  input  logic s_valid,
  output logic s_ready,
  input  logic signed [31:0] s_data,
  input  logic [1:0] s_type,
  output logic a_wr_en,
  output logic [((M_MAX*K_MAX>1)?$clog2(M_MAX*K_MAX):1)-1:0] a_wr_addr,
  output logic signed [A_ELEM_W-1:0] a_wr_data,
  output logic b_wr_en,
  output logic [((K_MAX*N_MAX>1)?$clog2(K_MAX*N_MAX):1)-1:0] b_wr_addr,
  output logic signed [A_ELEM_W-1:0] b_wr_data,
  output logic bias_wr_en,
  output logic [((N_MAX>1)?$clog2(N_MAX):1)-1:0] bias_wr_addr,
  output logic signed [ACC_W-1:0] bias_wr_data,
  output logic load_done,
  output logic error_flag
);
  localparam int A_CNT_MAX = M_MAX*K_MAX;
  localparam int B_CNT_MAX = K_MAX*N_MAX;
  localparam int C_CNT_MAX = N_MAX;
  typedef enum logic [2:0] {L_IDLE,L_CMD,L_A,L_B,L_BIAS,L_DONE,L_ERR} lstate_t;
  lstate_t st;
  int unsigned ca, cb, cc;

  always_ff @(posedge clk) begin
    if (rst) begin st<=L_IDLE; ca<=0; cb<=0; cc<=0; load_done<=0; error_flag<=0; end
    else begin
      load_done<=0; a_wr_en<=0; b_wr_en<=0; bias_wr_en<=0;
      case(st)
        L_IDLE: if(start_load) st<=L_CMD;
        L_CMD: if(s_valid) begin
          if(s_type!=2'b00 || s_data[7:0]!=8'sd1) begin error_flag<=1; st<=L_ERR; end
          else st<=L_A;
        end
        L_A: if(s_valid) begin
          if(s_type!=2'b01 || s_data[31:8]!=24'd0) begin error_flag<=1; st<=L_ERR; end
          else begin a_wr_en<=1; a_wr_addr<=ca; a_wr_data<=s_data[A_ELEM_W-1:0]; ca<=ca+1; if(ca+1==A_CNT_MAX) st<=L_B; end
        end
        L_B: if(s_valid) begin
          if(s_type!=2'b10 || s_data[31:8]!=24'd0) begin error_flag<=1; st<=L_ERR; end
          else begin b_wr_en<=1; b_wr_addr<=cb; b_wr_data<=s_data[A_ELEM_W-1:0]; cb<=cb+1; if(cb+1==B_CNT_MAX) st<=L_BIAS; end
        end
        L_BIAS: if(s_valid) begin
          if(s_type!=2'b11) begin error_flag<=1; st<=L_ERR; end
          else begin bias_wr_en<=1; bias_wr_addr<=cc; bias_wr_data<=s_data; cc<=cc+1; if(cc+1==C_CNT_MAX) begin st<=L_DONE; load_done<=1; end end
        end
        L_DONE: st<=L_DONE;
        L_ERR: st<=L_ERR;
      endcase
    end
  end
  assign s_ready = (st==L_CMD)||(st==L_A)||(st==L_B)||(st==L_BIAS);
endmodule
