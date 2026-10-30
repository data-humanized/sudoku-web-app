"""
test_keyboard.py
Unit tests for keyboard controller and shortcut dispatcher.
"""

import unittest
from keyboard_controller import KeyboardAction, KeyboardController


class TestKeyboardController(unittest.TestCase):
    def test_digit_dispatch(self):
        called = []
        kc = KeyboardController(on_digit=lambda d: called.append(d))
        action = kc.dispatch_key('7')
        self.assertEqual(action, KeyboardAction.DIGIT)
        self.assertEqual(called, [7])

    def test_undo_and_notes(self):
        undo_called = [False]
        notes_called = [False]
        kc = KeyboardController(
            on_undo=lambda: undo_called.__setitem__(0, True),
            on_toggle_notes=lambda: notes_called.__setitem__(0, True),
        )
        self.assertEqual(kc.dispatch_key('u'), KeyboardAction.UNDO)
        self.assertTrue(undo_called[0])

        self.assertEqual(kc.dispatch_key('n'), KeyboardAction.TOGGLE_NOTES)
        self.assertTrue(notes_called[0])

    def test_arrow_navigation(self):
        moves = []
        kc = KeyboardController(on_move_selection=lambda dr, dc: moves.append((dr, dc)))
        kc.dispatch_key('ArrowUp')
        kc.dispatch_key('ArrowRight')
        self.assertEqual(moves, [(-1, 0), (0, 1)])


if __name__ == '__main__':
    unittest.main()
