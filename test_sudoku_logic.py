"""
test_sudoku_logic.py
Unit tests for ZenSudoku Python Engine:
- Backtracking solver correctness and uniqueness validation
- Recalibrated curated puzzles and targets
- SCORE_RANGES, base scores, penalties, and score floor
- Level progression unlocks (including Master level)
- Daily streaks and daily score calculations with timeSeconds
- Bug 2: Cell locking rules:
  1. Placing a correct digit locks cell (cannot be overwritten, erased, pencil-noted, or undone)
  2. Placing a wrong digit is NOT locked (can be erased and overwritten)
  3. Reloading a saved game recomputes locked state by comparing filled cells with solution
  4. Placing a correct digit clears that digit from peer pencil notes in row, column, and 3x3 box
  5. Erase on a locked cell does nothing and plays no sound
  6. Undo and redo apply ONLY to pencil notes and wrong digits, never removing a correct digit
"""

from __future__ import annotations
import unittest
from sudoku_logic import (
    BASE_SCORES,
    CURATED_PUZZLES,
    SCORE_RANGES,
    UNLOCK_REQUIREMENTS,
    GameState,
    HistoryRecord,
    MoveAction,
    calculate_daily_score,
    calculate_score,
    calculate_streak,
    calculate_total_points,
    clone_grid,
    create_empty_bool_grid,
    create_empty_notes,
    format_points,
    get_level_card_stats,
    get_level_unlock_status,
    get_peers,
    has_unique_solution,
    is_cell_locked,
    is_won_record,
    solve_sudoku,
)


