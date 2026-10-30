"""
test_api.py
Direct functional unit tests for api_server endpoints without requiring external network ports.
"""

import unittest
from api_server import (
    BackupCreateRequest,
    BackupVerifyRequest,
    PuzzleRequest,
    ScoreRequest,
    SolveRequest,
    api_calculate_score,
    api_create_backup,
    api_new_puzzle,
    api_solve_puzzle,
    api_verify_backup,
    health_check,
)
from sudoku_logic import SCORE_RANGES


class TestApiServer(unittest.TestCase):
    def test_health_check(self):
        res = health_check()
        self.assertEqual(res['status'], 'healthy')

    def test_new_puzzle_and_solve(self):
        # 1. Request master puzzle
        req = PuzzleRequest(level='master')
        p_res = api_new_puzzle(req)
        self.assertEqual(p_res['level'], 'master')
        self.assertEqual(p_res['score_range']['max'], 16000)

        # 2. Solve the puzzle
        s_req = SolveRequest(grid=p_res['puzzle'])
        s_res = api_solve_puzzle(s_req)
        self.assertTrue(s_res['is_unique'])
        self.assertIsNotNone(s_res['solution'])

    def test_score_calculation(self):
        req = ScoreRequest(level='master', elapsed_seconds=300, mistakes=0, hints_used=0)
        res = api_calculate_score(req)
        self.assertEqual(res['score'], 16000)
        self.assertTrue(res['is_valid_range'])

    def test_backup_create_and_verify(self):
        records = [
            {'id': 'api-1', 'date': '2025-01-01', 'level': 'easy', 'score': 800, 'timeSeconds': 120, 'mistakes': 0, 'hintsUsed': 0},
            {'id': 'api-2', 'date': '2025-01-02', 'level': 'master', 'score': 15000, 'timeSeconds': 700, 'mistakes': 0, 'hintsUsed': 0},
        ]
        create_req = BackupCreateRequest(records=records)
        c_res = api_create_backup(create_req)
        self.assertTrue(c_res['success'])
        self.assertIn('base64', c_res)

        verify_req = BackupVerifyRequest(base64_data=c_res['base64'])
        v_res = api_verify_backup(verify_req)
        self.assertTrue(v_res['valid'])
        self.assertEqual(v_res['records_count'], 2)
        self.assertGreaterEqual(v_res['streaks']['best_streak'], 2)


if __name__ == '__main__':
    unittest.main()
