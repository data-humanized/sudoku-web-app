"""
test_solver.py
Unit tests for Dancing Links (DLX) Sudoku solver.
"""

import unittest
from solver import solve_with_dlx
from sudoku_logic import CURATED_PUZZLES


class TestDLXSolver(unittest.TestCase):
    def test_dlx_solves_easy(self):
        puzzle = CURATED_PUZZLES['easy'][0]['puzzle']
        count, sol = solve_with_dlx(puzzle)
        self.assertEqual(count, 1)
        self.assertIsNotNone(sol)
        self.assertEqual(sol[0][0], 5)

    def test_dlx_solves_master(self):
        puzzle = CURATED_PUZZLES['master'][0]['puzzle']
        count, sol = solve_with_dlx(puzzle)
        self.assertEqual(count, 1)
        self.assertIsNotNone(sol)


if __name__ == '__main__':
    unittest.main()
