import os
import ast
from collections import defaultdict
from src.scheduler import ScheduledNodeInfo
from dfg_creator import BaseNode , OperatorNode, IdentifierNode
class VerilogGenerator:
    
    def _get_reg_name(self, node_id):
        if node_id not in self.node_map:
            return "unknown"
        info = self.node_map[node_id]
        return f"reg_{info.node.op_type}{info.node.id}"

    def _collect_inputs(self):
        for info in self.schedule_info:
            for operand in info.node.operands:
                if type(operand).__name__ == "IdentifierNode":
                    if operand.value is None:
                        self.inputs.add(operand.name)

    def _get_operand_source(self, operand):
        if type(operand).__name__ == "IdentifierNode":
            if operand.value is not None:
                return f"32'd{operand.value}"
            return operand.name
            
        elif type(operand).__name__ == "OperatorNode":
            return self._get_reg_name(operand.id)
        return "32'd0"

    def _build_mux_tables(self):
        
        for resource_name, nodes in self.resources.items():
                
            for op_idx in [0, 1]: 
                sources = set()
                
                for info in nodes:
                    if info.node.operands[op_idx]:
                        src = self._get_operand_source(info.node.operands[op_idx])
                        sources.add(src)
                
                for idx, src in enumerate(sources):
                    self.mux_tables[resource_name][op_idx][src] = idx


    def __init__(self, schedule_info: list[ScheduledNodeInfo]):
        
        self.schedule_info = sorted(schedule_info, key=lambda x: x.node.id)
        self.node_map = {info.node.id: info for info in self.schedule_info}
        
        self.inputs = set()
        self._collect_inputs()
        
        self.resources : dict[str:list[ScheduledNodeInfo]] = {}
        for info in self.schedule_info:
            resource_name = f"{info.node.op_type}{info.resource_num}"
            self.resources[resource_name].append(info)
            
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

        # {resource_name: {operand_index (0/1): {source_name: select_value}}}
        self.mux_tables: dict[str:dict[dict[int:str]]] = {}
        self._build_mux_tables()
     
    def _get_op_width(self, res_type):
        res_type = res_type.lower()
        
        if "alu" in res_type or "logic" in res_type: 
            return 2
        else:
            return 1   

    def generate_datapath(self):
        lines = []
        
        lines.append("module datapath(")
        lines.append("  input clk, rst,")
        
        inputs_list = sorted(list(self.inputs))
        inputs_str = ",\n // Data Inputs\n  ".join([f"input [31:0] {i}" for i in inputs_list])
        if inputs_list: inputs_str = f"  {inputs_str},"
        else: inputs_str = "  // No data inputs detected"
        lines.append(inputs_str)

        lines.append(" // Control Signals from Controller")
        for res in sorted(self.resources.keys()):
            op_width = self._get_op_width(res)
            lines.append(f"  input [3:0] {res}_sel1, {res}_sel2,")
            if op_width > 1:
                lines.append(f"  input [{op_width-1}:0] {res}_op,")
            elif op_width == 1:
                lines.append(f"  input {res}_op,")
            else:
                pass
        
        lines.append("  input done_next, result_en,")
        for info in self.schedule_info:
            lines.append(f"  input {self._get_reg_name(info.node.id)}_en,")
        
        lines.append("  // Outputs")    
        lines.append("  output reg [31:0] result,")
        lines.append("  output reg done")
        lines.append(");\n")

    #     for res in sorted(self.resources.keys()):
    #         lines.append(f"wire [31:0] {res}_out, {res}_op1, {res}_op2;")
    #         if "alu" in res.lower():
    #             lines.append(f"wire {res}_zero, {res}_greater, {res}_less;")
    #         if "logic" in res.lower():
    #             lines.append(f"wire {res}_eq;") # برای Eq, NotEq

    #     lines.append("\n// Registers")
    #     for info in self.schedule_info:
    #         lines.append(f"reg [31:0] {self._get_reg_name(info.node.id)};")

    #     lines.append("\n// Muxing Logic")
    #     for res in sorted(self.resources.keys()):
    #         for op_idx in [0, 1]:
    #             suffix = "1" if op_idx == 0 else "2"
    #             lines.append(f"reg [31:0] {res}_op{suffix}_reg;")
    #             lines.append(f"always @(*) begin")
    #             lines.append(f"  case ({res}_sel{suffix})")
    #             for src, sel_val in self.mux_tables[res][op_idx].items():
    #                 lines.append(f"    4'd{sel_val}: {res}_op{suffix}_reg = {src};")
    #             lines.append(f"    default: {res}_op{suffix}_reg = 0;")
    #             lines.append(f"  endcase")
    #             lines.append(f"end")
    #             lines.append(f"assign {res}_op{suffix} = {res}_op{suffix}_reg;")

    #     lines.append("\n// Functional Units Logic")
    #     for res in sorted(self.resources.keys()):
    #         res_lower = res.lower()
    #         lines.append(f"// {res.upper()} Unit")
    #         lines.append(f"reg [31:0] {res}_out_reg;")
            
    #         if "alu" in res_lower:
    #             lines.append(f"wire [31:0] {res}_diff = {res}_op1 - {res}_op2;")
    #             lines.append(f"assign {res}_zero = ({res}_diff == 0);")
    #             lines.append(f"assign {res}_less = {res}_diff[31];") # علامت منفی
    #             lines.append(f"assign {res}_greater = (!{res}_diff[31] && !{res}_zero);")
                
    #             lines.append(f"always @(*) begin")
    #             lines.append(f"  case ({res}_op)")
    #             lines.append(f"    2'd0: {res}_out_reg = {res}_op1 + {res}_op2;")
    #             lines.append(f"    2'd1: {res}_out_reg = {res}_diff;") # Sub
    #             lines.append(f"    2'd2: {res}_out_reg = -{res}_op1;")  # USub
    #             lines.append(f"    default: {res}_out_reg = 0;")
    #             lines.append(f"  endcase")
    #             lines.append(f"end")
            
    #         elif "logic" in res_lower:
    #             lines.append(f"assign {res}_eq = ({res}_op1 == {res}_op2);")
                
    #             lines.append(f"always @(*) begin")
    #             lines.append(f"  case ({res}_op)")
    #             lines.append(f"    2'd0: {res}_out_reg = {res}_op1 & {res}_op2;")
    #             lines.append(f"    2'd1: {res}_out_reg = {res}_op1 | {res}_op2;")
    #             lines.append(f"    2'd2: {res}_out_reg = {res}_op1 ^ {res}_op2;")
    #             lines.append(f"    2'd3: {res}_out_reg = ~{res}_op1;")
    #             lines.append(f"    default: {res}_out_reg = 0;")
    #             lines.append(f"  endcase")
    #             lines.append(f"end")
            
    #         elif "mul" in res_lower:
    #             lines.append(f"always @(*) case ({res}_op)")
    #             lines.append(f"  1'd0: {res}_out_reg = {res}_op1 * {res}_op2;")
    #             lines.append(f"  1'd1: {res}_out_reg = {res}_op1 / {res}_op2;")
    #             lines.append(f"  default: {res}_out_reg = 0;")
    #             lines.append(f"endcase")
    #         elif "shift" in res_lower:
    #             lines.append(f"always @(*) case ({res}_op)")
    #             lines.append(f"  1'd0: {res}_out_reg = {res}_op1 << {res}_op2;")
    #             lines.append(f"  1'd1: {res}_out_reg = {res}_op1 >> {res}_op2;")
    #             lines.append(f"  default: {res}_out_reg = 0;")
    #             lines.append(f"endcase")

    #         lines.append(f"assign {res}_out = {res}_out_reg;")

    #     lines.append("\n// Register Update Logic")
    #     lines.append("always @(posedge clk or posedge rst) begin")
    #     lines.append("  if (rst) begin")
    #     for info in self.schedule_info: lines.append(f"    {self._get_reg_name(info.node.id)} <= 0;")
    #     lines.append("    result <= 0; done <= 0;")
    #     lines.append("  end else begin")
    #     lines.append("    done <= done_next;")
        
    #     for info in self.schedule_info:
    #         reg_name = self._get_reg_name(info.node.id)
    #         res_prefix = f"{info.node.op_type}{info.resource_num}" # e.g. alu1
    #         op_type = type(info.node.op)
            
            
    #         source_wire = f"{res_prefix}_out" 
    #         if op_type == ast.Lt:   source_wire = f"{{31'b0, {res_prefix}_less}}"
    #         elif op_type == ast.Gt: source_wire = f"{{31'b0, {res_prefix}_greater}}"
    #         elif op_type == ast.LtE: source_wire = f"{{31'b0, ({res_prefix}_less | {res_prefix}_zero)}}" # L or Z
    #         elif op_type == ast.GtE: source_wire = f"{{31'b0, ({res_prefix}_greater | {res_prefix}_zero)}}" # G or Z
            
    #         elif op_type == ast.Eq:    source_wire = f"{{31'b0, {res_prefix}_eq}}"
    #         elif op_type == ast.NotEq: source_wire = f"{{31'b0, !{res_prefix}_eq}}"
            
    #         lines.append(f"    if ({reg_name}_en) {reg_name} <= {source_wire};")

    #     lines.append("    if (result_en) result <= alu1_out; // Simplification")
    #     lines.append("  end")
    #     lines.append("end")
    #     lines.append("endmodule")
    #     return "\n".join(lines)

    # def generate_controller(self):
    #     lines = []
    #     max_time = max([info.scheduled_time for info in self.schedule_info]) if self.schedule_info else 0
        
    #     lines.append("module controller(")
    #     lines.append("  input clk, rst, start,")
    #     lines.append("  output reg op_ready,")
        
    #     output_decls = []
    #     for res in sorted(self.resources.keys()):
    #         op_width = self.get_op_width(res)
    #         output_decls.append(f"  output reg [3:0] {res}_sel1, {res}_sel2")
    #         output_decls.append(f"  output reg [{op_width-1}:0] {res}_op")
    #     if output_decls: lines.append(",\n".join(output_decls) + ",")
        
    #     lines.append("  output reg done_next, result_en,")
    #     reg_enables = [f"  output reg {self._get_reg_name(info.node.id)}_en" for info in self.schedule_info]
    #     if reg_enables: lines.append(",\n".join(reg_enables))
    #     lines.append(");\n")

    #     lines.append("reg [31:0] state, next_state;")
    #     lines.append("localparam S_IDLE = 0, S_DONE = 1000;")
    #     for t in range(1, max_time + 1): lines.append(f"localparam S_CYCLE_{t} = {t};")
        
    #     lines.append("\nalways @(posedge clk or posedge rst) begin")
    #     lines.append("  if (rst) state <= S_IDLE; else state <= next_state;")
    #     lines.append("end")

    #     lines.append("\nalways @(*) begin")
    #     lines.append("  op_ready = 0; next_state = state; result_en = 0; done_next = 0;")
    #     for info in self.schedule_info: lines.append(f"  {self._get_reg_name(info.node.id)}_en = 0;")
    #     for res in self.resources: lines.append(f"  {res}_sel1 = 0; {res}_sel2 = 0; {res}_op = 0;")

    #     lines.append("  case (state)")
    #     lines.append("    S_IDLE: begin op_ready = 1; if (start) next_state = S_CYCLE_1; end")
        
    #     nodes_by_time = defaultdict(list)
    #     for info in self.schedule_info: nodes_by_time[info.scheduled_time].append(info)

    #     for t in range(1, max_time + 1):
    #         lines.append(f"    S_CYCLE_{t}: begin")
    #         for info in nodes_by_time[t]:
    #             res = f"{info.node.op_type}{info.resource_num}"
    #             reg_name = self._get_reg_name(info.node.id)
    #             op_val = self.op_codes.get(type(info.node.op), 0)
    #             op_width = self.get_op_width(res)
                
    #             lines.append(f"      {res}_op = {op_width}'d{op_val};")
                
    #             if info.node.operands[0]:
    #                 src = self.get_operand_source(info.node.operands[0])
    #                 lines.append(f"      {res}_sel1 = {self.mux_tables[res][0].get(src, 0)};")
    #             if info.node.operands[1]:
    #                 src = self.get_operand_source(info.node.operands[1])
    #                 lines.append(f"      {res}_sel2 = {self.mux_tables[res][1].get(src, 0)};")
                
    #             lines.append(f"      {reg_name}_en = 1;")
            
    #         if t < max_time: lines.append(f"      next_state = S_CYCLE_{t+1};")
    #         else: lines.append("      result_en = 1; next_state = S_DONE;")
    #         lines.append("    end")

    #     lines.append("    S_DONE: begin done_next = 1; next_state = S_IDLE; end")
    #     lines.append("  endcase")
    #     lines.append("end")
    #     lines.append("endmodule")
    #     return "\n".join(lines)

def generate_verilog(folder_path : str, schedule_info : list[ScheduledNodeInfo]):
    
    generator = VerilogGenerator(schedule_info)
    
    datapath_code = generator.generate_datapath()
    controller_code = generator.generate_controller()
    
    output_dir = os.path.join(folder_path, "codes")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "Datapath.v"), "w") as f:
        f.write(datapath_code)
        
    with open(os.path.join(output_dir, "Controller.v"), "w") as f:
        f.write(controller_code)
        
    print("Verilog generated")