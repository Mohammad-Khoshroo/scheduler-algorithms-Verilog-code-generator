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
  input       ALU1_sel2,
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
  input       ALU1_reg_en,
 // resource logic1
  input       logic1_reg_en,
 // resource mult1
  input       mult1_reg_en,

);
endmodule