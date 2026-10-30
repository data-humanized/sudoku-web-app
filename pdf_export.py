"""
pdf_export.py
Pure Python Printables & PDF Generation Engine for ZenSudoku.
Builds 100% offline, standalone PDF 1.4 documents for Sudoku puzzles and solutions:
- A4 Portrait (595.28 x 841.89 pt), ~15 mm margins
- Two 9x9 grids per page with clear labels ("Level - Puzzle N", "Level - Solution N")
- First solutions page includes "Solutions" header
- Thick lines (3x3 boxes & outer border) and thin lines (inner cells)
- Given digits in bold black; solved answers in medium grey (0.5 0.5 0.5 rg / #808080)
- Page numbers at bottom
- All puzzles first, then all solutions, ordered Easy -> Medium -> Hard -> Expert -> Master
- Full offline generation with built-in Helvetica fonts
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from sudoku_logic import Difficulty, Grid, create_empty_grid, get_canonical_fingerprint
from puzzle_generator import generate_puzzle_for_level


LEVELS_ORDER: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']

LEVEL_DISPLAY_NAMES: Dict[Difficulty, str] = {
    'easy': 'Easy',
    'medium': 'Medium',
    'hard': 'Hard',
    'expert': 'Expert',
    'master': 'Master',
}

# A4 dimensions in PDF points (72 pt/inch, 25.4 mm/inch)
PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN = 42.52  # 15 mm

GRID_SIZE = 216.0  # 9 * 24 pt
CELL_SIZE = 24.0

# 2 columns horizontally (Page width = 595.28 pt):
GRID_COLS_X = [50.0, 329.28]

# 3 rows vertically (Page height = 841.89 pt, PDF Y=0 is bottom):
GRID_ROWS_Y = [546.0, 292.0, 38.0]
TITLE_ROWS_Y = [769.0, 515.0, 261.0]

PAGE_NUM_Y = 18.0
SOLUTIONS_HEADER_Y = 802.0


class PdfDocument:
    """Lightweight, standalone PDF 1.4 binary builder using built-in Helvetica."""

    def __init__(self):
        self.pages_content: List[str] = []

    def add_page(self, content_stream: str) -> None:
        self.pages_content.append(content_stream)

    def to_bytes(self) -> bytes:
        total_pages = len(self.pages_content)
        if total_pages == 0:
            self.add_page("BT /F1 12 Tf 100 700 Td (No puzzles selected) Tj ET")
            total_pages = 1

        # Object structure:
        # 1: Catalog
        # 2: Pages
        # 3: Font Helvetica
        # 4: Font Helvetica-Bold
        # 5 .. 4 + total_pages: Page objects
        # 5 + total_pages .. 4 + 2*total_pages: Content stream objects
        num_objects = 4 + 2 * total_pages

        obj_offsets: List[int] = [0] * (num_objects + 1)
        output = bytearray()

        def write(b: bytes):
            output.extend(b)

        write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        # 1: Catalog
        obj_offsets[1] = len(output)
        write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2: Pages
        kids_refs = " ".join(f"{5 + i} 0 R" for i in range(total_pages))
        obj_offsets[2] = len(output)
        write(
            f"2 0 obj\n<< /Type /Pages /Kids [{kids_refs}] /Count {total_pages} >>\nendobj\n".encode(
                "latin-1"
            )
        )

        # 3: Helvetica
        obj_offsets[3] = len(output)
        write(
            b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n"
        )

        # 4: Helvetica-Bold
        obj_offsets[4] = len(output)
        write(
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n"
        )

        # Page objects: 5 .. 4 + total_pages
        for i in range(total_pages):
            page_obj_num = 5 + i
            content_obj_num = 5 + total_pages + i
            obj_offsets[page_obj_num] = len(output)
            page_dict = (
                f"{page_obj_num} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R\n"
                f"   /MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}]\n"
                f"   /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >>\n"
                f"   /Contents {content_obj_num} 0 R\n"
                f">>\nendobj\n"
            )
            write(page_dict.encode("latin-1"))

        # Content streams: 5 + total_pages .. 4 + 2*total_pages
        for i in range(total_pages):
            content_obj_num = 5 + total_pages + i
            content_bytes = self.pages_content[i].encode("latin-1")
            obj_offsets[content_obj_num] = len(output)
            stream_dict = (
                f"{content_obj_num} 0 obj\n"
                f"<< /Length {len(content_bytes)} >>\n"
                f"stream\n"
            ).encode("latin-1")
            write(stream_dict)
            write(content_bytes)
            write(b"\nendstream\nendobj\n")

        # XREF table
        xref_offset = len(output)
        write(b"xref\n")
        write(f"0 {num_objects + 1}\n".encode("latin-1"))
        write(b"0000000000 65535 f \r\n")
        for i in range(1, num_objects + 1):
            write(f"{obj_offsets[i]:010d} 00000 n \r\n".encode("latin-1"))

        # Trailer
        trailer = (
            f"trailer\n"
            f"<< /Size {num_objects + 1}\n"
            f"   /Root 1 0 R\n"
            f">>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        )
        write(trailer.encode("latin-1"))

        return bytes(output)


def escape_pdf_text(text: str) -> str:
    """Escapes special characters in PDF string literals."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf_grid(
    grid_left: float,
    grid_bottom: float,
    puzzle_grid: Grid,
    solution_grid: Optional[Grid] = None,
    is_solution_mode: bool = False,
) -> str:
    """
    Renders PDF drawing commands for a 9x9 Sudoku grid.
    - Thick outer border and 3x3 box borders (2.0 pt)
    - Thin inner cell borders (0.5 pt)
    - Given digits: Helvetica-Bold in black (0 0 0 rg)
    - Solved fill-ins: Helvetica in medium grey (0.5 0.5 0.5 rg)
    """
    cmd: List[str] = []

    # 1. Thin inner cell grid lines
    cmd.append("q")
    cmd.append("0.4 0.4 0.4 RG")  # Dark grey thin lines
    cmd.append("0.5 w")
    for i in range(1, 9):
        if i % 3 != 0:
            # Horizontal line
            y = grid_bottom + i * CELL_SIZE
            cmd.append(f"{grid_left:.2f} {y:.2f} m {grid_left + GRID_SIZE:.2f} {y:.2f} l S")
            # Vertical line
            x = grid_left + i * CELL_SIZE
            cmd.append(f"{x:.2f} {grid_bottom:.2f} m {x:.2f} {grid_bottom + GRID_SIZE:.2f} l S")
    cmd.append("Q")

    # 2. Thick 3x3 block lines & outer border
    cmd.append("q")
    cmd.append("0 0 0 RG")
    cmd.append("1.5 w")
    for b in (3, 6):
        y = grid_bottom + b * CELL_SIZE
        cmd.append(f"{grid_left:.2f} {y:.2f} m {grid_left + GRID_SIZE:.2f} {y:.2f} l S")
        x = grid_left + b * CELL_SIZE
        cmd.append(f"{x:.2f} {grid_bottom:.2f} m {x:.2f} {grid_bottom + GRID_SIZE:.2f} l S")
    # Outer border
    cmd.append(f"{grid_left:.2f} {grid_bottom:.2f} {GRID_SIZE:.2f} {GRID_SIZE:.2f} re S")
    cmd.append("Q")

    # 3. Cell digits
    char_w = 7.5
    char_h = 9.5
    dx = (CELL_SIZE - char_w) / 2.0
    dy = (CELL_SIZE - char_h) / 2.0 + 1.0

    for r in range(9):
        for c in range(9):
            given_val = puzzle_grid[r][c]
            # In PDF Y origin is at bottom, row 0 is top of grid
            row_from_bottom = 8 - r
            cell_x = grid_left + c * CELL_SIZE
            cell_y = grid_bottom + row_from_bottom * CELL_SIZE
            tx = cell_x + dx
            ty = cell_y + dy

            if not is_solution_mode:
                # Puzzle Grid: only givens in bold black
                if given_val != 0:
                    cmd.append("BT")
                    cmd.append("/F2 13 Tf")
                    cmd.append("0 0 0 rg")
                    cmd.append(f"{tx:.2f} {ty:.2f} Td")
                    cmd.append(f"({given_val}) Tj")
                    cmd.append("ET")
            else:
                # Solution Grid:
                # Given digits in bold black
                # Solved digits in medium grey (~#808080)
                sol_val = solution_grid[r][c] if solution_grid else given_val
                if sol_val != 0:
                    is_given = given_val != 0
                    font_ref = "/F2" if is_given else "/F1"
                    color_str = "0 0 0 rg" if is_given else "0.5 0.5 0.5 rg"

                    cmd.append("BT")
                    cmd.append(f"{font_ref} 13 Tf")
                    cmd.append(color_str)
                    cmd.append(f"{tx:.2f} {ty:.2f} Td")
                    cmd.append(f"({sol_val}) Tj")
                    cmd.append("ET")

    return "\n".join(cmd)


