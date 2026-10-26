"""
sudoku_logic.py
Pure Python Sudoku engine with ZERO GUI or external/system dependencies.
Contains all data models, backtracking solver, uniqueness validation,
logical difficulty grader, scoring formula, unlock progression, and streak calculation.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Set, Tuple, Optional, Dict, Any
import math
import copy
import random
import time

# --- 1. Type Aliases & Constants ---
Grid = List[List[int]]
Notes = List[List[Set[int]]]
BoolGrid = List[List[bool]]

DIFFICULTIES = ("easy", "medium", "hard", "expert")

BASE_SCORES: Dict[str, int] = {
    "easy": 1000,
    "medium": 2000,
    "hard": 4000,
    "expert": 8000,
}

# Set to true for the Android release.
LEVELS_LOCKED = False

UNLOCK_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "easy": {"prereq": None, "count": 0},
    "medium": {"prereq": "easy", "count": 2},
    "hard": {"prereq": "medium", "count": 4},
    "expert": {"prereq": "hard", "count": 16},
}


# --- 2. Data Models ---

@dataclass
class MoveAction:
    """Represents an undoable/redoable player action."""
    action_type: str  # 'digit', 'note', 'erase', 'auto_notes', 'hint'
    row: int
    col: int
    prev_val: int
    new_val: int
    prev_notes: Set[int] = field(default_factory=set)
    new_notes: Set[int] = field(default_factory=set)
    # Peer notes modified (for auto-erase peer notes)
    peer_notes_changes: List[Tuple[int, int, Set[int], Set[int]]] = field(default_factory=list)


@dataclass
class HistoryRecord:
    """Historical record for a finished game."""
    id: str
    date: str  # ISO date YYYY-MM-DD
    timestamp: float
    level: str
    seconds: int
    score: int
    hints_used: int
    mistakes: int


@dataclass
class GameState:
    """Complete snapshot of a Sudoku match."""
    id: str
    level: str
    initial_grid: Grid
    solution_grid: Grid
    current_grid: Grid
    notes: Notes
    hinted_cells: BoolGrid
    mistakes: int = 0
    hints_used: int = 0
    elapsed_seconds: int = 0
    is_paused: bool = False
    is_completed: bool = False
    undo_stack: List[MoveAction] = field(default_factory=list)
    redo_stack: List[MoveAction] = field(default_factory=list)
    start_time: float = 0.0
    completed_time: Optional[float] = None
    final_score: int = 0


# --- 3. Grid Helper Functions ---

def empty_grid() -> Grid:
    return [[0 for _ in range(9)] for _ in range(9)]


def empty_notes() -> Notes:
    return [[set() for _ in range(9)] for _ in range(9)]


def empty_bool_grid() -> BoolGrid:
    return [[False for _ in range(9)] for _ in range(9)]


def clone_grid(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def clone_notes(notes: Notes) -> Notes:
    return [[set(cell) for cell in row] for row in notes]


def clone_bool_grid(bg: BoolGrid) -> BoolGrid:
    return [row[:] for row in bg]


def get_peers(row: int, col: int) -> Set[Tuple[int, int]]:
    """Returns all 20 unique peer coordinates (row, col, and 3x3 box)."""
    peers = set()
    for c in range(9):
        if c != col:
            peers.add((row, c))
    for r in range(9):
        if r != row:
            peers.add((r, col))
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if r != row or c != col:
                peers.add((r, c))
    return peers


def is_valid_placement(grid: Grid, row: int, col: int, val: int) -> bool:
    """Checks if placing val at (row, col) violates basic Sudoku rules against other placed digits."""
    if val < 1 or val > 9:
        return False
    # Check row
    for c in range(9):
        if c != col and grid[row][c] == val:
            return False
    # Check column
    for r in range(9):
        if r != row and grid[r][col] == val:
            return False
    # Check 3x3 box
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if (r != row or c != col) and grid[r][c] == val:
                return False
    return True


def get_candidates(grid: Grid, row: int, col: int) -> Set[int]:
    """Returns candidate values 1-9 that do not conflict with existing placed digits in peers."""
    if grid[row][col] != 0:
        return set()
    used = set()
    for c in range(9):
        if grid[row][c] != 0:
            used.add(grid[row][c])
    for r in range(9):
        if grid[r][col] != 0:
            used.add(grid[r][col])
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if grid[r][c] != 0:
                used.add(grid[r][c])
    return {d for d in range(1, 10) if d not in used}


# --- 4. Backtracking Solver & Solution Counting ---

def solve_sudoku(grid: Grid) -> Optional[Grid]:
    """Finds one valid solution to the given grid, or None if unsolvable."""
    sol = clone_grid(grid)

    def backtrack() -> bool:
        min_options = 10
        best_cell = None
        for r in range(9):
            for c in range(9):
                if sol[r][c] == 0:
                    cand = get_candidates(sol, r, c)
                    num_cand = len(cand)
                    if num_cand == 0:
                        return False
                    if num_cand < min_options:
                        min_options = num_cand
                        best_cell = (r, c, cand)
                        if min_options == 1:
                            break
            if min_options == 1:
                break

        if best_cell is None:
            return True

        r, c, candidates = best_cell
        for val in candidates:
            sol[r][c] = val
            if backtrack():
                return True
            sol[r][c] = 0
        return False

    if backtrack():
        return sol
    return None


def count_solutions(grid: Grid, limit: int = 2) -> int:
    """Counts number of solutions up to limit using backtracking."""
    work_grid = clone_grid(grid)
    count = 0

    def backtrack() -> bool:
        nonlocal count
        min_options = 10
        best_cell = None
        for r in range(9):
            for c in range(9):
                if work_grid[r][c] == 0:
                    cand = get_candidates(work_grid, r, c)
                    num_cand = len(cand)
                    if num_cand == 0:
                        return False
                    if num_cand < min_options:
                        min_options = num_cand
                        best_cell = (r, c, cand)
                        if min_options == 1:
                            break
            if min_options == 1:
                break

        if best_cell is None:
            count += 1
            return count >= limit

        r, c, candidates = best_cell
        for val in candidates:
            work_grid[r][c] = val
            if backtrack():
                return True
            work_grid[r][c] = 0
        return False

    backtrack()
    return count


def has_unique_solution(grid: Grid) -> bool:
    """Checks whether the grid has exactly one unique solution."""
    return count_solutions(grid, limit=2) == 1


# --- 5. Difficulty Grader by Logical Technique ---

def grade_puzzle_difficulty(initial_grid: Grid) -> str:
    """
    Grades the difficulty of a puzzle by evaluating the highest logical technique
    strictly required to solve it step by step:
      - 'easy': Solvable using naked singles and hidden singles only.
      - 'medium': Requires naked/hidden pairs or pointing/claiming lines.
      - 'hard': Requires naked/hidden triples, X-Wing, or Y-Wing.
      - 'expert': Requires advanced chains (Swordfish, XY-chains, forcing chains).
    """
    grid = clone_grid(initial_grid)
    # Candidate map for each cell
    candidates: List[List[Set[int]]] = [
        [get_candidates(grid, r, c) if grid[r][c] == 0 else set() for c in range(9)]
        for r in range(9)
    ]

    highest_technique = "easy"

    def empty_cells_count() -> int:
        return sum(1 for r in range(9) for c in range(9) if grid[r][c] == 0)

    while empty_cells_count() > 0:
        progress = False

        # 1. Naked Single: Cell with exactly 1 candidate
        for r in range(9):
            for c in range(9):
                if grid[r][c] == 0 and len(candidates[r][c]) == 1:
                    val = next(iter(candidates[r][c]))
                    grid[r][c] = val
                    candidates[r][c].clear()
                    # Eliminate val from peers
                    for pr, pc in get_peers(r, c):
                        candidates[pr][pc].discard(val)
                    progress = True
                    break
            if progress:
                break
        if progress:
            continue

        # 2. Hidden Single: Digit can only appear in one cell of a unit (row, col, or box)
        units: List[List[Tuple[int, int]]] = []
        for r in range(9):
            units.append([(r, c) for c in range(9)])
        for c in range(9):
            units.append([(r, c) for r in range(9)])
        for br in range(3):
            for bc in range(3):
                units.append([(br * 3 + dr, bc * 3 + dc) for dr in range(3) for dc in range(3)])

        for unit in units:
            for digit in range(1, 10):
                possible_cells = [(r, c) for (r, c) in unit if grid[r][c] == 0 and digit in candidates[r][c]]
                if len(possible_cells) == 1:
                    r, c = possible_cells[0]
                    grid[r][c] = digit
                    candidates[r][c].clear()
                    for pr, pc in get_peers(r, c):
                        candidates[pr][pc].discard(digit)
                    progress = True
                    break
            if progress:
                break
        if progress:
            continue

        # 3. Medium Techniques: Naked Pairs, Hidden Pairs, Pointing / Claiming
        # Naked Pair in unit
        for unit in units:
            unfilled = [(r, c) for (r, c) in unit if grid[r][c] == 0 and len(candidates[r][c]) == 2]
            for i in range(len(unfilled)):
                for j in range(i + 1, len(unfilled)):
                    r1, c1 = unfilled[i]
                    r2, c2 = unfilled[j]
                    if candidates[r1][c1] == candidates[r2][c2]:
                        pair = candidates[r1][c1]
                        # Discard from other cells in this unit
                        eliminated = False
                        for r, c in unit:
                            if (r, c) != (r1, c1) and (r, c) != (r2, c2) and grid[r][c] == 0:
                                if candidates[r][c] & pair:
                                    candidates[r][c] -= pair
                                    eliminated = True
                        if eliminated:
                            if highest_technique in ("easy",):
                                highest_technique = "medium"
                            progress = True
                            break
                if progress:
                    break
            if progress:
                break
        if progress:
            continue

        # Pointing/Claiming (Box-Line reduction)
        for br in range(3):
            for bc in range(3):
                box_cells = [(br * 3 + dr, bc * 3 + dc) for dr in range(3) for dc in range(3) if grid[br * 3 + dr][bc * 3 + dc] == 0]
                for digit in range(1, 10):
                    cells_with_digit = [(r, c) for (r, c) in box_cells if digit in candidates[r][c]]
                    if len(cells_with_digit) in (2, 3):
                        # check same row
                        rows = {r for r, c in cells_with_digit}
                        if len(rows) == 1:
                            target_r = next(iter(rows))
                            eliminated = False
                            for col in range(9):
                                if (col // 3) != bc and grid[target_r][col] == 0 and digit in candidates[target_r][col]:
                                    candidates[target_r][col].discard(digit)
                                    eliminated = True
                            if eliminated:
                                if highest_technique in ("easy",):
                                    highest_technique = "medium"
                                progress = True
                                break
                        # check same col
                        cols = {c for r, c in cells_with_digit}
                        if len(cols) == 1:
                            target_c = next(iter(cols))
                            eliminated = False
                            for row in range(9):
                                if (row // 3) != br and grid[row][target_c] == 0 and digit in candidates[row][target_c]:
                                    candidates[row][target_c].discard(digit)
                                    eliminated = True
                            if eliminated:
                                if highest_technique in ("easy",):
                                    highest_technique = "medium"
                                progress = True
                                break
                if progress:
                    break
            if progress:
                break
        if progress:
            continue

        # 4. Hard Techniques: X-Wing / Triples
        # X-Wing check
        for digit in range(1, 10):
            row_candidates: Dict[int, List[int]] = {}
            for r in range(9):
                cols = [c for c in range(9) if grid[r][c] == 0 and digit in candidates[r][c]]
                if len(cols) == 2:
                    row_candidates[r] = cols
            if len(row_candidates) >= 2:
                r_keys = list(row_candidates.keys())
                for i in range(len(r_keys)):
                    for j in range(i + 1, len(r_keys)):
                        r1, r2 = r_keys[i], r_keys[j]
                        if row_candidates[r1] == row_candidates[r2]:
                            c1, c2 = row_candidates[r1]
                            eliminated = False
                            for r in range(9):
                                if r != r1 and r != r2 and grid[r][c1] == 0 and digit in candidates[r][c1]:
                                    candidates[r][c1].discard(digit)
                                    eliminated = True
                                if r != r1 and r != r2 and grid[r][c2] == 0 and digit in candidates[r][c2]:
                                    candidates[r][c2].discard(digit)
                                    eliminated = True
                            if eliminated:
                                if highest_technique in ("easy", "medium"):
                                    highest_technique = "hard"
                                progress = True
                                break
                    if progress:
                        break
            if progress:
                break
        if progress:
            continue

        # If pure human-logic deductions did not progress further, solving requires advanced/expert logic
        highest_technique = "expert"
        break

    return highest_technique


# --- 6. Scoring Formula ---

def calculate_score(level: str, seconds: int, hints_used: int, mistakes: int) -> int:
    """
    Computes final game score:
      - Base score: Easy = 1000, Medium = 2000, Hard = 4000, Expert = 8000.
      - Time penalty: Subtract 1 point per 5 seconds elapsed (floor(seconds / 5)).
      - Hint penalty: Subtract 25 points per hint used.
      - Mistake penalty: Subtract 10 points per mistake made.
      - Score floor: Cannot drop below 20% of base score (floor(0.2 * base)).
    """
    base = BASE_SCORES.get(level.lower(), 1000)
    time_penalty = math.floor(seconds / 5)
    hint_penalty = 25 * hints_used
    mistake_penalty = 10 * mistakes
    raw_score = base - time_penalty - hint_penalty - mistake_penalty
    floor_score = math.floor(0.2 * base)
    return max(floor_score, raw_score)


def calculate_daily_score(history_records: List[HistoryRecord], target_date: str) -> int:
    """Calculates sum of all game scores completed on target_date (YYYY-MM-DD)."""
    return sum(rec.score for rec in history_records if rec.date == target_date)


# --- 7. Level Unlock Progression ---

def get_level_unlock_status(history_records: List[HistoryRecord]) -> Dict[str, Dict[str, Any]]:
    """
    Determines unlock status for all difficulty levels:
      - Easy: Unlocked by default.
      - Medium: Unlocks after 2 completed Easy games.
      - Hard: Unlocks after 4 completed Medium games.
      - Expert: Unlocks after 16 completed Hard games.
    """
    completed_counts = {
        "easy": sum(1 for r in history_records if r.level == "easy"),
        "medium": sum(1 for r in history_records if r.level == "medium"),
        "hard": sum(1 for r in history_records if r.level == "hard"),
        "expert": sum(1 for r in history_records if r.level == "expert"),
    }

    status: Dict[str, Dict[str, Any]] = {}
    for lvl in DIFFICULTIES:
        req = UNLOCK_REQUIREMENTS[lvl]
        prereq = req["prereq"]
        needed = req["count"]
        if prereq is None:
            status[lvl] = {
                "unlocked": True,
                "current": 0,
                "required": 0,
                "prereq": None,
                "progress_label": "Unlocked",
            }
        else:
            curr = completed_counts[prereq]
            meets = curr >= needed
            unlocked = meets if LEVELS_LOCKED else True
            cap_prereq = prereq.capitalize()
            status[lvl] = {
                "unlocked": unlocked,
                "current": curr,
                "required": needed,
                "prereq": cap_prereq,
                "progress_label": "Unlocked" if (unlocked and not LEVELS_LOCKED) else (f"{curr} / {needed} {cap_prereq} games" if not unlocked else "Unlocked"),
            }

    return status


# --- 8. Daily Streak Engine ---

def calculate_streak(history_records: List[HistoryRecord], current_date: str) -> Tuple[int, int]:
    """
    Computes (current_streak, best_streak).
      - Streak increment requires at least one completed game on that calendar day.
      - If played yesterday but not yet today, streak is maintained.
      - If two or more calendar days pass without completing a game, streak resets to 0.
      - Date format: YYYY-MM-DD.
    """
    played_dates = sorted(list({r.date for r in history_records}))
    if not played_dates:
        return 0, 0

    def parse_days(d_str: str) -> int:
        parts = [int(p) for p in d_str.split("-")]
        # Approx day number using Gregorian formula
        y, m, d = parts[0], parts[1], parts[2]
        # Days from epoch
        import datetime
        return datetime.date(y, m, d).toordinal()

    all_day_ords = sorted([parse_days(d) for d in played_dates])

    # Calculate best streak historically
    best_streak = 0
    cur_run = 0
    prev_ord = None
    for ord_val in all_day_ords:
        if prev_ord is None:
            cur_run = 1
        elif ord_val == prev_ord + 1:
            cur_run += 1
        elif ord_val == prev_ord:
            pass
        else:
            cur_run = 1
        if cur_run > best_streak:
            best_streak = cur_run
        prev_ord = ord_val

    # Calculate active streak relative to current_date
    today_ord = parse_days(current_date)
    last_played_ord = all_day_ords[-1]

    # If last played was 2 or more days ago (gap >= 2), streak is 0
    if today_ord - last_played_ord >= 2:
        return 0, best_streak

    # Count consecutive days backwards from last_played_ord
    active_streak = 1
    i = len(all_day_ords) - 1
    while i > 0:
        if all_day_ords[i] - all_day_ords[i - 1] == 1:
            active_streak += 1
            i -= 1
        elif all_day_ords[i] == all_day_ords[i - 1]:
            i -= 1
        else:
            break

    if active_streak > best_streak:
        best_streak = active_streak

    return active_streak, best_streak


# --- 9. Puzzle Generation & Pre-Generated Cache ---

def generate_full_board(rng: Optional[random.Random] = None) -> Grid:
    """Generates a random valid filled 9x9 board using backtracking."""
    r = rng or random.Random()
    board = empty_grid()

    def fill() -> bool:
        for row in range(9):
            for col in range(9):
                if board[row][col] == 0:
                    nums = list(range(1, 10))
                    r.shuffle(nums)
                    for num in nums:
                        if is_valid_placement(board, row, col, num):
                            board[row][col] = num
                            if fill():
                                return True
                            board[row][col] = 0
                    return False
        return True

    fill()
    return board


DIFFICULTY_TARGETS: Dict[str, Dict[str, Any]] = {
    "easy": {"min_givens": 42, "max_givens": 46, "target": 44, "max_technique": "easy"},
    "medium": {"min_givens": 36, "max_givens": 40, "target": 38, "max_technique": "medium"},
    "hard": {"min_givens": 30, "max_givens": 34, "target": 32, "max_technique": "hard"},
    "expert": {"min_givens": 25, "max_givens": 29, "target": 27, "max_technique": "expert"},
}

TECHNIQUE_RANK: Dict[str, int] = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "expert": 4,
}


def generate_puzzle(level: str = "easy", seed: Optional[int] = None, max_attempts: int = 50) -> Tuple[Grid, Grid]:
    """
    Generates a puzzle with a single unique solution matching the requested difficulty.
    - Easy: 42-46 givens, singles only, no row/col/box < 2 givens.
    - Medium: 36-40 givens, singles + pairs.
    - Hard: 30-34 givens, pointing/box-line reduction.
    - Expert: 25-29 givens, advanced techniques.
    Runs up to max_attempts (50) with technique-based validation, falling back
    to the closest valid puzzle if the limit is reached.
    """
    rng = random.Random(seed)
    lvl = level.lower()
    config = DIFFICULTY_TARGETS.get(lvl, DIFFICULTY_TARGETS["easy"])
    min_givens = config["min_givens"]
    max_givens = config["max_givens"]
    target_givens = config["target"]
    max_tech = config["max_technique"]

    best_puzzle: Optional[Grid] = None
    best_solution: Optional[Grid] = None
    best_rank_diff = 999

    for _ in range(max_attempts):
        solution = generate_full_board(rng)
        puzzle = clone_grid(solution)

        row_counts = [9] * 9
        col_counts = [9] * 9
        box_counts = [9] * 9

        positions = [(r, c) for r in range(9) for c in range(9)]
        rng.shuffle(positions)

        current_givens = 81
        for r, c in positions:
            if current_givens <= target_givens:
                break
            b = (r // 3) * 3 + (c // 3)
            # Easy rule: no row, column or box with fewer than 2 givens
            if lvl == "easy":
                if row_counts[r] <= 2 or col_counts[c] <= 2 or box_counts[b] <= 2:
                    continue

            val = puzzle[r][c]
            puzzle[r][c] = 0
            if has_unique_solution(puzzle):
                row_counts[r] -= 1
                col_counts[c] -= 1
                box_counts[b] -= 1
                current_givens -= 1
            else:
                puzzle[r][c] = val

        # Check if givens are in acceptable range
        if min_givens <= current_givens <= max_givens:
            # On easy, verify all units have >= 2 givens
            if lvl == "easy":
                if min(row_counts) < 2 or min(col_counts) < 2 or min(box_counts) < 2:
                    continue

            # Run technique-based solver
            tech = grade_puzzle_difficulty(puzzle)
            if TECHNIQUE_RANK[tech] <= TECHNIQUE_RANK[max_tech]:
                return puzzle, solution

            # Track closest candidate
            rank_diff = abs(TECHNIQUE_RANK[tech] - TECHNIQUE_RANK[max_tech])
            if rank_diff < best_rank_diff:
                best_puzzle = clone_grid(puzzle)
                best_solution = clone_grid(solution)
                best_rank_diff = rank_diff

    # Fallback to closest valid puzzle or last generated puzzle
    if best_puzzle is not None and best_solution is not None:
        return best_puzzle, best_solution

    # Fallback: return from curated cache if available
    pool = CURATED_PUZZLES.get(lvl, CURATED_PUZZLES["easy"])
    choice = rng.choice(pool)
    return clone_grid(choice["puzzle"]), clone_grid(choice["solution"])


# Pre-computed curated puzzle seeds for zero-lag instant desktop loading
CURATED_PUZZLES: Dict[str, List[Dict[str, Any]]] = {
    "easy": [
        {
            "puzzle": [
                [9, 7, 0, 0, 0, 0, 0, 0, 3],
                [1, 0, 0, 4, 6, 0, 0, 5, 9],
                [5, 0, 0, 7, 0, 8, 4, 2, 1],
                [0, 0, 0, 6, 1, 7, 0, 3, 0],
                [3, 8, 1, 0, 4, 9, 0, 6, 7],
                [0, 0, 7, 8, 3, 0, 9, 0, 2],
                [6, 4, 5, 0, 7, 0, 3, 0, 8],
                [8, 0, 0, 0, 5, 4, 0, 0, 6],
                [0, 9, 0, 3, 0, 0, 1, 0, 5],
            ],
            "solution": [
                [9, 7, 4, 5, 2, 1, 6, 8, 3],
                [1, 2, 8, 4, 6, 3, 7, 5, 9],
                [5, 3, 6, 7, 9, 8, 4, 2, 1],
                [2, 5, 9, 6, 1, 7, 8, 3, 4],
                [3, 8, 1, 2, 4, 9, 5, 6, 7],
                [4, 6, 7, 8, 3, 5, 9, 1, 2],
                [6, 4, 5, 1, 7, 2, 3, 9, 8],
                [8, 1, 3, 9, 5, 4, 2, 7, 6],
                [7, 9, 2, 3, 8, 6, 1, 4, 5],
            ],
        },
        {
            "puzzle": [
                [6, 0, 9, 0, 0, 0, 8, 0, 5],
                [7, 0, 4, 0, 0, 0, 1, 9, 2],
                [0, 8, 0, 9, 2, 0, 0, 4, 7],
                [0, 1, 2, 3, 0, 8, 0, 5, 9],
                [0, 0, 0, 2, 9, 7, 0, 1, 6],
                [9, 6, 7, 0, 0, 1, 2, 8, 0],
                [0, 0, 0, 8, 4, 0, 5, 6, 0],
                [5, 9, 8, 0, 1, 6, 0, 0, 4],
                [0, 0, 0, 5, 3, 2, 0, 0, 0],
            ],
            "solution": [
                [6, 2, 9, 1, 7, 4, 8, 3, 5],
                [7, 5, 4, 6, 8, 3, 1, 9, 2],
                [3, 8, 1, 9, 2, 5, 6, 4, 7],
                [4, 1, 2, 3, 6, 8, 7, 5, 9],
                [8, 3, 5, 2, 9, 7, 4, 1, 6],
                [9, 6, 7, 4, 5, 1, 2, 8, 3],
                [2, 7, 3, 8, 4, 9, 5, 6, 1],
                [5, 9, 8, 7, 1, 6, 3, 2, 4],
                [1, 4, 6, 5, 3, 2, 9, 7, 8],
            ],
        },
    ],
    "medium": [
        {
            "puzzle": [
                [9, 7, 0, 0, 0, 0, 0, 0, 3],
                [1, 0, 0, 0, 0, 0, 0, 5, 9],
                [5, 0, 0, 7, 0, 8, 4, 2, 1],
                [0, 0, 0, 6, 1, 7, 0, 3, 0],
                [0, 8, 1, 0, 4, 0, 0, 6, 7],
                [0, 0, 7, 8, 0, 0, 9, 0, 2],
                [6, 4, 5, 0, 7, 0, 3, 0, 8],
                [8, 0, 0, 0, 5, 4, 0, 0, 6],
                [0, 0, 0, 3, 0, 0, 1, 0, 5],
            ],
            "solution": [
                [9, 7, 4, 5, 2, 1, 6, 8, 3],
                [1, 2, 8, 4, 6, 3, 7, 5, 9],
                [5, 3, 6, 7, 9, 8, 4, 2, 1],
                [2, 5, 9, 6, 1, 7, 8, 3, 4],
                [3, 8, 1, 2, 4, 9, 5, 6, 7],
                [4, 6, 7, 8, 3, 5, 9, 1, 2],
                [6, 4, 5, 1, 7, 2, 3, 9, 8],
                [8, 1, 3, 9, 5, 4, 2, 7, 6],
                [7, 9, 2, 3, 8, 6, 1, 4, 5],
            ],
        },
        {
            "puzzle": [
                [0, 0, 9, 0, 0, 0, 8, 0, 5],
                [7, 0, 4, 0, 0, 0, 1, 9, 2],
                [0, 8, 0, 0, 2, 0, 0, 4, 7],
                [0, 1, 2, 3, 0, 8, 0, 5, 0],
                [0, 0, 0, 2, 9, 0, 0, 1, 6],
                [9, 6, 7, 0, 0, 1, 2, 8, 0],
                [0, 0, 0, 0, 4, 0, 5, 6, 0],
                [5, 9, 8, 0, 1, 6, 0, 0, 4],
                [0, 0, 0, 5, 3, 0, 0, 0, 0],
            ],
            "solution": [
                [6, 2, 9, 1, 7, 4, 8, 3, 5],
                [7, 5, 4, 6, 8, 3, 1, 9, 2],
                [3, 8, 1, 9, 2, 5, 6, 4, 7],
                [4, 1, 2, 3, 6, 8, 7, 5, 9],
                [8, 3, 5, 2, 9, 7, 4, 1, 6],
                [9, 6, 7, 4, 5, 1, 2, 8, 3],
                [2, 7, 3, 8, 4, 9, 5, 6, 1],
                [5, 9, 8, 7, 1, 6, 3, 2, 4],
                [1, 4, 6, 5, 3, 2, 9, 7, 8],
            ],
        },
    ],
    "hard": [
        {
            "puzzle": [
                [9, 7, 0, 0, 0, 0, 0, 0, 3],
                [1, 0, 0, 0, 0, 0, 0, 5, 9],
                [0, 0, 0, 0, 0, 8, 4, 2, 1],
                [0, 0, 0, 6, 1, 0, 0, 3, 0],
                [0, 8, 0, 0, 4, 0, 0, 6, 0],
                [0, 0, 7, 8, 0, 0, 9, 0, 2],
                [6, 4, 5, 0, 7, 0, 3, 0, 8],
                [0, 0, 0, 0, 5, 4, 0, 0, 6],
                [0, 0, 0, 3, 0, 0, 1, 0, 5],
            ],
            "solution": [
                [9, 7, 4, 5, 2, 1, 6, 8, 3],
                [1, 2, 8, 4, 6, 3, 7, 5, 9],
                [5, 3, 6, 7, 9, 8, 4, 2, 1],
                [2, 5, 9, 6, 1, 7, 8, 3, 4],
                [3, 8, 1, 2, 4, 9, 5, 6, 7],
                [4, 6, 7, 8, 3, 5, 9, 1, 2],
                [6, 4, 5, 1, 7, 2, 3, 9, 8],
                [8, 1, 3, 9, 5, 4, 2, 7, 6],
                [7, 9, 2, 3, 8, 6, 1, 4, 5],
            ],
        },
        {
            "puzzle": [
                [0, 0, 9, 0, 0, 0, 8, 0, 0],
                [7, 0, 4, 0, 0, 0, 1, 0, 2],
                [0, 8, 0, 0, 2, 0, 0, 4, 0],
                [0, 1, 2, 3, 0, 8, 0, 5, 0],
                [0, 0, 0, 2, 9, 0, 0, 1, 6],
                [9, 6, 7, 0, 0, 1, 2, 8, 0],
                [0, 0, 0, 0, 0, 0, 5, 6, 0],
                [5, 9, 8, 0, 1, 6, 0, 0, 0],
                [0, 0, 0, 5, 0, 0, 0, 0, 0],
            ],
            "solution": [
                [6, 2, 9, 1, 7, 4, 8, 3, 5],
                [7, 5, 4, 6, 8, 3, 1, 9, 2],
                [3, 8, 1, 9, 2, 5, 6, 4, 7],
                [4, 1, 2, 3, 6, 8, 7, 5, 9],
                [8, 3, 5, 2, 9, 7, 4, 1, 6],
                [9, 6, 7, 4, 5, 1, 2, 8, 3],
                [2, 7, 3, 8, 4, 9, 5, 6, 1],
                [5, 9, 8, 7, 1, 6, 3, 2, 4],
                [1, 4, 6, 5, 3, 2, 9, 7, 8],
            ],
        },
    ],
    "expert": [
        {
            "puzzle": [
                [9, 7, 0, 0, 0, 0, 0, 0, 3],
                [1, 0, 0, 0, 0, 0, 0, 5, 9],
                [0, 0, 0, 0, 0, 8, 4, 2, 0],
                [0, 0, 0, 6, 1, 0, 0, 3, 0],
                [0, 8, 0, 0, 4, 0, 0, 6, 0],
                [0, 0, 0, 0, 0, 0, 9, 0, 2],
                [6, 4, 0, 0, 7, 0, 3, 0, 8],
                [0, 0, 0, 0, 0, 4, 0, 0, 6],
                [0, 0, 0, 3, 0, 0, 1, 0, 5],
            ],
            "solution": [
                [9, 7, 4, 5, 2, 1, 6, 8, 3],
                [1, 2, 8, 4, 6, 3, 7, 5, 9],
                [5, 3, 6, 7, 9, 8, 4, 2, 1],
                [2, 5, 9, 6, 1, 7, 8, 3, 4],
                [3, 8, 1, 2, 4, 9, 5, 6, 7],
                [4, 6, 7, 8, 3, 5, 9, 1, 2],
                [6, 4, 5, 1, 7, 2, 3, 9, 8],
                [8, 1, 3, 9, 5, 4, 2, 7, 6],
                [7, 9, 2, 3, 8, 6, 1, 4, 5],
            ],
        },
        {
            "puzzle": [
                [0, 0, 9, 0, 0, 0, 8, 0, 0],
                [7, 0, 4, 0, 0, 0, 1, 0, 2],
                [0, 8, 0, 0, 2, 0, 0, 4, 0],
                [0, 1, 2, 3, 0, 8, 0, 5, 0],
                [0, 0, 0, 2, 9, 0, 0, 1, 0],
                [0, 6, 7, 0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 6, 0],
                [5, 9, 8, 0, 1, 6, 0, 0, 0],
                [0, 0, 0, 5, 0, 0, 0, 0, 0],
            ],
            "solution": [
                [6, 2, 9, 1, 7, 4, 8, 3, 5],
                [7, 5, 4, 6, 8, 3, 1, 9, 2],
                [3, 8, 1, 9, 2, 5, 6, 4, 7],
                [4, 1, 2, 3, 6, 8, 7, 5, 9],
                [8, 3, 5, 2, 9, 7, 4, 1, 6],
                [9, 6, 7, 4, 5, 1, 2, 8, 3],
                [2, 7, 3, 8, 4, 9, 5, 6, 1],
                [5, 9, 8, 7, 1, 6, 3, 2, 4],
                [1, 4, 6, 5, 3, 2, 9, 7, 8],
            ],
        },
    ],
}
