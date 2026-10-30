"""
components/grid.py
Sudoku Grid Component for NiceGUI.

Rules:
- Wrong input: No shake or wobble animation. Digit shows in red (#dc2626) and stays red until erased or corrected.
- Pencil Notes: Fixed 3x3 layout inside each cell: digit d always sits at the same position (1 top-left ... 9 bottom-right).
- Font size about 27% of cell height, semi-bold, high-contrast dark slate (#0f172a), with visible padding from cell border.
- Size notes relative to the cell size so they stay sharp and readable across screen sizes.
"""

from typing import Callable, Optional, Set, Tuple
from nicegui import ui
from sudoku_logic import GameState


def render_sudoku_grid(
    game: GameState,
    selected_cell: Optional[Tuple[int, int]],
    on_cell_select: Callable[[int, int], None],
    shaking_cell: Optional[Tuple[int, int]] = None,  # Kept optional for backward compatibility
) -> None:
    sel_r, sel_c = selected_cell if selected_cell is not None else (-1, -1)
    sel_val = game['current_grid'][sel_r][sel_c] if 0 <= sel_r < 9 and 0 <= sel_c < 9 else 0

    with ui.card().classes('w-full max-w-[480px] mx-auto p-1.5 sm:p-2 bg-slate-800 rounded-2xl shadow-xl border border-slate-700/60'):
        with ui.element('div').classes('grid grid-cols-9 gap-[1px] bg-slate-600/80 p-[2px] rounded-xl overflow-hidden aspect-square'):
            for r in range(9):
                for c in range(9):
                    val = game['current_grid'][r][c]
                    is_initial = game['initial_grid'][r][c] != 0
                    is_hinted = game['hinted_cells'][r][c]
                    is_selected = (r == sel_r and c == sel_c)
                    is_same_val = (val != 0 and val == sel_val)
                    is_peer = (r == sel_r or c == sel_c or (r // 3 == sel_r // 3 and c // 3 == sel_c // 3))
                    is_error = (val != 0 and not is_initial and val != game['solution_grid'][r][c])

                    # Thick 3x3 box borders
                    border_classes = []
                    if r % 3 == 0 and r != 0:
                        border_classes.append('border-t-2 border-slate-700')
                    if c % 3 == 0 and c != 0:
                        border_classes.append('border-l-2 border-slate-700')

                    # Background styling based on selection hierarchy - NO shake or wobble
                    if is_selected:
                        bg_cls = 'bg-indigo-600 text-white ring-2 ring-indigo-400 z-10'
                    elif is_error:
                        # Error red background and text; stays red until corrected or erased
                        bg_cls = 'bg-rose-50 text-[#dc2626]'
                    elif is_same_val:
                        bg_cls = 'bg-indigo-100 text-indigo-950 font-bold'
                    elif is_peer and sel_val != 0:
                        bg_cls = 'bg-indigo-50/60'
                    elif is_peer:
                        bg_cls = 'bg-slate-50'
                    else:
                        bg_cls = 'bg-white'

                    cell_classes = (
                        f"relative flex items-center justify-center aspect-square select-none cursor-pointer transition-colors "
                        f"{bg_cls} {' '.join(border_classes)}"
                    )

                    with ui.element('div').classes(cell_classes).style('container-type: size;').on(
                        'click', lambda _, row=r, col=c: on_cell_select(row, col)
                    ):
                        if val != 0:
                            # Placed digit: initial = bold slate-900, error = #dc2626 red, hinted = violet, placed = indigo
                            if is_selected:
                                text_cls = 'text-white font-extrabold'
                            elif is_error:
                                text_cls = 'text-[#dc2626] font-bold'
                            elif is_initial:
                                text_cls = 'text-slate-900 font-extrabold'
                            elif is_hinted:
                                text_cls = 'text-purple-600 font-bold'
                            else:
                                text_cls = 'text-indigo-600 font-bold'

                            ui.label(str(val)).classes(f"text-xl sm:text-2xl md:text-3xl {text_cls} leading-none pointer-events-none")
                        else:
                            # Pencil Notes: Fixed 3x3 layout (digit d at position d, font size ~27% of cell height, high-contrast dark slate #0f172a)
                            notes_set: Set[int] = game['notes'][r][c]
                            if notes_set:
                                with ui.element('div').classes('w-full h-full p-[3px] grid grid-cols-3 grid-rows-3 pointer-events-none'):
                                    for digit in range(1, 10):
                                        has_digit = digit in notes_set
                                        note_text = str(digit) if has_digit else ''
                                        ui.element('div').classes(
                                            'flex items-center justify-center font-semibold leading-none text-[#0f172a]'
                                        ).style(
                                            'font-size: clamp(8px, 27cqh, 20px);'
                                        ).text = note_text
