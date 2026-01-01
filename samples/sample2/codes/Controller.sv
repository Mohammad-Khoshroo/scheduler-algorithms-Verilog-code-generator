module Controller (
  input  wire clk, rst, start,
  output reg  done,
 // Out Control Signals
 // resource ALU1
  output reg [1:0] ALU1_sel1,
  output reg       ALU1_sel2,
  output reg [1:0] ALU1_op,
 // resource ALU2
  output reg [1:0] ALU2_op,
 // resource ALU3
  output reg [1:0] ALU3_op,
 // resource logic1
  output reg [1:0] logic1_op,
 // resource logic2
  output reg [1:0] logic2_op,
 // resource mult1
  output reg       mult1_sel1,
  output reg       mult1_sel2,
  output reg       mult1_op,
 // Out Registers En
 // resource ALU1
  output reg       ALU1_reg0_en,
 // resource ALU2
  output reg       ALU2_reg0_en,
 // resource ALU3
  output reg       ALU3_reg0_en,
 // resource logic1
  output reg       logic1_reg0_en,
 // resource logic2
  output reg       logic2_reg0_en,
 // resource mult1
  output reg       mult1_reg0_en
);

  // State Encoding
  localparam IDLE     = 3'd0;
  localparam CYCLE1   = 3'd1;
  localparam CYCLE2   = 3'd2;
  localparam CYCLE3   = 3'd3;
  localparam CYCLE4   = 3'd4;
  localparam DONE     = 3'd5;

  reg [2:0] current_state, next_state;

  // State Register
  always @(posedge clk or posedge rst) begin
    if (rst)
      current_state <= IDLE;
    else
      current_state <= next_state;
  end

  // Next State Block
  always @(*) begin
    case (current_state)
      IDLE: begin
        if (start) next_state = CYCLE1;
        else       next_state = IDLE;
      end
      CYCLE1: next_state = CYCLE2;
      CYCLE2: next_state = CYCLE3;
      CYCLE3: next_state = CYCLE4;
      CYCLE4: next_state = DONE;
      DONE: next_state = IDLE;
      default: next_state = IDLE;
    endcase
  end

  // Output Block
  always @(*) begin
    // Default values (0) to prevent latches
    done = 0;
    ALU1_op = 0;
    ALU1_sel1 = 0;
    ALU1_sel2 = 0;
    ALU1_reg0_en = 0;
    ALU2_op = 0;
    ALU2_reg0_en = 0;
    ALU3_op = 0;
    ALU3_reg0_en = 0;
    logic1_op = 0;
    logic1_reg0_en = 0;
    logic2_op = 0;
    logic2_reg0_en = 0;
    mult1_op = 0;
    mult1_sel1 = 0;
    mult1_sel2 = 0;
    mult1_reg0_en = 0;

    case (current_state)
      IDLE: begin
        done = 0;
      end
      CYCLE1: begin
        ALU1_op = 0;
        ALU1_sel1 = 0;
        ALU1_sel2 = 0;
        logic2_op = 1;
        mult1_op = 1;
        mult1_sel1 = 1;
        mult1_sel2 = 1;
        logic1_op = 0;
        ALU1_reg0_en = 1;
        logic1_reg0_en = 1;
        logic2_reg0_en = 1;
        mult1_reg0_en = 1;
      end
      CYCLE2: begin
        ALU3_op = 1;
        ALU2_op = 1;
        ALU1_op = 1;
        ALU1_sel1 = 2;
        ALU1_sel2 = 1;
        ALU2_reg0_en = 1;
        ALU3_reg0_en = 1;
      end
      CYCLE3: begin
        mult1_op = 1;
        mult1_sel1 = 0;
        mult1_sel2 = 0;
        ALU1_op = 0;
        ALU1_sel1 = 1;
        ALU1_sel2 = 1;
      end
      CYCLE4: begin
        ALU1_op = 0;
        ALU1_sel1 = 1;
        ALU1_sel2 = 1;
      end
      DONE: begin
        done = 1;
      end
    endcase
  end

endmodule
