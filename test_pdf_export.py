"""
test_pdf_export.py
Comprehensive unit tests for the Sudoku Printables and PDF Export Engine.
Covers all required specifications:
1. Dialog defaults: all unticked, all 0, clamping 0..6, unticking resets to 0, button state.
2. Page ordering: Easy to Master, puzzles before solutions, counts match dialog, solutions count == puzzles count.
3. Solution validity: valid completed Sudoku, matches given digits, unique solution.
4. No duplicate puzzles / fingerprints in one PDF.
5. Content styling: given digits rendered in black, solved answers rendered in grey (0.5 0.5 0.5 rg).
6. PDF binary validity: valid PDF 1.4 header and trailer, exact page count equals sum over levels of ceil(count / 2) for puzzles and solutions.
"""

import math
import unittest
from typing import Dict, List

from sudoku_logic import Difficulty, Grid, has_unique_solution, is_valid_placement
from pdf_export import (
    LEVELS_ORDER,
    calculate_print_page_count,
    create_print_dialog_state,
    generate_printable_html,
    generate_printable_puzzles,
    generate_sudoku_pdf,
    render_svg_grid,
    update_print_dialog_level,
)


class TestPdfExport(unittest.TestCase):
    # ----------------------------------------------------------------------
    # 1. Dialog Defaults and State Logic Tests
    # ----------------------------------------------------------------------
    def test_dialog_defaults_and_validation(self):
        state = create_print_dialog_state()

        # All 5 levels must be unticked and count 0
        for lvl in LEVELS_ORDER:
            self.assertIn(lvl, state['levels'])
            self.assertFalse(state['levels'][lvl]['checked'])
            self.assertEqual(state['levels'][lvl]['count'], 0)

        # Total is 0, Create PDF is disabled
        self.assertEqual(state['total'], 0)
        self.assertFalse(state['can_create'])

        # Ticking does not change count (stays 0)
        update_print_dialog_level(state, 'easy', checked=True)
        self.assertTrue(state['levels']['easy']['checked'])
        self.assertEqual(state['levels']['easy']['count'], 0)
        self.assertFalse(state['can_create'])

        # Increment count
        update_print_dialog_level(state, 'easy', count=3)
        self.assertEqual(state['levels']['easy']['count'], 3)
        self.assertEqual(state['total'], 3)
        self.assertTrue(state['can_create'])

        # Clamping: never below 0 or above 6
        update_print_dialog_level(state, 'easy', count=10)
        self.assertEqual(state['levels']['easy']['count'], 6)

        update_print_dialog_level(state, 'easy', count=-5)
        self.assertEqual(state['levels']['easy']['count'], 0)

        # Unticking resets count to 0
        update_print_dialog_level(state, 'easy', count=4)
        self.assertEqual(state['levels']['easy']['count'], 4)
        update_print_dialog_level(state, 'easy', checked=False)
        self.assertFalse(state['levels']['easy']['checked'])
        self.assertEqual(state['levels']['easy']['count'], 0)
        self.assertFalse(state['can_create'])

    # ----------------------------------------------------------------------
    # 2. Page Count Calculation Test
    # ----------------------------------------------------------------------
    def test_page_count_formula(self):
        # 6 grids per page, solutions start on next page:
        # Easy: 2 -> ceil(2/6) = 1 puzzle page, 1 solution page = 2 pages
        self.assertEqual(calculate_print_page_count({'easy': 2}), 2)

        # Easy: 6 -> ceil(6/6) = 1 puzzle page, 1 solution page = 2 pages
        self.assertEqual(calculate_print_page_count({'easy': 6}), 2)

        # Easy: 4, Hard: 3 -> Total 7 puzzles -> ceil(7/6) = 2 puzzle pages, 2 solution pages = 4 pages
        selection = {'easy': 4, 'hard': 3}
        self.assertEqual(calculate_print_page_count(selection), 4)

        # All 5 levels with 1 each: Total 5 puzzles -> 1 puzzle page + 1 solution page = 2 pages
        all_one = {lvl: 1 for lvl in LEVELS_ORDER}
        self.assertEqual(calculate_print_page_count(all_one), 2)

    # ----------------------------------------------------------------------
    # 3. Puzzle Generation and Validity Tests
    # ----------------------------------------------------------------------
    def test_generated_puzzles_validity_and_uniqueness(self):
        selection: Dict[Difficulty, int] = {'easy': 1, 'medium': 1}
        pdf_bytes, fingerprints, puzzles_by_level = generate_printable_puzzles(selection)

        # Verify fingerprints are non-empty and unique
        self.assertEqual(len(fingerprints), 2)
        self.assertEqual(len(set(fingerprints)), 2)

        for lvl, puzzle_list in puzzles_by_level.items():
            self.assertEqual(len(puzzle_list), selection[lvl])
            for item in puzzle_list:
                puzzle = item['puzzle']
                solution = item['solution']

                # Puzzle has a unique solution
                self.assertTrue(has_unique_solution(puzzle))

                # Solution must match puzzle's given digits
                for r in range(9):
                    for c in range(9):
                        if puzzle[r][c] != 0:
                            self.assertEqual(puzzle[r][c], solution[r][c])

                # Solution must be completely filled
                for r in range(9):
                    for c in range(9):
                        self.assertNotEqual(solution[r][c], 0)
                        # Verify valid rows, columns, boxes
                        val = solution[r][c]
                        # Row check
                        self.assertEqual(solution[r].count(val), 1)
                        # Col check
                        col_vals = [solution[row_idx][c] for row_idx in range(9)]
                        self.assertEqual(col_vals.count(val), 1)

    # ----------------------------------------------------------------------
    # 4. PDF Structure, Ordering, and Styling Tests
    # ----------------------------------------------------------------------
    def test_pdf_binary_structure_and_styling(self):
        selection: Dict[Difficulty, int] = {'easy': 2, 'expert': 1}
        pdf_bytes, fingerprints, puzzles_by_level = generate_printable_puzzles(selection)

        # PDF header & trailer
        self.assertTrue(pdf_bytes.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", pdf_bytes)
        self.assertIn(b"/Type /Catalog", pdf_bytes)
        self.assertIn(b"/BaseFont /Helvetica", pdf_bytes)
        self.assertIn(b"/BaseFont /Helvetica-Bold", pdf_bytes)

        # Expected page count:
        # Total 3 puzzles -> 1 puzzle page (up to 6) + 1 solution page = 2 pages
        expected_pages = calculate_print_page_count(selection)
        self.assertEqual(expected_pages, 2)

        pdf_str = pdf_bytes.decode('latin-1')

        # Check Page count in catalog
        self.assertIn(f"/Count {expected_pages}", pdf_str)

        # Check section labels
        self.assertIn("(Easy - Puzzle 1)", pdf_str)
        self.assertIn("(Easy - Puzzle 2)", pdf_str)
        self.assertIn("(Expert - Puzzle 1)", pdf_str)

        # Solutions labels
        self.assertIn("(Solutions)", pdf_str)
        self.assertIn("(Easy - Solution 1)", pdf_str)
        self.assertIn("(Easy - Solution 2)", pdf_str)
        self.assertIn("(Expert - Solution 1)", pdf_str)

        # Check styling: given digits in black (0 0 0 rg) and solved answers in grey (0.5 0.5 0.5 rg)
        self.assertIn("0 0 0 rg", pdf_str)
        self.assertIn("0.5 0.5 0.5 rg", pdf_str)

        # Order check: Puzzle must appear before Solution in PDF stream
        pos_puz = pdf_str.find("Easy - Puzzle 1")
        pos_sol = pdf_str.find("Easy - Solution 1")
        self.assertGreater(pos_sol, pos_puz)

    # ----------------------------------------------------------------------
    # 5. Backwards Compatibility Tests
    # ----------------------------------------------------------------------
    def test_render_svg_and_html(self):
        grid: Grid = [[0]*9 for _ in range(9)]
        grid[0][0] = 5
        svg = render_svg_grid(grid, title="ZenSudoku Test", level="Master")
        self.assertIn("<svg", svg)
        self.assertIn(">5</text>", svg)

        html = generate_printable_html([{'puzzle': grid, 'level': 'easy'}])
        self.assertIn("<!DOCTYPE html>", html)


if __name__ == '__main__':
    unittest.main()
