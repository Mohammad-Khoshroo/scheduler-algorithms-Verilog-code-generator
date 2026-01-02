import os
import ast
from src.scheduler import ScheduledNodeInfo
class VerilogGenerator:
     
    def _get_reg_name(self, node_id):
        if node_id not in self.node_map:
            return "unknown"
        info = self.node_map[node_id]
        return f"reg_{info.node.op_type}{info.node.id}"

    def _get_op_width(self, res_type):
        res_type = res_type.lower()
        
        if "alu" in res_type or "logic" in res_type: 
            return 2
        else:
            return 1   
        
    def _get_operand_source(self, operand):
        if type(operand).__name__ == "IdentifierNode":
            if operand.value is not None:
                return f"32'd{operand.value}"
            return operand.name
            
        elif type(operand).__name__ == "OperatorNode":
            if operand.id in self.node_to_reg_map:
                return self.node_to_reg_map[operand.id]
            else:
                return "32'd0" 
        return "32'd0"

    def __init__(self, schedule_info: list[ScheduledNodeInfo], folder_path: str):
        
        self.path = folder_path
        
        self.op_codes = {
            ast.Add: 0,
            ast.Sub: 1, 
            ast.Lt: 1, ast.LtE: 1, ast.Gt: 1, ast.GtE: 1,
            ast.USub: 2,
            
            ast.Mult: 0,
            ast.Div: 1,
            ast.FloorDiv: 1,
            ast.Mod: 1,
            
            ast.Eq: 0,
            ast.NotEq: 0,
            ast.BitAnd: 0,
            ast.BitOr: 1,
            ast.BitXor: 2,
            ast.Invert: 3,
            
            ast.LShift: 0, ast.RShift: 1,
            
            ast.Pow: 0
        }
        
        self.schedule_info = sorted(schedule_info, key=lambda x: x.node.id)
        self.node_map = {info.node.id: info for info in self.schedule_info}
        self.node_to_reg_map = {}
        
        self._collect_max_cycles()
        self._collect_inputs()
        self._collect_resources()
        
        self._build_registers()
        self._build_mux_tables()
        self._build_control_table()
        
        
###############################################################################################
        
    def _collect_inputs(self):
        self.inputs = set()
        for info in self.schedule_info:
            for operand in info.node.operands:
                if type(operand).__name__ == "IdentifierNode":
                    if operand.value is None:
                        self.inputs.add(operand.name)
        
    def _collect_resources(self):
        self.resources : dict[str:list[ScheduledNodeInfo]] = {}
        for info in self.schedule_info:
            resource_name = f"{info.node.op_type}{info.resource_num}"
            if resource_name not in self.resources:
                    self.resources[resource_name] = []
            self.resources[resource_name].append(info)
    
    def _collect_max_cycles(self):
        self.max_cycle = 0
        for info in self.schedule_info:
            if info.scheduled_time > self.max_cycle:
                self.max_cycle = info.scheduled_time
        self.total_states = self.max_cycle + 2 
        
