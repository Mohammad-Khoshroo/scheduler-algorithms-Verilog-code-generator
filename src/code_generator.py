import os
import ast
from src.scheduler import ScheduledNodeInfo
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
                    if resource_name not in self.mux_tables:
                        self.mux_tables[resource_name] = {}
                    if op_idx not in  self.mux_tables[resource_name] :
                        self.mux_tables[resource_name][op_idx] = {}
                    if src not in self.mux_tables[resource_name][op_idx]:
                        self.mux_tables[resource_name][op_idx][src] = ""     
                    self.mux_tables[resource_name][op_idx][src] = idx

    def _build_resources_start_duration_table(self):
        
        # RSD = Resource (Start,Duration) for each result which we need it Table  
        self.rsd_table : dict[str:list[(int,int)]] = {}
        
        for res in sorted(self.resources.keys()):
            self.rsd_table[res] = []
       
        for _ , node_info in self.node_map.items():
            lop_info = None
            rop_info = None
            if node_info.node.operands[0].id  in self.node_map.keys(): 
                lop_info = self.node_map[node_info.node.operands[0].id]
                self.rsd_table[lop_info.resource].append((lop_info.scheduled_time,node_info.scheduled_time))
            if node_info.node.operands[1].id  in self.node_map.keys(): 
                rop_info = self.node_map[node_info.node.operands[1].id]
                self.rsd_table[rop_info.resource].append((rop_info.scheduled_time,node_info.scheduled_time))
         
        print(self.rsd_table)           
        
    def __init__(self, schedule_info: list[ScheduledNodeInfo]):
        
        self.schedule_info = sorted(schedule_info, key=lambda x: x.node.id)
        self.node_map = {info.node.id: info for info in self.schedule_info}
        self.inputs = set()
        self._collect_inputs()
        
        self.resources : dict[str:list[ScheduledNodeInfo]] = {}
        for info in self.schedule_info:
            resource_name = f"{info.node.op_type}{info.resource_num}"
            if resource_name not in self.resources:
                    self.resources[resource_name] = []
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
        self.mux_tables: dict[str:dict[int:dict[int:str]]] = {}
        self._build_mux_tables()
        self._build_resources_start_duration_table()
     
    def _get_op_width(self, res_type):
        res_type = res_type.lower()
        
        if "alu" in res_type or "logic" in res_type: 
            return 2
        else:
            return 1   
    
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
            in_out = "output"
        
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
            in_out = "output"
        
        control_str += "\n"

        for res in sorted(self.resources.keys()):
            control_str += f" // resource {res}\n"

            control_str += f"  {in_out}       {res}_reg_en,\n"
            
        
        control_str += "\n"

        return control_str

    def generate_datapath(self):
        
        lines = ""
        
        lines += "module datapath(\n"
        lines += "  input clk, rst,\n"
        lines += "  output reg [31:0] result,\n"
        
        lines += self._generate_input_signals()
        lines += self._generate_control_signals(mode="datapath")
        lines += self._generate_reg_enables(mode="datapath")
          
        lines += ");\n"

    #     for res in sorted(self.resources.keys()):
    #         lines += f"wire [31:0] {res}_out, {res}_op1, {res}_op2;")
    #         if "alu" in res.lower():
    #             lines += f"wire {res}_zero, {res}_greater, {res}_less;")
    #         if "logic" in res.lower():
    #             lines += f"wire {res}_eq;") # برای Eq, NotEq

    #     lines += "\n// Registers")
    #     for info in self.schedule_info:
    #         lines += f"reg [31:0] {self._get_reg_name(info.node.id)};")

    #     lines += "\n// Muxing Logic")
    #     for res in sorted(self.resources.keys()):
    #         for op_idx in [0, 1]:
    #             suffix = "1" if op_idx == 0 else "2"
    #             lines += f"reg [31:0] {res}_op{suffix}_reg;")
    #             lines += f"always @(*) begin")
    #             lines += f"  case ({res}_sel{suffix})")
    #             for src, sel_val in self.mux_tables[res][op_idx].items():
    #                 lines += f"    4'd{sel_val}: {res}_op{suffix}_reg = {src};")
    #             lines += f"    default: {res}_op{suffix}_reg = 0;")
    #             lines += f"  endcase")
    #             lines += f"end")
    #             lines += f"assign {res}_op{suffix} = {res}_op{suffix}_reg;")

    #     lines += "\n// Functional Units Logic")
    #     for res in sorted(self.resources.keys()):
    #         res_lower = res.lower()
    #         lines += f"// {res.upper()} Unit")
    #         lines += f"reg [31:0] {res}_out_reg;")
            
    #         if "alu" in res_lower:
    #             lines += f"wire [31:0] {res}_diff = {res}_op1 - {res}_op2;")
    #             lines += f"assign {res}_zero = ({res}_diff == 0);")
    #             lines += f"assign {res}_less = {res}_diff[31];") # علامت منفی
    #             lines += f"assign {res}_greater = (!{res}_diff[31] && !{res}_zero);")
                
    #             lines += f"always @(*) begin")
    #             lines += f"  case ({res}_op)")
    #             lines += f"    2'd0: {res}_out_reg = {res}_op1 += {res}_op2;")
    #             lines += f"    2'd1: {res}_out_reg = {res}_diff;") # Sub
    #             lines += f"    2'd2: {res}_out_reg = -{res}_op1;")  # USub
    #             lines += f"    default: {res}_out_reg = 0;")
    #             lines += f"  endcase")
    #             lines += f"end")
            
    #         elif "logic" in res_lower:
    #             lines += f"assign {res}_eq = ({res}_op1 == {res}_op2);")
                
    #             lines += f"always @(*) begin")
    #             lines += f"  case ({res}_op)")
    #             lines += f"    2'd0: {res}_out_reg = {res}_op1 & {res}_op2;")
    #             lines += f"    2'd1: {res}_out_reg = {res}_op1 | {res}_op2;")
    #             lines += f"    2'd2: {res}_out_reg = {res}_op1 ^ {res}_op2;")
    #             lines += f"    2'd3: {res}_out_reg = ~{res}_op1;")
    #             lines += f"    default: {res}_out_reg = 0;")
    #             lines += f"  endcase")
    #             lines += f"end")
            
    #         elif "mul" in res_lower:
    #             lines += f"always @(*) case ({res}_op)")
    #             lines += f"  1'd0: {res}_out_reg = {res}_op1 * {res}_op2;")
    #             lines += f"  1'd1: {res}_out_reg = {res}_op1 / {res}_op2;")
    #             lines += f"  default: {res}_out_reg = 0;")
    #             lines += f"endcase")
    #         elif "shift" in res_lower:
    #             lines += f"always @(*) case ({res}_op)")
    #             lines += f"  1'd0: {res}_out_reg = {res}_op1 << {res}_op2;")
    #             lines += f"  1'd1: {res}_out_reg = {res}_op1 >> {res}_op2;")
    #             lines += f"  default: {res}_out_reg = 0;")
    #             lines += f"endcase")

    #         lines += f"assign {res}_out = {res}_out_reg;")

    #     lines += "\n// Register Update Logic")
    #     lines += "always @(posedge clk or posedge rst) begin")
    #     lines += "  if (rst) begin")
    #     for info in self.schedule_info: lines += f"    {self._get_reg_name(info.node.id)} <= 0;")
    #     lines += "    result <= 0; done <= 0;")
    #     lines += "  end else begin")
    #     lines += "    done <= done_next;")
        
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
            
    #         lines += f"    if ({reg_name}_en) {reg_name} <= {source_wire};")

    #     lines += "    if (result_en) result <= alu1_out; // Simplification")
    #     lines += "  end")
    #     lines += "end")
        
        lines += "endmodule"
        return lines

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
    # controller_code = generator.generate_controller()
    
    output_dir = os.path.join(folder_path, "codes")
    os.makedirs(output_dir, exist_ok=True)
    
    # print(datapath_code)
    
    with open(os.path.join(output_dir, "Datapath.sv"), "w") as f:
        f.write(datapath_code)
        
    # with open(os.path.join(output_dir, "Controller.v"), "w") as f:
        # f.write(controller_code)
        
    print("Verilog generated")