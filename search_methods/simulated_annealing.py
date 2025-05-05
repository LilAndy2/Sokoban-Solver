from search_methods.solver import Solver
from sokoban.map import Map
from search_methods.heuristics import total_manhattan_distance
import numpy as np

class SimulatedAnnealingSolver(Solver):
    def __init__(self, 
                 map: Map,
                 heuristic,
                 deadlocks,
                 initial_temp: float = 1000,
                 decay_rate: float = 0.000003,
                 min_temp: float = 1) -> None:
        super().__init__(map)
        self.initial_temp = initial_temp
        self.decay_rate = decay_rate
        self.min_temp = min_temp
        self.alpha = 0.01
        self.heuristic = heuristic
        self.deadlocks = deadlocks

        self.nodes_expanded = 0
        self.pull_moves = 0

        self.move_path: list[int] = []

    def softmax(self, x: np.array) -> float:
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    def solve(self) -> list[int]:
        current_map = self.map.copy()
        temp = self.initial_temp

        # count every time we generate/evaluate a successor
        nodes = 0

        while temp > self.min_temp:
            if current_map.is_solved():
                break

            curr_h = self.heuristic(current_map, self.deadlocks)
            moves = current_map.filter_possible_moves()
            next_states = []
            next_moves  = []
            
            for mv in moves:
                nodes += 1
                m2 = current_map.copy()
                try:
                    m2.apply_move(mv)
                    next_states.append(m2)
                    next_moves.append(mv)
                except ValueError:
                    continue

            if not next_states:
                temp *= (1 - self.decay_rate)
                continue
            
            scores = [ total_manhattan_distance(s, self.deadlocks)
                       for s in next_states ]

            idx = np.random.choice(len(next_states),
                                   p=self.softmax(-np.array(scores)))
            sel_state = next_states[idx]
            sel_score = scores[idx]
            sel_move  = next_moves[idx]

            accept = (sel_score < curr_h) or \
                     (np.exp((curr_h - sel_score)/(temp*self.alpha))
                        > np.random.rand())

            if accept:
                current_map = sel_state
                self.move_path.append(sel_move)

            temp *= (1 - self.decay_rate)

        self.nodes_expanded = nodes

        final_map = self.map.copy()
        for mv in self.move_path:
            final_map.apply_move(mv)
        self.pull_moves = final_map.undo_moves

        return self.move_path
