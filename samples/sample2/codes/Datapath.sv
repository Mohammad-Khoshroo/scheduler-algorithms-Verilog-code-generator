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
  input [31:0] i1,
  input [31:0] i2,
  input [31:0] i3,
 // Control Signals from Controller
 // resource ALU1
  input [1:0] ALU1_sel1,
  input       ALU1_sel2,
  input [1:0] ALU1_op,
 // resource ALU2
  input [1:0] ALU2_op,
 // resource ALU3
  input [1:0] ALU3_op,
 // resource logic1
  input [1:0] logic1_op,
 // resource logic2
  input [1:0] logic2_op,
 // resource mult1
  input       mult1_sel1,
  input       mult1_sel2,
  input       mult1_op,
 // Register En from Controller
 // resource ALU1
  input       ALU1_reg0_en,
 // resource ALU2
  input       ALU2_reg0_en,
 // resource ALU3
  input       ALU3_reg0_en,
 // resource logic1
  input       logic1_reg0_en,
 // resource logic2
  input       logic2_reg0_en,
 // resource mult1
  input       mult1_reg0_en
);

  // ALU1
  reg  [31:0] ALU1_reg_0;
  wire [31:0] ALU1_out, ALU1_op1, ALU1_op2;
  // Mux for Operands
  assign ALU1_op1 = 
    (ALU1_sel1 == 0) ? i2 :
    (ALU1_sel1 == 1) ? mult1_reg_0 :
    (ALU1_sel1 == 2) ? i1 :
    32'd0;
  assign ALU1_op2 = 
    (ALU1_sel2 == 0) ? i3 :
    (ALU1_sel2 == 1) ? 32'd0 :
    32'd0;

  wire ALU1_zero, ALU1_greater, ALU1_less;
  ALU ALU1 (
     .a(ALU1_op1),
     .b(ALU1_op2),
     .result(ALU1_out),
     .zero(ALU1_zero),
     .gt(ALU1_greater),
     .lt(ALU1_less)
  );

  // ALU2
  reg  [31:0] ALU2_reg_0;
  wire [31:0] ALU2_out, ALU2_op1, ALU2_op2;
  // Mux for Operands
  assign ALU2_op1 = logic2_reg_0;
  assign ALU2_op2 = 32'd0;

  wire ALU2_zero, ALU2_greater, ALU2_less;
  ALU ALU2 (
     .a(ALU2_op1),
     .b(ALU2_op2),
     .result(ALU2_out),
     .zero(ALU2_zero),
     .gt(ALU2_greater),
     .lt(ALU2_less)
  );

  // ALU3
  reg  [31:0] ALU3_reg_0;
  wire [31:0] ALU3_out, ALU3_op1, ALU3_op2;
  // Mux for Operands
  assign ALU3_op1 = i1;
  assign ALU3_op2 = i2;

  wire ALU3_zero, ALU3_greater, ALU3_less;
  ALU ALU3 (
     .a(ALU3_op1),
     .b(ALU3_op2),
     .result(ALU3_out),
     .zero(ALU3_zero),
     .gt(ALU3_greater),
     .lt(ALU3_less)
  );

  // logic1
  reg  [31:0] logic1_reg_0;
  wire [31:0] logic1_out, logic1_op1, logic1_op2;
  // Mux for Operands
  assign logic1_op1 = i2;
  assign logic1_op2 = i3;

  wire logic1_eq;
  ALU logic1 (
     .a(logic1_op1),
     .b(logic1_op2),
     .result(logic1_out),
     .eq(logic1_eq)
  );

  // logic2
  reg  [31:0] logic2_reg_0;
  wire [31:0] logic2_out, logic2_op1, logic2_op2;
  // Mux for Operands
  assign logic2_op1 = i3;
  assign logic2_op2 = i1;

  wire logic2_eq;
  ALU logic2 (
     .a(logic2_op1),
     .b(logic2_op2),
     .result(logic2_out),
     .eq(logic2_eq)
  );

  // mult1
  reg  [31:0] mult1_reg_0;
  wire [31:0] mult1_out, mult1_op1, mult1_op2;
  // Mux for Operands
  assign mult1_op1 = 
    (mult1_sel1 == 0) ? logic1_reg_0 :
    (mult1_sel1 == 1) ? i3 :
    32'd0;
  assign mult1_op2 = 
    (mult1_sel2 == 0) ? 32'd0 :
    (mult1_sel2 == 1) ? i2 :
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
      ALU2_reg_0 <= 0;
      ALU3_reg_0 <= 0;
      logic1_reg_0 <= 0;
      logic2_reg_0 <= 0;
      mult1_reg_0 <= 0;
      result <= 0;
    end
    else begin
      if (ALU1_reg0_en) ALU1_reg_0 <= ALU1_out;
      if (ALU2_reg0_en) ALU2_reg_0 <= ALU2_out;
      if (ALU3_reg0_en) ALU3_reg_0 <= ALU3_out;
      if (logic1_reg0_en) logic1_reg_0 <= logic1_out;
      if (logic2_reg0_en) logic2_reg_0 <= logic2_out;
      if (mult1_reg0_en) mult1_reg_0 <= mult1_out;
    end
  end

endmodule

`endif // DATAPATH