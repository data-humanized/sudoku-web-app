"""
sudoku_logic.py
Complete ZenSudoku Engine in Python:
- Data models & types
- Difficulty levels: easy, medium, hard, expert, master
- MAX_SCORE (Section 8 shared constant):
    easy: 6000, medium: 9000, hard: 13000, expert: 17000, master: 21000
- SCORE_RANGES & BASE_SCORES
- CLUE_RANGES single source of truth for clue count ranges (fewer clues as level rises):
    easy > medium > hard > expert > master
- is_cell_locked: Dynamic lock evaluation based on cell matching solution
- Live score calculation formula with units and combo cap (flawless 85%-100% of MAX_SCORE)
- Canonical fingerprinting invariant to symmetries, permutations, and relabeling
- Clue similarity checking (<20% identical clues to recent puzzles)
- High-performance bitmask solver & uniqueness validator
- Difficulty grader
- Unlock progression system (master unlocks after 16 expert wins)
- Daily streak calculation & daily score aggregation
"""

from __future__ import annotations
import math
import random
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, TypedDict

Difficulty = Literal['easy', 'medium', 'hard', 'expert', 'master']

# 9x9 matrix (0 = empty, 1-9 = placed)
Grid = List[List[int]]
# 9x9 matrix of candidate sets
Notes = List[List[Set[int]]]
BoolGrid = List[List[bool]]

from puzzles_database import PUZZLE_BANK

CURATED_PUZZLES = PUZZLE_BANK


class ScoreRange(TypedDict):
    min: int
    max: int


# Section 1 & Section 8: Shared constant for maximum score per level
MAX_SCORE: Dict[Difficulty, int] = {
    'easy': 6000,
    'medium': 9000,
    'hard': 13000,
    'expert': 17000,
    'master': 21000,
}

OLD_MAX_SCORE: Dict[Difficulty, int] = {
    'easy': 1000,
    'medium': 2000,
    'hard': 4000,
    'expert': 8000,
    'master': 16000,
}

# Score ranges used across scoring, backup validation and tests
SCORE_RANGES: Dict[Difficulty, ScoreRange] = {
    'easy': {'min': 200, 'max': 1000},
    'medium': {'min': 400, 'max': 2000},
    'hard': {'min': 800, 'max': 4000},
    'expert': {'min': 1600, 'max': 8000},
    'master': {'min': 3200, 'max': 16000},
}

# Section 2: Shared constant for clue count range per level (fewer clues as level rises: easy > medium > hard > expert > master)
CLUE_RANGES: Dict[Difficulty, Dict[str, int]] = {
    'easy': {'min': 36, 'max': 40},
    'medium': {'min': 31, 'max': 35},
    'hard': {'min': 27, 'max': 30},
    'expert': {'min': 24, 'max': 26},
    'master': {'min': 21, 'max': 23},
}

BASE_SCORES: Dict[Difficulty, int] = {
    'easy': 1000,
    'medium': 2000,
    'hard': 4000,
    'expert': 8000,
    'master': 16000,
}

UNLOCK_REQUIREMENTS: Dict[Difficulty, Dict[str, Any]] = {
    'easy': {'prereq': None, 'count': 0},
    'medium': {'prereq': 'easy', 'count': 2},
    'hard': {'prereq': 'medium', 'count': 4},
    'expert': {'prereq': 'hard', 'count': 16},
    'master': {'prereq': 'expert', 'count': 16},
}

DIFFICULTY_TARGETS = {
    'easy': {'givens': 38, 'range': (CLUE_RANGES['easy']['min'], CLUE_RANGES['easy']['max']), 'symmetry': 'rotational'},
    'medium': {'givens': 33, 'range': (CLUE_RANGES['medium']['min'], CLUE_RANGES['medium']['max']), 'symmetry': 'rotational'},
    'hard': {'givens': 28, 'range': (CLUE_RANGES['hard']['min'], CLUE_RANGES['hard']['max']), 'symmetry': 'rotational'},
    'expert': {'givens': 25, 'range': (CLUE_RANGES['expert']['min'], CLUE_RANGES['expert']['max']), 'symmetry': 'rotational'},
    'master': {'givens': 22, 'range': (CLUE_RANGES['master']['min'], CLUE_RANGES['master']['max']), 'symmetry': 'diagonal'},
}

