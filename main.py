import ast
import sys
import json
from pathlib import Path
from src.dfg_creator import GraphBuilder
from src.graph_visualizer import expression_to_graph, visualize_graph, visualize_scheduled_graph,visualize_scheduled_graph_ranked 
from src.scheduler import MinLatencyScheduler, MinResourceScheduler, ScheduledNodeInfo
from src.code_generator import generate_verilog

MinResourceAlgorithm = "MinResourceLatencyConstrained"
MinlatencyAlgorithm = "MinLatencyResourceContrained"

def load_input(filename: str) -> dict:
    with open(filename, "r") as file:
        return json.load(file)

def ast_to_dict(node):
    if isinstance(node, ast.AST):
        result = {"_type": node.__class__.__name__}
        for field in node._fields:
            result[field] = ast_to_dict(getattr(node, field))
        return result
    elif isinstance(node, list):
        return [ast_to_dict(x) for x in node]
    else:
        return node

def build_dfg(expression: str, folder_path : str):
    
    ast_root = expression_to_graph(expression)
    # root
    # print(ast_root)          # BinOp

    # left and right operands
    # ast_root.left     - Name(id='a', ctx=Load())
    # ast_root.right    - BinOp(...)

    # operation
    # type(ast_root.op) - <class '_ast.Add'>
    
    # and recursively...
    # ast_root.right.left  , ast_root.right.right , ast_root.right.op , etc.
    
    with open(folder_path + "/ast_output.log", "w") as f:
        f.write(ast.dump(ast_root, indent=4))
    
    ast_dict = ast_to_dict(ast_root)
    with open(folder_path + "/ast_output.json", "w") as f:
        json.dump(ast_dict, f, indent=4)
    
        
    dotv1 = visualize_graph(ast_root,version = 1)
    dotv1.attr(label="", labelloc='t', fontsize='17')  
    dotv1.render(folder_path + "/pics/DFG-V1", format='png', view=False, cleanup=True)

    dotv2 = visualize_graph(ast_root,version = 2)
    dotv2.attr(label="", labelloc='t', fontsize='17')  
    dotv2.render(folder_path + "/pics/DFG-V2", format='png', view=False, cleanup=True)

    print("Visulization Done")
    
    builder = GraphBuilder()
    
    print("Build Done")
    return builder.build(ast_root)


def schedule_dfg(dfg_root, algorithm : str, config : dict, folder_path : str) -> list:
    
    if (algorithm == MinResourceAlgorithm):
        scheduler = MinResourceScheduler(dfg_root=dfg_root, max_time=config["MaxTime"], numof_resources=None)
    
    elif (algorithm == MinlatencyAlgorithm):
        scheduler = MinLatencyScheduler(dfg_root=dfg_root, numof_resources=config["Resources"])    
            
    else:
        raise ValueError(f"Unknown scheduling algorithm: {algorithm}")
    
    scheduler.schedule()
    schedule_info = scheduler.get_scheduling_info()

    print("schedule Done")
    dotv1 = visualize_scheduled_graph(root_id=dfg_root.id, schedule_info=schedule_info, version = 1)
    dotv1.attr(label="", labelloc='t', fontsize='17')  
    dotv1.render(folder_path + "/pics/ScheduledDFG-V1", format='png', view=False, cleanup=True)
    
    dotv2 = visualize_scheduled_graph(root_id=dfg_root.id, schedule_info=schedule_info, version = 2)
    dotv2.attr(label="", labelloc='t', fontsize='17')  
    dotv2.render(folder_path + "/pics/ScheduledDFG-V2", format='png', view=False, cleanup=True)

    print("Visualize schedule Done")
    dotv1 = visualize_scheduled_graph_ranked(root_id=dfg_root.id, schedule_info=schedule_info, version = 1)
    dotv1.attr(label="", labelloc='t', fontsize='17')  
    dotv1.render(folder_path + "/pics/RankedScheduledDFG-V1", format='png', view=False, cleanup=True)
    
    dotv2 = visualize_scheduled_graph_ranked(root_id=dfg_root.id, schedule_info=schedule_info, version = 2)
    dotv2.attr(label="", labelloc='t', fontsize='17')  
    dotv2.render(folder_path + "/pics/RankedScheduledDFG-V2", format='png', view=False, cleanup=True)
    print("Visualize Rank schedule done")

    return schedule_info

def save_result(folder_path : str, schedule_info : list[ScheduledNodeInfo]):
    json_output = {}
    with open(folder_path + "/output.json", "w") as file:
        for node_info in schedule_info:
            json_output[node_info.node.id] = {
                "clk_cycle": node_info.scheduled_time,
                "resource_type": node_info.node.op_type,
                "resource_num": node_info.resource_num
            }
        json.dump(json_output, file, indent=4)


def run_test(folder_path : str):
    input_file_path = folder_path + "/input.json"
    data = load_input(input_file_path)

    dfg_root = build_dfg(expression=data["Expression"], folder_path=folder_path)

    schedule_info = schedule_dfg(dfg_root, algorithm=data["Algorithm"], config=data["Config"], folder_path=folder_path)

    save_result(folder_path=folder_path, schedule_info=schedule_info)

    generate_verilog(folder_path=folder_path, schedule_info=schedule_info)

def main():
    if len(sys.argv) == 2:
        run_test(folder_path=sys.argv[1])
    else:
        print("Please provide the input folder path.")

if __name__ == "__main__":
    main()
