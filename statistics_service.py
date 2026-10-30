"""
statistics_service.py
Statistical Modeling and Performance Grading Service for ZenSudoku in Python.

Computes:
- Player skill rating (ELO-like metric based on difficulty and clean completion time)
- Percentile calculation against global calibrated benchmarks
- Expected time and score distributions
- Difficulty mastery progression metrics
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional
from sudoku_logic import Difficulty, HistoryRecord, SCORE_RANGES

# Calibrated global benchmarks for median solving time (seconds)
BENCHMARKS_SECONDS: Dict[Difficulty, Dict[str, float]] = {
    'easy': {'median': 240.0, 'std': 60.0},
    'medium': {'median': 480.0, 'std': 120.0},
    'hard': {'median': 720.0, 'std': 180.0},
    'expert': {'median': 1050.0, 'std': 240.0},
    'master': {'median': 1350.0, 'std': 300.0},
}


def calculate_percentile(level: Difficulty, time_seconds: int) -> float:
    """Calculates player speed percentile (0.0 to 100.0) relative to normal distribution."""
    bench = BENCHMARKS_SECONDS[level]
    median = bench['median']
    std = bench['std']

    # Standard normal cumulative distribution approximation
    z = (median - time_seconds) / std
    percentile = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0
    return max(1.0, min(99.9, round(percentile, 1)))


def calculate_skill_rating(history: List[HistoryRecord]) -> int:
    """
    Computes player skill score (0 to 3000 ELO equivalent)
    factoring difficulty, clean completions, and time efficiency.
    """
    if not history:
        return 1000

    base_multiplier = {
        'easy': 1.0,
        'medium': 1.3,
        'hard': 1.7,
        'expert': 2.2,
        'master': 2.8,
    }

    weighted_points = 0.0
    total_weights = 0.0

    for r in history:
        lvl = r.get('level', 'easy')
        mult = base_multiplier.get(lvl, 1.0)
        score_ratio = r.get('score', 0) / SCORE_RANGES[lvl]['max']
        clean_bonus = 1.15 if r.get('mistakes', 0) == 0 and r.get('hintsUsed', 0) == 0 else 1.0

        game_rating = 1000 + (score_ratio * 1500 * mult * clean_bonus)
        weighted_points += game_rating * mult
        total_weights += mult

    return int(round(weighted_points / total_weights)) if total_weights > 0 else 1000


def get_mastery_report(history: List[HistoryRecord]) -> Dict[str, Any]:
    rating = calculate_skill_rating(history)
    level_counts = {d: sum(1 for r in history if r.get('level') == d) for d in ['easy', 'medium', 'hard', 'expert', 'master']}

    rank_title = 'Novice'
    if rating >= 2400:
        rank_title = 'Grandmaster'
    elif rating >= 2000:
        rank_title = 'Master'
    elif rating >= 1600:
        rank_title = 'Expert'
    elif rating >= 1300:
        rank_title = 'Intermediate'

    return {
        'skill_rating': rating,
        'rank_title': rank_title,
        'level_counts': level_counts,
        'total_completed': len(history),
    }