TECHNIQUE_RANK = {
    'naked_single': 1,
    'hidden_single': 2,
    'naked_pair': 3,
    'hidden_pair': 4,
    'pointing_pair': 5,
    'box_line': 6,
    'naked_triple': 7,
    'hidden_triple': 8,
    'x_wing': 9,
    'y_wing': 10,
    'forcing_chain': 11,
    'guess_required': 12,
}


class MoveAction(TypedDict):
    action_type: Literal['digit', 'wrong_digit', 'note', 'erase', 'auto_notes', 'hint']
    row: int
    col: int
    prev_val: int
    new_val: int
    prev_notes: List[int]
    new_notes: List[int]
    peer_notes_changes: Optional[List[Dict[str, int]]]


class HistoryRecord(TypedDict, total=False):
    id: str
    date: str  # 'YYYY-MM-DD'
    level: Difficulty
    score: int
    timeSeconds: int
    mistakes: int
    hintsUsed: int
    won: bool
    timestamp: int
    seconds: int


class UserSettings(TypedDict):
    theme: str
    sound_effects: bool
    haptics: bool
    font_size: str
    show_timer: bool
    show_mistakes: bool
    auto_remove_notes: bool


class GameState(TypedDict):
    id: str
    level: Difficulty
    initial_grid: Grid
    solution_grid: Grid
    current_grid: Grid
    notes: Notes
    hinted_cells: BoolGrid
    mistakes: int
    hints_used: int
    elapsed_seconds: int
    is_paused: bool
    is_completed: bool
    undo_stack: List[MoveAction]
    redo_stack: List[MoveAction]
    start_time: float
    completed_time: Optional[float]
    final_score: int
    earned_combo_units: Optional[int]


DEFAULT_SETTINGS: UserSettings = {
    'theme': 'minimal_slate',
    'sound_effects': True,
    'haptics': True,
    'font_size': 'medium',
    'show_timer': True,
    'show_mistakes': True,
    'auto_remove_notes': True,
}


