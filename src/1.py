import ast
from abc import ABC, abstractmethod
from typing import Optional, List

OP_TYPES = ["ALU", "mult", "shift", "logic", "unary", "cmp", "pow"]

op_map = {
    ast.Pow: "pow",
    ast.Add: "ALU", ast.Sub: "ALU",
    ast.Mult: "mult", ast.Div: "mult", ast.FloorDiv: "mult", ast.Mod: "mult",
    ast.LShift: "shift", ast.RShift: "shift",
    ast.BitAnd: "logic", ast.BitOr: "logic", ast.BitXor: "logic",
    ast.Invert: "unary", ast.Not: "unary", ast.UAdd: "unary", ast.USub: "unary",
    ast.Eq: "cmp", ast.NotEq: "cmp", ast.Lt: "cmp", ast.LtE: "cmp",
    ast.Gt: "cmp", ast.GtE: "cmp",
}

class BaseNode(ABC):
    def __init__(self, depth: int, id: int):
        self.operands: List[Optional['BaseNode']] = []
        self.depth = depth
        self.id = id

    @abstractmethod
    def __repr__(self) -> str:
        pass

class IdentifierNode(BaseNode):
    def __init__(self, name: str, depth: int, id: int):
        super().__init__(depth=depth, id=id)
        self.name = name
        self.operands = [None, None]

    def __repr__(self) -> str:
        return f"[id={self.id}] {self.name} (d={self.depth})"

class OperatorNode(BaseNode):
    def __init__(self, op_type: str, op: ast.operator | ast.unaryop | ast.cmpop, left_operand: BaseNode, right_operand: Optional[BaseNode], depth: int, id: int):
        super().__init__(depth=depth, id=id)
        if op_type not in op_map.values():
            raise ValueError(f"op_type must be one of {op_map.values()}")

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
        right_name = get_operand_name(self.operands[1]) if self.operands[1] else "None"
        return f"[id={self.id}] {self.op_type} ['{left_name}', '{right_name}'] (depth={self.depth})"

# سازنده گراف داده‌ها
class GraphBuilder:
    def __init__(self):
        self.all_nodes = []

    def build(self, tree):
        visited_identifiers = {}
        node_id = 0

        def recursively_build_DFG(node, depth):
            nonlocal visited_identifiers, node_id

            if node is None:
                return None

            # عملیات دوطرفه
            if isinstance(node, ast.BinOp):
                left_node = recursively_build_DFG(node.left, depth+1)
                right_node = recursively_build_DFG(node.right, depth+1)
                new_node = OperatorNode(
                    op_type=op_map.get(type(node.op), '?'),
                    op=node.op,
                    left_operand=left_node,
                    right_operand=right_node,
                    depth=depth,
                    id=node_id
                )
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node

            # عملیات یکطرفه
            elif isinstance(node, ast.UnaryOp):
                operand_node = recursively_build_DFG(node.operand, depth+1)
                new_node = OperatorNode(
                    op_type=op_map.get(type(node.op), '?'),
                    op=node.op,
                    left_operand=operand_node,
                    right_operand=None,
                    depth=depth,
                    id=node_id
                )
                node_id += 1
                self.all_nodes.append(new_node)
                return new_node

            # عملیات مقایسه‌ای
            elif isinstance(node, ast.Compare):
                left_node = recursively_build_DFG(node.left, depth+1)
                current_node = left_node
                for op_item, right in zip(node.ops, node.comparators):
                    right_node = recursively_build_DFG(right, depth+1)
                    new_node = OperatorNode(
                        op_type=op_map.get(type(op_item), '?'),
                        op=op_item,
                        left_operand=current_node,
                        right_operand=right_node,
                        depth=depth,
                        id=node_id
                    )
                    node_id += 1
                    self.all_nodes.append(new_node)
                    current_node = new_node
                return current_node

            # متغیرها
            elif isinstance(node, ast.Name):
                if node.id in visited_identifiers:
                    existing_node = visited_identifiers[node.id]
                    existing_node.depth = max(depth, existing_node.depth)
                    return existing_node
                else:
                    new_node = IdentifierNode(name=node.id, depth=depth, id=node_id)
                    node_id += 1
                    visited_identifiers[new_node.name] = new_node
                    self.all_nodes.append(new_node)
                    return new_node

            else:
                print(f"Unknown Node: {type(node)}")
                return None

        return recursively_build_DFG(tree, 0)
