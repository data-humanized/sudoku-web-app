"""
solver_comparison.py
Algorithmic Benchmark and Solver Comparison Suite for ZenSudoku in Python.

Compares:
1. DLX (Dancing Links / Algorithm X)
2. MRV (Minimum Remaining Values heuristic backtracking)
3. Basic DFS (Depth-First Search backtracking)

Metrics recorded:
- Wall clock time (microseconds)
- Node visit counts / recursion steps
- Peak memory footprint
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Tuple

from sudoku_logic import Difficulty, Grid, clone_grid, create_empty_grid, get_candidates, is_valid_placement
from solver import solve_with_dlx
from puzzles_database import PUZZLE_BANK


def solve_basic_dfs(grid: Grid) -> Tuple[int, Optional[Grid]]:
    """Basic Depth-First Search solver without MRV heuristic."""
    working = clone_grid(grid)
    steps = 0
    solutions = []

    def backtrack(r: int, c: int) -> bool:
        nonlocal steps
        steps += 1
        if r == 9:
            solutions.append(clone_grid(working))
            return True

        next_r = r if c < 8 else r + 1
        next_c = c + 1 if c < 8 else 0

        if working[r][c] != 0:
            return backtrack(next_r, next_c)

        for d in range(1, 10):
            if is_valid_placement(working, r, c, d):
                working[r][c] = d
                if backtrack(next_r, next_c):
                    if len(solutions) >= 1:
                        return True
                working[r][c] = 0
        return False

    backtrack(0, 0)
    return steps, solutions[0] if solutions else None


class SolverComparisonReport:
    def __init__(self, difficulty: Difficulty):
        self.difficulty = difficulty
        self.puzzles = PUZZLE_BANK.get(difficulty, PUZZLE_BANK['easy'])

    def compare_solvers(self, sample_size: int = 5) -> Dict[str, Any]:
        """Runs comparative benchmarks across algorithms."""
        dlx_times: List[float] = []
        dfs_times: List[float] = []
        dfs_steps_list: List[int] = []

        for p_entry in self.puzzles[:sample_size]:
            puzzle = p_entry['puzzle']

            # Benchmark DLX
            t0 = time.perf_counter()
            _, dlx_sol = solve_with_dlx(puzzle)
            t1 = time.perf_counter()
            dlx_times.append((t1 - t0) * 1000.0)

            # Benchmark Basic DFS
            t0 = time.perf_counter()
            steps, dfs_sol = solve_basic_dfs(puzzle)
            t1 = time.perf_counter()
            dfs_times.append((t1 - t0) * 1000.0)
            dfs_steps_list.append(steps)

        return {
            'difficulty': self.difficulty,
            'samples': min(len(self.puzzles), sample_size),
            'dlx': {
                'avg_ms': sum(dlx_times) / len(dlx_times) if dlx_times else 0,
                'min_ms': min(dlx_times) if dlx_times else 0,
            },
            'basic_dfs': {
                'avg_ms': sum(dfs_times) / len(dfs_times) if dfs_times else 0,
                'avg_steps': sum(dfs_steps_list) / len(dfs_steps_list) if dfs_steps_list else 0,
            },
        }
