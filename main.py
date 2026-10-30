"""
main.py
Main application entry point for ZenSudoku written in Python using NiceGUI.
Full desktop & mobile web experience with pure Python state management and UI.
"""

from __future__ import annotations
import math
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from nicegui import app, ui

from sudoku_logic import (
    DEFAULT_SETTINGS,
    Difficulty,
    GameState,
    Grid,
    HistoryRecord,
    MoveAction,
    Notes,
    UserSettings,
    calculate_daily_score,
    calculate_score,
    calculate_streak,
    clone_bool_grid,
    clone_grid,
    clone_notes,
    create_empty_bool_grid,
    create_empty_notes,
    get_candidates,
    get_level_unlock_status,
    get_new_puzzle,
    get_peers,
    is_cell_locked,
)
from storage import (
    ZenSudokuStorage,
    create_backup_binary,
    load_zen_data,
    save_zen_data,
    validate_and_parse_backup,
)
from sound_effects import sounds
from components.header import render_home_header, render_in_game_header
from components.home import render_home_screen
from components.grid import render_sudoku_grid
from components.controls import (
    render_number_pad_row,
    render_tool_buttons_row,
)
from components.modals import (
    show_analytics_modal,
    show_completion_modal,
    show_lives_modal,
    show_settings_modal,
)


