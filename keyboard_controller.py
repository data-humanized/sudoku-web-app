"""
keyboard_controller.py
Desktop Keyboard Navigation and Shortcut Dispatcher for ZenSudoku in Python.

Keybindings:
- 1-9: Place digit (or toggle pencil note if in notes mode)
- Backspace / Delete: Erase selected cell (pencil note or placed digit)
- N: Toggle pencil notes mode
- U: Undo last move
- R: Redo move
- H: Request hint
- Arrow keys (Up, Down, Left, Right): Navigate 9x9 grid coordinates
- Escape: Deselect cell or return to home
- Space / P: Toggle timer pause
"""

from __future__ import annotations
from typing import Callable, Dict, Optional, Tuple


class KeyboardAction:
    DIGIT = "digit"
    ERASE = "erase"
    TOGGLE_NOTES = "toggle_notes"
    UNDO = "undo"
    REDO = "redo"
    HINT = "hint"
    NAVIGATE = "navigate"
    ESCAPE = "escape"
    TOGGLE_PAUSE = "toggle_pause"


class KeyboardController:
    def __init__(
        self,
        on_digit: Optional[Callable[[int], None]] = None,
        on_erase: Optional[Callable[[], None]] = None,
        on_toggle_notes: Optional[Callable[[], None]] = None,
        on_undo: Optional[Callable[[], None]] = None,
        on_redo: Optional[Callable[[], None]] = None,
        on_hint: Optional[Callable[[], None]] = None,
        on_move_selection: Optional[Callable[[int, int], None]] = None,
        on_escape: Optional[Callable[[], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
    ):
        self.on_digit = on_digit
        self.on_erase = on_erase
        self.on_toggle_notes = on_toggle_notes
        self.on_undo = on_undo
        self.on_redo = on_redo
        self.on_hint = on_hint
        self.on_move_selection = on_move_selection
        self.on_escape = on_escape
        self.on_pause = on_pause

    def dispatch_key(self, key: str, ctrl_or_cmd: bool = False, shift: bool = False) -> Optional[str]:
        """Dispatches keyboard events and triggers mapped game callbacks."""
        k = key.lower()

        # Undo / Redo shortcuts (Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y)
        if ctrl_or_cmd:
            if k == 'z' and shift:
                if self.on_redo: self.on_redo()
                return KeyboardAction.REDO
            elif k == 'z':
                if self.on_undo: self.on_undo()
                return KeyboardAction.UNDO
            elif k == 'y':
                if self.on_redo: self.on_redo()
                return KeyboardAction.REDO

        # Digits 1-9
        if k in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
            digit = int(k)
            if self.on_digit: self.on_digit(digit)
            return KeyboardAction.DIGIT

        # Erase
        if k in ('backspace', 'delete', 'del'):
            if self.on_erase: self.on_erase()
            return KeyboardAction.ERASE

        # Tool toggles
        if k == 'n':
            if self.on_toggle_notes: self.on_toggle_notes()
            return KeyboardAction.TOGGLE_NOTES
        if k == 'u':
            if self.on_undo: self.on_undo()
            return KeyboardAction.UNDO
        if k == 'r':
            if self.on_redo: self.on_redo()
            return KeyboardAction.REDO
        if k == 'h':
            if self.on_hint: self.on_hint()
            return KeyboardAction.HINT
        if k in ('escape', 'esc'):
            if self.on_escape: self.on_escape()
            return KeyboardAction.ESCAPE
        if k in ('p', ' '):
            if self.on_pause: self.on_pause()
            return KeyboardAction.TOGGLE_PAUSE

        # Arrow navigations
        if k == 'arrowup':
            if self.on_move_selection: self.on_move_selection(-1, 0)
            return KeyboardAction.NAVIGATE
        if k == 'arrowdown':
            if self.on_move_selection: self.on_move_selection(1, 0)
            return KeyboardAction.NAVIGATE
        if k == 'arrowleft':
            if self.on_move_selection: self.on_move_selection(0, -1)
            return KeyboardAction.NAVIGATE
        if k == 'arrowright':
            if self.on_move_selection: self.on_move_selection(0, 1)
            return KeyboardAction.NAVIGATE

        return None
