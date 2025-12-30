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
  input [1:0] ALU1_sel2,
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
  input       ALU1_reg_en,
 // resource ALU2
  input       ALU2_reg_en,
 // resource ALU3
  input       ALU3_reg_en,
 // resource logic1
  input       logic1_reg_en,
 // resource logic2
  input       logic2_reg_en,
 // resource mult1
  input       mult1_reg_en,

);
endmodule