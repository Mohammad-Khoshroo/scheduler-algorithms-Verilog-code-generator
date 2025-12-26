import ast
import graphviz
from .scheduler import ScheduledNodeInfo
from .dfg_creator import *
from collections import defaultdict


def determine_operation_type(op) -> str:
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

    sym = symbols.get(type(op), "?")

    if isinstance(op, (ast.Add, ast.Sub)):
        return f"ALU({sym})"

    elif isinstance(op, (ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)):
        return f"mult({sym})"

    elif isinstance(op, (ast.LShift, ast.RShift)):
        return f"shift({sym})"

    elif isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
        return f"logic({sym})"

    elif isinstance(op, (ast.Invert, ast.Not, ast.UAdd, ast.USub)):
        return f"unaryLogic({sym})"

    elif isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
        return f"cmp({sym})"

    else:
        return f"?({sym})"


def visualize_graph(root, version=1):
    dot = graphviz.Digraph(comment="Abstract Syntax Tree")
    dot.attr(rankdir="TB", size="8,8")

    node_counter = 0
    visited_identifiers = dict()
    identifier_nodes = []

    def add_node_and_edges(node, parent_id=None):
        nonlocal node_counter
        nonlocal visited_identifiers
        cur_node_id = str(node_counter)
        node_counter += 1

        if isinstance(node, ast.BinOp):
            label = f"{determine_operation_type(node.op)}"
            add_node_and_edges(node.left, cur_node_id)
            add_node_and_edges(node.right, cur_node_id)

        elif isinstance(node, ast.UnaryOp):
            label = f"{determine_operation_type(node.op)}"
            add_node_and_edges(node.operand, cur_node_id)
            
        elif isinstance(node, ast.Compare):
            label = f"{determine_operation_type(node.ops[0])}"

            add_node_and_edges(node.left, cur_node_id)

            for comp in node.comparators:
                add_node_and_edges(comp, cur_node_id)

        elif isinstance(node, ast.Name):
            label = f"{node.id}"

        elif isinstance(node, ast.Constant):
            label = f"const= {node.value}"

        else:
            label = type(node).__name__

        if (
            version == 2
            and not label.startswith("c=")
            and not label.startswith("ALU")
            and not label.startswith("mult")
            and not label.startswith("shift")
            and not label.startswith("logic")
            and not label.startswith("unary")
            and not label.startswith("cmp")
        ):
            if label in visited_identifiers.keys():
                cur_node_id = visited_identifiers[label]
            else:
                visited_identifiers[label] = cur_node_id
                dot.node(cur_node_id, label)
                identifier_nodes.append(cur_node_id)
        else:
            dot.node(cur_node_id, label)

        if parent_id is not None:
            dot.edge(cur_node_id, parent_id)

    add_node_and_edges(root)

    if version == 2 and identifier_nodes:
        with dot.subgraph() as s:
            s.attr(rank="source")
            for nid in identifier_nodes:
                s.node(nid)
    return dot


def visualize_scheduled_graph(
    root_id, schedule_info: List[ScheduledNodeInfo], version=1
):

    def find_node_by_id(id) -> ScheduledNodeInfo:
        for sched_node in schedule_info:
            if sched_node.node.id == id:
                return sched_node
        return None

    dot = graphviz.Digraph(comment="Scheduled Graph")
    dot.attr(rankdir="TB", size="8,8")

    node_counter = 0
    visited_identifiers = dict()
    identifier_nodes = []

    def add_node_and_edges(
        node_sched: ScheduledNodeInfo, node: BaseNode, parent_id=None
    ):
        nonlocal node_counter
        nonlocal visited_identifiers
        nonlocal identifier_nodes
        cur_node_id = str(node_counter)
        node_counter += 1

        if node_sched is None:
            if node.name.isdigit():
                label = f"const={node.name}"
            else:
                label = node.name
        else:
            if isinstance(node_sched.node, OperatorNode):
                label = (
                    f"{node.name}\ntime_cycle: {node_sched.scheduled_time}\n"
                    f"resource: {node_sched.node.op_type} {node_sched.resource_num}"
                )
            elif isinstance(node_sched.node, IdentifierNode):
                label = node_sched.node.name
            else:
                label = type(node).__name__

        if version == 2:
            if not (
                label.startswith("const=")
                or label.lower().startswith("alu")
                or label.lower().startswith("mult")
                or label.lower().startswith("shift")
                or label.lower().startswith("logic")
                or label.lower().startswith("unary")
                or label.lower().startswith("cmp")
            ):
                if label in visited_identifiers:
                    cur_node_id = visited_identifiers[label]
                else:
                    visited_identifiers[label] = cur_node_id
                    dot.node(cur_node_id, label)
            else:
                dot.node(cur_node_id, label)
        else:
            dot.node(cur_node_id, label)


        if parent_id is not None:
            dot.edge(cur_node_id, parent_id)

        if node_sched is not None and isinstance(node_sched.node, OperatorNode):
            for child_node in node_sched.node.operands:
                child_sched = find_node_by_id(child_node.id)
                add_node_and_edges(
                    node_sched=child_sched, node=child_node, parent_id=cur_node_id
                )

    root_sched = find_node_by_id(root_id)
    add_node_and_edges(node_sched=root_sched, node=root_sched.node)

    if version == 2 and identifier_nodes:
        with dot.subgraph() as s:
            s.attr(rank="source")
            for nid in identifier_nodes:
                s.node(nid)

    return dot


