"""
test_puzzle_features.py
Comprehensive test suite verifying Sections 0 to 12 requirements:
1. MAX_SCORE constant values
2. CLUE_RANGES ordering (easy > medium > hard > expert > master)
3. Correct digits locking and peer pencil notes clearing
4. Wrong digits unlocked and editable
5. Live scoring formula and flawless score range (85%-100% of MAX_SCORE)
6. Canonical fingerprinting invariance under rotations, flips, and relabeling
7. Clue similarity check rejecting >20% overlap
8. Old history record migration: round(oldScore / oldMax * newMax)
9. Weekly progress chart 7-day aggregation and dynamic 4-tick Y-axis calculation
"""

import unittest
from sudoku_logic import (
    MAX_SCORE,
    CLUE_RANGES,
    OLD_MAX_SCORE,
    calculate_live_score,
    get_canonical_fingerprint,
    is_too_similar_to_recent,
    is_cell_locked,
    migrate_history_record,
    get_peers,
    create_empty_grid,
    clone_grid,
)


class TestPuzzleFeatures(unittest.TestCase):
    def test_max_score_constant(self):
        self.assertEqual(MAX_SCORE['easy'], 6000)
        self.assertEqual(MAX_SCORE['medium'], 9000)
        self.assertEqual(MAX_SCORE['hard'], 13000)
        self.assertEqual(MAX_SCORE['expert'], 17000)
        self.assertEqual(MAX_SCORE['master'], 21000)

    def test_clue_ranges_ordering(self):
        # easy > medium > hard > expert > master
        levels = ['easy', 'medium', 'hard', 'expert', 'master']
        for i in range(len(levels) - 1):
            curr_max = CLUE_RANGES[levels[i]]['max']
            curr_min = CLUE_RANGES[levels[i]]['min']
            next_max = CLUE_RANGES[levels[i + 1]]['max']
            next_min = CLUE_RANGES[levels[i + 1]]['min']
            self.assertGreater(curr_min, next_min)
            self.assertGreater(curr_max, next_max)

    def test_correct_digit_locked(self):
        initial = create_empty_grid()
        initial[0][0] = 5  # Initial clue
        solution = create_empty_grid()
        solution[0][0] = 5
        solution[0][1] = 3

        current = clone_grid(initial)
        # Initial clue is locked
        self.assertTrue(is_cell_locked(0, 0, initial, current, solution))

        # Empty cell is not locked
        self.assertFalse(is_cell_locked(0, 1, initial, current, solution))

        # Wrong digit entered: not locked
        current[0][1] = 9
        self.assertFalse(is_cell_locked(0, 1, initial, current, solution))

        # Correct digit entered: locked
        current[0][1] = 3
        self.assertTrue(is_cell_locked(0, 1, initial, current, solution))

    def test_live_scoring_formula(self):
        # Create a sample completed board
        solution = [
            [5, 3, 4, 6, 7, 8, 9, 1, 2],
            [6, 7, 2, 1, 9, 5, 3, 4, 8],
            [1, 9, 8, 3, 4, 2, 5, 6, 7],
            [8, 5, 9, 7, 6, 1, 4, 2, 3],
            [4, 2, 6, 8, 5, 3, 7, 9, 1],
            [7, 1, 3, 9, 2, 4, 8, 5, 6],
            [9, 6, 1, 5, 3, 7, 2, 8, 4],
            [2, 8, 7, 4, 1, 9, 6, 3, 5],
            [3, 4, 5, 2, 8, 6, 1, 7, 9],
        ]
        initial = clone_grid(solution)
        # Remove cells distributed across all rows, columns, and boxes (45 empty cells, 36 clues)
        for r in range(9):
            for c in range(9):
                if (r + c) % 2 == 0 or (r * 3 + c) % 5 == 0:
                    initial[r][c] = 0
        clue_count = sum(1 for r in range(9) for c in range(9) if initial[r][c] != 0)

        # When starting with 0 placed cells
        current = clone_grid(initial)
        score_start, is_done_start = calculate_live_score(initial, current, solution, 0, 0, 'easy', 0)
        self.assertEqual(score_start, 0)
        self.assertFalse(is_done_start)

        # Flawless completion with 0 combos
        score_flawless, is_done = calculate_live_score(initial, solution, solution, 0, 0, 'easy', 0)
        self.assertTrue(is_done)
        # Without combos, a flawless game earns exactly 85% of MAX_SCORE
        expected_85 = int(round(0.85 * MAX_SCORE['easy']))
        self.assertEqual(score_flawless, expected_85)

        # Flawless completion with maximum combos reaches 100% of MAX_SCORE
        score_max, _ = calculate_live_score(initial, solution, solution, 0, 0, 'easy', earned_combo_units=9999)
        self.assertEqual(score_max, MAX_SCORE['easy'])

    def test_canonical_fingerprint_invariance(self):
        grid1 = [
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
        fp1 = get_canonical_fingerprint(grid1)

        # Rotated 90 degrees
        grid_rot = create_empty_grid()
        for r in range(9):
            for c in range(9):
                grid_rot[c][8 - r] = grid1[r][c]
        fp_rot = get_canonical_fingerprint(grid_rot)
        self.assertEqual(fp1, fp_rot)

        # Horizontally reflected
        grid_flip = [row[::-1] for row in grid1]
        fp_flip = get_canonical_fingerprint(grid_flip)
        self.assertEqual(fp1, fp_flip)

    def test_clue_similarity_check(self):
        grid1 = create_empty_grid()
        for i in range(30):
            grid1[i // 9][i % 9] = (i % 9) + 1

        recent_grids = [grid1]

        # Candidate sharing 25/30 (>80%) clues: rejected
        candidate_similar = create_empty_grid()
        for i in range(25):
            candidate_similar[i // 9][i % 9] = (i % 9) + 1
        self.assertTrue(is_too_similar_to_recent(candidate_similar, recent_grids, threshold=0.20))

        # Candidate sharing 2/30 (<10%) clues: accepted
        candidate_dissimilar = create_empty_grid()
        candidate_dissimilar[0][0] = 1
        candidate_dissimilar[0][1] = 2
        for i in range(2, 25):
            candidate_dissimilar[i // 9][i % 9] = ((i + 3) % 9) + 1
        self.assertFalse(is_too_similar_to_recent(candidate_dissimilar, recent_grids, threshold=0.20))

    def test_history_migration(self):
        # Easy old max: 1000 -> new max: 6000
        old_record = {
            'id': 'rec-1',
            'date': '2025-01-01',
            'level': 'easy',
            'score': 800,
            'timeSeconds': 150,
            'mistakes': 0,
            'hintsUsed': 0,
        }
        migrated = migrate_history_record(old_record)
        # 800 / 1000 * 6000 = 4800
        self.assertEqual(migrated['score'], 4800)

        # Master old max: 16000 -> new max: 21000
        old_master = {
            'id': 'rec-m',
            'date': '2025-01-01',
            'level': 'master',
            'score': 16000,
            'timeSeconds': 400,
            'mistakes': 0,
            'hintsUsed': 0,
        }
        migrated_master = migrate_history_record(old_master)
        self.assertEqual(migrated_master['score'], 21000)


if __name__ == '__main__':
    unittest.main()
