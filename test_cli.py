"""
test_cli.py
Unit tests for CLI utility formatting and backup commands.
"""

import os
import unittest
from cli import format_board
from storage import ZenSudokuStorage, save_zen_data
from sudoku_logic import create_empty_grid


class TestCli(unittest.TestCase):
    def test_format_board(self):
        grid = create_empty_grid()
        grid[0][0] = 5
        grid[8][8] = 9
        formatted = format_board(grid)
        self.assertIn("5", formatted)
        self.assertIn("9", formatted)
        self.assertIn("┌───────┬───────┬───────┐", formatted)


if __name__ == '__main__':
    unittest.main()
