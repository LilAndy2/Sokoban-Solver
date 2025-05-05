# plot_helpers.py
import matplotlib.pyplot as plt

def plot_states_for_map_algorithm(data: dict, map_name: str, algorithm: str, output_path: str):
    """
    Bar‐plot of explored states for each heuristic on one map+algorithm.
    """
    heuristics = list(data[map_name][algorithm].keys())
    states     = [data[map_name][algorithm][h]['states'] for h in heuristics]

    plt.figure(figsize=(5,3))
    plt.bar(heuristics, states)
    plt.ylabel("Explored States")
    plt.title(f"{map_name} – {algorithm} states")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_runtime_evolution(data: dict, algorithm: str, heuristic: str, output_path: str):
    """
    Line‐plot of runtime across all maps for one algorithm+heuristic.
    """
    maps     = list(data.keys())
    runtimes = [data[m][algorithm][heuristic]['runtime'] for m in maps]

    plt.figure(figsize=(6,3))
    plt.plot(maps, runtimes, marker='o')
    plt.xlabel("Map")
    plt.ylabel("Runtime (s)")
    plt.title(f"{algorithm} – {heuristic} runtime")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_pulls_for_map_algorithm(data: dict, map_name: str, algorithm: str, output_path: str):
    """
    Bar‐plot of pull‐moves for each heuristic on one map+algorithm.
    """
    heuristics = list(data[map_name][algorithm].keys())
    pulls      = [data[map_name][algorithm][h]['pulls'] for h in heuristics]

    plt.figure(figsize=(5,3))
    plt.bar(heuristics, pulls)
    plt.ylabel("Pull Moves")
    plt.title(f"{map_name} – {algorithm} pulls")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
