`ifndef DATAPATH
`define DATAPATH

`include "ALU.sv"
`include "BarrelShifter.sv"
`include "Divider.sv"
`include "LogicUnit.sv"
`include "Multiplier.sv"

module datapath(
  input clk, rst,
  output reg [31:0] result,
 // input signals
  input [31:0] a,
  input [31:0] b,
  input [31:0] c,
  input [31:0] d,
  input [31:0] f,
  input [31:0] g,
 // Control Signals from Controller
 // resource ALU1
  input       ALU1_sel1,
  input [1:0] ALU1_op,
 // resource logic1
  input [1:0] logic1_sel1,
  input [1:0] logic1_sel2,
  input [1:0] logic1_op,
 // resource mult1
  input       mult1_sel1,
  input       mult1_sel2,
  input       mult1_op,
 // Register En from Controller
 // resource ALU1
  input       ALU1_reg0_en,
 // resource logic1
  input       logic1_reg0_en,
 // resource mult1
  input       mult1_reg0_en,
  input       mult1_reg1_en
);

  // ALU1
  reg  [31:0] ALU1_reg_0;
  wire [31:0] ALU1_out, ALU1_op1, ALU1_op2;
  // Mux for Operands
  assign ALU1_op1 = 
    (ALU1_sel1 == 0) ? mult1_reg_1 :
    (ALU1_sel1 == 1) ? logic1_reg_0 :
    32'd0;
  assign ALU1_op2 = 32'd0;

  wire ALU1_zero, ALU1_greater, ALU1_less;
  ALU ALU1 (
     .a(ALU1_op1),
     .b(ALU1_op2),
     .result(ALU1_out),
     .zero(ALU1_zero),
     .gt(ALU1_greater),
     .lt(ALU1_less)
  );

  // logic1
  reg  [31:0] logic1_reg_0;
  wire [31:0] logic1_out, logic1_op1, logic1_op2;
  // Mux for Operands
  assign logic1_op1 = 
    (logic1_sel1 == 0) ? c :
    (logic1_sel1 == 1) ? ALU1_reg_0 :
    (logic1_sel1 == 2) ? logic1_reg_0 :
    32'd0;
  assign logic1_op2 = 
    (logic1_sel2 == 0) ? a :
    (logic1_sel2 == 1) ? g :
    (logic1_sel2 == 2) ? f :
    32'd0;

  wire logic1_eq;
  ALU logic1 (
     .a(logic1_op1),
     .b(logic1_op2),
     .result(logic1_out),
     .eq(logic1_eq)
  );

  // mult1
  reg  [31:0] mult1_reg_0;
  reg  [31:0] mult1_reg_1;
  wire [31:0] mult1_out, mult1_op1, mult1_op2;
  // Mux for Operands
  assign mult1_op1 = 
    (mult1_sel1 == 0) ? c :
    (mult1_sel1 == 1) ? a :
    32'd0;
  assign mult1_op2 = 
    (mult1_sel2 == 0) ? b :
    (mult1_sel2 == 1) ? d :
    32'd0;

  Multipier mult1 (
     .a(mult1_op1),
     .b(mult1_op2),
     .mult(mult1_out)
  );

  // Registers
  always @(posedge clk or posedge rst) begin
    if (rst) begin
      ALU1_reg_0 <= 0;
      logic1_reg_0 <= 0;
      mult1_reg_0 <= 0;
      mult1_reg_1 <= 0;
      result <= 0;
    end
    else begin
      if (ALU1_reg0_en) ALU1_reg_0 <= ALU1_out;
      if (logic1_reg0_en) logic1_reg_0 <= logic1_out;
      if (mult1_reg0_en) mult1_reg_0 <= mult1_out;
      if (mult1_reg1_en) mult1_reg_1 <= mult1_out;
    end
  end

endmodule

`endif // DATAPATH