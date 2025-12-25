module controller(
  input clk, rst, start,
  output reg op_ready,
  output reg [3:0] alu1_sel1, alu1_sel2, log1_sel1, log1_sel2, mul1_sel1, mul1_sel2,
  output reg alu1_op,
  output reg [1:0] log1_op,
  output reg mul1_op,
  output reg done_next, result_en,
  output reg reg_alu0_en, reg_alu5_en, reg_log3_en, reg_mul1_en, reg_mul2_en, reg_mul4_en
);

reg [2:0] state, next_state;
localparam S_IDLE = 0, S_DONE = 5;
localparam S_CYCLE_1 = 1;
localparam S_CYCLE_2 = 2;
localparam S_CYCLE_3 = 3;
localparam S_CYCLE_4 = 4;

// State transition logic
always @(posedge clk or posedge rst) begin
  if (rst) state <= S_IDLE;
  else state <= next_state;
end

// Next state and output logic
always @(*) begin
  op_ready = 1'b0;
  next_state = state;
  reg_alu0_en = 0;
  reg_mul1_en = 0;
  reg_mul2_en = 0;
  reg_log3_en = 0;
  reg_mul4_en = 0;
  reg_alu5_en = 0;
  alu1_sel1 = 0;
  alu1_sel2 = 0;
  mul1_sel1 = 0;
  mul1_sel2 = 0;
  log1_sel1 = 0;
  log1_sel2 = 0;
  alu1_op = 0;
  mul1_op = 0;
  log1_op = 0;
  result_en = 0;
  done_next = 0;

  case (state)
    S_IDLE: begin
      op_ready = 1'b1;
      if (start) next_state = S_CYCLE_1;
    end
    S_CYCLE_1: begin
      alu1_op = 1'b0;
      alu1_sel1 = 0;
      alu1_sel2 = 1;
      reg_alu0_en = 1'b1;
      mul1_op = 1'b1;
      mul1_sel1 = 0;
      mul1_sel2 = 2;
      reg_mul1_en = 1'b1;
      log1_op = 2'b00;
      log1_sel1 = 1;
      log1_sel2 = 2;
      reg_log3_en = 1'b1;
      next_state = S_CYCLE_2;
    end
    S_CYCLE_2: begin
      mul1_op = 1'b0;
      mul1_sel1 = 3;
      mul1_sel2 = 4;
      reg_mul2_en = 1'b1;
      next_state = S_CYCLE_3;
    end
    S_CYCLE_3: begin
      mul1_op = 1'b0;
      mul1_sel1 = 6;
      mul1_sel2 = 0;
      reg_mul4_en = 1'b1;
      next_state = S_CYCLE_4;
    end
    S_CYCLE_4: begin
      alu1_op = 1'b0;
      alu1_sel1 = 5;
      alu1_sel2 = 7;
      reg_alu5_en = 1'b1;
      result_en = 1'b1;
      next_state = S_DONE;
    end
    S_DONE: begin
      done_next = 1'b1;
      next_state = S_IDLE;
    end
  endcase
end
endmodule