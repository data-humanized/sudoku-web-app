"""
state_machine.py
State Machine and Action History Ledger for ZenSudoku in Python.

Manages:
- Transactional game moves (digit placement, pencil note toggle, cell erasure)
- Undo and Redo command execution with candidate restoration
- Automated note clearing on digit placements
- Game completion verification
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from sudoku_logic import (
    GameState,
    MoveAction,
    clone_bool_grid,
    clone_grid,
    clone_notes,
    get_peers,
)


class GameStateMachine:
    def __init__(self, game_state: GameState, auto_remove_notes: bool = True):
        self.game = game_state
        self.auto_remove_notes = auto_remove_notes

    def apply_digit(self, row: int, col: int, digit: int) -> Dict[str, Any]:
        """Applies a placed digit with mistake detection and peer note eviction."""
        if self.game['initial_grid'][row][col] != 0:
            return {'success': False, 'reason': 'initial_cell'}

        correct = self.game['solution_grid'][row][col]
        if digit != correct:
            self.game['mistakes'] += 1
            return {
                'success': False,
                'is_mistake': True,
                'mistakes_count': self.game['mistakes'],
                'game_over': self.game['mistakes'] >= 3,
            }

        prev_val = self.game['current_grid'][row][col]
        prev_notes = list(self.game['notes'][row][col])

        self.game['current_grid'][row][col] = digit
        self.game['notes'][row][col].clear()

        peer_changes = []
        if self.auto_remove_notes:
            for pr, pc in get_peers(row, col):
                if digit in self.game['notes'][pr][pc]:
                    self.game['notes'][pr][pc].remove(digit)
                    peer_changes.append({'row': pr, 'col': pc, 'digit': digit})

        move: MoveAction = {
            'action_type': 'digit',
            'row': row,
            'col': col,
            'prev_val': prev_val,
            'new_val': digit,
            'prev_notes': prev_notes,
            'new_notes': [],
            'peer_notes_changes': peer_changes,
        }
        self.game['undo_stack'].append(move)
        self.game['redo_stack'].clear()

        is_completed = self.check_completed()
        return {
            'success': True,
            'is_mistake': False,
            'is_completed': is_completed,
        }

    def toggle_note(self, row: int, col: int, digit: int) -> Dict[str, Any]:
        """Toggles pencil note candidate inside selected cell."""
        if self.game['initial_grid'][row][col] != 0 or self.game['current_grid'][row][col] != 0:
            return {'success': False, 'reason': 'cell_not_empty'}

        prev_notes = list(self.game['notes'][row][col])
        current_set = set(prev_notes)
        if digit in current_set:
            current_set.remove(digit)
        else:
            current_set.add(digit)
        new_notes = list(current_set)

        self.game['notes'][row][col] = current_set

        move: MoveAction = {
            'action_type': 'note',
            'row': row,
            'col': col,
            'prev_val': 0,
            'new_val': 0,
            'prev_notes': prev_notes,
            'new_notes': new_notes,
            'peer_notes_changes': None,
        }
        self.game['undo_stack'].append(move)
        self.game['redo_stack'].clear()
        return {'success': True, 'new_notes': new_notes}

    def erase_cell(self, row: int, col: int) -> Dict[str, Any]:
        """Erases either cell value or pencil notes."""
        if self.game['initial_grid'][row][col] != 0:
            return {'success': False, 'reason': 'initial_cell'}

        prev_val = self.game['current_grid'][row][col]
        prev_notes = list(self.game['notes'][row][col])

        if prev_val == 0 and not prev_notes:
            return {'success': False, 'reason': 'already_empty'}

        self.game['current_grid'][row][col] = 0
        self.game['notes'][row][col].clear()

        move: MoveAction = {
            'action_type': 'erase',
            'row': row,
            'col': col,
            'prev_val': prev_val,
            'new_val': 0,
            'prev_notes': prev_notes,
            'new_notes': [],
            'peer_notes_changes': None,
        }
        self.game['undo_stack'].append(move)
        self.game['redo_stack'].clear()
        return {'success': True}

    def undo(self) -> Optional[MoveAction]:
        """Reverts the last action from undo stack."""
        if not self.game['undo_stack']:
            return None
        move = self.game['undo_stack'].pop()
        self.game['redo_stack'].append(move)

        r, c = move['row'], move['col']
        self.game['current_grid'][r][c] = move['prev_val']
        self.game['notes'][r][c] = set(move['prev_notes'])

        if move.get('peer_notes_changes'):
            for ch in move['peer_notes_changes']:
                self.game['notes'][ch['row']][ch['col']].add(ch['digit'])

        return move

    def redo(self) -> Optional[MoveAction]:
        """Re-applies the last undone action."""
        if not self.game['redo_stack']:
            return None
        move = self.game['redo_stack'].pop()
        self.game['undo_stack'].append(move)

        r, c = move['row'], move['col']
        self.game['current_grid'][r][c] = move['new_val']
        self.game['notes'][r][c] = set(move['new_notes'])

        if move.get('peer_notes_changes'):
            for ch in move['peer_notes_changes']:
                self.game['notes'][ch['row']][ch['col']].discard(ch['digit'])

        return move

    def check_completed(self) -> bool:
        """Verifies if the board matches the unique solution."""
        for r in range(9):
            for c in range(9):
                if self.game['current_grid'][r][c] != self.game['solution_grid'][r][c]:
                    return False
        self.game['is_completed'] = True
        return True
