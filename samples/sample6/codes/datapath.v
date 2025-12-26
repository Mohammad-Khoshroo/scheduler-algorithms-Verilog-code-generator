module datapath(
  input clk, rst,
  // Data Inputs
  input [31:0] i1,
  input [31:0] i2,
  input [31:0] i3,
  // Control Signals from Controller
  input [3:0] alu1_sel1,
  input [3:0] alu1_sel2,
  input [3:0] log1_sel1,
  input [3:0] log1_sel2,
  input [3:0] mul1_sel1,
  input [3:0] mul1_sel2,
  input alu1_op,
  input [1:0] log1_op,
  input mul1_op,
  input done_next,
  input result_en,
  input reg_alu0_en,
  input reg_alu1_en,
  input reg_alu3_en,
  input reg_alu7_en,
  input reg_alu8_en,
  input reg_alu9_en,
  input reg_log2_en,
  input reg_log6_en,
  input reg_mul4_en,
  input reg_mul5_en,
  // Outputs
  output reg [31:0] result,
  output reg done
);

// Wires for FU outputs and Mux outputs
wire [31:0] alu1_out;
wire [31:0] alu1_op1, alu1_op2;
wire [31:0] mul1_out;
wire [31:0] mul1_op1, mul1_op2;
wire [31:0] log1_out;
wire [31:0] log1_op1, log1_op2;

// Registers for intermediate values
reg [31:0] reg_alu0;
reg [31:0] reg_alu1;
reg [31:0] reg_alu3;
reg [31:0] reg_alu7;
reg [31:0] reg_alu8;
reg [31:0] reg_alu9;
reg [31:0] reg_log2;
reg [31:0] reg_log6;
reg [31:0] reg_mul4;
reg [31:0] reg_mul5;

// Muxing logic for FU inputs
reg [31:0] alu1_op1_reg;
always @(*) begin
  case (alu1_sel1)
    4'd0: alu1_op1_reg = i1;
    4'd1: alu1_op1_reg = i2;
    4'd2: alu1_op1_reg = i3;
    4'd3: alu1_op1_reg = reg_alu0;
    4'd4: alu1_op1_reg = reg_alu1;
    4'd5: alu1_op1_reg = reg_log2;
    4'd6: alu1_op1_reg = reg_alu3;
    4'd7: alu1_op1_reg = reg_mul4;
    4'd8: alu1_op1_reg = reg_mul5;
    4'd9: alu1_op1_reg = reg_log6;
    4'd10: alu1_op1_reg = reg_alu7;
    4'd11: alu1_op1_reg = reg_alu8;
    4'd12: alu1_op1_reg = reg_alu9;
    default: alu1_op1_reg = 0;
  endcase
end
assign alu1_op1 = alu1_op1_reg;

reg [31:0] alu1_op2_reg;
always @(*) begin
  case (alu1_sel2)
    4'd0: alu1_op2_reg = i1;
    4'd1: alu1_op2_reg = i2;
    4'd2: alu1_op2_reg = i3;
    4'd3: alu1_op2_reg = reg_alu0;
    4'd4: alu1_op2_reg = reg_alu1;
    4'd5: alu1_op2_reg = reg_log2;
    4'd6: alu1_op2_reg = reg_alu3;
    4'd7: alu1_op2_reg = reg_mul4;
    4'd8: alu1_op2_reg = reg_mul5;
    4'd9: alu1_op2_reg = reg_log6;
    4'd10: alu1_op2_reg = reg_alu7;
    4'd11: alu1_op2_reg = reg_alu8;
    4'd12: alu1_op2_reg = reg_alu9;
    default: alu1_op2_reg = 0;
  endcase
end
assign alu1_op2 = alu1_op2_reg;

reg [31:0] mul1_op1_reg;
always @(*) begin
  case (mul1_sel1)
    4'd0: mul1_op1_reg = i1;
    4'd1: mul1_op1_reg = i2;
    4'd2: mul1_op1_reg = i3;
    4'd3: mul1_op1_reg = reg_alu0;
    4'd4: mul1_op1_reg = reg_alu1;
    4'd5: mul1_op1_reg = reg_log2;
    4'd6: mul1_op1_reg = reg_alu3;
    4'd7: mul1_op1_reg = reg_mul4;
    4'd8: mul1_op1_reg = reg_mul5;
    4'd9: mul1_op1_reg = reg_log6;
    4'd10: mul1_op1_reg = reg_alu7;
    4'd11: mul1_op1_reg = reg_alu8;
    4'd12: mul1_op1_reg = reg_alu9;
    default: mul1_op1_reg = 0;
  endcase
end
assign mul1_op1 = mul1_op1_reg;

