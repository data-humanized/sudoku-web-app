"""
test_themes.py
Unit tests for theme palettes and WCAG contrast ratio calculations.
"""

import unittest
from themes import THEMES, get_contrast_ratio


class TestThemes(unittest.TestCase):
    def test_themes_exist(self):
        self.assertIn('minimal_slate', THEMES)
        self.assertIn('dark_oled', THEMES)
        self.assertIn('warm_sepia', THEMES)
        self.assertIn('forest_zen', THEMES)
        self.assertIn('midnight_indigo', THEMES)

    def test_contrast_ratio_wcag(self):
        # Black on white has maximum ratio 21.0
        ratio = get_contrast_ratio('#000000', '#ffffff')
        self.assertEqual(ratio, 21.0)

        # Minimal slate dark text on white cell should exceed WCAG AA (4.5:1)
        theme = THEMES['minimal_slate']
        slate_ratio = get_contrast_ratio(theme.text_clue, theme.cell_bg)
        self.assertGreaterEqual(slate_ratio, 4.5)

    def test_css_generation(self):
        theme = THEMES['minimal_slate']
        css = theme.to_css_vars()
        self.assertIn('--zen-bg:', css)
        self.assertIn('--zen-accent:', css)


if __name__ == '__main__':
    unittest.main()
