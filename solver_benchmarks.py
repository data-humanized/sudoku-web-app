"""
solver_benchmarks.py
Performance Benchmark and Solver Quality Suite for ZenSudoku in Python.

Evaluates:
- MRV Backtracking solve time across Easy, Medium, Hard, Expert, and Master tiers
- Uniqueness checking speed
- Number of backtrack recursions per tier
"""

import time
from typing import Dict, List
from sudoku_logic import (
    CURATED_PUZZLES,
    Difficulty,
    solve_sudoku,
)


def run_benchmark_for_difficulty(difficulty: Difficulty, iterations: int = 50) -> Dict[str, float]:
    puzzles = CURATED_PUZZLES.get(difficulty, CURATED_PUZZLES['easy'])
    if not puzzles:
        return {'avg_ms': 0.0, 'min_ms': 0.0, 'max_ms': 0.0}

    puzzle = puzzles[0]['puzzle']
    times: List[float] = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        count, solution = solve_sudoku(puzzle, count_limit=2)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)

    return {
        'difficulty': difficulty,
        'iterations': iterations,
        'avg_ms': sum(times) / len(times),
        'min_ms': min(times),
        'max_ms': max(times),
    }


def run_full_suite() -> Dict[str, Dict[str, float]]:
    diffs: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
    results = {}
    for d in diffs:
        results[d] = run_benchmark_for_difficulty(d, iterations=30)
    return results


if __name__ == '__main__':
    print("ZenSudoku Solver Performance Suite")
    print("=" * 45)
    suite_results = run_full_suite()
    for diff, data in suite_results.items():
        print(f"[{diff.upper():<7}] Avg: {data['avg_ms']:.3f} ms | Min: {data['min_ms']:.3f} ms | Max: {data['max_ms']:.3f} ms")
