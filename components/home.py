"""
components/home.py
Home Screen Component for ZenSudoku in NiceGUI.

Rules:
- Levels in order: easy, medium, hard, expert, master.
- Master is the hardest getting 16,000 points.
- Level Card Description:
  - Technique descriptions removed from all five cards.
  - Replaced with two rows:
    a) "Best time" (trophy icon): lowest timeSeconds among won games, as mm:ss (or "--:--").
    b) "Games won" (check icon): "won / total" (or "0 / 0").
  - Locked level: shows lock icon and "Finish <previous level> to unlock" instead of the two rows, with PLAY button greyed out.
  - Keeps identical card height on every level.
"""

from typing import Callable, Dict, List, Optional
from nicegui import ui
from sudoku_logic import (
    BASE_SCORES,
    Difficulty,
    GameState,
    HistoryRecord,
    UNLOCK_REQUIREMENTS,
    calculate_daily_score,
    calculate_streak,
    calculate_total_points,
    format_points,
    get_level_unlock_status,
    is_won_record,
)

PREVIOUS_LEVEL_NAME: Dict[Difficulty, Optional[str]] = {
    'easy': None,
    'medium': 'Easy',
    'hard': 'Medium',
    'expert': 'Hard',
    'master': 'Expert',
}


def render_home_screen(
    history: List[HistoryRecord],
    active_game: Optional[GameState],
    on_start_game: Callable[[Difficulty], None],
    on_resume_game: Callable[[], None],
    on_open_print: Optional[Callable[[], None]] = None,
) -> None:
    unlocks = get_level_unlock_status(history)
    streak_data = calculate_streak(history)
    total_points = calculate_total_points(history)
    all_time_won = [r for r in history if is_won_record(r)]
    all_time_count = len(all_time_won)
    formatted_points = format_points(total_points)
    exact_full_points = f"{total_points:,}"

    with ui.column().classes('w-full max-w-[540px] mx-auto px-3 pb-8 gap-4'):
        # 1. Daily Streak Card & Total Points
        with ui.card().classes('w-full bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-2xl p-4 shadow-lg border border-indigo-700/40'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('local_fire_department', size='1.75rem').classes('text-amber-400')
                    with ui.column().classes('gap-0'):
                        ui.label(f"{streak_data['active_streak']} Day Streak").classes('text-lg font-bold leading-none')
                        ui.label('Keep the streak alive').classes('text-xs text-indigo-200 mt-1')

                with ui.column().classes('items-end gap-0'):
                    ui.label("TOTAL POINTS").classes('text-[10px] text-indigo-300 uppercase tracking-wider font-bold')
                    with ui.row().classes('items-baseline gap-1'):
                        pts_lbl = ui.label(f"{formatted_points}").classes('text-lg font-bold font-mono leading-none text-blue-400 cursor-default')
                        pts_lbl.props(f'title="{exact_full_points}"')
                        ui.label("pts").classes('text-xs text-indigo-200')
                    ui.label(f"Across all games: {all_time_count}").classes('text-[10px] text-indigo-300 mt-1')

            # Streak progress indicators
            with ui.row().classes('w-full justify-between mt-3 pt-3 border-t border-indigo-800/60'):
                days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
                for d in days:
                    with ui.column().classes('items-center gap-1'):
                        ui.label(d).classes('text-[10px] text-indigo-300 font-semibold')
                        ui.element('div').classes('w-6 h-6 rounded-full bg-indigo-800/80 border border-indigo-600/50 flex items-center justify-center text-xs text-amber-300')

        # 2. Resume Active Game banner
        if active_game and not active_game.get('is_completed'):
            with ui.card().classes('w-full bg-indigo-50 border border-indigo-200 rounded-2xl p-3.5 shadow-sm cursor-pointer hover:bg-indigo-100/60 transition-colors').on('click', lambda _: on_resume_game()):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.row().classes('items-center gap-3'):
                        with ui.element('div').classes('w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white'):
                            ui.icon('play_arrow', size='1.25rem')
                        with ui.column().classes('gap-0'):
                            ui.label(f"Resume {active_game['level'].title()} Game").classes('text-sm font-bold text-slate-800 leading-none')
                            mins = active_game['elapsed_seconds'] // 60
                            secs = active_game['elapsed_seconds'] % 60
                            ui.label(f"Elapsed: {mins:02d}:{secs:02d} • {active_game['mistakes']}/3 mistakes").classes('text-xs text-slate-500 mt-1')
                    ui.icon('chevron_right', size='1.25rem').classes('text-indigo-600')

        # 3. Difficulty Level Selector
        with ui.row().classes('w-full justify-between items-center mt-2'):
            ui.label('SELECT DIFFICULTY').classes('text-[11px] font-extrabold tracking-wider text-slate-400 uppercase')
            if on_open_print:
                with ui.button('Print', on_click=lambda _: on_open_print()).props('flat dense').classes('px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 shadow-xs cursor-pointer'):
                    ui.icon('print', size='1rem').classes('text-slate-600 mr-1')

        levels: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
        points_map = {
            'easy': '1,000',
            'medium': '2,000',
            'hard': '4,000',
            'expert': '8,000',
            'master': '16,000',
        }

        with ui.column().classes('w-full gap-3'):
            for lvl in levels:
                is_unlocked = unlocks.get(lvl, False)
                prev_lvl = PREVIOUS_LEVEL_NAME[lvl]

                # Calculate Best Time and Games Won from history records
                level_records = [r for r in history if r.get('level') == lvl]
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

                # Uniform card container height (h-[160px])
                card_cls = (
                    f"w-full h-[160px] p-4 rounded-xl border flex flex-col justify-between transition-all "
                    f"{'bg-white border-slate-200 hover:border-indigo-400 shadow-sm' if is_unlocked else 'bg-slate-50/70 border-slate-200/80 opacity-80'}"
                )

                with ui.card().classes(card_cls):
                    with ui.column().classes('w-full gap-2'):
                        # Card Header: Level Title on left, points badge or lock icon on right
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label(lvl.title()).classes('text-base font-bold text-slate-900 leading-none')
                            if is_unlocked:
                                with ui.element('span').classes('text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 font-mono rounded'):
                                    ui.label(f"{points_map[lvl]} pts")
                            else:
                                with ui.element('span').classes('p-1 bg-slate-100 text-slate-400 rounded'):
                                    ui.icon('lock', size='1rem')

                        # Card Body: Two rows if unlocked, or lock message if locked
                        if is_unlocked:
                            with ui.column().classes('w-full gap-1 pt-1'):
                                # Row 1: Best time
                                with ui.row().classes('w-full justify-between items-center text-xs'):
                                    with ui.row().classes('items-center gap-1.5 text-slate-500'):
                                        ui.icon('emoji_events', size='1rem').classes('text-slate-400')
                                        ui.label('Best time')
                                    ui.label(best_time_str).classes('font-mono font-semibold text-slate-700')

                                # Row 2: Games won
                                with ui.row().classes('w-full justify-between items-center text-xs'):
                                    with ui.row().classes('items-center gap-1.5 text-slate-500'):
                                        ui.icon('check_circle', size='1rem').classes('text-slate-400')
                                        ui.label('Games won')
                                    ui.label(games_won_str).classes('font-mono font-semibold text-slate-700')
                        else:
                            # Locked level message
                            with ui.row().classes('items-center gap-2 py-2 text-xs text-slate-500'):
                                ui.icon('lock', size='1rem').classes('text-slate-400')
                                ui.label(f"Finish {prev_lvl or 'previous level'} to unlock")

                    # Footer: Play button (greyed out when locked)
                    with ui.row().classes('w-full pt-2 border-t border-slate-100'):
                        if is_unlocked:
                            ui.button(
                                'PLAY',
                                on_click=lambda _, l=lvl: on_start_game(l),
                            ).classes(
                                'w-full py-1.5 bg-slate-900 hover:bg-indigo-600 text-white font-semibold text-xs tracking-wider transition-colors'
                            )
                        else:
                            ui.button(
                                'PLAY',
                            ).classes(
                                'w-full py-1.5 bg-slate-200 text-slate-400 font-semibold text-xs tracking-wider cursor-not-allowed'
                            ).props('disabled')
