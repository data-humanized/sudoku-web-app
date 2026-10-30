"""
test_sound_effects.py
Unit tests for Sound Effects System:
- Single shared SOUND_GAIN constant: correct (0.25), wrong (0.25), erase (0.12)
- Erase button pencil scribble lower volume
- Correct digit short pop/tick sound
- Wrong digit uses existing erase sound
- Silence for undo, redo, hints, pencil notes, and navigation
- Sound toggle enabling/disabling
"""

import unittest
from sound_effects import SOUND_GAIN, SoundManager, sounds


class TestSoundEffects(unittest.TestCase):
    def test_sound_gain_constant(self):
        """Verify SOUND_GAIN constant is defined with exact expected gain balances."""
        self.assertIn('correct', SOUND_GAIN)
        self.assertIn('wrong', SOUND_GAIN)
        self.assertIn('erase', SOUND_GAIN)

        self.assertEqual(SOUND_GAIN['correct'], 0.25)
        self.assertEqual(SOUND_GAIN['wrong'], 0.25)
        self.assertEqual(SOUND_GAIN['erase'], 0.12)

        # Erase scribble must be softer than tones
        self.assertLess(SOUND_GAIN['erase'], SOUND_GAIN['correct'])
        self.assertLess(SOUND_GAIN['erase'], SOUND_GAIN['wrong'])

    def test_sound_actions(self):
        """Verify correct JS triggers for each action."""
        mgr = SoundManager(enabled=True)

        # Correct digit tick/pop
        correct_js = mgr.get_sound_js('correct')
        self.assertIsNotNone(correct_js)
        self.assertIn('playCorrect()', correct_js)

        # Wrong digit action plays existing erase sound (descending sine)
        wrong_js = mgr.get_sound_js('wrong_digit')
        self.assertIsNotNone(wrong_js)
        self.assertIn('playWrongDigit()', wrong_js)

        mistake_js = mgr.get_sound_js('mistake')
        self.assertEqual(mistake_js, wrong_js)

        # Erase button action plays pencil scribble
        erase_js = mgr.get_sound_js('erase')
        self.assertIsNotNone(erase_js)
        self.assertIn('playErase()', erase_js)

        # Strictly silent actions
        self.assertIsNone(mgr.get_sound_js('hint'))
        self.assertIsNone(mgr.get_sound_js('undo'))
        self.assertIsNone(mgr.get_sound_js('redo'))
        self.assertIsNone(mgr.get_sound_js('note'))
        self.assertIsNone(mgr.get_sound_js('nav'))
        self.assertIsNone(mgr.get_sound_js('unknown_action'))

    def test_sound_disabled(self):
        """When sound is disabled, all actions return None (silent)."""
        mgr = SoundManager(enabled=False)
        self.assertIsNone(mgr.get_sound_js('correct'))
        self.assertIsNone(mgr.get_sound_js('wrong_digit'))
        self.assertIsNone(mgr.get_sound_js('erase'))


if __name__ == '__main__':
    unittest.main()
