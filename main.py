from sokoban import Map
from search_methods.ida_star import IDAStarSolver
from search_methods.simulated_annealing import SimulatedAnnealingSolver
from search_methods.heuristics import (
    simulated_annealing_heuristic,
    hungarian_assignment,
    ida_star_heuristic,
    exact_matching_cost,
    is_corner_deadlock,
    is_tunnel_deadlock,
    is_edge_deadlock,
    is_2x2_deadlock,
    manhattan_greedy_safe
)
from plot_helpers import plot_states_for_map_algorithm, plot_runtime_evolution, plot_pulls_for_map_algorithm
import argparse
import os
import imageio.v2 as imageio
import shutil
import sys
import time
import json

HEURISTICS = {
    'manhattan': manhattan_greedy_safe,
    'simulated_annealing': simulated_annealing_heuristic,
    'hungarian': hungarian_assignment,
    'ida_star': ida_star_heuristic,
    'exact_matching': exact_matching_cost,
}

DEADLOCKS = {
    'corner': is_corner_deadlock,
    'tunnel': is_tunnel_deadlock,
    'edge': is_edge_deadlock,
    '2x2': is_2x2_deadlock,
}

def create_output_directories(base_dir, algorithm, test_name):
    """Create directory structure for output files"""
    # Main directories
    algorithm_dir = os.path.join(base_dir, algorithm)
    test_dir = os.path.join(algorithm_dir, test_name)
    frames_dir = os.path.join(test_dir, 'frames')
    gif_dir = os.path.join(test_dir, 'gifs')
    
    # Create directories if they don't exist
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(gif_dir, exist_ok=True)
    
    return frames_dir, gif_dir

