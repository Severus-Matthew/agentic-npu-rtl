module postproc_relu_bias #(parameter int M_FIXED=8,N_FIXED=8)(/*ports via top .* */);
// Finalize one element per cycle: y=max(0, acc+bias) in signed int32.
endmodule