###############################################################################################
       
    def _build_mux_tables(self):
        
        # {resource_name: {operand_index (0/1): {source_name: select_value}}}
        self.mux_tables: dict[str:dict[int:dict[int:str]]] = {}
        
        for resource_name, nodes in self.resources.items():
                
            for op_idx in [0, 1]: 
                sources = set()
                
                for info in nodes:
                    if info.node.operands[op_idx]:
                        src = self._get_operand_source(info.node.operands[op_idx])
                        sources.add(src)
                
                for idx, src in enumerate(sources):
                    if resource_name not in self.mux_tables:
                        self.mux_tables[resource_name] = {}
                    if op_idx not in  self.mux_tables[resource_name] :
                        self.mux_tables[resource_name][op_idx] = {}
                    if src not in self.mux_tables[resource_name][op_idx]:
                        self.mux_tables[resource_name][op_idx][src] = ""     
                    self.mux_tables[resource_name][op_idx][src] = idx

    def _build_resources_start_duration_table(self):
        
        # RSD = Resource (node,Start,Duration) for each result which we need it Table  
        self.rsd_table : dict[str:list[(int,int, int)]] = {}
        
        for res in sorted(self.resources.keys()):
            self.rsd_table[res] = []
       
        for _ , node_info in self.node_map.items():
            
            if node_info.node.operands[0].id  in self.node_map.keys(): 
                lop_info = self.node_map[node_info.node.operands[0].id]
                self.rsd_table[lop_info.resource].append((lop_info.scheduled_time,node_info.scheduled_time, lop_info.node.id))
            if node_info.node.operands[1].id  in self.node_map.keys(): 
                rop_info = self.node_map[node_info.node.operands[1].id]
                self.rsd_table[rop_info.resource].append((rop_info.scheduled_time,node_info.scheduled_time, lop_info.node.id))
             
    def _build_registers(self):
        """
        Calculates the required number of registers and their enable times 
        for each resource found in self.rsd_table.
        """
        
        self._build_resources_start_duration_table()
        # {'resource_name': {'reg_count': 2, 'schedule_cycles': {1: [3, 10], 2: [5]}}}
        self.registers_config = {}

        for resource_name, tuples_list in self.rsd_table.items():
            
            merged_requests = {}
            for start, end, node_id in tuples_list:
                if start in merged_requests:
                    merged_requests[start]['end'] = max(merged_requests[start]['end'], end)
                    merged_requests[start]['nodes'].append(node_id)
                else:
                    merged_requests[start] = {'end': end, 'nodes': [node_id]}
            
            sorted_intervals = sorted(merged_requests.items(), key=lambda x: x[0])

            registers_free_time = []
            schedule = {}           

            for start, data in sorted_intervals:
                end = data['end']
                current_nodes = data['nodes']
                
                allocated = False
                assigned_reg_id = -1
                
                for i in range(len(registers_free_time)):
                    if start >= registers_free_time[i]:
                        registers_free_time[i] = end
                        assigned_reg_id = i
                        if (i + 1) not in schedule: schedule[i + 1] = []
                        schedule[i + 1].append(start)
                        allocated = True
                        break
                
                if not allocated:
                    registers_free_time.append(end)
                    assigned_reg_id = len(registers_free_time) - 1
                    schedule[assigned_reg_id + 1] = [start]
                
                real_verilog_name = f"{resource_name}_reg_{assigned_reg_id}"
                for nid in current_nodes:
                    self.node_to_reg_map[nid] = real_verilog_name
                    
            self.registers_config[resource_name] = {
                "count": len(registers_free_time),
                "schedule": schedule
            }
            
        # print(self.registers_config)

    def _build_control_table(self):
        """
        Creates a dictionary of control signals for each time step (cycle).
        Output: self.cycle_signals = { time: { 'signal_name': value } }
        """
        self.cycle_signals = {t: {} for t in range(1, self.max_cycle + 1)}

        for info in self.schedule_info:
            t = info.scheduled_time
            res = f"{info.node.op_type}{info.resource_num}"
            
            op_code_val = self.op_codes.get(type(info.node.op), 0)
            if self._get_op_width(res) > 0:
                self.cycle_signals[t][f"{res}_op"] = op_code_val

            if len(info.node.operands) > 0:
                if len(self.mux_tables[res][0]) > 1:
                    src1 = self._get_operand_source(info.node.operands[0])
                    if src1 in self.mux_tables[res][0]:
                        sel_val1 = self.mux_tables[res][0][src1]
                        self.cycle_signals[t][f"{res}_sel1"] = sel_val1
            
            if len(info.node.operands) > 1:
                if len(self.mux_tables[res][1]) > 1:
                    src2 = self._get_operand_source(info.node.operands[1])
                    if src2 in self.mux_tables[res][1]:
                        sel_val2 = self.mux_tables[res][1][src2]
                        self.cycle_signals[t][f"{res}_sel2"] = sel_val2

        for res, config in self.registers_config.items():
            for reg_id, enable_times in config['schedule'].items():
                for t in enable_times:
                    if t <= self.max_cycle:
                        self.cycle_signals[t][f"{res}_reg{reg_id-1}_en"] = 1