def main():
    parser = argparse.ArgumentParser(
        description="Sokoban Solver using IDA* and Simulated Annealing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    ################################ Argument for test selection ################################
    parser.add_argument(
        'test_files',
        nargs='+',
        help='Path to the test file(s) containing the map(s) to solve'
    )

    ############################# Argument for algorithm selection ##############################
    parser.add_argument(
        '-a', '--algorithm',
        choices=['ida_star', 'simulated_annealing'],
        default='ida_star',
        help='Algorithm to use for solving the Sokoban puzzle'
    )

    ############################# Argument for heuristic selection ##############################
    parser.add_argument(
        '-H', '--heuristic',
        choices=list(HEURISTICS.keys()),
        default='exact_matching',
        help='Heuristic function to use for the selected algorithm'
    )

    ############################ Argument for choosing no deadlocks #############################
    parser.add_argument(
        '--no-deadlocks',
        action='store_true',
        help='Disable all deadlock detection'
    )

    ########################### Argument for choosing corner deadlock ###########################
    parser.add_argument(
        '--corner',
        action='store_true',
        help='Enable corner deadlock detection'
    )

    ########################### Argument for choosing tunnel deadlock ###########################
    parser.add_argument(
        '--tunnel',
        action='store_true',
        help='Enable tunnel deadlock detection'
    )

    ########################### Argument for choosing square deadlock ###########################
    parser.add_argument(
        '--square',
        action='store_true',
        help='Enable 2x2 square deadlock detection'
    )

    ########################### Argument for choosing edge deadlock ###########################
    parser.add_argument(
        '--edge',
        action='store_true',
        help='Enable edge deadlock detection'
    )

    ############################### Argument for GIF file saving ################################
    parser.add_argument(
        '--save-gif', 
        action='store_true', 
        help='Save the solution playback as a GIF file'
    )

    ############################### Argument for visual options #################################
    parser.add_argument(
        '--no-visual',
        action='store_true',
        help='Disable visual output during solving'
    )

    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run full batch of algorithms×heuristics and plot results'
    )

    args = parser.parse_args()

    # try:
    #     map_from_yaml = Map.from_yaml(args.test_file)
    # except Exception as e:
    #     print(f"Error loading map file: {e}")
    #     sys.exit(1)

    if args.benchmark:
        files_to_run = args.test_files
    else:
        files_to_run = [args.test_files[0]]

    active_deadlocks = []
    if not args.no_deadlocks:
        if args.corner:
            active_deadlocks.append('corner')
        if args.tunnel:
            active_deadlocks.append('tunnel')
        if args.square:
            active_deadlocks.append('2x2')
        if args.edge:
            active_deadlocks.append('edge')

    all_results = {}

    # BENCHMARK MODE
    if args.benchmark:
        for test_file in files_to_run:
            test_name = os.path.splitext(os.path.basename(test_file))[0]
            try:
                map_from_yaml = Map.from_yaml(test_file)
            except Exception as e:
                print(f"Error loading map file: {e}")
                sys.exit(1)

            all_results[test_name] = {'IDA*': {}, 'SA': {}}

            for alg_name, SolverClass in [
                ('IDA*', IDAStarSolver),
                ('SA',   SimulatedAnnealingSolver)
            ]:
                for heu_name, heu_func in HEURISTICS.items():
                    # skip incompatible combos
                    if alg_name == 'IDA*' and heu_name not in ('manhattan', 'exact_matching'):
                        continue
                    if alg_name == 'SA' and heu_name not in ('simulated_annealing', 'exact_matching'):
                        continue

                    # map_from_yaml = Map.from_yaml('./tests/easy_map1.yaml')

                    start = time.perf_counter()
                    solver = SolverClass(
                        map_from_yaml,
                        heuristic=heu_func,
                        deadlocks=active_deadlocks,
                    )
                    solution = solver.solve()
                    elapsed = time.perf_counter() - start
                    minutes, seconds = divmod(elapsed, 60)

                    final_map = map_from_yaml.copy()
                    for move in solution:
                        final_map.apply_move(move)
                    pull_moves = final_map.undo_moves

                    print(f"\nTest: {test_name}")
                    print(f"Algorithm: {alg_name.upper()}")
                    print(f"Heuristic: {heu_name}")
                    print(f"Solution found in {len(solution)} moves!")
                    print(f"States expanded: {solver.nodes_expanded}")
                    print(f"Pull moves: {pull_moves}")
                    print(f"Time elapsed: {int(minutes)}m {int(seconds)}s")

                    # replay solution to count pulls
                    final_map = map_from_yaml.copy()
                    for mv in solution or []:
                        final_map.apply_move(mv)

                    all_results[test_name][alg_name][heu_name] = {
                        'states':  solver.nodes_expanded,
                        'runtime': elapsed,
                        'pulls':   final_map.undo_moves
                    }

            continue

        # dump raw data
        serial = lambda d: {f"{k[0]}|{k[1]}":v for k,v in d.items()}
        with open('results.json','w') as f:
            json.dump(all_results, f, indent=2)

        for map_name, alg_data in all_results.items():
            for alg_name in alg_data:
                out_s = f"{map_name}_{alg_name}_states.png"
                plot_states_for_map_algorithm(all_results, map_name, alg_name, out_s)
                out_p = f"{map_name}_{alg_name}_pulls.png"
                plot_pulls_for_map_algorithm(all_results, map_name, alg_name, out_p)

        combos = {
            'IDA*': ['manhattan','exact_matching'],
            'SA':   ['simulated_annealing','exact_matching']
        }

        for alg_name, heuristics in combos.items():
            for heu_name in heuristics:
                out_r = f"{alg_name}_{heu_name}_runtime.png"
                plot_runtime_evolution(all_results, alg_name, heu_name, out_r)

        print("Benchmark complete. See results.json, states_comparison.png, runtime_comparison.png")
        return
    
    # MANUAL MODE
    base_dir = 'images'
    frames_dir, gif_dir = create_output_directories(base_dir, args.algorithm, test_name)

    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)

    heuristic_chosen = HEURISTICS[args.heuristic]

    # Run the selected algorithm
    start = time.perf_counter()
    
    if args.algorithm == 'ida_star':
        solver = IDAStarSolver(
            map_from_yaml,
            heuristic=heuristic_chosen,
            deadlocks=active_deadlocks,
            debug=not args.no_visual
        )
        solution = solver.solve()
        #
        if solution:
            final_map = map_from_yaml.copy()
            for move in solution:
                final_map.apply_move(move)
            pull_moves = final_map.undo_moves
            nodes_expanded = solver.nodes_expanded
    else:  # simulated_annealing
        solver = SimulatedAnnealingSolver(
            map_from_yaml,
            heuristic=heuristic_chosen,
            deadlocks=active_deadlocks,
        )
        solution = solver.solve()
        nodes_expanded = solver.nodes_expanded
        pull_moves = solver.pull_moves

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(elapsed, 60)

    if not args.no_visual:
        print(f"\nAlgorithm: {args.algorithm.upper()}")
        print(f"Heuristic: {args.heuristic}")
        print(f"Solution found in {len(solution)} moves!")
        print(f"States expanded: {nodes_expanded}")
        print(f"Pull moves: {pull_moves}")
        print(f"Time elapsed: {int(minutes)}m {int(seconds)}s")

    # When saving frames and GIFs:
    if solution:
        if not args.no_visual:
            print(f"\nSolution found in {len(solution)} moves!")

        if args.save_gif:
            # Save frames
            test_map = map_from_yaml.copy()
            for i, move in enumerate(solution):
                test_map.apply_move(move)
                frame_file = os.path.join(frames_dir, f"frame_{i:04d}.png")
                test_map.save_map(save_path=frames_dir, save_name=f"frame_{i:04d}.png")
            
            # Create GIF
            png_files = sorted(
                [os.path.join(frames_dir, f) for f in os.listdir(frames_dir) 
                if f.endswith('.png')]
            )
            gif_path = os.path.join(gif_dir, f"{test_name}.gif")
            images = [imageio.imread(p) for p in png_files]
            imageio.mimsave(gif_path, images, duration=500)
            
            if not args.no_visual:
                print(f"GIF saved to {gif_path}")
    else:
        if not args.no_visual:
            print("\nNo solution found")
            print(f"Final map state:")
            print(map_from_yaml)
        sys.exit(1)

if __name__ == '__main__':
    main()