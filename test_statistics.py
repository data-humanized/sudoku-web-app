"""
test_statistics.py
Unit tests for statistics and player skill rating service.
"""

import unittest
from statistics_service import calculate_percentile, calculate_skill_rating, get_mastery_report


class TestStatisticsService(unittest.TestCase):
    def test_percentile_calculation(self):
        # Median time is 50th percentile
        p_med = calculate_percentile('easy', 240)
        self.assertAlmostEqual(p_med, 50.0, delta=1.0)

        # Fast time is > 80th percentile
        p_fast = calculate_percentile('easy', 120)
        self.assertGreater(p_fast, 80.0)

        # Slow time is < 20th percentile
        p_slow = calculate_percentile('easy', 400)
        self.assertLess(p_slow, 20.0)

    def test_skill_rating_and_mastery(self):
        history = [
            {'id': '1', 'date': '2025-01-01', 'level': 'master', 'score': 16000, 'timeSeconds': 900, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '2', 'date': '2025-01-02', 'level': 'master', 'score': 15500, 'timeSeconds': 1000, 'mistakes': 0, 'hintsUsed': 0},
        ]
        rating = calculate_skill_rating(history)
        self.assertGreater(rating, 2000)

        report = get_mastery_report(history)
        self.assertEqual(report['rank_title'], 'Grandmaster')
        self.assertEqual(report['total_completed'], 2)


if __name__ == '__main__':
    unittest.main()
