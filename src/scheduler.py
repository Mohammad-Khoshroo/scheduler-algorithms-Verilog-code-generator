from abc import ABC, abstractmethod
from .dfg_creator import BaseNode, OperatorNode, resource_allocator, OP_TYPES
from typing import List

class ScheduledNodeInfo:
    def __init__(self, node : OperatorNode, scheduled_time : int, resource_num : int, duration_cycles :int = 1):
        self.node = node
        self.scheduled_time = scheduled_time
        self.duration_cycles = duration_cycles
        self.resource_num = resource_num


class ListScheduler(ABC):
    
    def __init__(self, dfg_root : BaseNode, numof_reources : dict):
        self.root = dfg_root
        if numof_reources is None:
            self.numof_resources = {op: 1 for op in OP_TYPES}
        else:
            self.numof_resources = numof_reources

        self.scheduled_nodes_info : List[ScheduledNodeInfo] = []
        self.min_latency = 0
        
        self.nodes :set[OperatorNode] = set()
        self.priorities = {}
        self.scheduled_ids = set()
        
        self._get_all_nodes(self.root)
        self._calculate_priorities()
        
        self.current_time = 1

    def record_scheduled_node(self, node : OperatorNode, scheduled_time : int, resource_num : int, duration_cycles :int = 1):
        '''
            For a node, records its execution cycle and index of the resource to be executed on.
        '''
        recorded_info = ScheduledNodeInfo(node=node, scheduled_time=scheduled_time, resource_num=resource_num, duration_cycles=duration_cycles)
        self.scheduled_nodes_info.append(recorded_info)

    def _get_all_nodes(self, root: BaseNode) -> None:
        '''
            Recursively collects all OperatorNodes in the DFG starting from root.
        '''
        if isinstance(root, OperatorNode):
            self.nodes.add(root)
        
            for child in root.operands:
                if child is not None:
                    self._get_all_nodes(child)    
    
    def _get_node_priority(self, node: OperatorNode) -> int:
        '''
            Returns the priority of a node.
        '''
        return self.priorities.get(node.id, 0)

    def _calculate_priorities(self) -> dict[int, int]:
        '''
            Calculates priorities for each node based on its distance from the root.
            The priority is defined as the length of the longest path from the node to any leaf node.
        '''
        def assign_levels(node : BaseNode, level : int):
             
            if not isinstance(node, OperatorNode):
                self.min_latency =  max(self.min_latency, level + 1)
                return

            if node.id in self.priorities:
                self.priorities[node.id] = max(self.priorities[node.id], level)
            else:
                self.priorities[node.id] = level

            for child in node.operands:
                assign_levels(child, level + 1)

        assign_levels(self.root, 0)
    
    def _find_candidate_nodes(self) -> List[OperatorNode]:
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
    def _select_from_frontier(self, frontier : dict) -> List[OperatorNode]:
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


class MinLatencyScheduler(ListScheduler):
    
    def __init__(self, dfg_root: BaseNode, numof_resources: dict):
        super().__init__(dfg_root=dfg_root, numof_reources=numof_resources)
        self.resource_queues: dict[str, list] = {}

    def _select_from_frontier(self, condidates: List[OperatorNode]) -> List[OperatorNode]:
        
        selected_nodes = []
        self.resource_queues = {}
        
        for node in condidates:
            
            resource_type = resource_allocator(node)
            
            if resource_type not in self.resource_queues:
                self.resource_queues[resource_type] = []
                
            self.resource_queues[resource_type].append(node)
            
        for resource_type, nodes in self.resource_queues.items():
            nodes.sort(key=self._get_node_priority, reverse=True)
            
            available_count = self.numof_resources.get(resource_type, 0)
            
            nodes_to_pick = nodes[:available_count]
            
            selected_nodes.extend(nodes_to_pick)
        
        return selected_nodes
            
    def schedule(self) -> None:
        
        
        while len(self.scheduled_ids) < len(self.nodes):
            
            resource_usage = {op: 0 for op in self.numof_resources.keys()}
            
            candidates = self._find_candidate_nodes()
            
            if (not candidates):
                raise RuntimeError("Deadlock detected or disconnected graph.")

            
            selected = self._select_from_frontier(candidates)

            for node in selected:  
                              
                resource_type = resource_allocator(node)
                if resource_type not in resource_usage:
                        raise KeyError(f"Resource '{resource_type}' required for node {node.id} but not found in numof_resources.")

                self.record_scheduled_node(
                    node=node, 
                    scheduled_time=self.current_time, 
                    resource_num = resource_usage[resource_type]
                )
                self.scheduled_ids.add(node.id)
            
                resource_usage[resource_type] += 1
            
            self.current_time += 1


class MinResourceScheduler(ListScheduler):
    
    def __init__(self, dfg_root : BaseNode, numof_resources : dict, max_time : int):
        
        super().__init__(dfg_root=dfg_root, numof_reources=numof_resources)
        self.max_time = max_time
        self.latest_time = self.find_latest_times()


    '''
        Assigns the latest possible time for each node to be executed.
        It's used on Minimum-Resource, Latency-Constrained algorithm.
    '''
    # TODO
    def find_latest_times(self) -> dict:
        latest_time = dict()
        # ...
        return latest_time
   
    # TODO
    def find_candidate_nodes(self) -> List[OperatorNode]:
        pass

    # TODO
    def select_from_frontier(self, frontier : dict) -> List[OperatorNode]:
        pass

    # TODO
    def schedule(self) -> None:
        pass