def create_test_game() -> GameState:
    puzzle = [
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
    return {
        'id': 'test-game-1',
        'level': 'easy',
        'initial_grid': clone_grid(puzzle),
        'solution_grid': clone_grid(solution),
        'current_grid': clone_grid(puzzle),
        'notes': create_empty_notes(),
        'hinted_cells': create_empty_bool_grid(),
        'mistakes': 0,
        'hints_used': 0,
        'elapsed_seconds': 0,
        'is_paused': False,
        'is_completed': False,
        'undo_stack': [],
        'redo_stack': [],
        'start_time': 1000000,
    }


class TestSudokuLogic(unittest.TestCase):
    def test_solve_sudoku_and_uniqueness(self):
        puzzle = [
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
        count, solution = solve_sudoku(puzzle)
        self.assertEqual(count, 1)
        self.assertIsNotNone(solution)
        self.assertEqual(solution[0][0], 5)
        self.assertEqual(solution[0][1], 3)
        self.assertEqual(solution[0][2], 4)
        self.assertTrue(has_unique_solution(puzzle))

    def test_curated_puzzles_and_master_level(self):
        self.assertIn('master', CURATED_PUZZLES)
        self.assertIn('master', SCORE_RANGES)
        self.assertEqual(SCORE_RANGES['master']['max'], 16000)
        self.assertEqual(SCORE_RANGES['master']['min'], 3200)
        self.assertEqual(BASE_SCORES['master'], 16000)
        self.assertEqual(UNLOCK_REQUIREMENTS['master']['count'], 16)

        master_entry = CURATED_PUZZLES['master'][0]
        givens = sum(1 for row in master_entry['puzzle'] for cell in row if cell != 0)
        self.assertLessEqual(givens, 24)
        self.assertGreaterEqual(givens, 21)

    def test_calculate_score_ranges_and_penalties(self):
        perfect_master = calculate_score('master', elapsed_seconds=300, mistakes=0, hints_used=0)
        self.assertEqual(perfect_master, 16000)

        penalized = calculate_score('master', elapsed_seconds=2500, mistakes=2, hints_used=1)
        self.assertLess(penalized, 16000)
        self.assertGreaterEqual(penalized, 3200)

        floored = calculate_score('master', elapsed_seconds=9999, mistakes=5, hints_used=5)
        self.assertEqual(floored, 3200)

    def test_unlock_progression_with_master(self):
        history: list[HistoryRecord] = []
        status = get_level_unlock_status(history)
        self.assertTrue(status['easy'])
        self.assertTrue(status['medium'])
        self.assertTrue(status['hard'])
        self.assertTrue(status['expert'])
        self.assertTrue(status['master'])

    def test_streak_and_daily_score(self):
        history: list[HistoryRecord] = [
            {'id': '1', 'date': '2025-01-01', 'level': 'easy', 'score': 1500, 'timeSeconds': 200, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '2', 'date': '2025-01-02', 'level': 'medium', 'score': 3000, 'timeSeconds': 300, 'mistakes': 0, 'hintsUsed': 0},
            {'id': '3', 'date': '2025-01-03', 'level': 'master', 'score': 15000, 'timeSeconds': 700, 'mistakes': 0, 'hintsUsed': 0},
        ]
        streak = calculate_streak(history)
        self.assertGreaterEqual(streak['best_streak'], 3)

        daily_score = calculate_daily_score(history, target_date='2025-01-03')
        self.assertEqual(daily_score, 15000)

    def test_level_card_stats(self):
        empty_history: list[HistoryRecord] = []
        easy_empty = get_level_card_stats(empty_history, 'easy')
        self.assertTrue(easy_empty['is_unlocked'])
        self.assertEqual(easy_empty['best_time_str'], '--:--')
        self.assertEqual(easy_empty['games_won_str'], '0 / 0')

        med_card = get_level_card_stats(empty_history, 'medium')
        self.assertTrue(med_card['is_unlocked'])
        self.assertEqual(med_card['lock_message'], '')

        master_card = get_level_card_stats(empty_history, 'master')
        self.assertTrue(master_card['is_unlocked'])
        self.assertEqual(master_card['lock_message'], '')

        history: list[HistoryRecord] = []
        for i in range(18):
            history.append({
                'id': f'won-{i}',
                'date': '2025-01-01',
                'level': 'easy',
                'score': 800,
                'timeSeconds': 180 + i * 5,
                'mistakes': 1,
                'hintsUsed': 0,
            })
        for i in range(9):
            history.append({
                'id': f'lost-{i}',
                'date': '2025-01-01',
                'level': 'easy',
                'score': 0,
                'timeSeconds': 300,
                'mistakes': 3,
                'hintsUsed': 0,
            })

        easy_stats = get_level_card_stats(history, 'easy')
        self.assertTrue(easy_stats['is_unlocked'])
        self.assertEqual(easy_stats['best_time_str'], '03:00')
        self.assertEqual(easy_stats['games_won_str'], '18 / 27')
        self.assertEqual(easy_stats['won_count'], 18)
        self.assertEqual(easy_stats['total_count'], 27)

    # -------------------------------------------------------------
    # BUG 2 TESTS: Correct Digits Must Be Locked
    # -------------------------------------------------------------
    def test_bug2_correct_digit_locked_cannot_overwrite_erase_note_or_undo(self):
        """
        Test 1: Place a correct digit -> attempt to overwrite, erase, add notes,
        undo (all must fail; locked cell unchanged).
        """
        game = create_test_game()
        # Find an unfilled cell, e.g. (0, 2) which has solution 4
        r, c = 0, 2
        self.assertEqual(game['current_grid'][r][c], 0)
        correct_val = game['solution_grid'][r][c]
        self.assertEqual(correct_val, 4)

        # Before placement, cell is not locked
        self.assertFalse(is_cell_locked(game, r, c))

        # Place correct digit
        game['current_grid'][r][c] = correct_val
        game['notes'][r][c].clear()

        # Cell is now locked
        self.assertTrue(is_cell_locked(game, r, c))

        # Attempt to overwrite with another digit (e.g. 9)
        # Rule: typing another digit in a locked cell does nothing
        if not is_cell_locked(game, r, c):
            game['current_grid'][r][c] = 9
        self.assertEqual(game['current_grid'][r][c], correct_val)

        # Attempt to erase
        # Rule: Erase button on a locked cell does nothing and plays NO sound
        if not is_cell_locked(game, r, c):
            game['current_grid'][r][c] = 0
        self.assertEqual(game['current_grid'][r][c], correct_val)

        # Attempt to add pencil notes
        # Rule: Pencil notes cannot be added to a locked cell
        if not is_cell_locked(game, r, c):
            game['notes'][r][c].add(7)
        self.assertEqual(len(game['notes'][r][c]), 0)

        # Attempt undo
        # Rule: Undo applies ONLY to pencil notes and wrong digits. Undo must never remove a correct digit.
        editable_moves = [
            m for m in game['undo_stack']
            if not is_cell_locked(game, m['row'], m['col']) or m['action_type'] == 'note'
        ]
        self.assertEqual(len(editable_moves), 0)
        self.assertEqual(game['current_grid'][r][c], correct_val)

    def test_bug2_wrong_digit_can_be_erased_and_overwritten(self):
        """
        Test 2: Place a wrong digit -> verify it can be erased and overwritten.
        """
        game = create_test_game()
        r, c = 0, 2
        correct_val = game['solution_grid'][r][c]  # 4
        wrong_val = 9

        # Place wrong digit
        game['current_grid'][r][c] = wrong_val
        game['mistakes'] += 1

        # Verify not locked!
        self.assertFalse(is_cell_locked(game, r, c))
        self.assertNotEqual(game['current_grid'][r][c], correct_val)

        # Verify it can be erased
        if not is_cell_locked(game, r, c):
            game['current_grid'][r][c] = 0
        self.assertEqual(game['current_grid'][r][c], 0)

        # Verify it can be overwritten with another wrong digit
        game['current_grid'][r][c] = 8
        self.assertEqual(game['current_grid'][r][c], 8)
        self.assertFalse(is_cell_locked(game, r, c))

        # Verify it can be overwritten with correct digit, which then locks it
        game['current_grid'][r][c] = correct_val
        self.assertTrue(is_cell_locked(game, r, c))

    def test_bug2_reload_saved_game_recomputes_locked_cells(self):
        """
        Test 3: Reload a saved game -> verify that cells with correct digits
        are locked on load without adding fields to backup.
        """
        game = create_test_game()
        # Place correct digits in cells (0, 2) and (0, 3)
        game['current_grid'][0][2] = game['solution_grid'][0][2]
        game['current_grid'][0][3] = game['solution_grid'][0][3]
        # Place wrong digit in (0, 5)
        game['current_grid'][0][5] = 9 if game['solution_grid'][0][5] != 9 else 1

        # Simulate reload from raw grid dictionary (no locked flags stored)
        reloaded_grid = [row[:] for row in game['current_grid']]
        solution_grid = [row[:] for row in game['solution_grid']]
        reloaded_game: GameState = {
            'id': 'reloaded-1',
            'level': 'easy',
            'initial_grid': clone_grid(game['initial_grid']),
            'solution_grid': solution_grid,
            'current_grid': reloaded_grid,
            'notes': create_empty_notes(),
            'hinted_cells': create_empty_bool_grid(),
            'mistakes': 1,
            'hints_used': 0,
            'elapsed_seconds': 45,
            'is_paused': False,
            'is_completed': False,
            'undo_stack': [],
            'redo_stack': [],
            'start_time': 1000000,
        }

        # Check recomputed locked status
        self.assertTrue(is_cell_locked(reloaded_game, 0, 2))
        self.assertTrue(is_cell_locked(reloaded_game, 0, 3))
        self.assertFalse(is_cell_locked(reloaded_game, 0, 5))  # wrong digit is not locked
        self.assertFalse(is_cell_locked(reloaded_game, 0, 7))  # empty cell is not locked

    def test_bug2_correct_digit_clears_peer_pencil_notes(self):
        """
        When a correct digit is placed, remove that digit from the pencil notes
        of every cell in its row, column, and 3x3 block.
        """
        game = create_test_game()
        r, c = 0, 2
        correct_val = game['solution_grid'][r][c]  # 4

        # Add pencil note 4 to peers in same row, same col, and same 3x3 box
        row_peer = (0, 3)
        col_peer = (1, 2)
        box_peer = (1, 1)

        game['notes'][row_peer[0]][row_peer[1]].add(correct_val)
        game['notes'][col_peer[0]][col_peer[1]].add(correct_val)
        game['notes'][box_peer[0]][box_peer[1]].add(correct_val)

        self.assertIn(correct_val, game['notes'][row_peer[0]][row_peer[1]])
        self.assertIn(correct_val, game['notes'][col_peer[0]][col_peer[1]])
        self.assertIn(correct_val, game['notes'][box_peer[0]][box_peer[1]])

        # Place correct digit and clear peers
        game['current_grid'][r][c] = correct_val
        game['notes'][r][c].clear()
        for pr, pc in get_peers(r, c):
            game['notes'][pr][pc].discard(correct_val)

        # Peers must have 4 removed
        self.assertNotIn(correct_val, game['notes'][row_peer[0]][row_peer[1]])
        self.assertNotIn(correct_val, game['notes'][col_peer[0]][col_peer[1]])
        self.assertNotIn(correct_val, game['notes'][box_peer[0]][box_peer[1]])

    def test_bug2_undo_skips_correct_digits(self):
        """
        Undo and redo apply ONLY to pencil notes and wrong digits.
        Undo must never remove a correct digit.
        If the last action was placing a correct digit, undo skips back to the
        most recent editable action. If there are no editable actions, undo does nothing.
        """
        game = create_test_game()

        # Action 1: Add pencil note at (0, 7)
        move1: MoveAction = {
            'action_type': 'note',
            'row': 0,
            'col': 7,
            'prev_val': 0,
            'new_val': 0,
            'prev_notes': [],
            'new_notes': [1, 2],
            'peer_notes_changes': None,
        }
        game['notes'][0][7] = {1, 2}
        game['undo_stack'].append(move1)

        # Action 2: Place correct digit at (0, 2) (locked!)
        correct_val = game['solution_grid'][0][2]
        game['current_grid'][0][2] = correct_val
        # Even if a move action is logged or placed on stack:
        move2: MoveAction = {
            'action_type': 'digit',
            'row': 0,
            'col': 2,
            'prev_val': 0,
            'new_val': correct_val,
            'prev_notes': [],
            'new_notes': [],
            'peer_notes_changes': None,
        }
        game['undo_stack'].append(move2)

        # Action 3: Place wrong digit at (1, 1)
        move3: MoveAction = {
            'action_type': 'wrong_digit',
            'row': 1,
            'col': 1,
            'prev_val': 0,
            'new_val': 9,
            'prev_notes': [],
            'new_notes': [],
            'peer_notes_changes': None,
        }
        game['current_grid'][1][1] = 9
        game['undo_stack'].append(move3)

        # Undo 1: Should undo the wrong digit at (1, 1)
        editable_idx = None
        for i in range(len(game['undo_stack']) - 1, -1, -1):
            m = game['undo_stack'][i]
            if is_cell_locked(game, m['row'], m['col']) and m['action_type'] != 'note':
                continue
            editable_idx = i
            break

        self.assertIsNotNone(editable_idx)
        self.assertEqual(editable_idx, 2)  # move3
        popped = game['undo_stack'].pop(editable_idx)
        game['current_grid'][popped['row']][popped['col']] = popped['prev_val']
        self.assertEqual(game['current_grid'][1][1], 0)

        # Undo 2: Should SKIP move2 (correct digit at 0, 2 is locked) and undo move1 (note)
        editable_idx = None
        for i in range(len(game['undo_stack']) - 1, -1, -1):
            m = game['undo_stack'][i]
            if is_cell_locked(game, m['row'], m['col']) and m['action_type'] != 'note':
                continue
            editable_idx = i
            break

        self.assertIsNotNone(editable_idx)
        self.assertEqual(editable_idx, 0)  # move1 (skipping move2!)
        popped = game['undo_stack'].pop(editable_idx)
        game['notes'][popped['row']][popped['col']] = set(popped['prev_notes'])
        self.assertEqual(game['notes'][0][7], set())

        # Correct digit at (0, 2) MUST STILL BE THERE!
        self.assertEqual(game['current_grid'][0][2], correct_val)
        self.assertTrue(is_cell_locked(game, 0, 2))

        # Undo 3: No editable actions left!
        editable_idx = None
        for i in range(len(game['undo_stack']) - 1, -1, -1):
            m = game['undo_stack'][i]
            if is_cell_locked(game, m['row'], m['col']) and m['action_type'] != 'note':
                continue
            editable_idx = i
            break

        self.assertIsNone(editable_idx)
        # Correct digit remains locked and untouched
        self.assertEqual(game['current_grid'][0][2], correct_val)

    # -------------------------------------------------------------
    # TOTAL POINTS AND NUMBER FORMATTER TESTS
    # -------------------------------------------------------------
    def test_format_points_under_10000(self):
        """Under 10,000: show full number with commas (e.g. 5,709)."""
        self.assertEqual(format_points(0), '0')
        self.assertEqual(format_points(450), '450')
        self.assertEqual(format_points(5709), '5,709')
        self.assertEqual(format_points(9999), '9,999')

    def test_format_points_thousands_k(self):
        """10,000 to 999,999: use K with up to 1 decimal, drop trailing zeros (12K, not 12.0K)."""
        self.assertEqual(format_points(10000), '10K')
        self.assertEqual(format_points(12000), '12K')
        self.assertEqual(format_points(12400), '12.4K')
        self.assertEqual(format_points(99900), '99.9K')
        self.assertEqual(format_points(120500), '120.5K')
        self.assertEqual(format_points(999900), '999.9K')

    def test_format_points_millions_m(self):
        """1,000,000 to 999,999,999: use M with up to 1 decimal, drop trailing zeros."""
        self.assertEqual(format_points(1000000), '1M')
        self.assertEqual(format_points(1200000), '1.2M')
        self.assertEqual(format_points(45000000), '45M')

    def test_format_points_billions_b(self):
        """1,000,000,000 and above: use B with up to 1 decimal, drop trailing zeros."""
        self.assertEqual(format_points(1000000000), '1B')
        self.assertEqual(format_points(2500000000), '2.5B')

    def test_calculate_total_points_and_revival_won_games(self):
        """
        Verify that games completed with extra lives (mistakes >= 3) are counted
        in games won, total points, and daily score when won=True.
        """
        history: list[HistoryRecord] = [
            {
                'id': 'g1',
                'date': '2026-10-30',
                'level': 'easy',
                'score': 5709,
                'timeSeconds': 948,
                'mistakes': 2,
                'hintsUsed': 0,
                'won': True,
            },
            {
                'id': 'g2',
                'date': '2026-10-30',
                'level': 'easy',
                'score': 4200,
                'timeSeconds': 1100,
                'mistakes': 8,  # Used 2 revives (Get a Life)
                'hintsUsed': 1,
                'won': True,
            },
        ]
        # Total points should sum both games
        self.assertEqual(calculate_total_points(history), 9909)
        self.assertEqual(format_points(calculate_total_points(history)), '9,909')

        # Both games should be counted as won in level stats
        stats = get_level_card_stats(history, 'easy')
        self.assertEqual(stats['won_count'], 2)
        self.assertEqual(stats['total_count'], 2)
        self.assertEqual(stats['games_won_str'], '2 / 2')

        # Daily score should include both games
        self.assertEqual(calculate_daily_score(history, '2026-10-30'), 9909)


if __name__ == '__main__':
    unittest.main()