###############################################################################################
   
    def _generate_input_signals(self):    
        inputs_list = sorted(list(self.inputs))
        inputs_str = " // input signals\n"
        
        if inputs_list:
            for input in inputs_list:
                inputs_str += f"  input [31:0] {input},\n" 
                        
        else: inputs_str = "  // No data inputs detected"
        
        return inputs_str
    
    def _generate_control_signals(self, mode="datapath"):
        control_str = ""
        in_out = ""
        if mode == "datapath":
            control_str += " // Control Signals from Controller"
            in_out = "input"
        elif mode == "fsm":
            control_str += " // Out Control Signals"
            in_out = "output reg"
        
        control_str += "\n"

        def clog2(n: int) -> int:
            if n <= 1:
                return 0
            return (n - 1).bit_length()

        for res in sorted(self.resources.keys()):
            control_str += f" // resource {res}\n"

            width_1 = clog2(len(self.mux_tables[res][0]))
            width_2 = clog2(len(self.mux_tables[res][1]))
            if width_1 == 0:
                pass
            elif width_1 == 1:
                control_str += f"  {in_out}       {res}_sel1,\n"
            else:
                control_str += f"  {in_out} [{width_1-1}:0] {res}_sel1,\n"

            if width_2 == 0:
                pass
            elif width_2 == 1:
                control_str += f"  {in_out}       {res}_sel2,\n"
            else:
                control_str += f"  {in_out} [{width_2-1}:0] {res}_sel2,\n"
                
            op_width = self._get_op_width(res)
            if op_width > 1:
                control_str += f"  {in_out} [{op_width-1}:0] {res}_op,"
            elif op_width == 1:
                control_str += f"  {in_out}       {res}_op,"
            else:
                pass
            control_str += "\n"
        
        return control_str

    def _generate_reg_enables(self, mode="datapath"):
        control_str = ""
        in_out = ""
        if mode == "datapath":
            control_str += " // Register En from Controller"
            in_out = "input"
        elif mode == "fsm":
            control_str += " // Out Registers En"
            in_out = "output reg"
        
        control_str += "\n"

        for res in sorted(self.resources.keys()):
            control_str += f" // resource {res}\n"
            for reg_num in range(self.registers_config[res]["count"]):
                control_str += f"  {in_out}       {res}_reg{reg_num}_en,\n"
        control_str = control_str[:-1]
        control_str = control_str[:-1]
        control_str += "\n"

        return control_str

    def _generate_registers(self):
        code_str = ""
        code_str += "  // Registers\n  always @(posedge clk or posedge rst) begin\n"
        code_str += "    if (rst) begin\n"
        for res in sorted(self.resources.keys()):
            for reg_num in range(self.registers_config[res]["count"]):
                code_str += f"      {res}_reg_{reg_num} <= 0;\n"
        code_str += "      result <= 0;\n    end\n"
        code_str += "    else begin\n"
        for res in sorted(self.resources.keys()):
            for reg_num in range(self.registers_config[res]["count"]):
                code_str += f"      if ({res}_reg{reg_num}_en) {res}_reg_{reg_num} <= {res}_out;\n"
        code_str += "    end\n"
        code_str += "  end\n"
        
        
        return code_str
    
    def _generate_muxes(self,res:str):
        mux_code = ""
        mux_code += f"  // Mux for Operands\n"
            
        for op_idx, wire_suffix in [(0, "op1"), (1, "op2")]:
            
            sources_map = self.mux_tables[res][op_idx]

            sel_signal = f"{res}_sel{op_idx + 1}"
            target_wire = f"{res}_{wire_suffix}"

            if not sources_map:
                mux_code += f"  assign {target_wire} = 32'd0;\n"
            
            elif len(sources_map) == 1:
                src = list(sources_map.keys())[0]
                mux_code += f"  assign {target_wire} = {src};\n"
                
            else:
                mux_code += f"  assign {target_wire} = \n"
                sorted_srcs = sorted(sources_map.items(), key=lambda item: item[1])

                for src_name, sel_val in sorted_srcs:
                    mux_code += f"    ({sel_signal} == {sel_val}) ? {src_name} :\n"
                
                mux_code += f"    32'd0;\n"
        
        mux_code += "\n"
            
        return mux_code

    def _generate_modules(self):
        
        modules_dir = os.path.join(self.path,"codes")

        alu_code = """`ifndef ALU_MODULE
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

`endif //ALU_MODULE"""


        with open(os.path.join(modules_dir, "ALU.sv"), "w") as f:
            f.write(alu_code)

##############################################

        logic_code = """`ifndef LOGICUNIT_MODULE
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
"""

        with open(os.path.join(modules_dir, "LogicUnit.sv"), "w") as f:
            f.write(logic_code)

