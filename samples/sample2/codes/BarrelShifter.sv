`ifndef BARREL_SHIFT_MODULE
`define BARREL_SHIFT_MODULE

module BarrelShifter (
    input  wire [31:0] data_in,
    input  wire [4:0] shift_amount,

    // 0 = Left shift, 1 = Right shift
    input  wire direction,

    output wire [31:0] data_out
    );

    assign data_out = direction ? (data_in >> shift_amount) : (data_in << shift_amount);

endmodule

`endif //BARREL_SHIFT_MODULE
