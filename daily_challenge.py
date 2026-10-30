"""
daily_challenge.py
Deterministic Daily Challenge and Trophy Milestone Engine for ZenSudoku in Python.

Provides:
- Deterministic puzzle selection for any calendar date based on cryptographic hashing
- Trophy milestone achievements:
  * Bronze Flame: 3-day active streak
  * Silver Flame: 7-day active streak
  * Gold Flame: 14-day active streak
  * Platinum Flame: 30-day active streak
  * Diamond Zen: 100-day active streak
- Monthly calendar challenge completion audit
- Daily challenge bonus score calculation
"""

from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sudoku_logic import (
    Difficulty,
    Grid,
    HistoryRecord,
    SCORE_RANGES,
    calculate_daily_score,
    calculate_score,
    calculate_streak,
)
from puzzles_database import PUZZLE_BANK


TROPHY_TIERS = [
    {'id': 'streak_3', 'name': 'Bronze Flame', 'days': 3, 'desc': '3-Day Active Streak', 'icon': 'local_fire_department', 'color': '#cd7f32'},
    {'id': 'streak_7', 'name': 'Silver Flame', 'days': 7, 'desc': '7-Day Active Streak', 'icon': 'workspace_premium', 'color': '#c0c0c0'},
    {'id': 'streak_14', 'name': 'Gold Flame', 'days': 14, 'desc': '14-Day Active Streak', 'icon': 'emoji_events', 'color': '#ffd700'},
    {'id': 'streak_30', 'name': 'Platinum Flame', 'days': 30, 'desc': '30-Day Active Streak', 'icon': 'military_tech', 'color': '#e5e4e2'},
    {'id': 'streak_100', 'name': 'Diamond Zen', 'days': 100, 'desc': '100-Day Active Streak', 'icon': 'diamond', 'color': '#b9f2ff'},
]


def get_daily_puzzle_for_date(date_str: str) -> Dict[str, Any]:
    """
    Returns the deterministic daily puzzle for a given ISO date (YYYY-MM-DD).
    Difficulty rotates through the week:
      Monday: Easy
      Tuesday: Medium
      Wednesday: Medium
      Thursday: Hard
      Friday: Hard
      Saturday: Expert
      Sunday: Master
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = dt.weekday()  # 0=Monday, 6=Sunday

    difficulty_map: Dict[int, Difficulty] = {
        0: 'easy',
        1: 'medium',
        2: 'medium',
        3: 'hard',
        4: 'hard',
        5: 'expert',
        6: 'master',
    }
    level = difficulty_map[weekday]

    # Deterministic index from date hash
    h = hashlib.sha256(date_str.encode('utf-8')).hexdigest()
    int_hash = int(h[:8], 16)

    pool = PUZZLE_BANK.get(level, PUZZLE_BANK['easy'])
    puzzle_idx = int_hash % len(pool)
    selected = pool[puzzle_idx]

    return {
        'date': date_str,
        'level': level,
        'weekday_name': dt.strftime('%A'),
        'puzzle': [row[:] for row in selected['puzzle']],
        'solution': [row[:] for row in selected['solution']],
        'max_score': SCORE_RANGES[level]['max'],
    }


def get_trophies_status(history: List[HistoryRecord]) -> List[Dict[str, Any]]:
    """Evaluates unlocked streak trophies against user history."""
    streaks = calculate_streak(history)
    best_streak = streaks['best_streak']
    active_streak = streaks['active_streak']

    result = []
    for tier in TROPHY_TIERS:
        required = tier['days']
        unlocked = best_streak >= required
        progress = min(1.0, active_streak / required) if required > 0 else 1.0
        result.append({
            'id': tier['id'],
            'name': tier['name'],
            'days_required': required,
            'description': tier['desc'],
            'icon': tier['icon'],
            'color': tier['color'],
            'unlocked': unlocked,
            'progress': progress,
        })
    return result


def get_monthly_completion(history: List[HistoryRecord], year: int, month: int) -> Dict[str, Any]:
    """Returns calendar days of a specific month completed by the player."""
    month_prefix = f"{year:04d}-{month:02d}"
    days_completed = set()
    total_score = 0

    for r in history:
        d = r.get('date', '')
        if d.startswith(month_prefix):
            day_num = int(d.split('-')[2])
            days_completed.add(day_num)
            total_score += r.get('score', 0)

    # Days in month
    if month in (1, 3, 5, 7, 8, 10, 12):
        total_days = 31
    elif month in (4, 6, 9, 11):
        total_days = 30
    else:
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        total_days = 29 if is_leap else 28

    return {
        'year': year,
        'month': month,
        'total_days': total_days,
        'days_completed': sorted(list(days_completed)),
        'completed_count': len(days_completed),
        'month_score': total_score,
        'is_perfect_month': len(days_completed) == total_days,
    }