##############################################

        shifter_code = """`ifndef BARREL_SHIFT_MODULE
`define BARREL_SHIFT_MODULE

module BarrelShifter (
    input  wire [31:0] data_in,
    input  wire [4:0] shift_amount,

    // 0 = Left shift, 1 = Right shift
    input  wire direction,

    output wire [31:0] data_out
    );

    assign data_out = direction ? (data_in >> shift_amount) : (data_in << shift_amount);

endmodule

`endif //BARREL_SHIFT_MODULE
"""


        with open(os.path.join(modules_dir, "BarrelShifter.sv"), "w") as f:
            f.write(shifter_code)

##############################################

        mult_code = """`ifndef MULT_MODULE
`define MULT_MODULE

module Multipier(
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] mult
    );

    assign mult = a * b;

endmodule

`endif  //MULT_MODULE
"""

        with open(os.path.join(modules_dir, "Multipier.sv"), "w") as f:
            f.write(mult_code)

##############################################

        div_code = """`ifndef DIV_MODULE
`define DIV_MODULE

module Divider(
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] result
    );

    assign result = (b != 0) ? (a / b) : 32'd0;

endmodule

`endif  //DIV_MODULE
"""

        with open(os.path.join(modules_dir, "Divider.sv"), "w") as f:
            f.write(div_code)

        # print(f"Modules generated in {modules_dir}")
    
    def generate_datapath(self):
        
        def _generate_ALU(res:str):
            code_str = ""
            code_str += f"  wire {res}_zero, {res}_greater, {res}_less;\n"
            code_str += f"  ALU {res} (\n     .a({res}_op1),\n     .b({res}_op2),\n     .result({res}_out),\n     .zero({res}_zero),\n     .gt({res}_greater),\n     .lt({res}_less)\n  );\n"
            return code_str + "\n"
        
        def _generate_logicUnit(res:str):
            code_str = ""
            code_str += f"  wire {res}_eq;\n"
            code_str += f"  ALU {res} (\n     .a({res}_op1),\n     .b({res}_op2),\n     .result({res}_out),\n     .eq({res}_eq)\n  );\n"
            return code_str + "\n"
            
        def _generate_shifter(res:str):
            code_str = ""
            code_str += f"  BarrelShifter {res} (\n     .in({res}_op1),\n     .shift_amount({res}_op2),\n     .shifted({res}_out)\n  );\n"
            return code_str + "\n"

        def _generate_divider(res:str):
            code_str = ""
            code_str += f"  Divider {res} (\n     .a({res}_op1),\n     .b({res}_op2),\n     .result({res}_out)\n  );\n"
            return code_str + "\n"
        
        def _generate_multiplier(res:str):
            code_str = ""
            code_str += f"  Multipier {res} (\n     .a({res}_op1),\n     .b({res}_op2),\n     .mult({res}_out)\n  );\n"
            return code_str + "\n"
        
        self._generate_modules()
        
        lines = """`ifndef DATAPATH
`define DATAPATH

`include "ALU.sv"
`include "BarrelShifter.sv"
`include "Divider.sv"
`include "LogicUnit.sv"
`include "Multiplier.sv"

"""
        
        lines += "module datapath(\n"
        lines += "  input clk, rst,\n"
        lines += "  output reg [31:0] result,\n"
        
        lines += self._generate_input_signals()
        lines += self._generate_control_signals(mode="datapath")
        lines += self._generate_reg_enables(mode="datapath")
          
        lines += ");\n\n"

        for res in sorted(self.resources.keys()):
            
            lines += f"  // {res}\n"
            for reg_num in range(self.registers_config[res]["count"]):
                lines += "  reg  [31:0] "
                lines += f"{res}_reg_{reg_num},"
                lines = lines[:-1]
                lines += ";\n"
            lines += f"  wire [31:0] {res}_out, {res}_op1, {res}_op2;\n"

            lines += self._generate_muxes(res)
            
            if "ALU" in res:
                lines += _generate_ALU(res)
            elif "logic" in res:
                lines += _generate_logicUnit(res)
            elif "shift" in res:
                lines += _generate_shifter(res)
            elif "mult" in res:
                lines += _generate_multiplier(res)
            
        
        lines += self._generate_registers()

        lines += "\nendmodule"
        lines += """

`endif // DATAPATH"""
        
        return lines
    
    def _generate_states(self):
        state_bits = (self.total_states - 1).bit_length() if self.total_states > 1 else 1
        
        code_str = ""
        code_str += f"  // State Encoding\n"
        code_str += f"  localparam IDLE     = {state_bits}'d0;\n"
        for t in range(1, self.max_cycle + 1):
            code_str += f"  localparam CYCLE{t}   = {state_bits}'d{t};\n"
        code_str += f"  localparam DONE     = {state_bits}'d{self.max_cycle + 1};\n\n"
        
        code_str += f"  reg [{state_bits-1}:0] current_state, next_state;\n\n"
        
        return code_str
    
    def _generate_seq_block(self):
        code_str = ""
        code_str += "  // State Register\n"
        code_str += "  always @(posedge clk or posedge rst) begin\n"
        code_str += "    if (rst)\n"
        code_str += "      current_state <= IDLE;\n"
        code_str += "    else\n"
        code_str += "      current_state <= next_state;\n"
        code_str += "  end\n\n"
        return code_str

    def _generate_next_state_block(self):
        code_str = ""
        code_str += "  // Next State Block\n"
        code_str += "  always @(*) begin\n"
        code_str += "    case (current_state)\n"
        code_str += "      IDLE: begin\n"
        code_str += "        if (start) next_state = CYCLE1;\n"
        code_str += "        else       next_state = IDLE;\n"
        code_str += "      end\n"
        
        for t in range(1, self.max_cycle):
            code_str += f"      CYCLE{t}: next_state = CYCLE{t+1};\n"
            
        if self.max_cycle > 0:
            code_str += f"      CYCLE{self.max_cycle}: next_state = DONE;\n"
            
        code_str += "      DONE: next_state = IDLE;\n"
        code_str += "      default: next_state = IDLE;\n"
        code_str += "    endcase\n"
        code_str += "  end\n\n"
        return code_str
    
    def _generate_output_block(self):
        code_str = ""
        code_str += "  // Output Block\n"
        code_str += "  always @(*) begin\n"
        code_str += "    done = 0;\n"
        
        for res in sorted(self.resources.keys()):
        
            # Op Code
            if self._get_op_width(res) > 0:
                code_str += f"    {res}_op = 0;\n"
            
            # Sel 1 (Only if Mux exists)
            if len(self.mux_tables[res][0]) > 1:
                code_str += f"    {res}_sel1 = 0;\n"
                
            # Sel 2 (Only if Mux exists)
            if len(self.mux_tables[res][1]) > 1:
                code_str += f"    {res}_sel2 = 0;\n"
            
            # Enables
            if res in self.registers_config:
                for reg_num in range(self.registers_config[res]["count"]):
                     code_str += f"    {res}_reg{reg_num}_en = 0;\n"
        
        code_str += "\n    case (current_state)\n"
        
        # IDLE
        code_str += "      IDLE: begin\n"
        code_str += "        done = 0;\n"
        code_str += "      end\n"

        # Active States
        for t in range(1, self.max_cycle + 1):
            code_str += f"      CYCLE{t}: begin\n"
            for sig, val in self.cycle_signals[t].items():
                code_str += f"        {sig} = {val};\n"
            code_str += "      end\n"
        
        # DONE
        code_str += "      DONE: begin\n"
        code_str += "        done = 1;\n"
        code_str += "      end\n"
        
        code_str += "    endcase\n"
        code_str += "  end\n\n"
        return code_str
    
    def generate_controller(self):
                
        lines = """`ifndef FSM
`define FSM

"""
        lines += "module Controller (\n"
        lines += "  input  wire clk, rst, start,\n"
        lines += "  output reg  done,\n"
        
        lines += self._generate_control_signals(mode="fsm")
        lines += self._generate_reg_enables(mode="fsm")
        
        lines += ");\n\n"

        
        lines += self._generate_states()
        lines += self._generate_seq_block()
        lines += self._generate_next_state_block()
        lines += self._generate_output_block()
        
        lines += "endmodule\n"
        lines += """
`endif // FSM"""
        return lines

    
def generate_verilog(folder_path : str, schedule_info : list[ScheduledNodeInfo]):

    generator = VerilogGenerator(schedule_info, folder_path)
    
    datapath_code = generator.generate_datapath()
    controller_code = generator.generate_controller()
    
    output_dir = os.path.join(folder_path, "codes")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "Datapath.sv"), "w") as f:
        f.write(datapath_code)
    print("datapath generated")
        
    with open(os.path.join(output_dir, "Controller.sv"), "w") as f:
        f.write(controller_code)
    print("controller generated")
    print("verilog generating done")