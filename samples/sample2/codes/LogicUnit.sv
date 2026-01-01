`ifndef LOGICUNIT_MODULE
`define LOGICUNIT_MODULE

module LogicUnit(
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [1:0]  op, // 0: And, 1: Or, 2: Xor, 3: Invert
    output reg  [31:0] result,
    output wire        eq
    );

    assign eq = (a == b);

    always @(*) begin
        case(op)
            2'd0: result = a & b;      // BitAnd
            2'd1: result = a | b;      // BitOr
            2'd2: result = a ^ b;      // BitXor
            2'd3: result = ~a;         // Invert (Not)
            default: result = 32'd0;
        endcase
    end

endmodule

`endif //LOGICUNIT_MODULE
