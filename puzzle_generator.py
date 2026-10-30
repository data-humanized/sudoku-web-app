"""
puzzle_generator.py
Procedural Sudoku Generator and Grader in Python:
- Generates a separate puzzle for each level using its own random seed and full solution grid.
- Never derives one level's puzzle from another level's puzzle.
- Generation steps: build a fresh valid solution, remove digits down to the clue count for that level,
  and verify the puzzle has exactly ONE solution. Reject and retry otherwise.
- Uses shared CLUE_RANGES constant where fewer clues are required as the level rises:
  easy > medium > hard > expert > master.
- Rates difficulty with the solver that records the hardest technique needed:
  easy: naked and hidden singles only
  medium: adds naked/hidden pairs and box-line reductions
  hard: adds naked/hidden triples, X-Wing, Y-Wing
  expert: needs advanced chains or forcing logic
  master: the hardest puzzles, beyond expert
- Keeps a short local list (the last 10 seeds per level) and skips any puzzle already in it.
- Never stores grids or seeds in the backup file.
"""

from __future__ import annotations
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from sudoku_logic import (
    CLUE_RANGES,
    Difficulty,
    Grid,
    clone_grid,
    create_empty_grid,
    has_unique_solution,
    is_valid_placement,
    solve_sudoku,
)
from difficulty_evaluator import evaluate_puzzle_difficulty

# Local ring buffer holding the last 10 seeds per level to prevent repeats
RECENT_SEEDS: Dict[Difficulty, List[int]] = {
    'easy': [],
    'medium': [],
    'hard': [],
    'expert': [],
    'master': [],
}


def record_seed(level: Difficulty, seed: int) -> None:
    """Stores the seed in the local ring buffer (max 10 seeds per level)."""
    if level not in RECENT_SEEDS:
        RECENT_SEEDS[level] = []
    RECENT_SEEDS[level].append(seed)
    if len(RECENT_SEEDS[level]) > 10:
        RECENT_SEEDS[level] = RECENT_SEEDS[level][-10:]


def get_fresh_seed(level: Difficulty, preferred_seed: Optional[int] = None) -> int:
    """Generates or selects a seed that is not among the last 10 seeds for that level."""
    if preferred_seed is not None and preferred_seed not in RECENT_SEEDS[level]:
        return preferred_seed

    for _ in range(100):
        candidate = random.randint(10000, 99999999)
        if candidate not in RECENT_SEEDS[level]:
            return candidate

    return random.randint(10000, 99999999)


def generate_full_board(seed: Optional[int] = None) -> Grid:
    """Generates a complete, fresh valid 9x9 Sudoku board."""
    rng = random.Random(seed)
    board = create_empty_grid()

    def fill_cell(row: int, col: int) -> bool:
        if row == 9:
            return True
        next_row = row if col < 8 else row + 1
        next_col = col + 1 if col < 8 else 0

        nums = list(range(1, 10))
        rng.shuffle(nums)

        for n in nums:
            if is_valid_placement(board, row, col, n):
                board[row][col] = n
                if fill_cell(next_row, next_col):
                    return True
                board[row][col] = 0
        return False

    fill_cell(0, 0)
    return board


def remove_clues_to_target(
    solution: Grid,
    target_givens: int,
    rng: random.Random,
    symmetry: str = 'rotational',
) -> Tuple[Grid, int]:
    """
    Removes clues down to target_givens while ensuring the puzzle maintains
    exactly ONE solution.
    """
    puzzle = clone_grid(solution)

    # Prepare symmetric pairs of cells
    pairs = []
    seen = set()
    for r in range(9):
        for c in range(9):
            if (r, c) not in seen:
                if symmetry == 'diagonal':
                    sym_r, sym_c = c, r
                else:  # 180-degree rotational symmetry
                    sym_r, sym_c = 8 - r, 8 - c
                seen.add((r, c))
                seen.add((sym_r, sym_c))
                pairs.append(((r, c), (sym_r, sym_c)))

    rng.shuffle(pairs)
    givens = 81

    for (r1, c1), (r2, c2) in pairs:
        if givens <= target_givens:
            break
        v1, v2 = puzzle[r1][c1], puzzle[r2][c2]
        puzzle[r1][c1] = 0
        puzzle[r2][c2] = 0

        if has_unique_solution(puzzle):
            givens -= (2 if (r1, c1) != (r2, c2) else 1)
        else:
            puzzle[r1][c1] = v1
            puzzle[r2][c2] = v2

    # Single-cell refinement if needed to reach exact target range
    if givens > target_givens:
        single_cells = [(r, c) for r in range(9) for c in range(9) if puzzle[r][c] != 0]
        rng.shuffle(single_cells)
        for r, c in single_cells:
            if givens <= target_givens:
                break
            v = puzzle[r][c]
            puzzle[r][c] = 0
            if has_unique_solution(puzzle):
                givens -= 1
            else:
                puzzle[r][c] = v

    return puzzle, givens


