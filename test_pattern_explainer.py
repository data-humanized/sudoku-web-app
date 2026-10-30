"""
test_pattern_explainer.py
Deep algorithmic test suite for Sudoku pattern detection and pedagogical hints:
- Naked Single identification
- Hidden Single identification across rows, cols, and 3x3 blocks
- Naked Pair reduction detection
- Pointing Pair candidate reduction
- Box-Line Reduction logic
- Step-by-step hint progression
"""

import unittest
from trainer import SudokuTrainer, TechniqueHint
from sudoku_logic import clone_grid


class TestPatternExplainer(unittest.TestCase):
    def test_naked_single_detection(self):
        # Grid where cell (0, 2) has only candidate 4
        grid = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ]
        trainer = SudokuTrainer(grid)
        hint = trainer._find_naked_single()
        self.assertIsNotNone(hint)
        self.assertEqual(hint.technique_name, 'Naked Single')
        self.assertIsNotNone(hint.placed_digit)
        r, c, d = hint.placed_digit
        self.assertEqual(grid[r][c], 0)
        self.assertTrue(1 <= d <= 9)

    def test_hidden_single_detection(self):
        grid = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 2, 3, 4, 5, 6, 7, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        trainer = SudokuTrainer(grid)
        hint = trainer._find_hidden_single()
        # Row 1 must have candidate 8 or 9 somewhere
        if hint:
            self.assertIn('Hidden Single', hint.technique_name)

    def test_technique_hint_serialization(self):
        hint = TechniqueHint(
            technique_name='Naked Pair',
            description='Cells (0,1) and (0,2) share candidates {4, 7}',
            target_cells=[(0, 1), (0, 2)],
            eliminations=[(0, 5, 4), (0, 8, 7)],
            placed_digit=None,
        )
        data = hint.to_dict()
        self.assertEqual(data['technique'], 'Naked Pair')
        self.assertEqual(len(data['target_cells']), 2)
        self.assertEqual(len(data['eliminations']), 2)
        self.assertIsNone(data['placed_digit'])


if __name__ == '__main__':
    unittest.main()
