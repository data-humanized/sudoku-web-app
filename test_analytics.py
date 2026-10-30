"""
test_analytics.py
Unit tests for analytics and state machine modules.
"""

import unittest
from analytics import AnalyticsReport
from state_machine import GameStateMachine
from sudoku_logic import GameState, clone_grid, create_empty_bool_grid, create_empty_notes


class TestAnalytics(unittest.TestCase):
    def test_analytics_summary_empty(self):
        report = AnalyticsReport([])
        summary = report.get_summary()
        self.assertEqual(summary['total_games'], 0)
        self.assertEqual(summary['total_score'], 0)

    def test_analytics_summary_with_records(self):
        records = [
            {'id': '1', 'date': '2025-01-01', 'level': 'easy', 'score': 800, 'timeSeconds': 150, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '2', 'date': '2025-01-02', 'level': 'master', 'score': 15000, 'timeSeconds': 900, 'mistakes': 1, 'hintsUsed': 0},
        ]
        report = AnalyticsReport(records)
        summary = report.get_summary()
        self.assertEqual(summary['total_games'], 2)
        self.assertEqual(summary['total_score'], 15800)
        self.assertEqual(summary['level_breakdown']['master']['count'], 1)
        self.assertEqual(summary['level_breakdown']['easy']['count'], 1)


class TestStateMachine(unittest.TestCase):
    def test_state_machine_moves(self):
        initial = [[0]*9 for _ in range(9)]
        initial[0][0] = 5
        solution = [[1]*9 for _ in range(9)]
        solution[0][0] = 5
        solution[0][1] = 3

        game: GameState = {
            'id': 'test-1',
            'level': 'easy',
            'initial_grid': initial,
            'solution_grid': solution,
            'current_grid': clone_grid(initial),
            'notes': create_empty_notes(),
            'hinted_cells': create_empty_bool_grid(),
            'mistakes': 0,
            'hints_used': 0,
            'elapsed_seconds': 0,
            'is_paused': False,
            'is_completed': False,
            'undo_stack': [],
            'redo_stack': [],
            'start_time': 0,
        }

        sm = GameStateMachine(game)
        # 1. Note toggle
        res = sm.toggle_note(0, 1, 3)
        self.assertTrue(res['success'])
        self.assertIn(3, game['notes'][0][1])

        # 2. Undo note
        sm.undo()
        self.assertNotIn(3, game['notes'][0][1])

        # 3. Mistake placement
        res_err = sm.apply_digit(0, 1, 9)  # 9 is wrong, 3 is correct
        self.assertTrue(res_err['is_mistake'])
        self.assertEqual(game['mistakes'], 1)

        # 4. Correct placement
        res_ok = sm.apply_digit(0, 1, 3)
        self.assertTrue(res_ok['success'])
        self.assertEqual(game['current_grid'][0][1], 3)


if __name__ == '__main__':
    unittest.main()
