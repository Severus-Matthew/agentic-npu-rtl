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

  localparam int A_AW = ((M_MAX*K_MAX)>1)?$clog2(M_MAX*K_MAX):1;
  localparam int B_AW = ((K_MAX*N_MAX)>1)?$clog2(K_MAX*N_MAX):1;
  localparam int C_AW = ((N_MAX)>1)?$clog2(N_MAX):1;

  typedef enum logic [2:0] {L_IDLE,L_CMD,L_A,L_B,L_BIAS,L_DONE,L_ERR} lstate_t;
  lstate_t st;

  logic [A_AW-1:0] ca;
  logic [B_AW-1:0] cb;
  logic [C_AW-1:0] cc;

  always_ff @(posedge clk) begin
    if (rst) begin
      st <= L_IDLE;
      ca <= '0;
      cb <= '0;
      cc <= '0;
      load_done <= 1'b0;
      error_flag <= 1'b0;
      a_wr_en <= 1'b0;
      b_wr_en <= 1'b0;
      bias_wr_en <= 1'b0;
      a_wr_addr <= '0;
      b_wr_addr <= '0;
      bias_wr_addr <= '0;
      a_wr_data <= '0;
      b_wr_data <= '0;
      bias_wr_data <= '0;
    end else begin
      load_done <= 1'b0;
      a_wr_en <= 1'b0;
      b_wr_en <= 1'b0;
      bias_wr_en <= 1'b0;

      if (start_load) begin
        st <= L_CMD;
        ca <= '0;
        cb <= '0;
        cc <= '0;
      end else begin
        case (st)
          L_IDLE: begin end
          L_CMD: if (s_valid) begin
            if ((s_type!=2'b00) || (s_data[7:0]!=8'd1) || (s_data[31:8]!=24'd0)) begin
              error_flag<=1'b1; st<=L_ERR;
            end else begin
              st <= L_A;
            end
          end
          L_A: if (s_valid) begin
            if ((s_type!=2'b01) || (s_data[31:8]!=24'd0)) begin error_flag<=1'b1; st<=L_ERR; end
            else begin
              a_wr_en <= 1'b1;
              a_wr_addr <= ca;
              a_wr_data <= s_data[A_ELEM_W-1:0];
              if (ca == A_CNT_MAX-1) st <= L_B;
              else ca <= ca + 1'b1;
            end
          end
          L_B: if (s_valid) begin
            if ((s_type!=2'b10) || (s_data[31:8]!=24'd0)) begin error_flag<=1'b1; st<=L_ERR; end
            else begin
              b_wr_en <= 1'b1;
              b_wr_addr <= cb;
              b_wr_data <= s_data[A_ELEM_W-1:0];
              if (cb == B_CNT_MAX-1) st <= L_BIAS;
              else cb <= cb + 1'b1;
            end
          end
          L_BIAS: if (s_valid) begin
            if (s_type!=2'b11) begin error_flag<=1'b1; st<=L_ERR; end
            else begin
              bias_wr_en <= 1'b1;
              bias_wr_addr <= cc;
              bias_wr_data <= s_data;
              if (cc == C_CNT_MAX-1) begin st<=L_DONE; load_done<=1'b1; end
              else cc <= cc + 1'b1;
            end
          end
          L_DONE: st <= L_IDLE;
          L_ERR: st <= L_ERR;
          default: st <= L_IDLE;
        endcase
      end
    end
  end

  assign s_ready = (st==L_CMD)||(st==L_A)||(st==L_B)||(st==L_BIAS);
endmodule