def generate_sudoku_pdf(puzzles_by_level: Dict[Difficulty, List[Dict[str, Any]]]) -> bytes:
    """
    Builds the complete printable PDF from the dictionary of generated puzzles.
    Follows all user specifications:
    - Order: Easy -> Medium -> Hard -> Expert -> Master
    - First all puzzles (6 grids per page in a 2-column x 3-row layout)
    - Solutions printed starting from the next page (6 grids per page)
    - Labels: 'Level - Puzzle N' and 'Level - Solution N'
    - 'Solutions' header on first solutions page
    - Centered small page numbers at bottom
    """
    # Filter active levels
    active_levels = [lvl for lvl in LEVELS_ORDER if puzzles_by_level.get(lvl)]
    if not active_levels:
        doc = PdfDocument()
        doc.add_page("BT /F1 14 Tf 50 750 Td (No puzzles selected for printing) Tj ET")
        return doc.to_bytes()

    # Collect all puzzle items in order: Easy -> Medium -> Hard -> Expert -> Master
    all_puzzle_items: List[Dict[str, Any]] = []
    for lvl in active_levels:
        lvl_name = LEVEL_DISPLAY_NAMES[lvl]
        for idx, item in enumerate(puzzles_by_level[lvl]):
            all_puzzle_items.append({
                'level': lvl,
                'level_name': lvl_name,
                'puzzle_num': idx + 1,
                'puzzle': item['puzzle'],
                'solution': item['solution'],
            })

    total_puzzles = len(all_puzzle_items)
    puz_page_count = math.ceil(total_puzzles / 6)
    sol_page_count = math.ceil(total_puzzles / 6)
    total_pages = puz_page_count + sol_page_count

    doc = PdfDocument()
    current_page_num = 1

    # --- PART 1: PUZZLES (6 per page) ---
    for page_idx in range(puz_page_count):
        chunk = all_puzzle_items[page_idx * 6 : (page_idx + 1) * 6]
        stream: List[str] = []

        for slot_idx, puz in enumerate(chunk):
            row_idx = slot_idx // 2
            col_idx = slot_idx % 2
            gx = GRID_COLS_X[col_idx]
            gy = GRID_ROWS_Y[row_idx]
            ty = TITLE_ROWS_Y[row_idx]

            # Label above grid
            stream.append("BT")
            stream.append("/F2 10 Tf")
            stream.append("0 0 0 rg")
            label_text = escape_pdf_text(f"{puz['level_name']} - Puzzle {puz['puzzle_num']}")
            stream.append(f"{gx:.2f} {ty:.2f} Td")
            stream.append(f"({label_text}) Tj")
            stream.append("ET")

            # Grid
            stream.append(render_pdf_grid(gx, gy, puz['puzzle'], is_solution_mode=False))

        # Centered page number at bottom
        stream.append("BT")
        stream.append("/F1 9 Tf")
        stream.append("0.4 0.4 0.4 rg")
        page_text = escape_pdf_text(f"Page {current_page_num} of {total_pages}")
        stream.append(f"265.00 {PAGE_NUM_Y:.2f} Td")
        stream.append(f"({page_text}) Tj")
        stream.append("ET")

        doc.add_page("\n".join(stream))
        current_page_num += 1

    # --- PART 2: SOLUTIONS (6 per page, starting from next page) ---
    is_first_sol_page = True
    for page_idx in range(sol_page_count):
        chunk = all_puzzle_items[page_idx * 6 : (page_idx + 1) * 6]
        stream: List[str] = []

        if is_first_sol_page:
            stream.append("BT")
            stream.append("/F2 14 Tf")
            stream.append("0 0 0 rg")
            header_text = escape_pdf_text("Solutions")
            stream.append(f"{GRID_COLS_X[0]:.2f} {SOLUTIONS_HEADER_Y:.2f} Td")
            stream.append(f"({header_text}) Tj")
            stream.append("ET")
            is_first_sol_page = False

        for slot_idx, puz in enumerate(chunk):
            row_idx = slot_idx // 2
            col_idx = slot_idx % 2
            gx = GRID_COLS_X[col_idx]
            gy = GRID_ROWS_Y[row_idx]
            ty = TITLE_ROWS_Y[row_idx]

            # Label above grid
            stream.append("BT")
            stream.append("/F2 10 Tf")
            stream.append("0 0 0 rg")
            label_text = escape_pdf_text(f"{puz['level_name']} - Solution {puz['puzzle_num']}")
            stream.append(f"{gx:.2f} {ty:.2f} Td")
            stream.append(f"({label_text}) Tj")
            stream.append("ET")

            # Solution Grid
            stream.append(
                render_pdf_grid(
                    gx,
                    gy,
                    puzzle_grid=puz['puzzle'],
                    solution_grid=puz['solution'],
                    is_solution_mode=True,
                )
            )

        # Centered page number at bottom
        stream.append("BT")
        stream.append("/F1 9 Tf")
        stream.append("0.4 0.4 0.4 rg")
        page_text = escape_pdf_text(f"Page {current_page_num} of {total_pages}")
        stream.append(f"265.00 {PAGE_NUM_Y:.2f} Td")
        stream.append(f"({page_text}) Tj")
        stream.append("ET")

        doc.add_page("\n".join(stream))
        current_page_num += 1

    return doc.to_bytes()


