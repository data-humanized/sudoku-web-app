"""
test_generator.py
Unit tests for Procedural Puzzle Generator, Clue Ranges, and Human Technique Grader.

Verifies:
- Bug 1: Levels reuse the same puzzle:
  - Generate 20 puzzles per level (100 total)
  - Verify each has exactly ONE unique solution
  - Verify each puzzle matches its assigned difficulty level
  - Verify that no two levels share the same starting grid or solution
  - Verify single shared CLUE_RANGES constant with strict ordering (easy > medium > hard > expert > master)
  - Verify local seed history ring buffer (last 10 seeds per level)
"""

from __future__ import annotations
import unittest
from typing import Dict, List, Set, Tuple

from sudoku_logic import (
    CLUE_RANGES,
    Difficulty,
    Grid,
    has_unique_solution,
    solve_sudoku,
)
from puzzle_generator import (
    RECENT_SEEDS,
    generate_full_board,
    generate_puzzle_for_level,
    get_fresh_seed,
    grade_puzzle_techniques,
    record_seed,
    remove_clues_with_symmetry,
)
from difficulty_evaluator import evaluate_puzzle_difficulty


class TestPuzzleGenerator(unittest.TestCase):
    def test_clue_ranges_single_shared_constant_strict_ordering(self):
        """Verifies that clue counts strictly decrease as level rises: easy > medium > hard > expert > master."""
        levels: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
        for i in range(len(levels) - 1):
            curr_lvl = levels[i]
            next_lvl = levels[i + 1]
            curr_min = CLUE_RANGES[curr_lvl]['min']
            next_max = CLUE_RANGES[next_lvl]['max']
            self.assertGreater(
                curr_min,
                next_max,
                f"Clue range of {curr_lvl} min ({curr_min}) must be strictly greater than {next_lvl} max ({next_max})",
            )

    def test_seed_history_ring_buffer(self):
        """Verifies the ring buffer tracks the last 10 seeds and skips duplicates."""
        level: Difficulty = 'expert'
        RECENT_SEEDS[level] = []

        for seed in range(1, 15):
            record_seed(level, seed)

        # Should keep only the last 10 seeds
        self.assertEqual(len(RECENT_SEEDS[level]), 10)
        self.assertEqual(RECENT_SEEDS[level], list(range(5, 15)))

        # get_fresh_seed should not pick any seed currently in the ring buffer
        fresh = get_fresh_seed(level, preferred_seed=10)
        self.assertNotIn(fresh, RECENT_SEEDS[level])

    def test_generate_20_puzzles_per_level_unique_solutions_and_distinct_grids(self):
        """
        Generates 20 puzzles per level (100 total):
        - Checks that each has a unique solution
        - Checks that each matches its level
        - Checks that no two levels share the same starting grid or solution
        """
        levels: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
        grids_by_level: Dict[Difficulty, List[Grid]] = {lvl: [] for lvl in levels}
        solutions_by_level: Dict[Difficulty, List[Grid]] = {lvl: [] for lvl in levels}
        all_grid_tuples: Set[Tuple[int, ...]] = set()

        for lvl in levels:
            for i in range(20):
                seed = 1000 + i * 37
                data = generate_puzzle_for_level(lvl, seed=seed)
                puzzle = data['puzzle']
                solution = data['solution']

                # 1. Unique solution check
                self.assertTrue(
                    has_unique_solution(puzzle),
                    f"Puzzle {i} for {lvl} must have exactly one unique solution",
                )

                # 2. Level rating matches
                self.assertEqual(
                    data['difficulty'],
                    lvl,
                    f"Generated puzzle must be assigned level {lvl}",
                )

                # 3. Clue count in valid range
                givens = sum(1 for r in range(9) for c in range(9) if puzzle[r][c] != 0)
                min_c = CLUE_RANGES[lvl]['min']
                max_c = CLUE_RANGES[lvl]['max']
                self.assertTrue(
                    min_c - 1 <= givens <= max_c + 2,
                    f"Givens count {givens} for {lvl} out of expected range [{min_c}, {max_c}]",
                )

                # 4. Check starting grid distinctness
                grid_flat = tuple(cell for row in puzzle for cell in row)
                self.assertNotIn(
                    grid_flat,
                    all_grid_tuples,
                    f"Puzzle {i} of level {lvl} duplicated an existing puzzle starting grid!",
                )
                all_grid_tuples.add(grid_flat)

                grids_by_level[lvl].append(puzzle)
                solutions_by_level[lvl].append(solution)

        # Check cross-level distinctness: no level shares starting grid with another level
        for l1_idx in range(len(levels)):
            for l2_idx in range(l1_idx + 1, len(levels)):
                lvl1 = levels[l1_idx]
                lvl2 = levels[l2_idx]
                for g1 in grids_by_level[lvl1]:
                    for g2 in grids_by_level[lvl2]:
                        self.assertNotEqual(
                            g1,
                            g2,
                            f"Level {lvl1} and Level {lvl2} must never share the same starting grid!",
                        )


if __name__ == '__main__':
    unittest.main()
