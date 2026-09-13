module mac_tile8x8 (
    input  logic clk,
    input  logic rst,
    input  logic clear,
    input  logic step,
    input  logic [63:0] act_lanes,
    input  logic [63:0] weight_lanes,
    input  logic [7:0] row_mask,
    input  logic [7:0] col_mask,
    input  logic [2:0] read_row,
    input  logic [2:0] read_col,
    output logic signed [31:0] sum
);
    logic signed [31:0] acc [0:7][0:7];

    generate
        for (genvar row = 0; row < 8; row = row + 1) begin : g_row
            for (genvar col = 0; col < 8; col = col + 1) begin : g_col
                logic signed [7:0] activation;
                logic signed [7:0] weight;
                logic signed [15:0] product;
                logic signed [31:0] product_extended;
                logic signed [32:0] addition_wide;

                assign activation = $signed(act_lanes[8*row +: 8]);
                assign weight = $signed(weight_lanes[8*col +: 8]);
                // Signed 8-bit operands, exact 16-bit multiplication result.
                assign product = activation * weight;
                assign product_extended = $signed({{16{product[15]}}, product});
                assign addition_wide = $signed({acc[row][col][31], acc[row][col]}) +
                                       $signed({product_extended[31], product_extended});

                // Reset inhibits all writes; only an explicit clear initializes state.
                always_ff @(posedge clk) begin
                    if (!rst) begin
                        if (clear)
                            acc[row][col] <= 32'sd0;
                        else if (step && row_mask[row] && col_mask[col])
                            acc[row][col] <= $signed(addition_wide[31:0]);
                    end
                end
            end
        end
    endgenerate

    assign sum = rst ? 32'sd0 : acc[read_row][read_col];
endmodule
