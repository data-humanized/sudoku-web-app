"""
test_sudoku_logic.py
Unit tests verifying sudoku_logic.py data models, backtracking solver,
uniqueness, recalibrated grading & generator, scoring formula, progression unlocks, and streak engine.
"""

import unittest
import sudoku_logic
from sudoku_logic import (
    solve_sudoku,
    count_solutions,
    has_unique_solution,
    grade_puzzle_difficulty,
    calculate_score,
    calculate_daily_score,
    get_level_unlock_status,
    calculate_streak,
    HistoryRecord,
    CURATED_PUZZLES,
    generate_puzzle,
)

class TestSudokuLogic(unittest.TestCase):
    def test_backtracking_solver_and_uniqueness(self):
        sample = CURATED_PUZZLES["easy"][0]
        puzzle = sample["puzzle"]
        expected_solution = sample["solution"]

        # Solve
        sol = solve_sudoku(puzzle)
        self.assertIsNotNone(sol)
        self.assertEqual(sol, expected_solution)

        # Count solutions
        self.assertEqual(count_solutions(puzzle), 1)
        self.assertTrue(has_unique_solution(puzzle))

    def test_recalibrated_curated_puzzle_targets(self):
        # Easy: 42-46 givens, technique is 'easy'
        for entry in CURATED_PUZZLES["easy"]:
            puz = entry["puzzle"]
            givens = sum(1 for r in range(9) for c in range(9) if puz[r][c] != 0)
            self.assertTrue(42 <= givens <= 46, f"Easy givens was {givens}")
            self.assertEqual(grade_puzzle_difficulty(puz), "easy")
            # Verify no row, col or box has fewer than 2 givens
            for r in range(9):
                self.assertGreaterEqual(sum(1 for c in range(9) if puz[r][c] != 0), 2)
            for c in range(9):
                self.assertGreaterEqual(sum(1 for r in range(9) if puz[r][c] != 0), 2)
            for br in range(3):
                for bc in range(3):
                    box_cnt = sum(1 for dr in range(3) for dc in range(3) if puz[br * 3 + dr][bc * 3 + dc] != 0)
                    self.assertGreaterEqual(box_cnt, 2)

        # Medium: 36-40 givens
        for entry in CURATED_PUZZLES["medium"]:
            givens = sum(1 for r in range(9) for c in range(9) if entry["puzzle"][r][c] != 0)
            self.assertTrue(36 <= givens <= 40, f"Medium givens was {givens}")

        # Hard: 30-34 givens
        for entry in CURATED_PUZZLES["hard"]:
            givens = sum(1 for r in range(9) for c in range(9) if entry["puzzle"][r][c] != 0)
            self.assertTrue(30 <= givens <= 34, f"Hard givens was {givens}")

        # Expert: 25-29 givens
        for entry in CURATED_PUZZLES["expert"]:
            givens = sum(1 for r in range(9) for c in range(9) if entry["puzzle"][r][c] != 0)
            self.assertTrue(25 <= givens <= 29, f"Expert givens was {givens}")

    def test_dynamic_generation_recalibrated(self):
        # Test dynamic generator for Easy
        puz, sol = generate_puzzle("easy", seed=123)
        givens = sum(1 for r in range(9) for c in range(9) if puz[r][c] != 0)
        self.assertTrue(42 <= givens <= 46)
        self.assertEqual(grade_puzzle_difficulty(puz), "easy")
        self.assertTrue(has_unique_solution(puz))

    def test_scoring_formula(self):
        score = calculate_score("easy", seconds=100, hints_used=1, mistakes=2)
        self.assertEqual(score, 935)

        floor_score = calculate_score("easy", seconds=10000, hints_used=20, mistakes=5)
        self.assertEqual(floor_score, 200)

        score_med = calculate_score("medium", seconds=50, hints_used=0, mistakes=0)
        self.assertEqual(score_med, 1990)

        score_exp_floor = calculate_score("expert", seconds=50000, hints_used=10, mistakes=3)
        self.assertEqual(score_exp_floor, 1600)

    def test_level_unlock_setting_and_progression(self):
        history = []
        # When LEVELS_LOCKED is False (default web release): all levels are unlocked
        sudoku_logic.LEVELS_LOCKED = False
        status_unlocked = get_level_unlock_status(history)
        self.assertTrue(status_unlocked["easy"]["unlocked"])
        self.assertTrue(status_unlocked["medium"]["unlocked"])
        self.assertTrue(status_unlocked["hard"]["unlocked"])
        self.assertTrue(status_unlocked["expert"]["unlocked"])
        self.assertEqual(status_unlocked["medium"]["progress_label"], "Unlocked")

        # When LEVELS_LOCKED is True (Android release): unlock progression is enforced
        try:
            sudoku_logic.LEVELS_LOCKED = True
            status_locked = get_level_unlock_status(history)
            self.assertTrue(status_locked["easy"]["unlocked"])
            self.assertFalse(status_locked["medium"]["unlocked"])
            self.assertEqual(status_locked["medium"]["progress_label"], "0 / 2 Easy games")

            history.append(HistoryRecord("1", "2026-10-25", 1.0, "easy", 120, 900, 0, 0))
            history.append(HistoryRecord("2", "2026-10-25", 2.0, "easy", 130, 900, 0, 0))
            status_prog = get_level_unlock_status(history)
            self.assertTrue(status_prog["medium"]["unlocked"])
            self.assertFalse(status_prog["hard"]["unlocked"])
            self.assertEqual(status_prog["hard"]["progress_label"], "0 / 4 Medium games")
        finally:
            sudoku_logic.LEVELS_LOCKED = False

    def test_daily_streak_engine(self):
        history = [
            HistoryRecord("1", "2026-10-24", 1.0, "easy", 100, 900, 0, 0),
            HistoryRecord("2", "2026-10-25", 2.0, "easy", 100, 900, 0, 0),
        ]
        active, best = calculate_streak(history, "2026-10-26")
        self.assertEqual(active, 2)
        self.assertEqual(best, 2)

        history.append(HistoryRecord("3", "2026-10-26", 3.0, "easy", 100, 900, 0, 0))
        active2, best2 = calculate_streak(history, "2026-10-26")
        self.assertEqual(active2, 3)
        self.assertEqual(best2, 3)

        active_gap, best_gap = calculate_streak(history, "2026-10-29")
        self.assertEqual(active_gap, 0)
        self.assertEqual(best_gap, 3)

    def test_daily_score_sum(self):
        records = [
            HistoryRecord("1", "2026-10-26", 1.0, "easy", 100, 950, 0, 0),
            HistoryRecord("2", "2026-10-26", 2.0, "medium", 200, 1920, 0, 0),
            HistoryRecord("3", "2026-10-25", 3.0, "easy", 120, 900, 0, 0),
        ]
        daily_score = calculate_daily_score(records, "2026-10-26")
        self.assertEqual(daily_score, 950 + 1920)

if __name__ == "__main__":
    unittest.main()
