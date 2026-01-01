module Controller (
  input  wire clk, rst, start,
  output reg  done,
 // Out Control Signals
 // resource ALU1
  output reg       ALU1_sel1,
  output reg [1:0] ALU1_op,
 // resource logic1
  output reg [1:0] logic1_sel1,
  output reg [1:0] logic1_sel2,
  output reg [1:0] logic1_op,
 // resource mult1
  output reg       mult1_sel1,
  output reg       mult1_sel2,
  output reg       mult1_op,
 // Out Registers En
 // resource ALU1
  output reg       ALU1_reg0_en,
 // resource logic1
  output reg       logic1_reg0_en,
 // resource mult1
  output reg       mult1_reg0_en,
  output reg       mult1_reg1_en
);

  // State Encoding
  localparam IDLE     = 3'd0;
  localparam CYCLE1   = 3'd1;
  localparam CYCLE2   = 3'd2;
  localparam CYCLE3   = 3'd3;
  localparam CYCLE4   = 3'd4;
  localparam CYCLE5   = 3'd5;
  localparam DONE     = 3'd6;

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
      CYCLE4: next_state = CYCLE5;
      CYCLE5: next_state = DONE;
      DONE: next_state = IDLE;
      default: next_state = IDLE;
    endcase
  end

  // Output Block
  always @(*) begin
    done = 0;
    ALU1_op = 0;
    ALU1_sel1 = 0;
    ALU1_reg0_en = 0;
    logic1_op = 0;
    logic1_sel1 = 0;
    logic1_sel2 = 0;
    logic1_reg0_en = 0;
    mult1_op = 0;
    mult1_sel1 = 0;
    mult1_sel2 = 0;
    mult1_reg0_en = 0;
    mult1_reg1_en = 0;

    case (current_state)
      IDLE: begin
        done = 0;
      end
      CYCLE1: begin
        mult1_op = 1;
        mult1_sel1 = 0;
        mult1_sel2 = 1;
        logic1_op = 0;
        logic1_sel1 = 0;
        logic1_sel2 = 2;
        logic1_reg0_en = 1;
        mult1_reg0_en = 1;
      end
      CYCLE2: begin
        mult1_op = 0;
        mult1_sel1 = 1;
        mult1_sel2 = 0;
        logic1_op = 1;
        logic1_sel1 = 2;
        logic1_sel2 = 1;
        logic1_reg0_en = 1;
        mult1_reg1_en = 1;
      end
      CYCLE3: begin
        ALU1_op = 0;
        ALU1_sel1 = 0;
        ALU1_reg0_en = 1;
      end
      CYCLE4: begin
        ALU1_op = 1;
        ALU1_sel1 = 1;
        ALU1_reg0_en = 1;
      end
      CYCLE5: begin
        logic1_op = 2;
        logic1_sel1 = 1;
        logic1_sel2 = 0;
      end
      DONE: begin
        done = 1;
      end
    endcase
  end

endmodule
