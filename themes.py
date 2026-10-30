"""
themes.py
Theme and Visual Styling Engine for ZenSudoku in Python.

Provides:
- Handcrafted visual themes:
  * Minimal Slate (clean daylight gray/slate)
  * Dark OLED (true black #000000 for battery saving)
  * Warm Sepia / Parchment (calm reading tint)
  * Forest Zen (subtle sage/emerald hues)
  * Midnight Indigo (deep navy blue night mode)
- WCAG AA contrast ratio compliance checks
- CSS injection builders for NiceGUI and Web frontends
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple


class ColorTheme:
    def __init__(
        self,
        id_name: str,
        display_name: str,
        bg_primary: str,
        bg_card: str,
        grid_border: str,
        grid_line: str,
        cell_bg: str,
        cell_selected: str,
        cell_highlight: str,
        cell_error: str,
        text_primary: str,
        text_clue: str,
        text_note: str,
        accent: str,
    ):
        self.id = id_name
        self.name = display_name
        self.bg_primary = bg_primary
        self.bg_card = bg_card
        self.grid_border = grid_border
        self.grid_line = grid_line
        self.cell_bg = cell_bg
        self.cell_selected = cell_selected
        self.cell_highlight = cell_highlight
        self.cell_error = cell_error
        self.text_primary = text_primary
        self.text_clue = text_clue
        self.text_note = text_note
        self.accent = accent

    def to_css_vars(self) -> str:
        return f"""
        :root {{
          --zen-bg: {self.bg_primary};
          --zen-card: {self.bg_card};
          --zen-grid-border: {self.grid_border};
          --zen-grid-line: {self.grid_line};
          --zen-cell-bg: {self.cell_bg};
          --zen-cell-sel: {self.cell_selected};
          --zen-cell-hi: {self.cell_highlight};
          --zen-cell-err: {self.cell_error};
          --zen-text: {self.text_primary};
          --zen-clue: {self.text_clue};
          --zen-note: {self.text_note};
          --zen-accent: {self.accent};
        }}
        """


THEMES: Dict[str, ColorTheme] = {
    'minimal_slate': ColorTheme(
        id_name='minimal_slate',
        display_name='Minimal Slate',
        bg_primary='#f8fafc',
        bg_card='#ffffff',
        grid_border='#334155',
        grid_line='#cbd5e1',
        cell_bg='#ffffff',
        cell_selected='#4f46e5',
        cell_highlight='#e0e7ff',
        cell_error='#fee2e2',
        text_primary='#0f172a',
        text_clue='#0f172a',
        text_note='#0f172a',
        accent='#4f46e5',
    ),
    'dark_oled': ColorTheme(
        id_name='dark_oled',
        display_name='Dark OLED',
        bg_primary='#000000',
        bg_card='#09090b',
        grid_border='#27272a',
        grid_line='#18181b',
        cell_bg='#09090b',
        cell_selected='#6366f1',
        cell_highlight='#1e1b4b',
        cell_error='#450a0a',
        text_primary='#f4f4f5',
        text_clue='#ffffff',
        text_note='#a1a1aa',
        accent='#818cf8',
    ),
    'warm_sepia': ColorTheme(
        id_name='warm_sepia',
        display_name='Warm Sepia',
        bg_primary='#fbf7f0',
        bg_card='#f5ece0',
        grid_border='#5c4a3e',
        grid_line='#d8c8b8',
        cell_bg='#fdfbf7',
        cell_selected='#8b5a2b',
        cell_highlight='#efe1d1',
        cell_error='#fce4e4',
        text_primary='#2c221e',
        text_clue='#1a1412',
        text_note='#4a3b32',
        accent='#8b5a2b',
    ),
    'forest_zen': ColorTheme(
        id_name='forest_zen',
        display_name='Forest Zen',
        bg_primary='#f4f7f4',
        bg_card='#ffffff',
        grid_border='#2d4a3e',
        grid_line='#c8d9cf',
        cell_bg='#ffffff',
        cell_selected='#059669',
        cell_highlight='#d1fae5',
        cell_error='#fee2e2',
        text_primary='#064e3b',
        text_clue='#022c22',
        text_note='#047857',
        accent='#059669',
    ),
    'midnight_indigo': ColorTheme(
        id_name='midnight_indigo',
        display_name='Midnight Indigo',
        bg_primary='#0f172a',
        bg_card='#1e293b',
        grid_border='#475569',
        grid_line='#334155',
        cell_bg='#1e293b',
        cell_selected='#4338ca',
        cell_highlight='#312e81',
        cell_error='#7f1d1d',
        text_primary='#f8fafc',
        text_clue='#ffffff',
        text_note='#94a3b8',
        accent='#6366f1',
    ),
}


def hex_to_relative_luminance(hex_str: str) -> float:
    """Calculates relative luminance for WCAG contrast ratio."""
    hex_clean = hex_str.lstrip('#')
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0

    def adjust(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)

    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def get_contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculates contrast ratio (1.0 to 21.0) between two colors."""
    l1 = hex_to_relative_luminance(hex1)
    l2 = hex_to_relative_luminance(hex2)
    bright = max(l1, l2)
    dark = min(l1, l2)
    return round((bright + 0.05) / (dark + 0.05), 2)
