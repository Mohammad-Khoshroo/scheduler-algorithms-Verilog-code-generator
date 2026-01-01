`ifndef DIV_MODULE
`define DIV_MODULE

module Divider(
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] result
    );

    assign result = (b != 0) ? (a / b) : 32'd0;

endmodule

`endif  //DIV_MODULE
