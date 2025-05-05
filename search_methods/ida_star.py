from search_methods.solver import Solver
from sokoban.map import Map

from typing import List, Set, Union, Dict
from collections import defaultdict
import math

class IDAStarSolver(Solver):
    def __init__(self, 
                 map: Map,
                 heuristic,
                 deadlocks,
                 max_depth: int = 100, 
                 debug: bool = False
                 ) -> None:
        super().__init__(map)
        self.heuristic = heuristic
        self.path = []
        self.visited = set()
        self.nodes_expanded = 0
        self.max_depth = max_depth
        self.debug = debug
        self.deadlocks = deadlocks

    def solve(self) -> Union[List[int], None]:
        threshold = self.heuristic(self.map, self.deadlocks)

        self.path: List[Map] = [self.map.copy()]

        path_dict: Dict[int, int] = {}

        while True:
            self.cost_so_far = defaultdict(lambda: math.inf)
            self.cost_so_far[self._hash(self.map)] = 0

            self.nodes_expanded = 0
            result = self.search(self.map.copy(), path_dict, 0, threshold, set())

            if result == 'FOUND':
                return self.path
            if result == float('inf'):
                return None

            threshold = result

    def search(self, 
               current_map: Map, 
               path_dict: Dict[int, int], 
               g: int, 
               threshold: int, 
               path_visited: Set[str]
               ) -> Union[float, str]:
        self.nodes_expanded += 1

        state_key = str(current_map)
        if state_key in path_visited:
            return float('inf')
        path_visited.add(state_key)

        try:
            h = self.heuristic(current_map, self.deadlocks)
            f = g + h

            if f > threshold:
                return f
            
            if g >= self.max_depth:
                return float('inf')
            
            if current_map.is_solved():
                self.path = [path_dict[i] for i in range(g)]
                return 'FOUND'
            
            min_cost = float('inf')

            for move in current_map.filter_possible_moves():
                path_dict[g] = move

                new_map = current_map.copy()
                try:
                    new_map.apply_move(move)
                except ValueError as e:
                    if self.debug:
                        print(f"Invalid move {move} attempted: {e}")
                    del path_dict[g]
                    continue

                hash = self._hash(new_map)
                if g + 1 >= self.cost_so_far[hash]:
                    del path_dict[g]
                    continue
                self.cost_so_far[hash] = g + 1
                    
                result = self.search(new_map, path_dict, g + 1, threshold, path_visited)
                    
                if result == "FOUND":
                    return "FOUND"
                if result < min_cost:
                    min_cost = result
                        
                del path_dict[g]

            return min_cost
        
        finally:
            path_visited.remove(state_key)

    def _hash(self, state: Map) -> tuple:
        """
        A simple, collision-resistant hash: sorted box positions plus player pos.
        """
        boxes = tuple(sorted((b.x, b.y) for b in state.boxes.values()))
        player = (state.player.x, state.player.y)
        return boxes + (player,)