reg [31:0] mul1_op2_reg;
always @(*) begin
  case (mul1_sel2)
    4'd0: mul1_op2_reg = i1;
    4'd1: mul1_op2_reg = i2;
    4'd2: mul1_op2_reg = i3;
    4'd3: mul1_op2_reg = reg_alu0;
    4'd4: mul1_op2_reg = reg_alu1;
    4'd5: mul1_op2_reg = reg_log2;
    4'd6: mul1_op2_reg = reg_alu3;
    4'd7: mul1_op2_reg = reg_mul4;
    4'd8: mul1_op2_reg = reg_mul5;
    4'd9: mul1_op2_reg = reg_log6;
    4'd10: mul1_op2_reg = reg_alu7;
    4'd11: mul1_op2_reg = reg_alu8;
    4'd12: mul1_op2_reg = reg_alu9;
    default: mul1_op2_reg = 0;
  endcase
end
assign mul1_op2 = mul1_op2_reg;

reg [31:0] log1_op1_reg;
always @(*) begin
  case (log1_sel1)
    4'd0: log1_op1_reg = i1;
    4'd1: log1_op1_reg = i2;
    4'd2: log1_op1_reg = i3;
    4'd3: log1_op1_reg = reg_alu0;
    4'd4: log1_op1_reg = reg_alu1;
    4'd5: log1_op1_reg = reg_log2;
    4'd6: log1_op1_reg = reg_alu3;
    4'd7: log1_op1_reg = reg_mul4;
    4'd8: log1_op1_reg = reg_mul5;
    4'd9: log1_op1_reg = reg_log6;
    4'd10: log1_op1_reg = reg_alu7;
    4'd11: log1_op1_reg = reg_alu8;
    4'd12: log1_op1_reg = reg_alu9;
    default: log1_op1_reg = 0;
  endcase
end
assign log1_op1 = log1_op1_reg;

reg [31:0] log1_op2_reg;
always @(*) begin
  case (log1_sel2)
    4'd0: log1_op2_reg = i1;
    4'd1: log1_op2_reg = i2;
    4'd2: log1_op2_reg = i3;
    4'd3: log1_op2_reg = reg_alu0;
    4'd4: log1_op2_reg = reg_alu1;
    4'd5: log1_op2_reg = reg_log2;
    4'd6: log1_op2_reg = reg_alu3;
    4'd7: log1_op2_reg = reg_mul4;
    4'd8: log1_op2_reg = reg_mul5;
    4'd9: log1_op2_reg = reg_log6;
    4'd10: log1_op2_reg = reg_alu7;
    4'd11: log1_op2_reg = reg_alu8;
    4'd12: log1_op2_reg = reg_alu9;
    default: log1_op2_reg = 0;
  endcase
end
assign log1_op2 = log1_op2_reg;

// Functional Units (ALU, MUL, LOG)
// ALU1 Functional Unit
reg [31:0] alu1_out_reg;
always @(*) begin
  case (alu1_op)
    1'b0: alu1_out_reg = alu1_op1 + alu1_op2;
    1'b1: alu1_out_reg = alu1_op1 - alu1_op2;
    default: alu1_out_reg = 0;
  endcase
end
assign alu1_out = alu1_out_reg;

// MUL1 Functional Unit
reg [31:0] mul1_out_reg;
always @(*) begin
  case (mul1_op)
    1'b0: mul1_out_reg = mul1_op1 * mul1_op2;
    1'b1: mul1_out_reg = mul1_op1 / mul1_op2;
    default: mul1_out_reg = 0;
  endcase
end
assign mul1_out = mul1_out_reg;

// LOG1 Functional Unit
reg [31:0] log1_out_reg;
always @(*) begin
  case (log1_op)
    2'b00: log1_out_reg = log1_op1 & log1_op2;
    2'b01: log1_out_reg = log1_op1 | log1_op2;
    2'b10: log1_out_reg = log1_op1 ^ log1_op2;
    default: log1_out_reg = 0;
  endcase
end
assign log1_out = log1_out_reg;

// Register update logic
always @(posedge clk or posedge rst) begin
  if (rst) begin
    reg_alu0 <= 0;
    reg_alu1 <= 0;
    reg_alu3 <= 0;
    reg_alu7 <= 0;
    reg_alu8 <= 0;
    reg_alu9 <= 0;
    reg_log2 <= 0;
    reg_log6 <= 0;
    reg_mul4 <= 0;
    reg_mul5 <= 0;
    result <= 0;
    done <= 0;
  end else begin
    done <= done_next;
    if (reg_alu0_en) reg_alu0 <= alu1_out;
    if (reg_alu1_en) reg_alu1 <= alu1_out;
    if (reg_log2_en) reg_log2 <= log1_out;
    if (reg_alu3_en) reg_alu3 <= alu1_out;
    if (reg_mul4_en) reg_mul4 <= mul1_out;
    if (reg_mul5_en) reg_mul5 <= mul1_out;
    if (reg_log6_en) reg_log6 <= log1_out;
    if (reg_alu7_en) reg_alu7 <= alu1_out;
    if (reg_alu8_en) reg_alu8 <= alu1_out;
    if (reg_alu9_en) reg_alu9 <= alu1_out;
    if (result_en) result <= alu1_out;
  end
end

endmodule
