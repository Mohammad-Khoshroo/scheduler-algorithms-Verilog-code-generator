from abc import ABC, abstractmethod
from .dfg_creator import BaseNode, OperatorNode, IdentifierNode, OutputNode, resource_allocator, OP_TYPES
from typing import List , Optional

class ScheduledNodeInfo:
    def __init__(self, node : OperatorNode | OutputNode, scheduled_time : int, resource_num : int, duration_cycles :int = 1):
        self.node = node
        self.scheduled_time = scheduled_time
        self.duration_cycles = duration_cycles
        
        if isinstance(node, OutputNode):
            self.node_op = "OUTPUT"
            self.resource = "OUTPUT"    
        elif isinstance(node, OperatorNode):
            self.node_op = node.op_type
            if self.node_op == "wiring":
                self.resource = "wiring"
            else:
                if resource_num == -1 and self.node_op != "MUX":
                    self.resource = "wiring"
                elif resource_num == -1 and self.node_op == "MUX":
                    self.resource = self.node_op
                else:
                    self.resource = self.node_op + str(resource_num)
        
        self.resource_num = resource_num
        

class ListScheduler(ABC):
    
    def __init__(self, dfg_roots : BaseNode| list[Optional:BaseNode], numof_resources : dict, op_cycs: dict = None):
        
        if isinstance(dfg_roots, list):
            self.roots = dfg_roots  
        else:
            self.roots = [dfg_roots]
        
        if numof_resources is None:
            self.numof_resources = {}
        else:
            self.numof_resources = numof_resources
        
        for op in OP_TYPES:
            if op not in self.numof_resources:
                if op == "MUX" or op == "wiring":
                    pass
                else:
                    self.numof_resources[op] = 1

        self.scheduled_nodes_info : List[ScheduledNodeInfo] = []
        self.min_latency = 0
        
        self.nodes :set[OperatorNode|OutputNode] = set()
        self.priorities = {}
        self.scheduled_ids = set()
        
        
        for root in self.roots:
            self._get_all_nodes(root)
        
        self._calculate_priorities()
        
        self.current_time = 1

    def _mark_as_scheduled(self, node: OperatorNode, res_idx: int, duration_cycles: int = 1):
        '''
            For a node, records its execution cycle and index of the resource to be executed on.
        '''
        recorded_info = ScheduledNodeInfo(node=node, scheduled_time=self.current_time, resource_num=res_idx, duration_cycles=duration_cycles)
        self.scheduled_nodes_info.append(recorded_info)
        self.scheduled_ids.add(node.id)

    def _get_all_nodes(self, root: BaseNode) -> None:
        if root in self.nodes:
            return
        
        if isinstance(root, OperatorNode) or isinstance(root, OutputNode):
            self.nodes.add(root)
        
            for child in root.operands:
                if child is not None:
                    self._get_all_nodes(child)    
    
    
    def _get_node_priority(self, node: OperatorNode | OutputNode) -> int:
        return self.priorities.get(node.id, 0)

    def _calculate_priorities(self) -> dict[int, int]:
        '''
            Calculates priorities for each node based on its distance from the root.
            The priority is defined as the length of the longest path from the node to any leaf node.
        '''
        def assign_levels(node : BaseNode, level : int):
             
            if not isinstance(node, OperatorNode) and (not isinstance(node, OutputNode)):
                self.min_latency =  max(self.min_latency, level + 1)
                return

            if node.id in self.priorities:
                self.priorities[node.id] = max(self.priorities[node.id], level)
            else:
                self.priorities[node.id] = level
            
            
            for child in node.operands:
                    assign_levels(child, level + 1)

        for root in self.roots:
            assign_levels(root, 0)
    
    def _find_candidate_nodes(self) -> List[OperatorNode|OutputNode]:
        '''
            Returns a list of nodes that are ready to execute at the time.
            Operands of these nodes are either an IdentifierNode or the result of an already executed OperatorNode.
        '''
        candidates = []
        
        for node in self.nodes:
 
            if node.id in self.scheduled_ids:
                continue
                
            is_ready = True
            for operand in node.operands:                
                if isinstance(operand, OperatorNode):
                    if operand.id not in self.scheduled_ids:
                        is_ready = False
                        break
                       
            if is_ready:
                candidates.append(node)
                
        return candidates
    
    @abstractmethod
    def _select_from_frontier(self, frontier : list[OperatorNode]) -> List[OperatorNode]:
        '''
            Based on the algorithm, it selects nodes from frontier to be executed on the currently available resources.
            Frontier is the output of find_candidate_nodes.
        '''
        pass

    @abstractmethod
    def schedule(self) -> None:
        '''
            Performes the process of scheduling.
            It repeatedly selects some nodes from frontier to be executed at the time and records their scheduling information until there are no more nodes. 
        '''
        pass
    
    def get_scheduling_info(self) -> List[ScheduledNodeInfo]:
        '''
            Returns the list of all ScheduledNodeInfos sorted by their node id.
        '''
        return sorted(self.scheduled_nodes_info, key = lambda node_info: node_info.node.id)


