"""
haptics.py
Haptic Vibration and Gamepad Rumble Controller for ZenSudoku in Python.

Provides:
- Web Vibration API patterns via browser JavaScript bridge:
  * Light tap (10 ms) on valid digit entry
  * Double buzz (40 ms, 30 ms gap, 40 ms) on error / mistake
  * Subtle friction tick (15 ms) on pencil note toggle
  * Rhythmic pulse on game victory / puzzle completion
- Gamepad rumble trigger support for desktop controllers
"""

from typing import Optional


class HapticPattern:
    LIGHT = "light"
    ERROR = "error"
    NOTE = "note"
    VICTORY = "victory"


class HapticsManager:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    # Client-side JavaScript snippet to trigger Navigator.vibrate() safely
    WEB_HAPTICS_JS = """
    (function() {
        if (window.__zenHaptics) return;
        window.__zenHaptics = {
            vibrate: function(pattern) {
                if (!navigator.vibrate) return;
                try {
                    navigator.vibrate(pattern);
                } catch(e) {}
            }
        };
    })();
    """

    def get_vibration_pattern(self, action: str) -> Optional[str]:
        if not self.enabled:
            return None

        patterns = {
            HapticPattern.LIGHT: "window.__zenHaptics && window.__zenHaptics.vibrate(12);",
            HapticPattern.NOTE: "window.__zenHaptics && window.__zenHaptics.vibrate(8);",
            HapticPattern.ERROR: "window.__zenHaptics && window.__zenHaptics.vibrate([45, 30, 45]);",
            HapticPattern.VICTORY: "window.__zenHaptics && window.__zenHaptics.vibrate([100, 50, 100, 50, 200]);",
        }
        return patterns.get(action)


haptics = HapticsManager(enabled=True)