class ZenSudokuApp:
    def __init__(self):
        # Persistence
        self.storage = load_zen_data()
        self.history: List[HistoryRecord] = self.storage.history
        self.settings: UserSettings = self.storage.settings
        self.active_game: Optional[GameState] = self.storage.active_game

        # View and interaction state
        self.current_view: str = 'home' if not self.active_game else 'game'
        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)
        self.is_notes_mode: bool = False
        self.is_loading_puzzle: bool = False

        # Sound effects sync
        sounds.enabled = self.settings.get('sound_effects', True)

    def get_today_iso(self) -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m-%d')

    def sync_storage(self) -> None:
        self.storage.history = self.history
        self.storage.active_game = self.active_game
        self.storage.settings = self.settings
        save_zen_data(self.storage)

    def start_new_game(self, level: Difficulty) -> None:
        """Starts a new puzzle generated separately for the given level."""
        self.is_loading_puzzle = True
        self.render_ui.refresh()

        puzzle_data = get_new_puzzle(level)
        puzzle = puzzle_data['puzzle']
        solution = puzzle_data['solution']

        new_game: GameState = {
            'id': f"game-{int(time.time())}",
            'level': level,
            'initial_grid': puzzle,
            'solution_grid': solution,
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
            'start_time': int(time.time()),
        }
        self.active_game = new_game
        self.selected_cell = (0, 0)
        self.is_notes_mode = False
        self.is_loading_puzzle = False
        self.current_view = 'game'
        self.sync_storage()
        self.render_ui.refresh()

    def handle_cell_select(self, row: int, col: int) -> None:
        """Tapping any cell (including locked cells) selects it and highlights matching digits."""
        self.selected_cell = (row, col)
        self.render_ui.refresh()

    def handle_digit_input(self, digit: int) -> None:
        """
        Handles digit or note input:
        - When a cell has a correct digit (matches solution), it is locked.
        - Typing another digit in a locked cell does nothing.
        - Pencil notes cannot be added to a locked cell.
        - Wrong digits can be typed over.
        - Placing a correct digit clears that digit from peer pencil notes in row, column, and box.
        """
        if not self.active_game or self.active_game['is_completed'] or self.active_game['is_paused']:
            return
        if not self.selected_cell:
            return

        r, c = self.selected_cell
        game = self.active_game

        # Rule: Once a digit matches the stored solution, the cell is locked.
        # Typing another digit or pencil note in a locked cell does nothing.
        if is_cell_locked(game, r, c):
            return

        if self.is_notes_mode:
            # Notes Mode: Only allowed in unfilled cells
            if game['current_grid'][r][c] != 0:
                return

            prev_notes = list(game['notes'][r][c])
            new_notes_set = set(prev_notes)
            if digit in new_notes_set:
                new_notes_set.remove(digit)
            else:
                new_notes_set.add(digit)
            new_notes = list(new_notes_set)

            move: MoveAction = {
                'action_type': 'note',
                'row': r,
                'col': c,
                'prev_val': 0,
                'new_val': 0,
                'prev_notes': prev_notes,
                'new_notes': new_notes,
                'peer_notes_changes': None,
            }
            game['undo_stack'].append(move)
            game['redo_stack'].clear()
            game['notes'][r][c] = new_notes_set
            self.sync_storage()
            self.render_ui.refresh()
            return

        # Placement Mode
        prev_val = game['current_grid'][r][c]
        if prev_val == digit:
            return

        correct_val = game['solution_grid'][r][c]
        if digit != correct_val:
            # Mistake! Show digit in red (#dc2626) and play wrong-digit sound; NO shake or wobble
            game['mistakes'] += 1
            prev_notes = list(game['notes'][r][c])
            game['current_grid'][r][c] = digit

            # Record editable wrong-digit action
            move: MoveAction = {
                'action_type': 'wrong_digit',
                'row': r,
                'col': c,
                'prev_val': prev_val,
                'new_val': digit,
                'prev_notes': prev_notes,
                'new_notes': prev_notes,
                'peer_notes_changes': None,
            }
            game['undo_stack'].append(move)
            game['redo_stack'].clear()

            js_sound = sounds.get_sound_js('wrong_digit')
            if js_sound:
                ui.run_javascript(js_sound)

            if game['mistakes'] >= 3:
                self.sync_storage()
                self.render_ui.refresh()
                show_lives_modal(
                    on_restart=lambda: self.start_new_game(game['level']),
                    on_go_home=self.go_home,
                )
                return

            self.sync_storage()
            self.render_ui.refresh()
            return

        # Correct Digit Placed: Cell becomes locked
        # Play clean tick/pop sound
        js_sound = sounds.get_sound_js('correct')
        if js_sound:
            ui.run_javascript(js_sound)

        game['current_grid'][r][c] = digit
        game['notes'][r][c].clear()

        # Rule: When a correct digit is placed, remove that digit from the pencil notes
        # of every cell in its row, column, and 3x3 block.
        for pr, pc in get_peers(r, c):
            game['notes'][pr][pc].discard(digit)

        # Clear redo stack upon placing a new valid digit
        game['redo_stack'].clear()

        # Check for victory
        is_won = all(
            game['current_grid'][row_idx][col_idx] == game['solution_grid'][row_idx][col_idx]
            for row_idx in range(9)
            for col_idx in range(9)
        )

        if is_won:
            self.complete_game()
            return

        self.sync_storage()
        self.render_ui.refresh()

    def handle_erase(self) -> None:
        """
        Handles Erase button:
        - The Erase button on a locked cell does nothing and plays NO sound.
        - On an editable cell (wrong digit or pencil notes), clears it, records undo,
          and plays the pencil scribble sound.
        """
        if not self.active_game or not self.selected_cell or self.active_game['is_completed']:
            return
        r, c = self.selected_cell
        game = self.active_game

        # Rule: The Erase button on a locked cell does nothing and plays NO sound.
        if is_cell_locked(game, r, c):
            return

        prev_val = game['current_grid'][r][c]
        prev_notes = list(game['notes'][r][c])

        if prev_val == 0 and not prev_notes:
            return

        move: MoveAction = {
            'action_type': 'erase',
            'row': r,
            'col': c,
            'prev_val': prev_val,
            'new_val': 0,
            'prev_notes': prev_notes,
            'new_notes': [],
            'peer_notes_changes': None,
        }
        game['undo_stack'].append(move)
        game['redo_stack'].clear()

        game['current_grid'][r][c] = 0
        game['notes'][r][c].clear()

        # Trigger pencil scribbling sound only for editable cells
        js_sound = sounds.get_sound_js('erase')
        if js_sound:
            ui.run_javascript(js_sound)

        self.sync_storage()
        self.render_ui.refresh()

    def handle_undo(self) -> None:
        """
        Undo applies ONLY to pencil notes and wrong digits.
        Undo must never remove a correct digit.
        If the last action was placing a correct digit, undo skips back to the
        most recent editable action. If there are no editable actions, undo does nothing.
        """
        if not self.active_game or not self.active_game['undo_stack'] or self.active_game['is_completed']:
            return
        game = self.active_game

        editable_idx = None
        for i in range(len(game['undo_stack']) - 1, -1, -1):
            m = game['undo_stack'][i]
            r, c = m['row'], m['col']
            # If the cell is locked with a correct digit, it cannot be undone
            if is_cell_locked(game, r, c) and m['action_type'] != 'note':
                continue
            editable_idx = i
            break

        if editable_idx is None:
            return

        move = game['undo_stack'].pop(editable_idx)
        game['redo_stack'].append(move)

        r, c = move['row'], move['col']
        if not is_cell_locked(game, r, c):
            game['current_grid'][r][c] = move['prev_val']
        game['notes'][r][c] = set(move['prev_notes'])

        if move.get('peer_notes_changes'):
            for ch in move['peer_notes_changes']:
                if not is_cell_locked(game, ch['row'], ch['col']):
                    game['notes'][ch['row']][ch['col']].add(ch['digit'])

        self.selected_cell = (r, c)
        self.sync_storage()
        self.render_ui.refresh()

    def handle_redo(self) -> None:
        """
        Redo applies ONLY to pencil notes and wrong digits.
        Redo must never alter or remove a correct digit.
        """
        if not self.active_game or not self.active_game['redo_stack'] or self.active_game['is_completed']:
            return
        game = self.active_game

        editable_idx = None
        for i in range(len(game['redo_stack']) - 1, -1, -1):
            m = game['redo_stack'][i]
            r, c = m['row'], m['col']
            if is_cell_locked(game, r, c) and m['action_type'] != 'note':
                continue
            editable_idx = i
            break

        if editable_idx is None:
            return

        move = game['redo_stack'].pop(editable_idx)
        game['undo_stack'].append(move)

        r, c = move['row'], move['col']
        if not is_cell_locked(game, r, c):
            game['current_grid'][r][c] = move['new_val']
        game['notes'][r][c] = set(move['new_notes'])

        if move.get('peer_notes_changes'):
            for ch in move['peer_notes_changes']:
                game['notes'][ch['row']][ch['col']].discard(ch['digit'])

        self.selected_cell = (r, c)
        self.sync_storage()
        self.render_ui.refresh()

    def handle_hint(self) -> None:
        if not self.active_game or self.active_game['is_completed']:
            return
        game = self.active_game

        # Find first empty or incorrect cell
        target = None
        for r in range(9):
            for c in range(9):
                if game['current_grid'][r][c] == 0 or game['current_grid'][r][c] != game['solution_grid'][r][c]:
                    target = (r, c)
                    break
            if target:
                break

        if not target:
            return

        r, c = target
        correct_val = game['solution_grid'][r][c]
        game['hints_used'] += 1
        game['hinted_cells'][r][c] = True
        game['current_grid'][r][c] = correct_val
        game['notes'][r][c].clear()

        # Remove from peers
        for pr, pc in get_peers(r, c):
            game['notes'][pr][pc].discard(correct_val)

        self.selected_cell = (r, c)

        # Check win
        if all(game['current_grid'][row_i][col_i] == game['solution_grid'][row_i][col_i] for row_i in range(9) for col_i in range(9)):
            self.complete_game()
            return

        self.sync_storage()
        self.render_ui.refresh()

    def complete_game(self) -> None:
        if not self.active_game:
            return
        game = self.active_game
        game['is_completed'] = True

        score = calculate_score(
            level=game['level'],
            elapsed_seconds=game['elapsed_seconds'],
            mistakes=game['mistakes'],
            hints_used=game['hints_used'],
        )

        record: HistoryRecord = {
            'id': game['id'],
            'date': self.get_today_iso(),
            'level': game['level'],
            'score': score,
            'timeSeconds': game['elapsed_seconds'],
            'mistakes': game['mistakes'],
            'hintsUsed': game['hints_used'],
            'won': True,
        }
        self.history.append(record)
        self.active_game = None
        self.sync_storage()
        self.render_ui.refresh()

        show_completion_modal(
            level=record['level'],
            score=record['score'],
            elapsed_seconds=record['timeSeconds'],
            mistakes=record['mistakes'],
            hints_used=record['hintsUsed'],
            on_play_again=lambda: self.start_new_game(record['level']),
            on_go_home=self.go_home,
        )

    def go_home(self) -> None:
        self.current_view = 'home'
        self.render_ui.refresh()

    def toggle_notes_mode(self) -> None:
        self.is_notes_mode = not self.is_notes_mode
        self.render_ui.refresh()

    def toggle_pause(self) -> None:
        if self.active_game:
            self.active_game['is_paused'] = not self.active_game['is_paused']
            self.render_ui.refresh()

    def reset_all(self) -> None:
        self.history.clear()
        self.active_game = None
        self.settings = dict(DEFAULT_SETTINGS)
        self.current_view = 'home'
        self.sync_storage()
        self.render_ui.refresh()
        ui.notify('All progress reset to defaults', type='info')

    def restore_backup(self, records: List[HistoryRecord], restored_settings: UserSettings) -> None:
        self.history = records
        self.settings = restored_settings
        self.active_game = None
        sounds.enabled = self.settings.get('sound_effects', True)
        self.current_view = 'home'
        self.sync_storage()
        self.render_ui.refresh()

    @ui.refreshable
    def render_ui(self) -> None:
        ui.add_head_html(sounds.WEB_AUDIO_JS)

        if self.current_view == 'home':
            render_home_header(
                on_open_analytics=lambda: show_analytics_modal(self.history),
                on_open_settings=lambda: show_settings_modal(
                    self.storage,
                    on_settings_change=lambda s: setattr(self, 'settings', s) or self.sync_storage(),
                    on_restore_backup=self.restore_backup,
                    on_reset_all=self.reset_all,
                ),
            )
            render_home_screen(
                history=self.history,
                active_game=self.active_game,
                on_start_game=self.start_new_game,
                on_resume_game=lambda: setattr(self, 'current_view', 'game') or self.render_ui.refresh(),
            )
        else:
            if not self.active_game:
                self.current_view = 'home'
                self.render_ui.refresh()
                return

            render_in_game_header(
                game=self.active_game,
                on_home=self.go_home,
                on_toggle_pause=self.toggle_pause,
                on_open_settings=lambda: show_settings_modal(
                    self.storage,
                    on_settings_change=lambda s: setattr(self, 'settings', s) or self.sync_storage(),
                    on_restore_backup=self.restore_backup,
                    on_reset_all=self.reset_all,
                ),
            )
            render_sudoku_grid(
                game=self.active_game,
                selected_cell=self.selected_cell,
                on_cell_select=self.handle_cell_select,
            )
            render_tool_buttons_row(
                game=self.active_game,
                is_notes_mode=self.is_notes_mode,
                on_undo=self.handle_undo,
                on_redo=self.handle_redo,
                on_erase=self.handle_erase,
                on_toggle_notes=self.toggle_notes_mode,
                on_hint=self.handle_hint,
            )
            render_number_pad_row(
                game=self.active_game,
                on_digit_input=self.handle_digit_input,
            )


@ui.page('/')
def index_page():
    sudoku_app = ZenSudokuApp()
    sudoku_app.render_ui()

    # Timer tick every 1 second
    def on_tick():
        if sudoku_app.active_game and not sudoku_app.active_game['is_paused'] and not sudoku_app.active_game['is_completed']:
            sudoku_app.active_game['elapsed_seconds'] += 1
            if sudoku_app.active_game['elapsed_seconds'] % 5 == 0:
                sudoku_app.sync_storage()
            sudoku_app.render_ui.refresh()

    ui.timer(1.0, on_tick)


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(
        title='ZenSudoku - Minimalist Sudoku Desktop',
        favicon='🎯',
        port=3000,
        reload=False,
    )
