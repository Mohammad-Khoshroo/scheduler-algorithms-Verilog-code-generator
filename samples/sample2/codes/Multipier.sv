`ifndef MULT_MODULE
`define MULT_MODULE

module Multipier(
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] mult
    );

    assign mult = a * b;

endmodule

`endif  //MULT_MODULE