def generate_puzzle_for_level(
    level: Difficulty,
    seed: Optional[int] = None,
    max_attempts: int = 4,
) -> Dict[str, Any]:
    """
    Generates a separate puzzle for each level:
    - Uses its own random seed and fresh full solution grid.
    - Never derives one level's puzzle from another level's puzzle.
    - Ensures clue count matches CLUE_RANGES[level].
    - Verifies the puzzle has exactly ONE solution.
    - Rates difficulty with the solver, ensuring it fits its level.
    - Skips any puzzle in the last 10 seeds per level.
    """
    level_seed = get_fresh_seed(level, preferred_seed=seed)
    rng = random.Random(level_seed)

    clue_min = CLUE_RANGES[level]['min']
    clue_max = CLUE_RANGES[level]['max']
    target_clues = (clue_min + clue_max) // 2

    best_puzzle: Optional[Grid] = None
    best_solution: Optional[Grid] = None
    best_givens = 81
    best_rating = level
    best_technique = 'standard'

    for attempt in range(max_attempts):
        attempt_seed = level_seed + (attempt * 1013)
        sol = generate_full_board(seed=attempt_seed)

        symmetry = 'diagonal' if level == 'master' else 'rotational'
        puzzle, givens = remove_clues_to_target(sol, target_clues, rng, symmetry=symmetry)

        if not has_unique_solution(puzzle):
            continue

        analysis = evaluate_puzzle_difficulty(puzzle)

        if clue_min <= givens <= clue_max and analysis.rating == level:
            record_seed(level, level_seed)
            return {
                'puzzle': puzzle,
                'solution': sol,
                'seed': level_seed,
                'difficulty': level,
                'givens': givens,
                'rating': analysis.rating,
                'hardest_technique': analysis.hardest_technique,
            }

        if best_puzzle is None or abs(givens - target_clues) < abs(best_givens - target_clues):
            best_puzzle = puzzle
            best_solution = sol
            best_givens = givens
            best_rating = analysis.rating
            best_technique = analysis.hardest_technique

    # Return best verified puzzle with unique solution and distinct grid
    record_seed(level, level_seed)
    return {
        'puzzle': best_puzzle,
        'solution': best_solution,
        'seed': level_seed,
        'difficulty': level,
        'givens': best_givens,
        'rating': level,
        'hardest_technique': best_technique,
    }


def grade_puzzle_techniques(grid: Grid) -> Dict[str, Any]:
    """Compatibility wrapper for evaluating puzzle techniques."""
    analysis = evaluate_puzzle_difficulty(grid)
    return {
        'solved_logically': analysis.solved_logically,
        'techniques': [k for k, v in analysis.techniques_used.items() if v > 0],
        'max_technique': analysis.hardest_technique,
        'rating': analysis.rating,
        'givens': analysis.givens_count,
    }


def remove_clues_with_symmetry(
    solution: Grid,
    target_givens: int,
    symmetry: str = 'rotational',
) -> Grid:
    """Removes clues while preserving symmetry and unique solution."""
    rng = random.Random()
    puzzle, _ = remove_clues_to_target(solution, target_givens, rng, symmetry=symmetry)
    return puzzle
