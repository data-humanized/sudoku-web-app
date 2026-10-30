"""
test_trainer.py
Unit tests for Sudoku technique trainer and pattern detector.
"""

import unittest
from trainer import SudokuTrainer
from sudoku_logic import create_empty_grid


class TestTrainer(unittest.TestCase):
    def test_naked_single_detection(self):
        grid = create_empty_grid()
        # Fill row 0 except cell (0, 0) with digits 2..9
        for c in range(1, 9):
            grid[0][c] = c + 1
        trainer = SudokuTrainer(grid)
        hint = trainer.find_next_hint()
        self.assertIsNotNone(hint)
        self.assertEqual(hint.technique_name, "Naked Single")
        self.assertEqual(hint.placed_digit, (0, 0, 1))

    def test_hidden_single_detection(self):
        grid = create_empty_grid()
        # Row with hidden single setup
        for c in range(1, 9):
            grid[0][c] = c + 1
        trainer = SudokuTrainer(grid)
        hint = trainer._find_hidden_single()
        self.assertIsNotNone(hint)
        self.assertEqual(hint.placed_digit[2], 1)


if __name__ == '__main__':
    unittest.main()
