import math
from collections import deque
from typing import Tuple, Set, Dict, List
from sokoban.map import Map
from sokoban.moves import LEFT, RIGHT, UP, DOWN
from scipy.optimize import linear_sum_assignment
import itertools
from math import inf

###################################### HEURISTICS ######################################

def total_manhattan_distance(map: Map, deadlocks) -> int:
    deadlock_checkers = configure_deadlocks(map, deadlocks)

    if deadlock_checkers:
        for deadlock_checker in deadlock_checkers:
            if deadlock_checker(map):
                return inf
            
    """Calculate sum of Manhattan distances from boxes to nearest targets"""
    total = 0
    for box in map.positions_of_boxes.keys():
        min_dist = float('inf')
        for target in map.targets:
            dist = abs(box[0] - target[0]) + abs(box[1] - target[1])
            if dist < min_dist:
                min_dist = dist
        total += min_dist
    return total

def simulated_annealing_heuristic(map_obj: Map,
                                deadlocks,
                                w_player: float = 0.5,
                                w_undo: float = 10.0
                                ) -> float:
    """
    Annealing-tailored heuristic:
      - Uses Hungarian assignment on Manhattan distances, but squares them.
      - Adds player→box distance term.
      - Penalizes any “undo” moves taken so far.
    """

    deadlock_checkers = configure_deadlocks(map_obj, deadlocks)

    if deadlock_checkers:
        for deadlock_checker in deadlock_checkers:
            if deadlock_checker(map_obj):
                return inf
            
    # 1) build cost matrix of manhattan distances
    boxes   = list(map_obj.positions_of_boxes.keys())
    targets = map_obj.targets
    n, m    = len(boxes), len(targets)
    if n == 0 or m == 0:
        return 0.0

    # cost[i][j] = |box_i - target_j|
    cost = [[ abs(bx - tx) + abs(by - ty)
              for (tx, ty) in targets ]
            for (bx, by) in boxes ]

    # 2) optimal assignment
    row_ind, col_ind = linear_sum_assignment(cost)

    # 3) sum of *squared* distances
    total_sq = 0.0
    for i, j in zip(row_ind, col_ind):
        d = cost[i][j]
        total_sq += d*d

    # 4) player→nearest‐box
    px, py = map_obj.player.x, map_obj.player.y
    dist_pb = min(abs(px - bx) + abs(py - by) for bx,by in boxes)

    # 5) undo‐moves penalty
    u_penalty = map_obj.undo_moves

    return total_sq + w_player * dist_pb + w_undo * u_penalty

def hungarian_assignment(map: Map) -> float:
    width, length = map.width, map.length

    obstacles: Set[Tuple[int, int]] = set(map.obstacles)
    targets: List[Tuple[int, int]] = list(map.targets)
    boxes: List[Tuple[int, int]] = list(map.positions_of_boxes.keys())

    number_of_boxes = len(boxes)
    number_of_targets = len(targets)
    if number_of_boxes == 0 or number_of_targets == 0:
        return 0.0
    
    # BFS from all targets to compute distances ignoring boxes
    distances: Dict[Tuple[int, int], int] = {}
    visited: Set[Tuple[int, int]] = set()
    queue = deque()

    for tx, ty in targets:
        queue.append((tx, ty, 0))
        visited.add((tx, ty))

    while queue:
        x, y, d = queue.popleft()
        distances[(x, y)] = d

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < length and 0 <= ny < width and
                    (nx, ny) not in visited and (nx, ny) not in obstacles):
                visited.add((nx, ny))
                queue.append((nx, ny, d + 1))

    # Build cost matrix: shape (n_boxes, n_targets)
    cost_matrix = [[
        distances.get((bx, by), math.inf)
        for (tx, ty) in targets
    ] for (bx, by) in boxes]

    # Use Hungarian algorithm for minimal assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    total_cost = 0.0
    for i, j in zip(row_ind, col_ind):
        # Only sum assignments for existing boxes
        if i < number_of_boxes and j < number_of_targets:
            total_cost += cost_matrix[i][j]
    return total_cost
    
def ida_star_heuristic(map: Map, deadlocks) -> float:
    min_distance = hungarian_assignment(map)

    deadlock_checkers = configure_deadlocks(map, deadlocks)

    if deadlock_checkers:
        for deadlock_checker in deadlock_checkers:
            if deadlock_checker(map):
                return inf
            
    # If no deadlocks were detected, return the Hungarian algorithm lower bound
    return min_distance

def manhattan_greedy_safe(state: Map, deadlocks):
    deadlock_checkers = configure_deadlocks(state, deadlocks)

    if deadlock_checkers:
        for deadlock_checker in deadlock_checkers:
            if deadlock_checker(state):
                return inf
            
    boxes = [(box[0], box[1]) for box in state.positions_of_boxes.keys()]
    targets = state.targets

    total = 0
    used_targets = set()

    for box in boxes:
        if is_simple_corner_deadlock(box, state):
            return math.inf

        best_dist = float('inf')
        best_target = None
        
        for target in targets:
            if target in used_targets:
                continue
            dist = abs(box[0] - target[0]) + abs(box[1] - target[1])
            if dist < best_dist:
                best_dist = dist
                best_target = target
        if best_target is not None:
            used_targets.add(best_target)
            total += best_dist

    return total