def visualize_scheduled_graph_ranked(
    root_id, schedule_info: list, version=1
):
    def find_node_by_id(id):
        for sched_node in schedule_info:
            if sched_node.node.id == id:
                return sched_node
        return None

    dot = graphviz.Digraph(comment="Scheduled Graph Ranked")
    dot.attr(rankdir="TB")
    dot.attr(newrank="true")
    
    node_counter = 0
    visited_identifiers = dict()
    
    layers = defaultdict(list)

    def add_node_and_edges(
        node_sched, node, parent_id=None
    ):
        nonlocal node_counter
        nonlocal visited_identifiers
        nonlocal layers

        label = ""
        cycle_key = None 

        if node_sched is None:
            cycle_key = "source"
            if hasattr(node, 'name') and node.name.isdigit():
                label = f"const={node.name}"
            elif hasattr(node, 'name'):
                label = node.name
            else:
                label = type(node).__name__
        else:
            cycle_key = node_sched.scheduled_time
            
            if hasattr(node, 'op_type'):
                label = (
                    f"{node.name}\ntime_cycle: {node_sched.scheduled_time}\n"
                    f"resource: {node_sched.node.op_type} {node_sched.resource_num}"
                )
            elif hasattr(node, 'name'):
                label = node.node.name
            else:
                label = type(node).__name__

        cur_node_id = str(node_counter)
        is_existing_node = False

        if version == 2:
            should_merge = True
            
            lower_label = label.lower()
            if (
                label.startswith("const=")
                or lower_label.startswith("alu")
                or lower_label.startswith("mult")
                or lower_label.startswith("div")
                or lower_label.startswith("shift")
                or lower_label.startswith("logic")
            ):
                should_merge = False

            if should_merge:
                if label in visited_identifiers:
                    cur_node_id = visited_identifiers[label]
                    is_existing_node = True
                else:
                    cur_node_id = str(node_counter)
                    node_counter += 1
                    visited_identifiers[label] = cur_node_id
            else:
                cur_node_id = str(node_counter)
                node_counter += 1
        else:
            cur_node_id = str(node_counter)
            node_counter += 1

        if not is_existing_node:
            dot.node(cur_node_id, label)
            layers[cycle_key].append(cur_node_id)
        
        if parent_id is not None:
            dot.edge(cur_node_id, parent_id)

        if node_sched is not None and hasattr(node, 'operands'):
            for child_node in node.operands:
                child_sched = find_node_by_id(child_node.id)
                add_node_and_edges(
                    node_sched=child_sched, node=child_node, parent_id=cur_node_id
                )

    root_sched = find_node_by_id(root_id)
    if root_sched:
        add_node_and_edges(node_sched=root_sched, node=root_sched.node)
    
    if "source" in layers:
        with dot.subgraph(name="cluster_inputs") as s:
            s.attr(style='invis')
            s.attr(rank='source')
            for nid in layers["source"]:
                s.node(nid)

    sorted_cycles = sorted([k for k in layers.keys() if k != "source"])
    
    for cycle in sorted_cycles:
        with dot.subgraph(name=f"cycle_{cycle}") as s:
            s.attr(rank='same')
            for nid in layers[cycle]:
                s.node(nid)

    return dot


def parse_expression(expression):
    try:
        tree = ast.parse(expression, mode="eval").body
        return tree
    except SyntaxError as e:
        print(f"Error parsing expression: {e}")
        return


def expression_to_graph(expression):
    return parse_expression(expression)
