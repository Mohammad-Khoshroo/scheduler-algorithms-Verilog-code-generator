import ast
from abc import ABC, abstractmethod
from typing import Optional, List

OP_TYPES = ["MUX", "ALU", "mult", "shift", "logic", "pow", "div","min", "max", "wiring"]

OP_CYCLES ={

    "MUX": 1,
    "ALU": 1,
    "mult": 1,
    "shift": 1,
    "logic": 1,
    "pow": 1,
    "div": 1,
    "min":1,
    "max":1,
    "wiring":0
}

op_map = {
    ast.IfExp: "MUX",
    ast.Subscript: "MUX",
    ast.Call: "call", 
    ast.Add: "ALU", ast.Sub: "ALU",
    ast.Mult: "mult", ast.Div: "div", ast.FloorDiv: "div", ast.Mod: "div",
    ast.Pow: "pow",
    ast.LShift: "shift", ast.RShift: "shift",
    ast.BitAnd: "logic", ast.BitOr: "logic", ast.BitXor: "logic",
    ast.Invert: "logic", 
    ast.USub: "ALU", 
    ast.Eq: "logic", ast.NotEq: "logic", ast.Lt: "ALU", ast.LtE: "ALU", ast.Gt: "ALU", ast.GtE: "ALU"
}

symbols = {
    ast.IfExp: "?:",
    ast.Subscript: "[]",
    ast.Call: "call",
    ast.Add: "+",
    ast.Sub: "—",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.BitAnd: "&",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.Invert: "~",
    ast.USub: "-",
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">="
}

class BaseNode(ABC):
    def __init__(self, depth: int, id: int, name: str):
        self.operands: List['BaseNode'] = []
        self.depth = depth
        self.id = id
        self.name = name

    @abstractmethod
    def __repr__(self) -> str:
        pass

class OutputNode(BaseNode):
    def __init__(self, source: BaseNode, name: str, id: int):
        super().__init__(depth=source.depth+1, id=id, name=name)
        self.operands = [source] 
        self.op_type = "OUTPUT"

    def __repr__(self) -> str:
        return f"OUTPUT [{self.name}] <- {self.operands[0].name}"

class IdentifierNode(BaseNode):
    def __init__(self, name: str, depth: int, id: int, value=None):
        super().__init__(depth=depth, id=id, name=str(name))
        self.value = value

    def __repr__(self) -> str:
        if self.value is not None:
            return f"[id={self.id}] CONST:{self.value}"
        return f"[id={self.id}] {self.name}"

class OperatorNode(BaseNode):
    def __init__(self, op_type: str, op: any, operands: List[BaseNode], depth: int, id: int, name: str):
        super().__init__(depth=depth, id=id, name=name)
        if op_type not in OP_TYPES:
            raise ValueError(f"op_type must be one of {OP_TYPES}")

        self.op_type = op_type
        self.op = op 
        self.operands = operands 

    def __repr__(self) -> str:
        ops_names = []
        for p in self.operands:
            if isinstance(p, IdentifierNode):
                ops_names.append(p.name)
            elif isinstance(p, OperatorNode):
                ops_names.append(f"({p.op_type})")
            else:
                ops_names.append("None")
        
        ops_str = ", ".join(ops_names)
        return f"{self.op_type} [{ops_str}] (depth={self.depth})"
  
def resource_allocator(node) -> Optional[str]:
    if isinstance(node, OutputNode) or isinstance(node, IdentifierNode) :
        return None     
    if isinstance(node, OperatorNode):
        if node.op_type == "wiring":
            return None
        return node.op_type
        
    return None
    
