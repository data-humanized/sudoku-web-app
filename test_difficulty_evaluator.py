"""
test_difficulty_evaluator.py
Unit tests for difficulty evaluation and grading engine.
"""

import unittest
from difficulty_evaluator import DifficultyScore, evaluate_puzzle_difficulty
from sudoku_logic import CURATED_PUZZLES


class TestDifficultyEvaluator(unittest.TestCase):
    def test_easy_puzzle_evaluation(self):
        easy_grid = CURATED_PUZZLES['easy'][0]['puzzle']
        analysis = evaluate_puzzle_difficulty(easy_grid)
        self.assertGreaterEqual(analysis.givens_count, 28)
        self.assertIn(analysis.rating, [DifficultyScore.EASY, DifficultyScore.MEDIUM])
        self.assertGreater(analysis.logical_steps, 0)

    def test_master_puzzle_evaluation(self):
        master_grid = CURATED_PUZZLES['master'][0]['puzzle']
        analysis = evaluate_puzzle_difficulty(master_grid)
        self.assertLessEqual(analysis.givens_count, 24)
        self.assertIn(analysis.rating, [DifficultyScore.EXPERT, DifficultyScore.MASTER])

    def test_analysis_serialization(self):
        easy_grid = CURATED_PUZZLES['easy'][0]['puzzle']
        analysis = evaluate_puzzle_difficulty(easy_grid)
        data = analysis.to_dict()
        self.assertIn('givens_count', data)
        self.assertIn('rating', data)
        self.assertIn('techniques_used', data)
        self.assertIn('logical_steps', data)


if __name__ == '__main__':
    unittest.main()
