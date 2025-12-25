import ast
import graphviz
from .scheduler import ScheduledNodeInfo
from .dfg_creator import *

def determine_operation_type(op) -> str:
    if isinstance(op, (ast.Add, ast.Sub)):
        return "ALU"
    elif isinstance(op, (ast.Mult, ast.Div, ast.Mod)):
        return "MUL"
    elif isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
        return "LOG"
    else:
        return "?"

def parse_expression(expression):
    try:
        tree = ast.parse(expression, mode='eval').body
        return tree
    except SyntaxError as e:
        print(f"Error parsing expression: {e}")
        return

def visualize_graph(root):
    dot = graphviz.Digraph(comment='Abstract Syntax Tree')
    dot.attr(rankdir='TB', size='8,8')

    node_counter = 0
    visited_identifiers = dict()

    def add_node_and_edges(node, parent_id=None):
        nonlocal node_counter
        nonlocal visited_identifiers
        cur_node_id = str(node_counter)
        node_counter += 1

        if isinstance(node, ast.BinOp):
            label = f"op ({determine_operation_type(node.op)})"
            add_node_and_edges(node.left, cur_node_id)
            add_node_and_edges(node.right, cur_node_id)
        elif isinstance(node, ast.Name):
            label = f"id ({node.id})"
        elif isinstance(node, ast.Constant):
            label = f"const ({node.value})"
        else:
            label = type(node).__name__

        if label.startswith("id"):
            if label in visited_identifiers.keys():
                cur_node_id = visited_identifiers[label]
            else:
                visited_identifiers[label] = cur_node_id
                dot.node(cur_node_id, label)
        else:
            dot.node(cur_node_id, label)

        if parent_id is not None:
            dot.edge(cur_node_id, parent_id)

    add_node_and_edges(root)
    return dot

def visualize_scheduled_graph(root_id, schedule_info : List[ScheduledNodeInfo]):
    
    def find_node_by_id(id) -> ScheduledNodeInfo:
        for sched_node in schedule_info:
            if sched_node.node.id == id:
                return sched_node
        return None

    dot = graphviz.Digraph(comment='Scheduled Graph')
    dot.attr(rankdir='TB', size='8,8')

    node_counter = 0
    visited_identifiers = dict()

    def add_node_and_edges(node_sched : ScheduledNodeInfo, node : BaseNode, parent_id=None):
        nonlocal node_counter
        nonlocal visited_identifiers
        cur_node_id = str(node_counter)
        node_counter += 1

        if node_sched == None:
            label = f"id ({node.name})"
            if label in visited_identifiers.keys():
                cur_node_id = visited_identifiers[label]
            else:
                visited_identifiers[label] = cur_node_id
                dot.node(cur_node_id, label)
        else:
            if isinstance(node_sched.node, OperatorNode):
                label = f"clk: {node_sched.scheduled_time}\nres: {node_sched.node.op_type.lower()} {node_sched.resource_num}"
                for child_node in node_sched.node.operands:
                    child_node_sched = find_node_by_id(child_node.id)
                    if child_node_sched == None:
                        add_node_and_edges(node_sched=None, node=child_node, parent_id=cur_node_id)
                    else:
                        add_node_and_edges(child_node_sched, child_node_sched.node, cur_node_id)
            elif isinstance(node_sched.node, IdentifierNode):
                label = f"id ({node_sched.node.name})"
            else:
                label = type(node).__name__
            dot.node(cur_node_id, label)

        if parent_id is not None:
            dot.edge(cur_node_id, parent_id)

    root_sched = find_node_by_id(root_id)
    add_node_and_edges(node_sched=root_sched, node=root_sched.node)
    return dot

def expression_to_graph(expression):
    return parse_expression(expression)
