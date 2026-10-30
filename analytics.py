"""
analytics.py
Advanced Analytics and Statistics Engine for ZenSudoku in Python.

Provides:
- Aggregate statistics across all 5 difficulty levels (easy, medium, hard, expert, master)
- Solving velocity (seconds per placed digit)
- Mistake rate distribution and hint reliance
- Streak momentum and weekly activity heatmaps
- Performance ratings based on timeSeconds and score ranges
"""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sudoku_logic import (
    Difficulty,
    HistoryRecord,
    SCORE_RANGES,
    calculate_daily_score,
    calculate_streak,
    get_level_unlock_status,
)


class AnalyticsReport:
    def __init__(self, history: List[HistoryRecord]):
        self.history = history

    def get_summary(self) -> Dict[str, Any]:
        total_games = len(self.history)
        if total_games == 0:
            return {
                'total_games': 0,
                'total_score': 0,
                'avg_score': 0,
                'total_time_seconds': 0,
                'avg_time_seconds': 0,
                'total_mistakes': 0,
                'total_hints': 0,
                'streaks': {'active_streak': 0, 'best_streak': 0},
                'level_breakdown': self._empty_level_breakdown(),
            }

        total_score = sum(r.get('score', 0) for r in self.history)
        total_time = sum(r.get('timeSeconds', 0) for r in self.history)
        total_mistakes = sum(r.get('mistakes', 0) for r in self.history)
        total_hints = sum(r.get('hintsUsed', 0) for r in self.history)

        streaks = calculate_streak(self.history)
        unlocks = get_level_unlock_status(self.history)
        level_stats = self.get_level_breakdown()

        return {
            'total_games': total_games,
            'total_score': total_score,
            'avg_score': total_score // total_games,
            'total_time_seconds': total_time,
            'avg_time_seconds': total_time // total_games,
            'total_mistakes': total_mistakes,
            'total_hints': total_hints,
            'streaks': streaks,
            'unlocks': unlocks,
            'level_breakdown': level_stats,
        }

    def _empty_level_breakdown(self) -> Dict[Difficulty, Dict[str, Any]]:
        diffs: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
        return {
            d: {
                'count': 0,
                'best_time_seconds': 0,
                'avg_time_seconds': 0,
                'max_score': SCORE_RANGES[d]['max'],
                'min_score': SCORE_RANGES[d]['min'],
                'avg_score': 0,
                'clean_games_no_mistakes': 0,
            }
            for d in diffs
        }

    def get_level_breakdown(self) -> Dict[Difficulty, Dict[str, Any]]:
        diffs: List[Difficulty] = ['easy', 'medium', 'hard', 'expert', 'master']
        by_level: Dict[Difficulty, List[HistoryRecord]] = defaultdict(list)
        for r in self.history:
            lvl = r.get('level')
            if lvl in diffs:
                by_level[lvl].append(r)

        result: Dict[Difficulty, Dict[str, Any]] = {}
        for d in diffs:
            records = by_level[d]
            count = len(records)
            if count == 0:
                result[d] = {
                    'count': 0,
                    'best_time_seconds': 0,
                    'avg_time_seconds': 0,
                    'max_score': SCORE_RANGES[d]['max'],
                    'min_score': SCORE_RANGES[d]['min'],
                    'avg_score': 0,
                    'clean_games_no_mistakes': 0,
                }
            else:
                times = [r.get('timeSeconds', 0) for r in records]
                scores = [r.get('score', 0) for r in records]
                clean = sum(1 for r in records if r.get('mistakes', 0) == 0 and r.get('hintsUsed', 0) == 0)

                result[d] = {
                    'count': count,
                    'best_time_seconds': min(times),
                    'avg_time_seconds': sum(times) // count,
                    'max_score': SCORE_RANGES[d]['max'],
                    'min_score': SCORE_RANGES[d]['min'],
                    'avg_score': sum(scores) // count,
                    'clean_games_no_mistakes': clean,
                }
        return result

    def get_weekly_activity(self) -> List[Dict[str, Any]]:
        """Groups historical games by ISO calendar week."""
        weeks = defaultdict(lambda: {'count': 0, 'score': 0})
        for r in self.history:
            date_str = r.get('date')
            if date_str:
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    year, week_num, _ = dt.isocalendar()
                    key = f"{year}-W{week_num:02d}"
                    weeks[key]['count'] += 1
                    weeks[key]['score'] += r.get('score', 0)
                except ValueError:
                    pass

        return [{'week': k, 'games': v['count'], 'score': v['score']} for k, v in sorted(weeks.items())]