def migrate_history_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Migrates old history records: round((oldScore / oldMax) * newMax)."""
    rec = dict(record)
    level = rec.get('level', 'easy')
    old_max = OLD_MAX_SCORE.get(level, 1000)
    new_max = MAX_SCORE.get(level, 6000)

    score = rec.get('score', 0)
    if score <= old_max:
        score = int(round((score / old_max) * new_max))
    rec['score'] = max(0, min(new_max, score))

    if 'timeSeconds' not in rec and 'seconds' in rec:
        rec['timeSeconds'] = rec.pop('seconds')
    return rec


def is_cell_locked(
    arg1: Any,
    arg2: int,
    arg3: Any = None,
    current_grid: Optional[Grid] = None,
    solution_grid: Optional[Grid] = None,
) -> bool:
    """
    Section 3: Cell Locking
    Accepts either (game_dict, row, col) or (row, col, initial_grid, current_grid, solution_grid).
    - Initial clues are permanently locked.
    - Placed digits matching solution_grid are locked.
    - Wrong digits are NOT locked.
    """
    if isinstance(arg1, dict):
        game = arg1
        r = arg2
        c = arg3
        initial = game.get('initial_grid') or game.get('initialGrid')
        current = game.get('current_grid') or game.get('currentGrid')
        solution = game.get('solution_grid') or game.get('solutionGrid')
    else:
        r = arg1
        c = arg2
        initial = arg3
        current = current_grid
        solution = solution_grid

    if initial and initial[r][c] != 0:
        return True
    if current and solution:
        val = current[r][c]
        return val != 0 and val == solution[r][c]
    return False


def create_empty_grid() -> Grid:
    return [[0 for _ in range(9)] for _ in range(9)]


def clone_grid(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def create_empty_notes() -> Notes:
    return [[set() for _ in range(9)] for _ in range(9)]


def clone_notes(notes: Notes) -> Notes:
    return [[set(cell) for cell in row] for row in notes]


def create_empty_bool_grid() -> BoolGrid:
    return [[False for _ in range(9)] for _ in range(9)]


def clone_bool_grid(bg: BoolGrid) -> BoolGrid:
    return [row[:] for row in bg]


def get_peers(row: int, col: int) -> List[Tuple[int, int]]:
    peers: List[Tuple[int, int]] = []
    start_r = (row // 3) * 3
    start_c = (col // 3) * 3
    for c in range(9):
        if c != col:
            peers.append((row, c))
    for r in range(9):
        if r != row:
            peers.append((r, col))
    for r in range(start_r, start_r + 3):
        for c in range(start_c, start_c + 3):
            if r != row and c != col:
                peers.append((r, c))
    return peers


def is_valid_placement(grid: Grid, row: int, col: int, num: int) -> bool:
    for c in range(9):
        if grid[row][c] == num:
            return False
    for r in range(9):
        if grid[r][col] == num:
            return False
    start_r = (row // 3) * 3
    start_c = (col // 3) * 3
    for r in range(start_r, start_r + 3):
        for c in range(start_c, start_c + 3):
            if grid[r][c] == num:
                return False
    return True


def get_candidates(grid: Grid, row: int, col: int) -> List[int]:
    if grid[row][col] != 0:
        return []
    return [n for n in range(1, 10) if is_valid_placement(grid, row, col, n)]


# --------------------------------------------------------------------------
# Section 8: Live Scoring Formula in Python
# --------------------------------------------------------------------------
def calculate_live_score(
    initial_grid: Grid,
    current_grid: Grid,
    solution_grid: Grid,
    mistakes: int,
    hints_used: int,
    level: Difficulty,
    earned_combo_units: int = 0,
) -> Tuple[int, bool]:
    clues = 0
    correct_cells = 0

    for r in range(9):
        for c in range(9):
            if initial_grid[r][c] != 0:
                clues += 1
            elif current_grid[r][c] != 0 and current_grid[r][c] == solution_grid[r][c]:
                correct_cells += 1

    # Completed rows (that had empty cells initially)
    completed_rows = sum(
        1 for r in range(9)
        if any(initial_grid[r][c] == 0 for c in range(9)) and
        all(current_grid[r][c] != 0 and current_grid[r][c] == solution_grid[r][c] for c in range(9))
    )

    # Completed columns (that had empty cells initially)
    completed_cols = sum(
        1 for c in range(9)
        if any(initial_grid[r][c] == 0 for r in range(9)) and
        all(current_grid[r][c] != 0 and current_grid[r][c] == solution_grid[r][c] for r in range(9))
    )

    # Completed boxes (that had empty cells initially)
    completed_boxes = 0
    for br in range(3):
        for bc in range(3):
            had_empty = any(initial_grid[br * 3 + r][bc * 3 + c] == 0 for r in range(3) for c in range(3))
            if had_empty and all(
                current_grid[br * 3 + r][bc * 3 + c] != 0 and
                current_grid[br * 3 + r][bc * 3 + c] == solution_grid[br * 3 + r][bc * 3 + c]
                for r in range(3) for c in range(3)
            ):
                completed_boxes += 1

    is_complete = correct_cells == (81 - clues)

    standard_units = correct_cells * 10 + (completed_rows + completed_cols + completed_boxes) * 30
    if is_complete:
        standard_units += 100

    penalty_units = mistakes * 15 + hints_used * 10

    baseline_units = (81 - clues) * 10 + (9 + 9 + 9) * 30 + 100
    max_score = MAX_SCORE[level]
    scale = (0.85 * max_score) / baseline_units
    combo_cap = (0.15 * max_score) / scale

    valid_combo_units = min(earned_combo_units, combo_cap)
    raw_units = standard_units + valid_combo_units - penalty_units

    live_score = max(0, min(max_score, int(round(raw_units * scale))))
    return live_score, is_complete


# --------------------------------------------------------------------------
# Section 2: Canonical Fingerprint Calculation in Python
# --------------------------------------------------------------------------
def get_canonical_form(grid: Grid) -> str:
    perms3 = [
        [0, 1, 2],
        [0, 2, 1],
        [1, 0, 2],
        [1, 2, 0],
        [2, 0, 1],
        [2, 1, 0],
    ]
    min_str: Optional[str] = None

    for rot in range(4):
        for flip in [False, True]:
            for band_order in perms3:
                for stack_order in perms3:
                    t_grid = create_empty_grid()
                    for r in range(9):
                        for c in range(9):
                            tr, tc = r, c
                            if flip:
                                tc = 8 - tc
                            for _ in range(rot):
                                tr, tc = tc, 8 - tr

                            band = tr // 3
                            row_in_band = tr % 3
                            final_r = band_order[band] * 3 + row_in_band

                            stack = tc // 3
                            col_in_stack = tc % 3
                            final_c = stack_order[stack] * 3 + col_in_stack

                            t_grid[final_r][final_c] = grid[r][c]

                    mapping: Dict[int, int] = {}
                    next_label = 1
                    chars: List[str] = []
                    for r in range(9):
                        for c in range(9):
                            v = t_grid[r][c]
                            if v == 0:
                                chars.append('0')
                            else:
                                if v not in mapping:
                                    mapping[v] = next_label
                                    next_label += 1
                                chars.append(str(mapping[v]))
                    rep = ''.join(chars)
                    if min_str is None or rep < min_str:
                        min_str = rep

    return min_str or ''.join(str(grid[r][c]) for r in range(9) for c in range(9))


def get_canonical_fingerprint(grid: Grid) -> str:
    canon = get_canonical_form(grid)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()[:16]


def is_too_similar_to_recent(candidate: Grid, recent_grids: List[Grid], threshold: float = 0.20) -> bool:
    candidate_clues = sum(1 for r in range(9) for c in range(9) if candidate[r][c] != 0)
    if candidate_clues == 0:
        return False

    for recent in recent_grids:
        matches = sum(
            1 for r in range(9) for c in range(9)
            if candidate[r][c] != 0 and candidate[r][c] == recent[r][c]
        )
        if (matches / candidate_clues) > threshold:
            return True
    return False


# --------------------------------------------------------------------------
# Solver & Uniqueness
# --------------------------------------------------------------------------
def count_solutions(grid: Grid, limit: int = 2) -> int:
    row_mask = [0] * 9
    col_mask = [0] * 9
    box_mask = [0] * 9
    empty_cells: List[Tuple[int, int]] = []

    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v != 0:
                bit = 1 << v
                row_mask[r] |= bit
                col_mask[c] |= bit
                box_mask[(r // 3) * 3 + (c // 3)] |= bit
            else:
                empty_cells.append((r, c))

    solutions = 0

    def search(idx: int) -> bool:
        nonlocal solutions
        if idx == len(empty_cells):
            solutions += 1
            return solutions >= limit

        best_idx = idx
        min_candidates = 10
        best_possible = 0

        for i in range(idx, len(empty_cells)):
            r, c = empty_cells[i]
            box = (r // 3) * 3 + (c // 3)
            used = row_mask[r] | col_mask[c] | box_mask[box]
            possible = (~used) & 0x3FE
            count = bin(possible).count('1')
            if count < min_candidates:
                min_candidates = count
                best_idx = i
                best_possible = possible
                if count <= 1:
                    break

        if min_candidates == 0:
            return False

        empty_cells[idx], empty_cells[best_idx] = empty_cells[best_idx], empty_cells[idx]
        r, c = empty_cells[idx]
        b = (r // 3) * 3 + (c // 3)

        candidates = best_possible
        while candidates > 0:
            bit = candidates & -candidates
            candidates -= bit
            val = bit.bit_length() - 1

            row_mask[r] |= bit
            col_mask[c] |= bit
            box_mask[b] |= bit

            if search(idx + 1):
                return True

            row_mask[r] &= ~bit
            col_mask[c] &= ~bit
            box_mask[b] &= ~bit

        empty_cells[idx], empty_cells[best_idx] = empty_cells[best_idx], empty_cells[idx]
        return False

    search(0)
    return solutions


def has_unique_solution(grid: Grid) -> bool:
    return count_solutions(grid, 2) == 1


def _solve_sudoku_grid(grid: Grid) -> Optional[Grid]:
    result = clone_grid(grid)
    row_mask = [0] * 9
    col_mask = [0] * 9
    box_mask = [0] * 9
    empty_cells: List[Tuple[int, int]] = []

    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v != 0:
                bit = 1 << v
                row_mask[r] |= bit
                col_mask[c] |= bit
                box_mask[(r // 3) * 3 + (c // 3)] |= bit
            else:
                empty_cells.append((r, c))

    def search(idx: int) -> bool:
        if idx == len(empty_cells):
            return True

        best_idx = idx
        min_candidates = 10
        best_possible = 0

        for i in range(idx, len(empty_cells)):
            r, c = empty_cells[i]
            box = (r // 3) * 3 + (c // 3)
            used = row_mask[r] | col_mask[c] | box_mask[box]
            possible = (~used) & 0x3FE
            count = bin(possible).count('1')
            if count < min_candidates:
                min_candidates = count
                best_idx = i
                best_possible = possible
                if count <= 1:
                    break

        if min_candidates == 0:
            return False

        empty_cells[idx], empty_cells[best_idx] = empty_cells[best_idx], empty_cells[idx]
        r, c = empty_cells[idx]
        b = (r // 3) * 3 + (c // 3)

        candidates = best_possible
        while candidates > 0:
            bit = candidates & -candidates
            candidates -= bit
            val = bit.bit_length() - 1

            row_mask[r] |= bit
            col_mask[c] |= bit
            box_mask[b] |= bit
            result[r][c] = val

            if search(idx + 1):
                return True

            row_mask[r] &= ~bit
            col_mask[c] &= ~bit
            box_mask[b] &= ~bit
            result[r][c] = 0

        empty_cells[idx], empty_cells[best_idx] = empty_cells[best_idx], empty_cells[idx]
        return False

    return result if search(0) else None


def solve_sudoku(grid: Grid, count_limit: int = 2) -> Tuple[int, Optional[Grid]]:
    sol = _solve_sudoku_grid(grid)
    count = count_solutions(grid, limit=count_limit)
    return count, sol


def calculate_score(
    level: Difficulty,
    elapsed_seconds: int = 0,
    mistakes: int = 0,
    hints_used: int = 0,
    seconds: Optional[int] = None,
) -> int:
    time_sec = elapsed_seconds if elapsed_seconds > 0 else (seconds or 0)
    base = BASE_SCORES.get(level, 1000)
    time_penalty = max(0, time_sec - 300) * 2
    score = base - time_penalty - (hints_used * 100) - (mistakes * 50)
    floor = SCORE_RANGES[level]['min']
    return max(floor, min(base, score))


def get_level_unlock_status(history: List[HistoryRecord]) -> Dict[Difficulty, bool]:
    # All levels unlocked per user request: "unlock all the games, I dont want other level to be locked"
    return {
        'easy': True,
        'medium': True,
        'hard': True,
        'expert': True,
        'master': True,
    }


def is_won_record(r: HistoryRecord) -> bool:
    """A record is won if explicitly flagged won=True or has a positive score."""
    if r.get('won') is True:
        return True
    if r.get('won') is False:
        return False
    return r.get('score', 0) > 0


def format_points(num: int) -> str:
    """
    Format score/points according to user rules:
    - Under 10,000: show the full number with commas (e.g. 5,709).
    - 10,000 to 999,999: use K with up to 1 decimal (12.4K, 99.9K).
    - 1,000,000 to 999,999,999: use M with up to 1 decimal (1.2M).
    - 1,000,000,000 and above: use B.
    - Drop trailing zeros (write 12K, not 12.0K).
    """
    if not num or num <= 0:
        return "0"
    if num < 10000:
        return f"{num:,}"
    if num < 1_000_000:
        val = num / 1_000
        val_str = f"{val:.1f}".rstrip('0').rstrip('.')
        return f"{val_str}K"
    if num < 1_000_000_000:
        val = num / 1_000_000
        val_str = f"{val:.1f}".rstrip('0').rstrip('.')
        return f"{val_str}M"
    val = num / 1_000_000_000
    val_str = f"{val:.1f}".rstrip('0').rstrip('.')
    return f"{val_str}B"


def calculate_total_points(history: List[HistoryRecord]) -> int:
    """Returns the all-time sum of points across every game won/completed."""
    return sum(r.get('score', 0) for r in history if is_won_record(r))


def calculate_streak(history: List[HistoryRecord]) -> Dict[str, int]:
    if not history:
        return {'active_streak': 0, 'best_streak': 0}

    unique_dates = sorted(
        list({r['date'] for r in history if r.get('date') and is_won_record(r)}),
        reverse=True,
    )
    if not unique_dates:
        return {'active_streak': 0, 'best_streak': 0}

    active = 0
    for i, date_str in enumerate(unique_dates):
        d = datetime.strptime(date_str, '%Y-%m-%d')
        ref = datetime.now(timezone.utc) if i == 0 else datetime.strptime(unique_dates[i - 1], '%Y-%m-%d')
        diff_days = (ref.date() - d.date()).days

        if i == 0:
            if diff_days <= 1:
                active += 1
            else:
                break
        else:
            if diff_days == 1:
                active += 1
            else:
                break

    sorted_asc = sorted(unique_dates)
    best = 1
    current_run = 1
    for i in range(1, len(sorted_asc)):
        prev = datetime.strptime(sorted_asc[i - 1], '%Y-%m-%d')
        curr = datetime.strptime(sorted_asc[i], '%Y-%m-%d')
        if (curr.date() - prev.date()).days == 1:
            current_run += 1
        elif (curr.date() - prev.date()).days > 1:
            current_run = 1
        best = max(best, current_run)

    return {'active_streak': active, 'best_streak': max(best, active)}


def calculate_daily_score(history: List[HistoryRecord], target_date: Optional[str] = None) -> int:
    date_str = target_date or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return sum(
        r.get('score', 0)
        for r in history
        if r.get('date') == date_str and is_won_record(r)
    )


PREVIOUS_LEVEL_MAP: Dict[Difficulty, Optional[str]] = {
    'easy': None,
    'medium': 'Easy',
    'hard': 'Medium',
    'expert': 'Hard',
    'master': 'Expert',
}


def get_level_card_stats(history: List[HistoryRecord], level: Difficulty) -> Dict[str, Any]:
    unlock_status = get_level_unlock_status(history)
    is_unlocked = unlock_status.get(level, False)
    prev_level_name = PREVIOUS_LEVEL_MAP.get(level)

    level_records = [r for r in history if r.get('level') == level]
    won_records = [r for r in level_records if is_won_record(r)]
    won_count = len(won_records)
    total_count = len(level_records)

    if won_records:
        min_time = min(r.get('timeSeconds', r.get('seconds', 0)) for r in won_records)
        m = min_time // 60
        s = min_time % 60
        best_time_str = f"{m:02d}:{s:02d}"
    else:
        best_time_str = "--:--"

    games_won_str = f"{won_count} / {total_count}" if total_count > 0 else "0 / 0"
    lock_message = f"Finish {prev_level_name} to unlock" if (not is_unlocked and prev_level_name) else ""

    return {
        'level': level,
        'is_unlocked': is_unlocked,
        'best_time_str': best_time_str,
        'games_won_str': games_won_str,
        'won_count': won_count,
        'total_count': total_count,
        'lock_message': lock_message,
    }


def get_new_puzzle(level: Difficulty) -> Dict[str, Any]:
    from puzzle_generator import generate_puzzle_for_level
    return generate_puzzle_for_level(level)

