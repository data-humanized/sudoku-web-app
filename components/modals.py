"""
components/modals.py
Modal Dialogs for ZenSudoku in NiceGUI:
- Analytics Modal (supports all 5 difficulties including master, using timeSeconds)
- Settings Modal (strict .sudokubak binary import/export, sound, haptics, timer)
- Completion Modal (victory screen, celebration stats)
- Lives Modal (3 mistakes game over)
"""

import base64
from typing import Any, Callable, Dict, List, Optional
from nicegui import ui
from sudoku_logic import Difficulty, GameState, HistoryRecord, UserSettings
from storage import (
    ZenSudokuStorage,
    create_backup_binary,
    restore_rollback_copy,
    save_rollback_copy,
    validate_and_parse_backup,
)


def show_analytics_modal(history: List[HistoryRecord]) -> None:
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-[460px] p-5 rounded-2xl bg-white shadow-2xl'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('insights', size='1.5rem').classes('text-indigo-600')
                ui.label('Game Analytics').classes('text-lg font-bold text-slate-800')
            with ui.button(on_click=dialog.close).props('flat round dense').classes('text-slate-400 hover:text-slate-600'):
                ui.icon('close', size='1.25rem')

        total_games = len(history)
        total_score = sum(r.get('score', 0) for r in history)
        avg_score = total_score // total_games if total_games > 0 else 0

        # Stats summary row
        with ui.row().classes('w-full grid grid-cols-3 gap-2 mb-5'):
            with ui.card().classes('p-3 bg-slate-50 border border-slate-100 rounded-xl items-center text-center'):
                ui.label(str(total_games)).classes('text-xl font-extrabold text-slate-800 leading-none')
                ui.label('Completed').classes('text-[11px] text-slate-400 mt-1')
            with ui.card().classes('p-3 bg-slate-50 border border-slate-100 rounded-xl items-center text-center'):
                ui.label(f"{total_score:,}").classes('text-xl font-extrabold text-indigo-600 leading-none')
                ui.label('Total Score').classes('text-[11px] text-slate-400 mt-1')
            with ui.card().classes('p-3 bg-slate-50 border border-slate-100 rounded-xl items-center text-center'):
                ui.label(f"{avg_score:,}").classes('text-xl font-extrabold text-emerald-600 leading-none')
                ui.label('Avg Score').classes('text-[11px] text-slate-400 mt-1')

        # Breakdown by Level
        ui.label('PERFORMANCE BY DIFFICULTY').classes('text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-2')
        levels: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']

        with ui.column().classes('w-full gap-2'):
            for lvl in levels:
                level_records = [r for r in history if r.get('level') == lvl]
                count = len(level_records)
                best_time = min((r.get('timeSeconds', 0) for r in level_records), default=0)
                mins = best_time // 60
                secs = best_time % 60
                time_str = f"{mins}m {secs}s" if count > 0 else '—'

                with ui.row().classes('w-full justify-between items-center p-2.5 bg-slate-50 rounded-xl border border-slate-100'):
                    with ui.column().classes('gap-0'):
                        ui.label(lvl.title()).classes('text-sm font-bold text-slate-800 capitalize')
                        ui.label(f"{count} game{'s' if count != 1 else ''} won").classes('text-xs text-slate-400')
                    with ui.column().classes('items-end gap-0'):
                        ui.label(time_str).classes('text-xs font-mono font-bold text-slate-700')
                        ui.label('Best Time').classes('text-[9px] text-slate-400')

    dialog.open()


