"""
components/controls.py
In-Game Controls and Keypad Components for NiceGUI.
"""

from typing import Callable, Dict, List
from nicegui import ui
from sudoku_logic import GameState


def render_tool_buttons_row(
    game: GameState,
    is_notes_mode: bool,
    on_undo: Callable[[], None],
    on_redo: Callable[[], None],
    on_erase: Callable[[], None],
    on_toggle_notes: Callable[[], None],
    on_hint: Callable[[], None],
) -> None:
    can_undo = len(game['undo_stack']) > 0
    can_redo = len(game['redo_stack']) > 0

    with ui.row().classes('w-full max-w-[480px] mx-auto justify-between items-center py-2 px-1'):
        # Undo Button
        with ui.button(on_click=on_undo).props('flat dense').classes(
            f"flex-1 flex flex-col items-center gap-1 text-xs py-2 rounded-xl transition-colors "
            f"{'text-slate-700 hover:bg-slate-100' if can_undo else 'text-slate-300 pointer-events-none'}"
        ):
            ui.icon('undo', size='1.25rem')
            ui.label('Undo').classes('text-[11px] font-medium')

        # Redo Button
        with ui.button(on_click=on_redo).props('flat dense').classes(
            f"flex-1 flex flex-col items-center gap-1 text-xs py-2 rounded-xl transition-colors "
            f"{'text-slate-700 hover:bg-slate-100' if can_redo else 'text-slate-300 pointer-events-none'}"
        ):
            ui.icon('redo', size='1.25rem')
            ui.label('Redo').classes('text-[11px] font-medium')

        # Erase Button (triggers new pencil scribbling sound)
        with ui.button(on_click=on_erase).props('flat dense').classes(
            'flex-1 flex flex-col items-center gap-1 text-xs py-2 rounded-xl text-slate-700 hover:bg-slate-100 transition-colors'
        ):
            ui.icon('backspace', size='1.25rem')
            ui.label('Erase').classes('text-[11px] font-medium')

        # Notes Toggle Button
        notes_bg = 'bg-indigo-600 text-white shadow-md' if is_notes_mode else 'text-slate-700 hover:bg-slate-100'
        with ui.button(on_click=on_toggle_notes).props('flat dense').classes(
            f"flex-1 flex flex-col items-center gap-1 text-xs py-2 rounded-xl transition-all relative {notes_bg}"
        ):
            ui.icon('edit', size='1.25rem')
            ui.label(f"Notes {'ON' if is_notes_mode else 'OFF'}").classes('text-[11px] font-semibold')

        # Hint Button
        with ui.button(on_click=on_hint).props('flat dense').classes(
            'flex-1 flex flex-col items-center gap-1 text-xs py-2 rounded-xl text-amber-600 hover:bg-amber-50 transition-colors'
        ):
            ui.icon('lightbulb', size='1.25rem')
            ui.label('Hint').classes('text-[11px] font-semibold')


def render_number_pad_row(
    game: GameState,
    on_digit_input: Callable[[int], None],
) -> None:
    # Calculate counts of remaining numbers
    counts: Dict[int, int] = {i: 0 for i in range(1, 10)}
    for r in range(9):
        for c in range(9):
            val = game['current_grid'][r][c]
            if val in counts:
                counts[val] += 1

    with ui.row().classes('w-full max-w-[480px] mx-auto grid grid-cols-9 gap-1.5 px-1 py-1'):
        for num in range(1, 10):
            is_exhausted = counts[num] >= 9
            remaining = max(0, 9 - counts[num])

            btn_cls = (
                'opacity-30 pointer-events-none bg-slate-100 text-slate-400'
                if is_exhausted
                else 'bg-white hover:bg-indigo-50 text-slate-800 shadow-sm border border-slate-200/80 active:scale-95'
            )

            with ui.button(on_click=lambda _, n=num: on_digit_input(n)).props('flat').classes(
                f"h-14 sm:h-16 flex flex-col items-center justify-center rounded-xl p-0 transition-transform {btn_cls}"
            ):
                ui.label(str(num)).classes('text-xl sm:text-2xl font-bold leading-none')
                ui.label(str(remaining) if not is_exhausted else '—').classes('text-[10px] text-slate-400 mt-1 font-medium')
