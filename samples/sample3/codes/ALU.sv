`ifndef ALU_MODULE
`define ALU_MODULE

module ALU(
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [1:0]  op, // 0: Add, 1: Sub, 2: USub
    output reg  [31:0] result,
    output wire        zero,
    output wire        gt,
    output wire        lt
    );
    
    always @(*) begin
        case(op)
            2'd0: result = a + b;       // Add
            2'd1: result = a - b;       // Sub, Lt, Gt, etc.
            2'd2: result = -a;          // USub
            default: result = 32'd0;
        endcase
    end

    assign zero = (result == 32'd0);
    assign gt   = ($signed(result) > 0);
    assign lt   = ($signed(result) < 0);
        
endmodule

`endif //ALU_MODULE