def show_settings_modal(
    storage: ZenSudokuStorage,
    on_settings_change: Callable[[UserSettings], None],
    on_restore_backup: Callable[[List[HistoryRecord], UserSettings], None],
    on_reset_all: Callable[[], None],
) -> None:
    settings = storage.settings

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-[460px] p-5 rounded-2xl bg-white shadow-2xl'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('settings', size='1.5rem').classes('text-indigo-600')
                ui.label('Preferences & Backup').classes('text-lg font-bold text-slate-800')
            with ui.button(on_click=dialog.close).props('flat round dense').classes('text-slate-400 hover:text-slate-600'):
                ui.icon('close', size='1.25rem')

        # Switches
        with ui.column().classes('w-full gap-3 mb-4'):
            sound_switch = ui.switch('Sound Effects', value=settings.get('sound_effects', True))
            timer_switch = ui.switch('Show Timer', value=settings.get('show_timer', True))
            notes_switch = ui.switch('Auto-remove Notes on Placement', value=settings.get('auto_remove_notes', True))

            def update_switches():
                new_s = dict(settings)
                new_s['sound_effects'] = sound_switch.value
                new_s['show_timer'] = timer_switch.value
                new_s['auto_remove_notes'] = notes_switch.value
                on_settings_change(new_s)

            sound_switch.on('update:model-value', lambda _: update_switches())
            timer_switch.on('update:model-value', lambda _: update_switches())
            notes_switch.on('update:model-value', lambda _: update_switches())

        # Backup & Restore Section (.sudokubak)
        ui.label('BACKUP & RECOVERY (.sudokubak)').classes('text-[10px] font-extrabold tracking-wider text-slate-400 uppercase mb-2')
        with ui.row().classes('w-full gap-2 mb-4'):
            def download_backup():
                binary = create_backup_binary(storage.history, storage.settings)
                b64 = base64.b64encode(binary).decode('utf-8')
                ui.run_javascript(f"""
                const a = document.createElement('a');
                a.href = 'data:application/octet-stream;base64,{b64}';
                a.download = 'zensudoku_backup.sudokubak';
                a.click();
                """)
                ui.notify('Backup downloaded successfully', type='positive')

            with ui.button('Download Backup', on_click=download_backup).props('outline').classes('flex-1 rounded-xl text-xs font-bold text-indigo-600'):
                ui.icon('download', size='1rem')

            async def handle_upload(e):
                try:
                    file_bytes = e.content.read()
                    save_rollback_copy(storage)
                    records, restored_settings = validate_and_parse_backup(file_bytes)
                    on_restore_backup(records, restored_settings)
                    ui.notify(f"Successfully restored {len(records)} records!", type='positive')
                    dialog.close()
                except Exception as ex:
                    ui.notify('Invalid or modified backup file', type='negative')

            with ui.upload(on_upload=handle_upload, max_file_size=1_000_000).props('flat dense auto-upload accept=".sudokubak"').classes('flex-1'):
                ui.button('Import .sudokubak').props('outline').classes('w-full rounded-xl text-xs font-bold text-slate-700')

        # Reset Danger Zone
        with ui.button('Reset All Game Progress', on_click=on_reset_all).props('flat text-color=red').classes('w-full text-xs font-bold text-rose-600 rounded-xl mt-2'):
            ui.icon('delete_outline', size='1rem')

    dialog.open()


def show_completion_modal(
    level: Difficulty,
    score: int,
    elapsed_seconds: int,
    mistakes: int,
    hints_used: int,
    on_play_again: Callable[[], None],
    on_go_home: Callable[[], None],
) -> None:
    mins = elapsed_seconds // 60
    secs = elapsed_seconds % 60
    time_str = f"{mins:02d}:{secs:02d}"

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-[420px] p-6 rounded-2xl bg-white shadow-2xl text-center items-center'):
        with ui.element('div').classes('w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mb-3 shadow-inner'):
            ui.icon('emoji_events', size='2.5rem')

        ui.label('Puzzle Solved!').classes('text-2xl font-extrabold text-slate-900 tracking-tight')
        ui.label(f"{level.title()} Completed").classes('text-xs text-slate-400 capitalize mb-4')

        # Score display
        with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-100 rounded-xl mb-4'):
            ui.label(f"{score:,}").classes('text-3xl font-extrabold text-indigo-600 font-mono leading-none')
            ui.label('TOTAL POINTS').classes('text-[10px] font-bold text-slate-400 tracking-wider mt-1')

        # Stats grid
        with ui.row().classes('w-full grid grid-cols-3 gap-2 mb-6'):
            with ui.column().classes('p-2 bg-slate-50 rounded-lg items-center'):
                ui.label(time_str).classes('font-mono font-bold text-sm text-slate-700')
                ui.label('Time').classes('text-[10px] text-slate-400')
            with ui.column().classes('p-2 bg-slate-50 rounded-lg items-center'):
                ui.label(f"{mistakes}/3").classes('font-mono font-bold text-sm text-slate-700')
                ui.label('Mistakes').classes('text-[10px] text-slate-400')
            with ui.column().classes('p-2 bg-slate-50 rounded-lg items-center'):
                ui.label(str(hints_used)).classes('font-mono font-bold text-sm text-slate-700')
                ui.label('Hints').classes('text-[10px] text-slate-400')

        with ui.row().classes('w-full gap-2'):
            ui.button('Home', on_click=lambda: (dialog.close(), on_go_home())).props('outline').classes('flex-1 rounded-xl font-bold text-slate-700')
            ui.button('Play Again', on_click=lambda: (dialog.close(), on_play_again())).classes('flex-1 bg-indigo-600 text-white rounded-xl font-bold shadow-md')

    dialog.open()


def show_lives_modal(
    on_restart: Callable[[], None],
    on_go_home: Callable[[], None],
) -> None:
    with ui.dialog() as dialog, ui.card().classes('w-full max-w-[380px] p-6 rounded-2xl bg-white shadow-2xl text-center items-center'):
        with ui.element('div').classes('w-16 h-16 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mb-3'):
            ui.icon('heart_broken', size='2.5rem')

        ui.label('3 Mistakes Reached').classes('text-xl font-bold text-slate-900 leading-none')
        ui.label('Every puzzle offers a chance to refine focus. Start fresh with renewed clarity.').classes('text-xs text-slate-500 mt-2 mb-6 leading-relaxed')

        with ui.row().classes('w-full gap-2'):
            ui.button('Give Up', on_click=lambda: (dialog.close(), on_go_home())).props('outline').classes('flex-1 rounded-xl font-bold text-slate-700')
            ui.button('Restart Puzzle', on_click=lambda: (dialog.close(), on_restart())).classes('flex-1 bg-rose-600 text-white rounded-xl font-bold shadow-md')

    dialog.open()


