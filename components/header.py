"""
components/header.py
Top Navigation Header Components for ZenSudoku in NiceGUI.
"""

from typing import Callable
from nicegui import ui
from sudoku_logic import Difficulty, GameState


def render_home_header(
    on_open_analytics: Callable[[], None],
    on_open_settings: Callable[[], None],
) -> None:
    with ui.row().classes('w-full max-w-[500px] mx-auto justify-between items-center py-4 px-3'):
        with ui.row().classes('items-center gap-2.5'):
            with ui.element('div').classes('w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-200'):
                ui.icon('grid_on', size='1.25rem')
            with ui.column().classes('gap-0'):
                ui.label('ZenSudoku').classes('text-xl font-extrabold tracking-tight text-slate-900 leading-none')
                ui.label('Minimal Logic').classes('text-[11px] font-medium text-slate-400 leading-none mt-1')

        with ui.row().classes('items-center gap-1'):
            with ui.button(on_click=on_open_analytics).props('flat round dense').classes('text-slate-600 hover:bg-slate-100'):
                ui.icon('insights', size='1.25rem')
            with ui.button(on_click=on_open_settings).props('flat round dense').classes('text-slate-600 hover:bg-slate-100'):
                ui.icon('settings', size='1.25rem')


def render_in_game_header(
    game: GameState,
    on_home: Callable[[], None],
    on_toggle_pause: Callable[[], None],
    on_open_settings: Callable[[], None],
) -> None:
    mins = game['elapsed_seconds'] // 60
    secs = game['elapsed_seconds'] % 60
    time_str = f"{mins:02d}:{secs:02d}"

    level_colors = {
        'easy': 'bg-emerald-50 text-emerald-700 border-emerald-200',
        'medium': 'bg-sky-50 text-sky-700 border-sky-200',
        'hard': 'bg-amber-50 text-amber-700 border-amber-200',
        'expert': 'bg-rose-50 text-rose-700 border-rose-200',
        'master': 'bg-purple-50 text-purple-700 border-purple-200',
    }
    badge_cls = level_colors.get(game['level'], 'bg-slate-50 text-slate-700 border-slate-200')

    with ui.row().classes('w-full max-w-[480px] mx-auto justify-between items-center py-2 px-2'):
        # Left: Home button & Difficulty badge
        with ui.row().classes('items-center gap-2'):
            with ui.button(on_click=on_home).props('flat round dense').classes('text-slate-600 hover:bg-slate-100'):
                ui.icon('arrow_back', size='1.25rem')
            ui.label(game['level'].upper()).classes(f"text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider {badge_cls}")

        # Center: Timer & Pause
        with ui.row().classes('items-center gap-1.5 cursor-pointer hover:opacity-80').on('click', lambda _: on_toggle_pause()):
            ui.icon('pause' if not game['is_paused'] else 'play_arrow', size='1rem').classes('text-slate-400')
            ui.label(time_str if not game['is_paused'] else 'PAUSED').classes('font-mono font-bold text-sm text-slate-700')

        # Right: Mistakes Lives (3 Hearts) & Settings
        with ui.row().classes('items-center gap-2'):
            with ui.row().classes('gap-0.5 items-center'):
                for i in range(3):
                    is_lost = i < game['mistakes']
                    heart_color = 'text-rose-400' if not is_lost else 'text-slate-200'
                    ui.icon('favorite', size='0.875rem').classes(heart_color)

            with ui.button(on_click=on_open_settings).props('flat round dense').classes('text-slate-600 hover:bg-slate-100'):
                ui.icon('settings', size='1.125rem')