def calculate_print_page_count(level_counts: Dict[str, int]) -> int:
    """
    Computes total page count:
    6 grids per page for puzzles, and solutions printed from next page (6 per page).
    Total pages = ceil(total_puzzles / 6) * 2.
    """
    total = sum(max(0, count) for count in level_counts.values())
    if total == 0:
        return 0
    puz_pages = math.ceil(total / 6)
    sol_pages = math.ceil(total / 6)
    return puz_pages + sol_pages


def create_print_dialog_state() -> Dict[str, Any]:
    """Returns the default initial state for the Print Puzzles dialog."""
    return {
        'levels': {
            lvl: {'checked': False, 'count': 0}
            for lvl in LEVELS_ORDER
        },
        'total': 0,
        'can_create': False,
    }


def update_print_dialog_level(
    state: Dict[str, Any],
    level: str,
    checked: Optional[bool] = None,
    count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Updates dialog state adhering to constraints:
    - Unticking resets that level's count to 0
    - Ticking keeps count at 0 until changed
    - Counts strictly clamp between 0 and 6
    - Included only if checked AND count >= 1
    - 'can_create' is True iff total >= 1
    """
    if level not in state['levels']:
        return state

    curr = state['levels'][level]
    new_checked = curr['checked'] if checked is None else checked
    new_count = curr['count'] if count is None else count

    if checked is False:
        new_count = 0

    new_count = max(0, min(6, new_count))

    state['levels'][level] = {'checked': new_checked, 'count': new_count}

    total = sum(
        lvl_data['count']
        for lvl_data in state['levels'].values()
        if lvl_data['checked'] and lvl_data['count'] >= 1
    )
    state['total'] = total
    state['can_create'] = total > 0
    return state


def generate_printable_puzzles(
    level_counts: Dict[Difficulty, int],
    existing_fingerprints: Optional[Set[str]] = None,
) -> Tuple[bytes, List[str], Dict[Difficulty, List[Dict[str, Any]]]]:
    """
    Generates fresh procedural puzzles matching level counts, verifying uniqueness
    and avoiding duplicate fingerprints.
    Returns:
    - PDF bytes
    - List of newly generated puzzle fingerprints (to save in storage)
    - Puzzles dictionary grouped by level
    """
    used_fingerprints: Set[str] = set(existing_fingerprints or [])
    new_fingerprints: List[str] = []
    puzzles_by_level: Dict[Difficulty, List[Dict[str, Any]]] = {}

    for lvl in LEVELS_ORDER:
        count = level_counts.get(lvl, 0)
        if count <= 0:
            continue

        puzzles_by_level[lvl] = []
        for _ in range(count):
            attempts = 0
            while attempts < 25:
                attempts += 1
                data = generate_puzzle_for_level(lvl)
                fp = data.get('fingerprint') or get_canonical_fingerprint(data['puzzle'])
                data['fingerprint'] = fp
                if fp in used_fingerprints:
                    continue
                used_fingerprints.add(fp)
                new_fingerprints.append(fp)
                puzzles_by_level[lvl].append(data)
                break

    pdf_bytes = generate_sudoku_pdf(puzzles_by_level)
    return pdf_bytes, new_fingerprints, puzzles_by_level


# --------------------------------------------------------------------------
# Backwards compatibility with previous SVG export helper
# --------------------------------------------------------------------------
def render_svg_grid(grid: Grid, title: str = "ZenSudoku", level: str = "Easy") -> str:
    """Generates a vector SVG representation of a 9x9 Sudoku grid."""
    size = 450
    cell_size = size / 9.0

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size + 60}" width="{size}" height="{size + 60}" style="font-family: sans-serif;">',
        '  <!-- Header -->',
        f'  <text x="10" y="32" font-size="20" font-weight="bold" fill="#0f172a">{title}</text>',
        f'  <text x="{size - 10}" y="32" font-size="14" font-weight="600" fill="#64748b" text-anchor="end" text-transform="uppercase">{level}</text>',
        '  <!-- Grid Background -->',
        f'  <rect x="0" y="50" width="{size}" height="{size}" fill="#ffffff" stroke="#0f172a" stroke-width="3" />',
    ]

    for i in range(1, 9):
        stroke_width = 3 if i % 3 == 0 else 1
        stroke_color = "#0f172a" if i % 3 == 0 else "#cbd5e1"
        pos = 50 + i * cell_size
        svg.append(f'  <line x1="0" y1="{pos}" x2="{size}" y2="{pos}" stroke="{stroke_color}" stroke-width="{stroke_width}" />')
        svg.append(f'  <line x1="{i * cell_size}" y1="50" x2="{i * cell_size}" y2="{size + 50}" stroke="{stroke_color}" stroke-width="{stroke_width}" />')

    for r in range(9):
        for c in range(9):
            val = grid[r][c]
            if val != 0:
                cx = c * cell_size + cell_size / 2
                cy = 50 + r * cell_size + cell_size / 2 + 7
                svg.append(f'  <text x="{cx}" y="{cy}" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">{val}</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


def generate_printable_html(puzzles: List[Dict[str, Any]]) -> str:
    """Generates an HTML print document formatted for standard sheets."""
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '  <meta charset="utf-8">',
        '  <title>ZenSudoku - Printable Puzzles</title>',
        '  <style>',
        '    @media print { body { margin: 0; padding: 20mm; } .page-break { page-break-after: always; } }',
        '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #fff; color: #0f172a; }',
        '    .puzzle-card { display: flex; flex-direction: column; align-items: center; margin-bottom: 40px; }',
        '  </style>',
        '</head>',
        '<body>',
    ]

    for p in puzzles:
        lvl = p.get('level', 'easy')
        svg_code = render_svg_grid(p['puzzle'], title="ZenSudoku", level=lvl)
        html_parts.append('  <div class="puzzle-card">')
        html_parts.append(f'    {svg_code}')
        html_parts.append('  </div>')
        html_parts.append('  <div class="page-break"></div>')

    html_parts.append('</body>')
    html_parts.append('</html>')
    return '\n'.join(html_parts)
