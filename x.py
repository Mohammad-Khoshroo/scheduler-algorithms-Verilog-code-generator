import graphviz
import ast

def visualize_graph(root, version=1, output_format='png'):
    dot = graphviz.Digraph(comment="Abstract Syntax Tree")
    dot.attr(dpi="300", rankdir="TB", size="10,10", splines="true")
    dot.format = output_format

    node_counter = 0
    visited_identifiers = dict()
    identifier_nodes = []

    # تابع کمکی برای خواندن مقدار ثابت (برای تمیزتر شدن گراف)
    def get_constant_value(node):
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None

    def add_node_and_edges(node, parent_id=None, edge_label=""):
        nonlocal node_counter
        nonlocal visited_identifiers
        
        # --- هندل کردن تاپل (چند خروجی) ---
        if isinstance(node, ast.Tuple):
            for i, elt in enumerate(node.elts):
                out_id = f"Output_Node_{i}"
                label = f"Out {i}"
                dot.node(out_id, label, shape="doublecircle", style="filled", fillcolor="#e0e0e0")
                add_node_and_edges(elt, parent_id=out_id)
            return 

        cur_node_id = str(node_counter)
        node_counter += 1
        label = ""
        
        # رنگ و شکل پیش‌فرض
        shape = "ellipse"
        style = "filled"
        fillcolor = "white"

        # ==========================================
        # 1. بخش جدید: هندل کردن Subscript (ایندکس و اسلایس)
        # ==========================================
        if isinstance(node, ast.Subscript):
            # بخش اول: متغیری که داریم روی آن عملیات انجام می‌دهیم (Target)
            # مثلا در x[7:0]، مقدار x همان value است
            add_node_and_edges(node.value, cur_node_id, edge_label="Target")

            # بخش دوم: تشخیص نوع اسلایس
            if isinstance(node.slice, ast.Slice):
                # حالت بازه: [7:0]
                # سعی می‌کنیم مقادیر ثابت را بخوانیم تا گراف شلوغ نشود
                lower = get_constant_value(node.slice.lower)
                upper = get_constant_value(node.slice.upper)
                
                if lower is not None and upper is not None:
                    # اگر هر دو عدد ثابت بودند، توی لیبل می‌نویسیم
                    label = f"Slice [{lower}:{upper}]"
                else:
                    # اگر متغیر بودند (مثل x[a:b])، نود جداگانه می‌سازیم
                    label = "Slice [ : ]"
                    if node.slice.lower:
                        add_node_and_edges(node.slice.lower, cur_node_id, edge_label="Lower")
                    if node.slice.upper:
                        add_node_and_edges(node.slice.upper, cur_node_id, edge_label="Upper")
                
                shape = "box" # شکل مستطیلی برای اسلایس
                fillcolor = "#fff2cc" # زرد کمرنگ

            else:
                # حالت ایندکس ساده: [i] یا [3]
                idx_val = get_constant_value(node.slice)
                if idx_val is not None:
                    label = f"Index [{idx_val}]"
                else:
                    label = "Index [ ]"
                    add_node_and_edges(node.slice, cur_node_id, edge_label="Idx")
                
                shape = "box"
                fillcolor = "#fff2cc"

        # ==========================================
        # 2. آپدیت بخش Call برای پشتیبانی از concat
        # ==========================================
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else 'func'
            
            if func_name == "concat":
                label = "{ Concat }"
                shape = "octagon" # شکل متفاوت برای کانکت
                fillcolor = "#d5e8d4" # سبز کمرنگ
            else:
                label = f"Call: {func_name}"
            
            # افزودن آرگومان‌ها
            for i, arg in enumerate(node.args):
                # اگر کانکت بود، شماره پورت رو هم بنویسیم بد نیست
                e_lbl = f"in{i}" if func_name == "concat" else ""
                add_node_and_edges(arg, cur_node_id, edge_label=e_lbl)

        # --- بقیه نودها (کد قبلی) ---
        elif isinstance(node, ast.BinOp):
            label = f"{determine_operation_type(node.op)}"
            add_node_and_edges(node.left, cur_node_id)
            add_node_and_edges(node.right, cur_node_id)

        elif isinstance(node, ast.UnaryOp):
            label = f"{determine_operation_type(node.op)}"
            add_node_and_edges(node.operand, cur_node_id)

        elif isinstance(node, ast.IfExp):
            label = "MUX"
            add_node_and_edges(node.test, cur_node_id, edge_label="Sel")
            add_node_and_edges(node.body, cur_node_id, edge_label="True")
            add_node_and_edges(node.orelse, cur_node_id, edge_label="False")
            shape = "diamond"

        elif isinstance(node, ast.Compare):
            label = f"{determine_operation_type(node.ops[0])}"
            add_node_and_edges(node.left, cur_node_id)
            for comp in node.comparators:
                add_node_and_edges(comp, cur_node_id)

        elif isinstance(node, ast.Name):
            label = f"{node.id}"

        elif isinstance(node, ast.Constant):
            label = f"{node.value}"
        
        else:
            label = type(node).__name__

        # --- رسم نود و یال ---
        if version == 2 and isinstance(node, ast.Name):
            if label in visited_identifiers:
                existing_id = visited_identifiers[label]
                if parent_id is not None:
                    dot.edge(existing_id, parent_id, label=edge_label, fontcolor="red", fontsize="10")
                return
            else:
                visited_identifiers[label] = cur_node_id
                dot.node(cur_node_id, label, shape="circle", style="filled", fillcolor="lightblue")
                identifier_nodes.append(cur_node_id)
        else:
            # اعمال استایل‌های تعیین شده
            dot.node(cur_node_id, label, shape=shape, style=style, fillcolor=fillcolor)

        if parent_id is not None:
            dot.edge(cur_node_id, parent_id, label=edge_label, fontsize="10")

    add_node_and_edges(root)

    if version == 2 and identifier_nodes:
        with dot.subgraph() as s:
            s.attr(rank="source")
            for nid in identifier_nodes:
                s.node(nid)
                
    return dot