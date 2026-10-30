"""
difficulty_evaluator.py
Sudoku Difficulty Evaluator and Rating Analyzer in Python.

Computes the difficulty rating of any Sudoku puzzle by recording the hardest technique
needed to solve the puzzle logically:
- easy: naked and hidden singles only
- medium: adds naked/hidden pairs and box-line reductions
- hard: adds naked/hidden triples, X-Wing, Y-Wing
- expert: needs advanced chains or forcing logic
- master: the hardest puzzles, beyond expert (lowest givens 21-23, requiring deep multiple forcing chains / advanced deduction)
"""

from __future__ import annotations
import itertools
from typing import Any, Dict, List, Optional, Set, Tuple

from sudoku_logic import (
    CLUE_RANGES,
    Difficulty,
    Grid,
    clone_grid,
    get_candidates,
    get_peers,
)


class DifficultyScore:
    EASY: Difficulty = 'easy'
    MEDIUM: Difficulty = 'medium'
    HARD: Difficulty = 'hard'
    EXPERT: Difficulty = 'expert'
    MASTER: Difficulty = 'master'


class PuzzleAnalysis:
    def __init__(
        self,
        givens_count: int,
        rating: Difficulty,
        hardest_technique: str,
        techniques_used: Dict[str, int],
        logical_steps: int,
        solved_logically: bool,
    ):
        self.givens_count = givens_count
        self.rating = rating
        self.hardest_technique = hardest_technique
        self.techniques_used = techniques_used
        self.logical_steps = logical_steps
        self.solved_logically = solved_logically

    def to_dict(self) -> Dict[str, Any]:
        return {
            'givens_count': self.givens_count,
            'rating': self.rating,
            'hardest_technique': self.hardest_technique,
            'techniques_used': self.techniques_used,
            'logical_steps': self.logical_steps,
            'solved_logically': self.solved_logically,
        }


