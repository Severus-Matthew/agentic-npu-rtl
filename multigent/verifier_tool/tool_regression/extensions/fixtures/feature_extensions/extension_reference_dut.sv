module extension_reference_dut (
    input  logic clk,
    input  logic rst_n,

    input  logic signed [7:0] op_a,
    input  logic signed [7:0] op_b,
    input  logic signed [7:0] op_bias,
    input  logic [2:0] shape_m,
    output logic signed [31:0] gemm_result,

    input  logic signed [7:0] matrix_a00,
    input  logic signed [7:0] matrix_a01,
    input  logic signed [7:0] matrix_a10,
    input  logic signed [7:0] matrix_a11,
    input  logic signed [7:0] matrix_a20,
    input  logic signed [7:0] matrix_a21,
    input  logic signed [7:0] matrix_a30,
    input  logic signed [7:0] matrix_a31,
    input  logic signed [7:0] matrix_b0,
    input  logic signed [7:0] matrix_b1,
    output logic signed [31:0] matrix_c0,
    output logic signed [31:0] matrix_c1,
    output logic signed [31:0] matrix_c2,
    output logic signed [31:0] matrix_c3,
    output logic [3:0] matrix_result_valid,

    input  logic [1:0] sparse_idx0,
    input  logic [1:0] sparse_idx1,
    input  logic signed [7:0] sparse_val0,
    input  logic signed [7:0] sparse_val1,
    input  logic signed [7:0] dense0,
    input  logic signed [7:0] dense1,
    input  logic signed [7:0] dense2,
    input  logic signed [7:0] dense3,
    output logic signed [31:0] sparse_result,

    input  logic signed [7:0] conv_x0,
    input  logic signed [7:0] conv_x1,
    input  logic signed [7:0] conv_x2,
    input  logic signed [7:0] conv_k0,
    input  logic signed [7:0] conv_k1,
    input  logic signed [7:0] conv_k2,
    output logic signed [31:0] conv_result,

    input  logic signed [7:0] attention_q,
    input  logic signed [7:0] attention_k,
    input  logic attention_mask,
    output logic signed [31:0] attention_result,
    input  logic signed [7:0] attention_k0,
    input  logic signed [7:0] attention_k1,
    input  logic signed [7:0] attention_v0,
    input  logic signed [7:0] attention_v1,
    input  logic attention_mask0,
    input  logic attention_mask1,
    output logic signed [31:0] sparse_attention_result,

    input  logic [2:0] round_shift,
    output logic signed [31:0] rounded_result,

    input  logic req_valid,
    output logic req_ready,
    input  logic [31:0] req_data,
    input  logic [3:0] req_id,
    input  logic req_last,
    input  logic [2:0] req_empty,
    input  logic [7:0] req_len,
    input  logic [3:0] req_delay,
    input  logic reverse_responses,
    output logic rsp_valid,
    input  logic rsp_ready,
    output logic [31:0] rsp_data,
    output logic [3:0] rsp_id,
    output logic rsp_last,
    output logic [2:0] rsp_empty,
    output logic [7:0] rsp_len,

    input  logic wb_cyc,
    input  logic wb_stb,
    input  logic wb_we,
    input  logic [31:0] wb_addr,
    input  logic [31:0] wb_wdata,
    input  logic [3:0] wb_delay,
    output logic wb_ack,
    output logic wb_err,
    output logic [31:0] wb_rdata,

    input  logic tl_a_valid,
    output logic tl_a_ready,
    input  logic [3:0] tl_a_source,
    input  logic [31:0] tl_a_data,
    output logic tl_d_valid,
    input  logic tl_d_ready,
    output logic [3:0] tl_d_source,
    output logic [31:0] tl_d_data,

    input  logic avmm_read,
    input  logic [31:0] avmm_address,
    input  logic [7:0] avmm_burstcount,
    input  logic [3:0] avmm_delay,
    output logic avmm_waitrequest,
    output logic avmm_readdatavalid,
    output logic [31:0] avmm_readdata,
    output logic [1:0] avmm_response,

    input  logic avst_in_valid,
    output logic avst_in_ready,
    input  logic [31:0] avst_in_data,
    input  logic avst_in_startofpacket,
    input  logic avst_in_endofpacket,
    input  logic [2:0] avst_in_empty,
    output logic avst_out_valid,
    input  logic avst_out_ready,
    output logic [31:0] avst_out_data,
    output logic avst_out_startofpacket,
    output logic avst_out_endofpacket,
    output logic [2:0] avst_out_empty,

    input  logic x_arvalid,
    output logic x_arready,
    input  logic [31:0] x_araddr,
    input  logic [3:0] x_arepoch,
    input  logic x_force_retry,
    output logic x_rvalid,
    input  logic x_rready,
    output logic [31:0] x_rdata,
    output logic [1:0] x_rresp,
    output logic [3:0] x_repoch,

    input  logic four_req,
    output logic four_ack,

    input  logic start,
    input  logic cancel,
    input  logic software_ack,
    input  logic illegal_command,
    input  logic sticky_completion,
    input  logic queue_enable,
    input  logic checkpoint_reset,
    input  logic [3:0] work_cycles,
    input  logic [3:0] job_id,
    output logic busy,
    output logic completion,
    output logic [3:0] completion_id,
    output logic error,
    output logic [3:0] accepted_jobs
);
    logic signed [7:0] dense [0:3];
    logic signed [31:0] gemm_accumulator;
    logic signed [31:0] attention_score0;
    logic signed [31:0] attention_score1;
    logic signed [31:0] attention_weight0;
    logic signed [31:0] attention_weight1;
    logic signed [31:0] attention_weight_sum;
    always_comb begin
        dense[0] = dense0;
        dense[1] = dense1;
        dense[2] = dense2;
        dense[3] = dense3;
        gemm_accumulator = $signed(op_a) * $signed(op_b)
                         + $signed({{24{op_bias[7]}}, op_bias});
        gemm_result = gemm_accumulator * $signed({1'b0, shape_m});
        matrix_c0 = $signed(matrix_a00) * $signed(matrix_b0)
                  + $signed(matrix_a01) * $signed(matrix_b1);
        matrix_c1 = $signed(matrix_a10) * $signed(matrix_b0)
                  + $signed(matrix_a11) * $signed(matrix_b1);
        matrix_c2 = $signed(matrix_a20) * $signed(matrix_b0)
                  + $signed(matrix_a21) * $signed(matrix_b1);
        matrix_c3 = $signed(matrix_a30) * $signed(matrix_b0)
                  + $signed(matrix_a31) * $signed(matrix_b1);
        case (shape_m)
            3'd1: matrix_result_valid = 4'b0001;
            3'd2: matrix_result_valid = 4'b0011;
            3'd4: matrix_result_valid = 4'b1111;
            default: matrix_result_valid = 4'b0000;
        endcase
        sparse_result = $signed(sparse_val0) * $signed(dense[sparse_idx0])
                      + $signed(sparse_val1) * $signed(dense[sparse_idx1]);
        conv_result = $signed(conv_x0) * $signed(conv_k0)
                    + $signed(conv_x1) * $signed(conv_k1)
                    + $signed(conv_x2) * $signed(conv_k2);
        attention_result = attention_mask ? 32'sd0 : $signed(attention_q) * $signed(attention_k);
        attention_score0 = $signed(attention_q) * $signed(attention_k0);
        attention_score1 = $signed(attention_q) * $signed(attention_k1);
        attention_weight0 = attention_mask0 || attention_score0 < 0 ? 0 : attention_score0;
        attention_weight1 = attention_mask1 || attention_score1 < 0 ? 0 : attention_score1;
        attention_weight_sum = attention_weight0 + attention_weight1;
        sparse_attention_result = attention_weight_sum == 0
                                ? 0
                                : (attention_weight0 * $signed(attention_v0)
                                 + attention_weight1 * $signed(attention_v1))
                                  / attention_weight_sum;
        rounded_result = round_shift == 0
                       ? gemm_result
                       : (gemm_result + (32'sd1 <<< (round_shift - 1'b1))) >>> round_shift;
    end

    logic [31:0] queue_data [0:1];
    logic [3:0] queue_id [0:1];
    logic queue_last [0:1];
    logic [2:0] queue_empty [0:1];
    logic [7:0] queue_len [0:1];
    logic [1:0] queue_count;
    logic [3:0] delay_count;
    logic reverse_second_pending;

    assign req_ready = queue_count < 2;
    assign four_ack = four_req;

    logic [3:0] remaining;
    logic [1:0] drain_remaining;
    logic cancelling;
    logic queued_job;
    logic [3:0] active_job_id;
    logic [3:0] queued_job_id;

    logic wb_pending;
    logic [3:0] wb_wait_count;
    logic [31:0] wb_saved_addr;
    logic [31:0] wb_saved_data;
    logic wb_saved_we;

    logic [31:0] tl_data_queue [0:1];
    logic [3:0] tl_source_queue [0:1];
    logic [1:0] tl_count;
    logic tl_second_pending;
    assign tl_a_ready = tl_count < 2;

    logic avmm_active;
    logic [3:0] avmm_wait_count;
    logic [7:0] avmm_beats_left;
    logic [7:0] avmm_beat_index;
    logic [31:0] avmm_saved_address;
    assign avmm_waitrequest = avmm_active;

    assign avst_in_ready = !avst_out_valid || avst_out_ready;

    logic x_pending;
    logic [31:0] x_saved_addr;
    logic [3:0] x_saved_epoch;
    logic x_saved_retry;
    assign x_arready = !x_pending && !x_rvalid;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            x_pending <= 1'b0;
            x_saved_addr <= '0;
            x_saved_epoch <= '0;
            x_saved_retry <= 1'b0;
            x_rvalid <= 1'b0;
            x_rdata <= '0;
            x_rresp <= '0;
            x_repoch <= '0;
        end else begin
            if (x_rvalid && x_rready)
                x_rvalid <= 1'b0;
            if (x_arvalid && x_arready) begin
                x_pending <= 1'b1;
                x_saved_addr <= x_araddr;
                x_saved_epoch <= x_arepoch;
                x_saved_retry <= x_force_retry;
            end else if (x_pending && !x_rvalid) begin
                x_pending <= 1'b0;
                x_rvalid <= 1'b1;
                x_rdata <= x_saved_addr + 1'b1;
                x_rresp <= x_saved_retry ? 2'b10 : 2'b00;
                x_repoch <= x_saved_epoch;
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            wb_pending <= 1'b0;
            wb_wait_count <= '0;
            wb_saved_addr <= '0;
            wb_saved_data <= '0;
            wb_saved_we <= 1'b0;
            wb_ack <= 1'b0;
            wb_err <= 1'b0;
            wb_rdata <= '0;
        end else begin
            wb_ack <= 1'b0;
            wb_err <= 1'b0;
            if (!wb_pending && wb_cyc && wb_stb) begin
                wb_pending <= 1'b1;
                wb_wait_count <= wb_delay;
                wb_saved_addr <= wb_addr;
                wb_saved_data <= wb_wdata;
                wb_saved_we <= wb_we;
            end else if (wb_pending) begin
                if (wb_wait_count != 0)
                    wb_wait_count <= wb_wait_count - 1'b1;
                else begin
                    wb_ack <= 1'b1;
                    wb_rdata <= wb_saved_we
                              ? wb_saved_data
                              : wb_saved_addr ^ wb_saved_data;
                    wb_pending <= 1'b0;
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            tl_count <= 0;
            tl_second_pending <= 1'b0;
            tl_d_valid <= 1'b0;
            tl_d_source <= '0;
            tl_d_data <= '0;
        end else begin
            if (tl_d_valid && tl_d_ready)
                tl_d_valid <= 1'b0;
            if (tl_a_valid && tl_a_ready) begin
                tl_data_queue[tl_count[0]] <= tl_a_data;
                tl_source_queue[tl_count[0]] <= tl_a_source;
                tl_count <= tl_count + 1'b1;
            end
            if (!tl_d_valid) begin
                if (tl_count == 2) begin
                    tl_d_valid <= 1'b1;
                    tl_d_source <= tl_source_queue[1];
                    tl_d_data <= tl_data_queue[1];
                    tl_count <= 1;
                    tl_second_pending <= 1'b1;
                end else if (tl_second_pending && tl_count == 1) begin
                    tl_d_valid <= 1'b1;
                    tl_d_source <= tl_source_queue[0];
                    tl_d_data <= tl_data_queue[0];
                    tl_count <= 0;
                    tl_second_pending <= 1'b0;
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            avmm_active <= 1'b0;
            avmm_wait_count <= '0;
            avmm_beats_left <= '0;
            avmm_beat_index <= '0;
            avmm_saved_address <= '0;
            avmm_readdatavalid <= 1'b0;
            avmm_readdata <= '0;
            avmm_response <= '0;
        end else begin
            avmm_readdatavalid <= 1'b0;
            if (!avmm_active && avmm_read) begin
                avmm_active <= 1'b1;
                avmm_wait_count <= avmm_delay;
                avmm_beats_left <= avmm_burstcount;
                avmm_beat_index <= 0;
                avmm_saved_address <= avmm_address;
            end else if (avmm_active) begin
                if (avmm_wait_count != 0)
                    avmm_wait_count <= avmm_wait_count - 1'b1;
                else if (avmm_beats_left != 0) begin
                    avmm_readdatavalid <= 1'b1;
                    avmm_readdata <= avmm_saved_address + {24'b0, avmm_beat_index};
                    avmm_response <= 0;
                    avmm_beat_index <= avmm_beat_index + 1'b1;
                    avmm_beats_left <= avmm_beats_left - 1'b1;
                    if (avmm_beats_left == 1)
                        avmm_active <= 1'b0;
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            avst_out_valid <= 1'b0;
            avst_out_data <= '0;
            avst_out_startofpacket <= 1'b0;
            avst_out_endofpacket <= 1'b0;
            avst_out_empty <= '0;
        end else if (avst_in_ready) begin
            avst_out_valid <= avst_in_valid;
            if (avst_in_valid) begin
                avst_out_data <= avst_in_data;
                avst_out_startofpacket <= avst_in_startofpacket;
                avst_out_endofpacket <= avst_in_endofpacket;
                avst_out_empty <= avst_in_empty;
            end
        end
    end

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            rsp_valid <= 1'b0;
            rsp_data <= '0;
            rsp_id <= '0;
            rsp_last <= 1'b0;
            rsp_empty <= '0;
            rsp_len <= '0;
            queue_count <= '0;
            delay_count <= '0;
            reverse_second_pending <= 1'b0;
            completion <= 1'b0;
            completion_id <= '0;
            error <= 1'b0;
            accepted_jobs <= '0;
            if (!checkpoint_reset) begin
                busy <= 1'b0;
                remaining <= '0;
                drain_remaining <= '0;
                cancelling <= 1'b0;
                queued_job <= 1'b0;
                active_job_id <= '0;
                queued_job_id <= '0;
            end
        end else begin
            if (!sticky_completion)
                completion <= 1'b0;
            if (software_ack) begin
                completion <= 1'b0;
                error <= 1'b0;
            end
            if (illegal_command)
                error <= 1'b1;

            if (start) begin
                if (!busy) begin
                    busy <= 1'b1;
                    remaining <= work_cycles;
                    active_job_id <= job_id;
                    accepted_jobs <= accepted_jobs + 1'b1;
                end else if (queue_enable && !queued_job) begin
                    queued_job <= 1'b1;
                    queued_job_id <= job_id;
                    accepted_jobs <= accepted_jobs + 1'b1;
                end
            end
            if (busy) begin
                if (cancel && !cancelling) begin
                    cancelling <= 1'b1;
                    drain_remaining <= 2;
                end else if (cancelling) begin
                    if (drain_remaining > 1)
                        drain_remaining <= drain_remaining - 1'b1;
                    else begin
                        drain_remaining <= '0;
                        cancelling <= 1'b0;
                        busy <= 1'b0;
                        queued_job <= 1'b0;
                    end
                end else if (remaining > 0) begin
                    remaining <= remaining - 1'b1;
                    if (remaining == 1) begin
                        completion <= 1'b1;
                        completion_id <= active_job_id;
                        if (queued_job) begin
                            queued_job <= 1'b0;
                            remaining <= work_cycles;
                            active_job_id <= queued_job_id;
                        end else begin
                            busy <= 1'b0;
                        end
                    end
                end
            end

            if (rsp_valid && rsp_ready)
                rsp_valid <= 1'b0;

            if (req_valid && req_ready) begin
                queue_data[queue_count[0]] <= req_data;
                queue_id[queue_count[0]] <= req_id;
                queue_last[queue_count[0]] <= req_last;
                queue_empty[queue_count[0]] <= req_empty;
                queue_len[queue_count[0]] <= req_len;
                queue_count <= queue_count + 1'b1;
                if (queue_count == 0)
                    delay_count <= req_delay;
            end

            if (!rsp_valid) begin
                if (reverse_responses && queue_count == 2) begin
                    rsp_valid <= 1'b1;
                    rsp_data <= queue_data[1];
                    rsp_id <= queue_id[1];
                    rsp_last <= queue_last[1];
                    rsp_empty <= queue_empty[1];
                    rsp_len <= queue_len[1];
                    queue_count <= 1;
                    reverse_second_pending <= 1'b1;
                end else if (reverse_responses && reverse_second_pending && queue_count == 1) begin
                    rsp_valid <= 1'b1;
                    rsp_data <= queue_data[0];
                    rsp_id <= queue_id[0];
                    rsp_last <= queue_last[0];
                    rsp_empty <= queue_empty[0];
                    rsp_len <= queue_len[0];
                    queue_count <= 0;
                    reverse_second_pending <= 1'b0;
                end else if (!reverse_responses && queue_count != 0) begin
                    if (delay_count != 0)
                        delay_count <= delay_count - 1'b1;
                    else begin
                        rsp_valid <= 1'b1;
                        rsp_data <= queue_data[0];
                        rsp_id <= queue_id[0];
                        rsp_last <= queue_last[0];
                        rsp_empty <= queue_empty[0];
                        rsp_len <= queue_len[0];
                        queue_count <= 0;
                    end
                end
            end
        end
    end
endmodule