class MinResourceScheduler(ListScheduler):
    
    def __init__(self, dfg_root: BaseNode|List[BaseNode], numof_resources : dict, max_time : int, op_cycs : dict = None):
        
        super().__init__(dfg_roots=dfg_root, numof_resources=numof_resources,op_cycs=op_cycs)
        self.max_time = max_time
        self.latest_times : dict[int : int] = {}  

        self._find_latest_times()
        
    def _get_node_slack(self, node: OperatorNode) -> int:
        # Slack = ALAP - Current_Time
        return self.latest_times.get(node.id, self.max_time) - self.current_time

    def _find_latest_times(self):
        # ALAP = Max_Time - Priority (Distance to Output)
        for node in self.nodes:
            p = self._get_node_priority(node)
            self.latest_times[node.id] = self.max_time - p
            
    def _select_from_frontier(self, frontier: List[BaseNode]) -> List[BaseNode]:
        frontier.sort(key=self._get_node_slack)
        return frontier

    
    def schedule(self) -> None:
        
        def is_power_of_two(n):
            if n == None: return 0
            return (n > 0) and ((n & (n - 1)) == 0)
        
        # {cycle: {resource_type: count}}        
        resource_usage_per_cycle = {}

        while len(self.scheduled_ids) < len(self.nodes):
            
        
            if self.current_time > self.max_time:
                raise RuntimeError("schedule need more cycle!!!")
            
            if self.current_time not in resource_usage_per_cycle:
                resource_usage_per_cycle[self.current_time] = {op: 0 for op in OP_TYPES}
            
            while True:
                candidates = self._find_candidate_nodes()
                if not candidates:
                    break    
                
        
                sorted_candidates = self._select_from_frontier(candidates)
                
        
                progress_flag = False
                
                for node in sorted_candidates:
                    
                    resource_type = resource_allocator(node)
                    slack = self._get_node_slack(node)
                    
                    
                    is_free = False
                    if  resource_type is None or\
                        (isinstance(node , OperatorNode) and (node.op_type == "MUX" or node.op_type == "ROM-LUT") and self.op_cycles.get(node.op_type, 1)==0) or\
                        (isinstance(node , OperatorNode) and  node.op_type == "shift" and len(node.operands) > 1 and (isinstance(node.operands[1], int) or (isinstance(node.operands[1], IdentifierNode) and node.value != None)) ) or\
                        (isinstance(node , OperatorNode) and  node.op_type == "mult"  and\
                            ((isinstance(node.operands[0],IdentifierNode) and  node.operands[0].value!= None and is_power_of_two(node.operands[0].value)) or ( len(node.operands) > 1 and isinstance(node.operands[1], IdentifierNode) and node.operands[1].value != None and is_power_of_two(node.operands[1].value)) or (isinstance(node.operands[0], int) and is_power_of_two(node.operands[0])) or ( len(node.operands) > 1 and isinstance(node.operands[1], int) and is_power_of_two(node.operands[1])) ) ):
                        is_free = True
                        
                    if is_free:
                        self._mark_as_scheduled(node, res_idx=-1, duration_cycles=0)
                        progress_flag = True
                        break 

                    else:
                        usage_dict = resource_usage_per_cycle[self.current_time]
                        
                        if resource_type not in usage_dict:
                            usage_dict[resource_type] = 0
                            if resource_type not in self.numof_resources: self.numof_resources[resource_type] = 0

                        current_res_count = usage_dict.get(resource_type, 0)
                        available_limit = self.numof_resources.get(resource_type, 1)

                        if current_res_count < available_limit:
                            usage_dict[resource_type] = current_res_count + 1
                            self._mark_as_scheduled(
                                node=node,
                                res_idx=usage_dict[resource_type]
                            )
                            progress_flag = True
                        
                        elif slack > 0 :
                            pass
                            
                        elif slack <= 0:
                            self.numof_resources[resource_type] = available_limit + 1
                            usage_dict[resource_type] = current_res_count + 1
                            self._mark_as_scheduled(
                                node=node,
                                res_idx=self.numof_resources[resource_type]
                            )
                            progress_flag = True
                
                if not progress_flag:
                    break
            
            self.current_time += 1
            

