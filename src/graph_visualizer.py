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

    elif isinstance(op, (ast.Mult)):
        return f"mult({sym})"
    
    elif isinstance(op, (ast.Div, ast.FloorDiv, ast.Mod)):
        return f"div({sym})"
    
    elif isinstance(op, (ast.LShift, ast.RShift)):
        return f"shift({sym})"

    elif isinstance(op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
        return f"logic({sym})"

    elif isinstance(op, (ast.Invert, ast.USub)):
        return f"ULogic({sym})"

    elif isinstance(op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
        return f"ALU[cmp]({sym})"

    else:
        return f"?({sym})"

def visualize_graph(root, version=1):
    dot = graphviz.Digraph(comment="Abstract Syntax Tree")
    dot.attr(dpi="300", rankdir="TB", size="8,8", splines="true")

    node_counter = 0
    visited_identifiers = dict()
    identifier_nodes = []
    
    def get_constant_value(node):
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None

    def add_node_and_edges(node, parent_id=None, edge_label=""):
        nonlocal node_counter
        nonlocal visited_identifiers
        fillcolor = "white"
        
        if isinstance(node, ast.Tuple) and parent_id is None:
            for i, elt in enumerate(node.elts):
                out_id = f"Output_Node_{i}"
                dot.node(out_id, f"Out {i}", style="filled", fillcolor="#b9b9b9")
                add_node_and_edges(elt, parent_id=out_id)            
            return 

        cur_node_id = str(node_counter)
        node_counter += 1

        label = "" 
        is_shared_node = False
        
        if isinstance(node, ast.BinOp):
            label = determine_operation_type(node.op)
            add_node_and_edges(node.left, cur_node_id)
            add_node_and_edges(node.right, cur_node_id)

        elif isinstance(node, ast.UnaryOp):
            label = determine_operation_type(node.op)
            add_node_and_edges(node.operand, cur_node_id)
            
        elif isinstance(node, ast.Compare):
            label = determine_operation_type(node.ops[0])
            add_node_and_edges(node.left, cur_node_id, edge_label="L")
            for i, comp in enumerate(node.comparators):
                lbl = "R" if len(node.comparators) == 1 else f"R{i}"
                add_node_and_edges(comp, cur_node_id, edge_label=lbl)

        elif isinstance(node, ast.Name):
            if "rom" in node.id.lower():
                label = f"ROM-LUT({node.id[4:]})"
                fillcolor = "lightgreen"
                is_shared_node = True
            else:
                label = f"{node.id}"
                fillcolor = "lightblue"
                if version == 2:
                    is_shared_node = True

        elif isinstance(node, ast.Constant):
            label = f"const= {node.value}"
            fillcolor = "lightblue"
        
        elif isinstance(node, ast.Subscript):
            is_constant_op = False
            edge_text = ""
            
            if isinstance(node.slice, ast.Slice):
                lower = get_constant_value(node.slice.lower)
                upper = get_constant_value(node.slice.upper)
                if lower is not None and upper is not None:
                    is_constant_op = True
                    edge_text = f"[{lower}:{upper}]"
            else:
                idx_node = node.slice
                idx_val = get_constant_value(idx_node)
                if idx_val is not None:
                    is_constant_op = True
                    edge_text = f"[{idx_val}]"

            if is_constant_op:
                if edge_label: edge_text = f"{edge_label}\n{edge_text}"
                add_node_and_edges(node.value, parent_id, edge_label=edge_text)
                return
            
            add_node_and_edges(node.value, cur_node_id)
            
            if isinstance(node.slice, ast.Slice):
                label = "Slice [ : ]"
                if node.slice.lower: add_node_and_edges(node.slice.lower, cur_node_id, edge_label="Lower")
                if node.slice.upper: add_node_and_edges(node.slice.upper, cur_node_id, edge_label="Upper")
            else:
                label = "MUX(Index[ ])"
                slice_n = node.slice
                add_node_and_edges(slice_n, cur_node_id, edge_label="select(idx)")
                
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else 'func'
            
            if func_name == "concat":
                dot.node(cur_node_id, label="", shape="point", width="0.1")
                for i, arg in enumerate(node.args):
                    add_node_and_edges(arg, cur_node_id, edge_label=f"part_{i}")
                if parent_id is not None:
                    dot.edge(cur_node_id, parent_id, label=edge_label, minlen="2")
                return

            label = f"Call: {func_name}"
            if func_name in ["min", "max"]:
                label = func_name.upper()
                fillcolor = "#ffe6cc"
            elif func_name == "abs":
                label = "| Abs |"
                fillcolor = "#dae8fc"

            for i, arg in enumerate(node.args):
                add_node_and_edges(arg, cur_node_id)
    
        elif isinstance(node, ast.IfExp):
            label = "MUX (?:)"
            add_node_and_edges(node.test, cur_node_id, edge_label="select")
            add_node_and_edges(node.body, cur_node_id, edge_label="true")
            add_node_and_edges(node.orelse, cur_node_id, edge_label="false")
        
        else:
            label = type(node).__name__

        # DRAW        
        if is_shared_node:
            if label in visited_identifiers:
                existing_id = visited_identifiers[label]
                if parent_id is not None:
                    dot.edge(existing_id, parent_id, label=edge_label)
                return
            else:
                visited_identifiers[label] = cur_node_id
                identifier_nodes.append(cur_node_id)
        
        dot.node(cur_node_id, label, style="filled", fillcolor=fillcolor)

        if parent_id is not None:
            dot.edge(cur_node_id, parent_id, label=edge_label)

    add_node_and_edges(root)

    if identifier_nodes:
        with dot.subgraph() as s:
            s.attr(rank="source")
            for nid in identifier_nodes:
                s.node(nid)
                
    return dot


def visualize_dfg(all_nodes, output_format='png'):
    dot = graphviz.Digraph(comment="Data Flow Graph")
    dot.attr(dpi="300", rankdir="TB", size="8,8", splines="true")
    dot.format = output_format

    for node in all_nodes:
        node_id = str(node.id)
        
        label = node.name
        shape = "ellipse"
        style = "filled"
        fillcolor = "white"
        fontsize = "14"
        width = "0.75"
        height = "0.5"

        if isinstance(node, IdentifierNode):
            fillcolor = "lightblue"
            if "rom" in node.name.lower():
                label = f"ROM-LUT({node.name.replace('rom', '').strip('_')})"
                fillcolor = "lightgreen"
            elif node.value is not None:
                label = f"const= {node.value}"
            else:
                label = node.name
        
        elif isinstance(node, OutputNode):
            fillcolor = "lightgray"
           
        elif isinstance(node, OperatorNode):
        
            label = f"{node.op_type}({node.name})"
        
            if node.op_type == "wiring":
                shape = "point"
                width = "0.1"
                height = "0.1"
                label = "const-index"
                fillcolor = "#666666"
            
            elif node.op_type == "MUX":
                if node.name == "?:": 
                    label = "MUX (?:)"
                    shape = "diamond"
                else: 
                    label = "MUX(Index[])"
                    fillcolor = "#fff2cc"

            elif node.op_type in ["min", "max"]:
                fillcolor = "#ffe6cc"
                label = node.op_type.upper()
            
            elif node.name == "abs":
                label = f"{node.op_type}(| Abs |)"
                fillcolor = "#dae8fc"
                    
        dot.node(node_id, label, shape=shape, style=style, fillcolor=fillcolor, 
                 fontsize=fontsize, width=width, height=height)

        if isinstance(node, (OperatorNode, OutputNode)):
            for i, operand in enumerate(node.operands):
                if operand is None: continue
                
                src_id = str(operand.id)
                edge_label = ""
                edge_color = "black"
                arrow_head = "normal"
                edge_style = "solid"
                minlen = "1"

                if isinstance(node, OperatorNode):
                    if node.op_type == "MUX":
                        if node.name == "?:":
                            if i == 0: 
                                edge_label = "select"
                                edge_color = "blue"
                                edge_style = "dashed"
                            elif i == 1: edge_label = "true"
                            elif i == 2: edge_label = "false"
                        else:
                            if i == 1: edge_label = "select(idx)"
                            else: edge_label = ""

                    elif node.name == "concat":
                        edge_label = f"part_{i}"

                    elif hasattr(node, 'op') and isinstance(node.op, (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                        if i == 0: edge_label = "L"
                        else: edge_label = f"R{i-1}" if i > 1 else "R"

                if isinstance(operand, OperatorNode) and operand.op_type == "wiring":
                    minlen = "2"
                    edge_color = "#555555"
                    arrow_head = "none"

                dot.edge(src_id, node_id, label=edge_label, 
                         color=edge_color, style=edge_style, 
                         fontsize="10", arrowhead=arrow_head, minlen=minlen)

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

def visualize_scheduled_graph_ranked(root_id, schedule_info: list, version=1):
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
    edges = []
    node_labels = {}

    def add_node_and_edges(node_sched, node, parent_id=None):
        nonlocal node_counter
        nonlocal visited_identifiers
        nonlocal layers
        nonlocal edges
        nonlocal node_labels

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
            if (
                label.startswith("const=")
                or label.startswith("ALU")
                or label.startswith("mult")
                or label.startswith("div")
                or label.startswith("shift")
                or label.startswith("logic")
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
            node_labels[cur_node_id] = label
            layers[cycle_key].append(cur_node_id)
        
        if parent_id is not None:
            edges.append((cur_node_id, parent_id))

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
                if nid in node_labels:
                    s.node(nid, label=node_labels[nid])

    sorted_cycles = sorted([k for k in layers.keys() if k != "source"])
    
    for cycle in sorted_cycles:
        with dot.subgraph(name=f"cycle_{cycle}") as s:
            s.attr(rank='same')
            for nid in layers[cycle]:
                if nid in node_labels:
                    s.node(nid, label=node_labels[nid])

    if "source" in layers and len(layers["source"]) > 0 and len(sorted_cycles) > 0:
         src_node = layers["source"][0]
         dst_node = layers[sorted_cycles[0]][0]
         dot.edge(src_node, dst_node, style="invis", weight="10")

    for i in range(len(sorted_cycles) - 1):
        c1 = sorted_cycles[i]
        c2 = sorted_cycles[i+1]
        if layers[c1] and layers[c2]:
            node_a = layers[c1][0]
            node_b = layers[c2][0]
            dot.edge(node_a, node_b, style="invis", weight="10")

    for src, dst in edges:
        dot.edge(src, dst)

    return dot


def parse_expression(expression):
    try:
        tree = ast.parse(expression, mode="eval").body
        return tree
    except SyntaxError as e:
        print(f"Error parsing expression: {e}")
        return

def expression_to_graph(input_data):
    
    if isinstance(input_data, str):
        final_expression = input_data
    
    elif isinstance(input_data, list):
        # input_data = ["a", "b", "c"]
        # final_expression = "(a, b, c)"
        final_expression = f"({', '.join(input_data)})"
    
    else:
        print("Error: Input format not supported.")
        return None

    print(f"Parsing: {final_expression}")
    
    root = parse_expression(final_expression)
    
    return root