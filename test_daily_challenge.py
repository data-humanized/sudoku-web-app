"""
test_daily_challenge.py
Unit tests for deterministic daily challenge and trophy achievements.
"""

import unittest
from daily_challenge import get_daily_puzzle_for_date, get_monthly_completion, get_trophies_status
from sudoku_logic import has_unique_solution


class TestDailyChallenge(unittest.TestCase):
    def test_daily_puzzle_deterministic(self):
        # Same date produces identical puzzle
        p1 = get_daily_puzzle_for_date('2025-05-15')
        p2 = get_daily_puzzle_for_date('2025-05-15')
        self.assertEqual(p1['puzzle'], p2['puzzle'])
        self.assertEqual(p1['level'], p2['level'])
        self.assertTrue(has_unique_solution(p1['puzzle']))

    def test_trophy_progression(self):
        history = [
            {'id': '1', 'date': '2025-01-01', 'level': 'easy', 'score': 800, 'timeSeconds': 100, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '2', 'date': '2025-01-02', 'level': 'easy', 'score': 800, 'timeSeconds': 100, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '3', 'date': '2025-01-03', 'level': 'easy', 'score': 800, 'timeSeconds': 100, 'mistakes': 0, 'hintsUsed': 0},
        ]
        trophies = get_trophies_status(history)
        bronze = next(t for t in trophies if t['id'] == 'streak_3')
        self.assertTrue(bronze['unlocked'])

    def test_monthly_completion(self):
        history = [
            {'id': '1', 'date': '2025-01-05', 'level': 'easy', 'score': 800, 'timeSeconds': 100, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '2', 'date': '2025-01-12', 'level': 'easy', 'score': 800, 'timeSeconds': 100, 'mistakes': 0, 'hintsUsed': 0},
        ]
        res = get_monthly_completion(history, 2025, 1)
        self.assertEqual(res['completed_count'], 2)
        self.assertIn(5, res['days_completed'])
        self.assertIn(12, res['days_completed'])


if __name__ == '__main__':
    unittest.main()