class MinLatencyScheduler(ListScheduler):
    
    def __init__(self, dfg_root: List[BaseNode], numof_resources: dict, op_cycs : dict = None):
        super().__init__(dfg_roots=dfg_root, numof_resources=numof_resources,op_cycs=op_cycs)
        self.resource_queues: dict[str, list] = {}

    def _select_from_frontier(self, condidates: List[BaseNode]) -> List[BaseNode]:
        
        selected_nodes = []
        self.resource_queues = {}
        
        for node in condidates:
            
            resource_type = resource_allocator(node)
            
            if (resource_type  == None) or (resource_type == "MUX"):
                resource_type = "free"
            
            if resource_type not in self.resource_queues:
                self.resource_queues[resource_type] = []
                
            self.resource_queues[resource_type].append(node)
            
        for _ , nodes in self.resource_queues.items():
            nodes.sort(key=lambda n: (self._get_node_priority(n), -n.id), reverse=True)
            
            selected_nodes.extend(nodes)

        return selected_nodes
            
    def schedule(self) -> None:
        
        def is_power_of_two(n):
            if n == None: return 0
            return (n > 0) and ((n & (n - 1)) == 0)
        
        while len(self.scheduled_ids) < len(self.nodes):
            
            resource_usage = {op: 0 for op in self.numof_resources.keys()}
            
            while True:
                candidates = self._find_candidate_nodes()
                
                if (not candidates):
                    break
                
                selected = self._select_from_frontier(candidates)

                progress_flag = False
                
                for node in selected:  
                                
                    resource_type = resource_allocator(node)
                    
                    if  resource_type is None or\
                        (isinstance(node , OperatorNode) and node.op_type == "MUX" ) or\
                        (isinstance(node , OperatorNode) and  node.op_type == "shift" and len(node.operands) > 1 and (isinstance(node.operands[1], int) or (isinstance(node.operands[1], IdentifierNode) and node.operands[1].value != None)) ) or\
                        (isinstance(node , OperatorNode) and  node.op_type == "mult"  and\
                            ((isinstance(node.operands[0], IdentifierNode) and node.operands[0].value != None and is_power_of_two(node.operands[0].value)) or (len(node.operands) > 1 and isinstance(node.operands[1], IdentifierNode) and node.operands[1].value != None and is_power_of_two(node.operands[1].value)) or (isinstance(node.operands[0], int) and is_power_of_two(node.operands[0])) or ( len(node.operands) > 1 and isinstance(node.operands[1], int) and is_power_of_two(node.operands[1])) ) ):
                        
                        self._mark_as_scheduled(node, res_idx=-1, duration_cycles=0)
                        progress_flag = True
                        break 

                    else:
                        if resource_type not in resource_usage:
                            raise KeyError(f"Resource '{resource_type}' required for node {node.id} but not found in numof_resources.")

                        available = self.numof_resources.get(resource_type, 1)
                        used = resource_usage[resource_type]
                        
                        
                        if used < available:
                            
                            
                            self._mark_as_scheduled(
                                node=node,
                                res_idx= resource_usage[resource_type],
                            )
                        
                            progress_flag = True
                          
                            resource_usage[resource_type] += 1
                        
                       
                if not progress_flag:
                    break    
                
            self.current_time += 1