def exact_matching_cost(map: Map, deadlocks) -> float:
    deadlock_checkers = configure_deadlocks(map, deadlocks)

    if deadlock_checkers:
        for deadlock_checker in deadlock_checkers:
            if deadlock_checker(map):
                return inf
            
    box_positions = [(b.x, b.y) for b in map.boxes.values()]
    target_positions = map.targets
    # 2) filter out already-solved boxes & targets
    boxes_to_move = [pos for pos in box_positions if pos not in target_positions]
    free_targets  = [pos for pos in target_positions if pos not in box_positions]
    # 3) exact matching cost
    total_box_dist = 0
    n = len(boxes_to_move)
    if n > 0:
        # for small n (≤ 6) brute-force the n! permutations
        best = inf
        for perm in itertools.permutations(free_targets, n):
            s = sum(abs(bx - tx) + abs(by - ty)
                    for (bx,by), (tx,ty) in zip(boxes_to_move, perm))
            if s < best:
                best = s
        total_box_dist = best

    # 4) player → nearest box
    pd = 0
    if boxes_to_move:
        px, py = map.player.x, map.player.y
        pd = min(abs(px - bx) + abs(py - by) for bx,by in boxes_to_move)

    # 5) combine
    return total_box_dist + 0.5 * pd

###################################### DEADLOCKS ######################################

def is_simple_corner_deadlock(box, state: Map) -> bool:
    x, y = box
    walls = state.obstacles
    # Dacă e prins într-un colț și nu e target
    if ((x-1, y) in walls and (x, y-1) in walls) or \
       ((x-1, y) in walls and (x, y+1) in walls) or \
       ((x+1, y) in walls and (x, y-1) in walls) or \
       ((x+1, y) in walls and (x, y+1) in walls):
        if (x, y) not in state.targets:
            return True
    return False

def is_static_deadlock(m:Map) -> bool:
  return any(pos in m.dead_squares for pos in m.positions_of_boxes)

def is_corner_deadlock(m: Map) -> bool:
    obstacles = set(m.obstacles)
    targets   = set(m.targets)
    
    for (x,y) in set(m.positions_of_boxes) - targets:
        # check each of the four corner‐orientations
        left  = ((x-1,y) in obstacles) or x-1 < 0
        right = ((x+1,y) in obstacles) or x+1 >= m.length
        up    = ((x,y-1) in obstacles) or y-1 < 0
        down  = ((x,y+1) in obstacles) or y+1 >= m.width

        # a true corner is exactly one horizontal + one vertical block
        if (left or right) and (up or down):
            # print("Corner deadlock at", (x,y))
            return True

    return False

def is_tunnel_deadlock(map: Map) -> bool:
    width, length = map.width, map.length
    obstacles: Set[Tuple[int, int]] = set(map.obstacles)
    targets: Set[Tuple[int, int]] = set(map.targets)
    boxes: Set[Tuple[int, int]] = set(map.positions_of_boxes.keys())

    for box_pos in boxes:
        x, y = box_pos
        
        # Skip if box is on a target
        if box_pos in targets:
            continue
        
        # Check for horizontal tunnel
        if (0 <= x - 1 < length and 0 <= x + 1 < length and 
            (x-1, y) in obstacles and (x+1, y) in obstacles):
            
            # Box is in horizontal tunnel, check if there's a target in this tunnel
            tunnel_has_target = False
            # Check tunnel to the left
            tx = x
            while 0 <= tx < length and (tx, y) not in obstacles:
                if (tx, y) in targets:
                    tunnel_has_target = True
                    break
                tx -= 1
            
            # Check tunnel to the right
            if not tunnel_has_target:
                tx = x
                while 0 <= tx < length and (tx, y) not in obstacles:
                    if (tx, y) in targets:
                        tunnel_has_target = True
                        break
                    tx += 1
            
            if not tunnel_has_target:
                print("Tunnel deadlock")
                return True  # Tunnel deadlock detected
            
    return False

def is_edge_deadlock(map: Map) -> bool:
    width, length = map.width, map.length
    targets: Set[Tuple[int, int]] = set(map.targets)
    boxes: Set[Tuple[int, int]] = set(map.positions_of_boxes.keys())

    for box_pos in boxes:
        x, y = box_pos
        
        # Skip if box is on a target
        if box_pos in targets:
            continue
            
        # Check if box is against an edge and not aligned with any target
        if x == 0 or x == length - 1 or y == 0 or y == width - 1:
            # Box is on an edge, check if there's any target on the same edge
            aligned_with_target = False
            
            if x == 0 or x == length - 1:
                # Box is on horizontal edge
                for tx, ty in targets:
                    if tx == x:  # Target is on the same horizontal edge
                        aligned_with_target = True
                        break
            
            if y == 0 or y == width - 1:
                # Box is on vertical edge
                for tx, ty in targets:
                    if ty == y:  # Target is on the same vertical edge
                        aligned_with_target = True
                        break
            
            if not aligned_with_target:
                print("Edge deadlock")
                return True
            
    return False

def is_2x2_deadlock(map: Map) -> bool:
    targets: Set[Tuple[int, int]] = set(map.targets)
    boxes: Set[Tuple[int, int]] = set(map.positions_of_boxes.keys())

    for box_pos in boxes:
        x, y = box_pos

        if box_pos in targets:
            continue

        square = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]

        if all(pos in boxes and not pos in targets for pos in square):
            print("Square deadlock")
            return True
        
    return False

def configure_deadlocks(map: Map, deadlocks):
    deadlock_checker = []
    for deadlock in deadlocks:
        if deadlock == 'corner':
            deadlock_checker.append(is_corner_deadlock)
        elif deadlock == 'tunnel':
            deadlock_checker.append(is_tunnel_deadlock)
        elif deadlock == 'edge':
            deadlock_checker.append(is_edge_deadlock)
        elif deadlock == '2x2':
            deadlock_checker.append(is_2x2_deadlock)

    return deadlock_checker