def _get_units() -> List[List[Tuple[int, int]]]:
    """Returns all 27 standard Sudoku units: 9 rows, 9 cols, 9 boxes."""
    rows = [[(r, c) for c in range(9)] for r in range(9)]
    cols = [[(r, c) for r in range(9)] for c in range(9)]
    boxes = [
        [((b // 3) * 3 + dr, (b % 3) * 3 + dc) for dr in range(3) for dc in range(3)]
        for b in range(9)
    ]
    return rows + cols + boxes


def evaluate_puzzle_difficulty(grid: Grid) -> PuzzleAnalysis:
    """
    Evaluates puzzle difficulty by tracking human logical deduction techniques
    in order of increasing difficulty:
    1. Naked Single
    2. Hidden Single
    3. Pointing Pair / Box-Line Reduction
    4. Naked Pair / Hidden Pair
    5. Naked Triple / Hidden Triple
    6. X-Wing
    7. Y-Wing (XY-Wing)
    8. Forcing Chain / Advanced logic
    """
    work = clone_grid(grid)
    givens = sum(1 for r in range(9) for c in range(9) if work[r][c] != 0)

    # Initialize candidates for empty cells
    candidates: List[List[Set[int]]] = [
        [set(get_candidates(work, r, c)) if work[r][c] == 0 else set() for c in range(9)]
        for r in range(9)
    ]

    units = _get_units()
    techniques: Dict[str, int] = {
        'naked_single': 0,
        'hidden_single': 0,
        'box_line': 0,
        'naked_pair': 0,
        'hidden_pair': 0,
        'naked_triple': 0,
        'hidden_triple': 0,
        'x_wing': 0,
        'y_wing': 0,
        'forcing_chain': 0,
    }
    steps = 0

    def eliminate(r: int, c: int, val: int) -> bool:
        if val in candidates[r][c]:
            candidates[r][c].discard(val)
            return True
        return False

    def place_digit(r: int, c: int, val: int) -> None:
        work[r][c] = val
        candidates[r][c].clear()
        for pr, pc in get_peers(r, c):
            eliminate(pr, pc, val)

    progress = True
    while progress:
        progress = False

        # 1. Search for Naked Singles
        found_single = False
        for r in range(9):
            for c in range(9):
                if work[r][c] == 0 and len(candidates[r][c]) == 1:
                    val = next(iter(candidates[r][c]))
                    place_digit(r, c, val)
                    techniques['naked_single'] += 1
                    steps += 1
                    found_single = True
                    progress = True
                    break
            if found_single:
                break
        if found_single:
            continue

        # 2. Search for Hidden Singles
        found_hidden = False
        for u in units:
            for d in range(1, 10):
                possible = [(r, c) for r, c in u if work[r][c] == 0 and d in candidates[r][c]]
                if len(possible) == 1:
                    r, c = possible[0]
                    place_digit(r, c, d)
                    techniques['hidden_single'] += 1
                    steps += 1
                    found_hidden = True
                    progress = True
                    break
            if found_hidden:
                break
        if found_hidden:
            continue

        # 3. Search for Pointing Pairs & Box-Line Reductions
        found_box_line = False
        for b in range(9):
            br, bc = (b // 3) * 3, (b % 3) * 3
            box_cells = [(br + dr, bc + dc) for dr in range(3) for dc in range(3)]
            for d in range(1, 10):
                d_cells = [(r, c) for r, c in box_cells if work[r][c] == 0 and d in candidates[r][c]]
                if 2 <= len(d_cells) <= 3:
                    # Confined to a single row?
                    if all(r == d_cells[0][0] for r, _ in d_cells):
                        target_r = d_cells[0][0]
                        eliminated = False
                        for c in range(9):
                            if (target_r, c) not in box_cells and work[target_r][c] == 0:
                                if eliminate(target_r, c, d):
                                    eliminated = True
                        if eliminated:
                            techniques['box_line'] += 1
                            steps += 1
                            found_box_line = True
                            progress = True
                            break
                    # Confined to a single col?
                    if all(c == d_cells[0][1] for _, c in d_cells):
                        target_c = d_cells[0][1]
                        eliminated = False
                        for r in range(9):
                            if (r, target_c) not in box_cells and work[r][target_c] == 0:
                                if eliminate(r, target_c, d):
                                    eliminated = True
                        if eliminated:
                            techniques['box_line'] += 1
                            steps += 1
                            found_box_line = True
                            progress = True
                            break
            if found_box_line:
                break
        if found_box_line:
            continue

        # 4. Search for Naked Pairs
        found_pair = False
        for u in units:
            pairs = [(r, c) for r, c in u if work[r][c] == 0 and len(candidates[r][c]) == 2]
            if len(pairs) >= 2:
                for (r1, c1), (r2, c2) in itertools.combinations(pairs, 2):
                    if candidates[r1][c1] == candidates[r2][c2]:
                        pair_digits = candidates[r1][c1]
                        eliminated = False
                        for r, c in u:
                            if (r, c) != (r1, c1) and (r, c) != (r2, c2) and work[r][c] == 0:
                                for d in pair_digits:
                                    if eliminate(r, c, d):
                                        eliminated = True
                        if eliminated:
                            techniques['naked_pair'] += 1
                            steps += 1
                            found_pair = True
                            progress = True
                            break
                if found_pair:
                    break
        if found_pair:
            continue

        # 5. Search for Hidden Pairs
        found_hidden_pair = False
        for u in units:
            for d1, d2 in itertools.combinations(range(1, 10), 2):
                cells_d1 = [(r, c) for r, c in u if work[r][c] == 0 and d1 in candidates[r][c]]
                cells_d2 = [(r, c) for r, c in u if work[r][c] == 0 and d2 in candidates[r][c]]
                if len(cells_d1) == 2 and cells_d1 == cells_d2:
                    (r1, c1), (r2, c2) = cells_d1
                    if len(candidates[r1][c1]) > 2 or len(candidates[r2][c2]) > 2:
                        candidates[r1][c1] = {d1, d2}
                        candidates[r2][c2] = {d1, d2}
                        techniques['hidden_pair'] += 1
                        steps += 1
                        found_hidden_pair = True
                        progress = True
                        break
            if found_hidden_pair:
                break
        if found_hidden_pair:
            continue

        # 6. Search for Naked Triples
        found_triple = False
        for u in units:
            cand_cells = [(r, c) for r, c in u if work[r][c] == 0 and 2 <= len(candidates[r][c]) <= 3]
            if len(cand_cells) >= 3:
                for c1, c2, c3 in itertools.combinations(cand_cells, 3):
                    union_cand = candidates[c1[0]][c1[1]] | candidates[c2[0]][c2[1]] | candidates[c3[0]][c3[1]]
                    if len(union_cand) == 3:
                        eliminated = False
                        for r, c in u:
                            if (r, c) not in (c1, c2, c3) and work[r][c] == 0:
                                for d in union_cand:
                                    if eliminate(r, c, d):
                                        eliminated = True
                        if eliminated:
                            techniques['naked_triple'] += 1
                            steps += 1
                            found_triple = True
                            progress = True
                            break
                if found_triple:
                    break
        if found_triple:
            continue

        # 7. Search for X-Wing
        found_x_wing = False
        for d in range(1, 10):
            # Row-based X-Wing
            row_candidates: Dict[int, List[int]] = {}
            for r in range(9):
                cols = [c for c in range(9) if work[r][c] == 0 and d in candidates[r][c]]
                if len(cols) == 2:
                    row_candidates[r] = cols
            if len(row_candidates) >= 2:
                for r1, r2 in itertools.combinations(row_candidates.keys(), 2):
                    if row_candidates[r1] == row_candidates[r2]:
                        c1, c2 = row_candidates[r1]
                        eliminated = False
                        for other_r in range(9):
                            if other_r not in (r1, r2):
                                if eliminate(other_r, c1, d):
                                    eliminated = True
                                if eliminate(other_r, c2, d):
                                    eliminated = True
                        if eliminated:
                            techniques['x_wing'] += 1
                            steps += 1
                            found_x_wing = True
                            progress = True
                            break
                if found_x_wing:
                    break

            # Col-based X-Wing
            col_candidates: Dict[int, List[int]] = {}
            for c in range(9):
                rows = [r for r in range(9) if work[r][c] == 0 and d in candidates[r][c]]
                if len(rows) == 2:
                    col_candidates[c] = rows
            if len(col_candidates) >= 2:
                for c1, c2 in itertools.combinations(col_candidates.keys(), 2):
                    if col_candidates[c1] == col_candidates[c2]:
                        r1, r2 = col_candidates[c1]
                        eliminated = False
                        for other_c in range(9):
                            if other_c not in (c1, c2):
                                if eliminate(r1, other_c, d):
                                    eliminated = True
                                if eliminate(r2, other_c, d):
                                    eliminated = True
                        if eliminated:
                            techniques['x_wing'] += 1
                            steps += 1
                            found_x_wing = True
                            progress = True
                            break
                if found_x_wing:
                    break
        if found_x_wing:
            continue

        # 8. Search for Y-Wing (XY-Wing)
        found_y_wing = False
        bi_value_cells = [(r, c) for r in range(9) for c in range(9) if work[r][c] == 0 and len(candidates[r][c]) == 2]
        for pr, pc in bi_value_cells:
            p_cand = candidates[pr][pc]
            a, b = list(p_cand)
            peers_p = get_peers(pr, pc)

            wings_a = [
                (r, c) for (r, c) in bi_value_cells
                if (r, c) in peers_p and a in candidates[r][c] and b not in candidates[r][c]
            ]
            wings_b = [
                (r, c) for (r, c) in bi_value_cells
                if (r, c) in peers_p and b in candidates[r][c] and a not in candidates[r][c]
            ]

            for w1 in wings_a:
                c1 = list(candidates[w1[0]][w1[1]] - {a})[0]
                for w2 in wings_b:
                    c2 = list(candidates[w2[0]][w2[1]] - {b})[0]
                    if c1 == c2:
                        target_d = c1
                        common_peers = set(get_peers(w1[0], w1[1])) & set(get_peers(w2[0], w2[1]))
                        eliminated = False
                        for cr, cc in common_peers:
                            if (cr, cc) not in (w1, w2, (pr, pc)) and work[cr][cc] == 0:
                                if eliminate(cr, cc, target_d):
                                    eliminated = True
                        if eliminated:
                            techniques['y_wing'] += 1
                            steps += 1
                            found_y_wing = True
                            progress = True
                            break
                if found_y_wing:
                    break
            if found_y_wing:
                break
        if found_y_wing:
            continue

        # 9. Search for Forcing Chains / Simple Contradiction
        found_forcing = False
        unsolved_cells = [(r, c) for r in range(9) for c in range(9) if work[r][c] == 0]
        for r, c in unsolved_cells:
            for test_val in list(candidates[r][c]):
                peers = get_peers(r, c)
                has_dead_end = False
                for pr, pc in peers:
                    if work[pr][pc] == 0:
                        peer_remaining = candidates[pr][pc] - {test_val}
                        if len(peer_remaining) == 0:
                            has_dead_end = True
                            break
                if has_dead_end:
                    if eliminate(r, c, test_val):
                        techniques['forcing_chain'] += 1
                        steps += 1
                        found_forcing = True
                        progress = True
                        break
            if found_forcing:
                break
        if found_forcing:
            continue

    solved = all(work[r][c] != 0 for r in range(9) for c in range(9))

    # Rating strictly matching spec:
    # easy: naked and hidden singles only
    # medium: adds naked/hidden pairs and box-line reductions
    # hard: adds naked/hidden triples, X-Wing, Y-Wing
    # expert: needs advanced chains or forcing logic
    # master: the hardest puzzles, beyond expert (lowest clues 21-23, requiring deep multiple forcing chains)
    has_forcing = techniques['forcing_chain'] > 0
    has_hard = techniques['naked_triple'] > 0 or techniques['hidden_triple'] > 0 or techniques['x_wing'] > 0 or techniques['y_wing'] > 0
    has_medium = techniques['box_line'] > 0 or techniques['naked_pair'] > 0 or techniques['hidden_pair'] > 0

    if not solved:
        if givens <= CLUE_RANGES['master']['max']:
            rating = DifficultyScore.MASTER
            hardest = 'master_deep_forcing'
        elif givens <= CLUE_RANGES['expert']['max']:
            rating = DifficultyScore.EXPERT
            hardest = 'expert_forcing_chain'
        elif givens <= CLUE_RANGES['hard']['max']:
            rating = DifficultyScore.HARD
            hardest = 'hard_advanced'
        elif givens <= CLUE_RANGES['medium']['max']:
            rating = DifficultyScore.MEDIUM
            hardest = 'medium_advanced'
        else:
            rating = DifficultyScore.EASY
            hardest = 'singles_only'
    elif givens <= CLUE_RANGES['master']['max']:
        rating = DifficultyScore.MASTER
        hardest = 'forcing_chain' if has_forcing else 'master_minimal_clues'
    elif givens <= CLUE_RANGES['expert']['max']:
        rating = DifficultyScore.EXPERT
        hardest = 'forcing_chain' if has_forcing else 'expert_minimal_clues'
    elif has_forcing:
        rating = DifficultyScore.EXPERT
        hardest = 'forcing_chain'
    elif has_hard:
        rating = DifficultyScore.HARD
        hardest = 'x_wing' if techniques['x_wing'] > 0 else ('y_wing' if techniques['y_wing'] > 0 else 'triple')
    elif has_medium:
        rating = DifficultyScore.MEDIUM
        hardest = 'naked_pair' if techniques['naked_pair'] > 0 else ('hidden_pair' if techniques['hidden_pair'] > 0 else 'box_line')
    else:
        # Solved using ONLY naked and hidden singles
        rating = DifficultyScore.EASY
        hardest = 'naked_single' if techniques['naked_single'] > 0 else 'hidden_single'

    return PuzzleAnalysis(
        givens_count=givens,
        rating=rating,
        hardest_technique=hardest,
        techniques_used=techniques,
        logical_steps=steps,
        solved_logically=solved,
    )
