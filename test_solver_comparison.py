"""
test_solver_comparison.py
Unit tests for solver comparison benchmarks and basic DFS.
"""

import unittest
from solver_comparison import SolverComparisonReport, solve_basic_dfs
from sudoku_logic import create_empty_grid


class TestSolverComparison(unittest.TestCase):
    def test_basic_dfs_solve(self):
        grid = create_empty_grid()
        # Seed top row partially
        grid[0][0] = 5
        grid[0][1] = 3
        steps, sol = solve_basic_dfs(grid)
        self.assertGreater(steps, 0)
        self.assertIsNotNone(sol)
        self.assertEqual(sol[0][0], 5)

    def test_comparison_report(self):
        report = SolverComparisonReport('easy')
        comp = report.compare_solvers(sample_size=1)
        self.assertIn('dlx', comp)
        self.assertIn('basic_dfs', comp)
        self.assertGreater(comp['dlx']['avg_ms'], 0)


if __name__ == '__main__':
    unittest.main()