class GraphBuilder:
    def __init__(self):
        self.all_nodes = []
        self.output_nodes = []
        
    def build(self, tree):
        
        visited_identifiers = dict()
        node_id = 0

        def get_constant_value(n):
            if isinstance(n, ast.Constant): return n.value
            return None

        def recursively_build_DFG(node: BaseNode, depth: int):
            
            nonlocal visited_identifiers, node_id
            
            if node is None:
                return None
            
            if isinstance(node, ast.Tuple):
                roots = []
                for elt in node.elts:
                    roots.append(recursively_build_DFG(elt, depth))
                return roots

            if isinstance(node, ast.BinOp):
                
                lop = recursively_build_DFG(node=node.left,  depth=depth+1)
                rop = recursively_build_DFG(node=node.right, depth=depth+1)
                
                new_node = OperatorNode(
                    op_type=        op_map.get(type(node.op), '?'),
                    op=             node.op,
                    operands=       [lop, rop],
                    depth=          depth,
                    id=             node_id,
                    name=           symbols.get(type(node.op), '?')
                )
                
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node
            
            elif isinstance(node, ast.UnaryOp):
                
                uop = recursively_build_DFG(node=node.operand, depth=depth+1)
                
                new_node = OperatorNode(
                    op_type=        op_map.get(type(node.op), '?'),
                    op=             node.op,
                    operands=       [uop],
                    depth=          depth,
                    id=             node_id,
                    name=           symbols.get(type(node.op), '?')
                )
                
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node
            
            elif isinstance(node, ast.Compare):

                lop = recursively_build_DFG(node=node.left,   depth=depth+1)

                ops = [lop]
                for c in node.comparators:
                    ops.append(recursively_build_DFG(node=c, depth=depth+1))

                new_node = OperatorNode(
                    op_type=        op_map.get(type(node.ops[0]), '?'),
                    op=             node.ops[0],
                    operands=       ops,
                    depth=          depth,
                    id=             node_id,
                    name=           symbols.get(type(node.ops[0]), '?')
                )

                node_id += 1
                self.all_nodes.append(new_node)
                return new_node


            elif isinstance(node, ast.IfExp):
                
                sel = recursively_build_DFG(node=node.test, depth=depth+1)
                tr = recursively_build_DFG(node=node.body, depth=depth+1)
                fl = recursively_build_DFG(node=node.orelse, depth=depth+1)
                
                new_node = OperatorNode(
                    op_type=        "MUX",
                    op=             node,
                    operands=       [sel, tr, fl],
                    depth=          depth,
                    id=             node_id,
                    name=           "?:"
                )
                
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node

            elif isinstance(node, ast.Call):
                func_name = node.func.id if isinstance(node.func, ast.Name) else 'func'
                
                args_nodes = []
                for arg in node.args:
                    args_nodes.append(recursively_build_DFG(arg, depth=depth+1))
                
                if func_name == "concat":
                    final_op_type = "wiring" 
                elif func_name == "abs":
                    final_op_type = "logic"
                elif func_name in ["min", "max"]:
                    final_op_type = func_name
                else:
                    raise ValueError(f"Function '{func_name}' not supported")

                new_node = OperatorNode(
                    op_type=        final_op_type,
                    op=             node,
                    operands=       args_nodes,
                    depth=          depth,
                    id=             node_id,
                    name=           func_name
                )
                
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node

            elif isinstance(node, ast.Subscript):
                target = recursively_build_DFG(node=node.value, depth=depth+1)
                
                is_constant = False
                idx_ops = []

                if isinstance(node.slice, ast.Slice):
            
                    l_val = get_constant_value(node.slice.lower) if node.slice.lower else None
                    u_val = get_constant_value(node.slice.upper) if node.slice.upper else None
                    
                    if (l_val is not None) or (u_val is not None): 
                        is_constant = True
                    
                    if node.slice.lower: 
                        idx_ops.append(recursively_build_DFG(node=node.slice.lower, depth=depth+1))
                    if node.slice.upper: 
                        idx_ops.append(recursively_build_DFG(node=node.slice.upper, depth=depth+1))
                    
                else:
            
                    real_slice = node.slice
                    if hasattr(ast, 'Index') and isinstance(real_slice, ast.Index):
                         real_slice = real_slice.value
                    
                    if get_constant_value(real_slice) is not None:
                        is_constant = True
                    
                    idx_ops = [recursively_build_DFG(node=real_slice, depth=depth+1)]

                if is_constant:
                    final_op_type = "wiring"
                    op_name = "const_slice"
                else:
                    final_op_type = "MUX"   
                    op_name = "bit-mux"

                new_node = OperatorNode(
                    op_type=        final_op_type,
                    op=             node,
                    operands=       [target] + idx_ops,
                    depth=          depth,
                    id=             node_id,
                    name=           op_name
                )
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node
            
            elif isinstance(node, ast.Name):
                if node.id in visited_identifiers:
                    existing_node = visited_identifiers[node.id]
                    existing_node.depth = max(depth, existing_node.depth)
                    return existing_node
                
                else:
                    new_node = IdentifierNode(
                        name=       node.id,
                        depth=      depth,
                        id=         node_id
                    )
                    node_id += 1
                    visited_identifiers[node.id] = new_node
                    self.all_nodes.append(new_node)
                    return new_node
                
            elif isinstance(node, ast.Constant):
                value = str(node.value)
                if value in visited_identifiers:
                    existing_node = visited_identifiers[value]
                    existing_node.depth = max(depth, existing_node.depth)
                    return existing_node
                else:    
                    new_node = IdentifierNode(
                        name=       value,
                        depth=      depth,
                        id=         node_id,
                        value=      node.value
                        )
                    node_id += 1
                    visited_identifiers[value] = new_node
                    self.all_nodes.append(new_node)
                    return new_node

            else:
                print(f"Unknown Node Type: {type(node)}")
                return None
        
        result = recursively_build_DFG(tree, 0)
        
        raw_outputs = []
        if isinstance(result, list):
            raw_outputs = result
        elif result is not None:
            raw_outputs = [result]
            
        self.output_nodes = []
        for i, r_node in enumerate(raw_outputs):
            
            out_node = OutputNode(
                source=r_node, 
                name=f"out_{i}", 
                id=node_id
            )
            node_id += 1
            
            self.all_nodes.append(out_node)
            self.output_nodes.append(out_node)
            
        return self.output_nodes