def show_print_puzzles_modal(storage: Optional[ZenSudokuStorage] = None) -> None:
    """Displays the 'Print puzzles' dialog matching specifications."""
    from pdf_export import (
        LEVELS_ORDER,
        LEVEL_DISPLAY_NAMES,
        create_print_dialog_state,
        generate_printable_puzzles,
        update_print_dialog_level,
    )
    import datetime

    state = create_print_dialog_state()

    with ui.dialog() as dialog, ui.card().classes('w-full max-w-[380px] p-5 rounded-none bg-white border border-slate-200 shadow-2xl relative'):
        with ui.row().classes('w-full justify-between items-center mb-3'):
            ui.label('Print puzzles').classes('text-base font-bold text-slate-900 tracking-tight')
            with ui.button(on_click=dialog.close).props('flat round dense').classes('text-slate-400 hover:text-slate-600'):
                ui.icon('close', size='1.25rem')

        rows_container = ui.column().classes('w-full divide-y divide-slate-100')
        total_label = ui.label('Total: 0 puzzles').classes('font-mono font-bold text-slate-900 text-xs')
        create_btn = ui.button('CREATE PDF').classes('flex-1 py-2.5 font-bold text-xs uppercase tracking-wider bg-slate-100 text-slate-400 rounded-none')
        create_btn.props('disabled')

        def refresh_dialog_ui():
            total = state['total']
            total_label.text = f"Total: {total} puzzle{'s' if total != 1 else ''}"
            if state['can_create']:
                create_btn.classes(replace='flex-1 py-2.5 font-bold text-xs uppercase tracking-wider bg-slate-900 text-white rounded-none cursor-pointer')
                create_btn.props(remove='disabled')
            else:
                create_btn.classes(replace='flex-1 py-2.5 font-bold text-xs uppercase tracking-wider bg-slate-100 text-slate-400 rounded-none cursor-not-allowed')
                create_btn.props('disabled')

        with rows_container:
            for lvl in LEVELS_ORDER:
                lvl_name = LEVEL_DISPLAY_NAMES[lvl]
                with ui.row().classes('w-full justify-between items-center py-2'):
                    with ui.row().classes('items-center gap-3'):
                        chk = ui.checkbox()
                        ui.label(lvl_name).classes('text-sm font-semibold text-slate-800')

                    picker = ui.number(value=0, min=0, max=6, step=1).classes('w-16').props('dense outlined')
                    picker.props('disable')

                    def on_chk_change(e, l=lvl, p=picker):
                        is_checked = e.value
                        if not is_checked:
                            p.value = 0
                            p.props('disable')
                            update_print_dialog_level(state, l, checked=False, count=0)
                        else:
                            p.props(remove='disable')
                            update_print_dialog_level(state, l, checked=True, count=int(p.value or 0))
                        refresh_dialog_ui()

                    def on_num_change(e, l=lvl):
                        val = int(e.value or 0)
                        update_print_dialog_level(state, l, count=val)
                        refresh_dialog_ui()

                    chk.on('update:model-value', on_chk_change)
                    picker.on('update:model-value', on_num_change)

        with ui.column().classes('w-full gap-0.5 pt-2 text-xs'):
            ui.label('Up to 6 per level. For more, print again.').classes('text-slate-500')
            # total_label placed here

        async def on_create_click():
            counts = {
                lvl: state['levels'][lvl]['count']
                for lvl in LEVELS_ORDER
                if state['levels'][lvl]['checked'] and state['levels'][lvl]['count'] >= 1
            }
            if not counts:
                return

            ui.notify('Generating PDF puzzles...', type='info')
            existing_fps = set(storage.recent_fingerprints) if storage and hasattr(storage, 'recent_fingerprints') else set()
            pdf_bytes, new_fps, _ = generate_printable_puzzles(counts, existing_fps)

            if storage and hasattr(storage, 'recent_fingerprints'):
                storage.recent_fingerprints.extend(new_fps)

            b64 = base64.b64encode(pdf_bytes).decode('utf-8')
            today_str = datetime.datetime.now().strftime('%Y-%m-%d')
            filename = f"Sudoku-Printables-{today_str}.pdf"

            ui.run_javascript(f"""
                const a = document.createElement('a');
                a.href = 'data:application/pdf;base64,{b64}';
                a.download = '{filename}';
                a.click();
            """)
            ui.notify('Printable PDF downloaded!', type='positive')
            dialog.close()

        create_btn.on('click', on_create_click)

        with ui.row().classes('w-full gap-3 pt-3'):
            ui.button('CANCEL', on_click=dialog.close).props('outline').classes('flex-1 py-2.5 font-bold text-xs uppercase tracking-wider text-slate-800 border-slate-300 rounded-none')
            # create_btn placed in layout

    dialog.open()

