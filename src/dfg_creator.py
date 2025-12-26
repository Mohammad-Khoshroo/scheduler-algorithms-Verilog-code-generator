import ast
from abc import ABC, abstractmethod
from typing import Optional, List

OP_TYPES = ["ALU", "mult", "shift", "logic", "pow"]

op_map = {
    ast.Add: "ALU", ast.Sub: "ALU",
    ast.Mult: "mult", ast.Div: "mult", ast.FloorDiv: "mult", ast.Mod: "mult",
    ast.Pow: "pow",
    ast.LShift: "shift", ast.RShift: "shift",
    ast.BitAnd: "logic", ast.BitOr: "logic", ast.BitXor: "logic",
    ast.Invert: "logic", ast.UAdd: "logic", ast.USub: "logic",
    ast.Eq: "logic", ast.NotEq: "logic", ast.Lt: "ALU", ast.LtE: "ALU", ast.Gt: "ALU", ast.GtE: "ALU",
}

symbols = {
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
        ast.UAdd: "+",
        ast.USub: "-",
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
    }

class BaseNode(ABC):
    def __init__(self, depth : int, id : int, name : str):
        self.operands: List[Optional['BaseNode']] = []
        self.depth = depth
        self.id = id
        self.name = name

    @abstractmethod
    def __repr__(self) -> str:
        pass

class IdentifierNode(BaseNode):
    def __init__(self, name: str, depth : int, id : int):
        super().__init__(depth=depth, id=id,name=name)
        self.operands = [None, None]

    def __repr__(self) -> str:
        return f"[id={self.id}] {self.name} (depth={self.depth})"

class OperatorNode(BaseNode):
    def __init__(self, op_type: str, op: ast.operator | ast.unaryop | ast.cmpop, left_operand: BaseNode, right_operand: Optional[BaseNode], depth : int, id : int, name :str):
        super().__init__(depth=depth, id=id, name=name)
        if op_type not in op_map.values():
            raise ValueError(f"op_type must be one of {list(op_map.values())}")

        self.op_type = op_type
        self.op = op 
        self.operands = [left_operand, right_operand]

    def __repr__(self) -> str:
        def get_operand_name(p):
            if isinstance(p, IdentifierNode):
                return p.name
            if isinstance(p, OperatorNode):
                return f"{p.op_type}"
            return "None"
            
        left_name = get_operand_name(self.operands[0])
        right_name = get_operand_name(self.operands[1]) if self.operands[1] else ""
        return f"{self.op_type} ['{left_name}', '{right_name}'] (depth={self.depth})"
  
def resource_allocator(node : OperatorNode) -> str:
    return "mult" if (node.op_type == "mult") else node.op_type
    
class GraphBuilder:
    def __init__(self):
        self.all_nodes = []
        
    def build(self, tree):

        visited_identifiers = dict()
        node_id = 0

        def recursively_build_DFG(node : BaseNode, depth : int):
            
            nonlocal visited_identifiers, node_id
            
            if node is None:
                return None
                        
            if isinstance(node, ast.BinOp):
                lop = recursively_build_DFG(node=node.left,  depth=depth+1)
                rop = recursively_build_DFG(node=node.right, depth=depth+1)

                new_node = OperatorNode(
                    op_type=        op_map.get(type(node.op), '?'),
                    op=             node.op,
                    left_operand=   lop,
                    right_operand=  rop,
                    depth=          depth,
                    id=             node_id,
                    name=           symbols[type(node.op)]
                )
                
                node_id += 1        
                self.all_nodes.append(new_node)
                return new_node
            
            elif isinstance(node, ast.UnaryOp):
                opn = recursively_build_DFG(node=node.operand, depth=depth+1)
                new_node = OperatorNode(
                    op_type=        op_map.get(type(node.op), '?'),
                    op=             node.op,
                    left_operand=   opn,
                    right_operand=  None,
                    depth=          depth,
                    id=             node_id,
                    name=           symbols[type(node.op)]
                )
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node
        
            elif isinstance(node, ast.Compare):
                lop = recursively_build_DFG(node.left, depth+1)
                current_node = lop
                
                for op_item, right in zip(node.ops, node.comparators):
                    rop = recursively_build_DFG(node=right, depth=depth+1)
                    
                    new_node = OperatorNode(
                        op_type=        op_map.get(type(op_item), '?'),
                        op=             op_item,
                        left_operand=   current_node,
                        right_operand=  rop,
                        depth=          depth,
                        id=             node_id,
                        name=           symbols[type(node.op)]
                    )
                    
                    node_id += 1
                    self.all_nodes.append(new_node)
                    current_node = new_node
        
                return current_node

            elif isinstance(node, ast.Name):
                if node.id in visited_identifiers.keys():
                    existing_node = visited_identifiers[node.id]
                    existing_node.depth = max(depth, existing_node.depth)
                    return existing_node
                else:
                    new_node = IdentifierNode(name=node.id, depth=depth, id=node_id)
                    node_id += 1
                    visited_identifiers[new_node.name] = new_node
                    self.all_nodes.append(new_node)
                    return new_node
            
            elif isinstance(node, ast.Constant):
                if node.value in visited_identifiers.keys():
                    existing_node = visited_identifiers[node.value]
                    existing_node.depth = max(depth, existing_node.depth)
                    return existing_node
                else:
                    new_node = IdentifierNode(name=node.value, depth=depth, id=node_id)
                    node_id += 1
                    visited_identifiers[new_node.name] = new_node
                    self.all_nodes.append(new_node)
                    return new_node
            
            else:
                print(node)
                print("Unknown Node")

        return recursively_build_DFG(tree, 0)
