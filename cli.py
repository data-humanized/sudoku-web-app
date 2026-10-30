"""
cli.py
ZenSudoku Command Line Interface (CLI) in Python.

Usage:
  python3 cli.py play [--level easy|medium|hard|expert|master]
  python3 cli.py solve <puzzle-string>
  python3 cli.py stats
  python3 cli.py backup --export <filename.sudokubak>
  python3 cli.py backup --import <filename.sudokubak>
  python3 cli.py benchmark
"""

from __future__ import annotations
import argparse
import sys
import time
from typing import List, Optional

from sudoku_logic import (
    DIFFICULTY_TARGETS,
    Difficulty,
    Grid,
    SCORE_RANGES,
    calculate_daily_score,
    calculate_score,
    calculate_streak,
    get_level_unlock_status,
    get_new_puzzle,
    solve_sudoku,
)
from storage import (
    create_backup_binary,
    load_zen_data,
    save_zen_data,
    validate_and_parse_backup,
)
from analytics import AnalyticsReport
from solver_benchmarks import run_full_suite


def format_board(grid: Grid) -> str:
    """Renders a clean Unicode box-drawing Sudoku grid."""
    lines = []
    lines.append("  ┌───────┬───────┬───────┐")
    for r in range(9):
        row_str = f"{r+1} │ "
        for c in range(9):
            val = grid[r][c]
            char = str(val) if val != 0 else "·"
            row_str += char + " "
            if c in (2, 5):
                row_str += "│ "
        row_str += "│"
        lines.append(row_str)
        if r in (2, 5):
            lines.append("  ├───────┼───────┼───────┤")
    lines.append("  └───────┴───────┴───────┘")
    lines.append("    a b c   d e f   g h i")
    return "\n".join(lines)


def cmd_play(level: Difficulty = 'easy'):
    print(f"\nZenSudoku • Minimalist Logic")
    print(f"Difficulty: {level.upper()} (Max Score: {SCORE_RANGES[level]['max']:,} pts)")
    print("-" * 45)

    puzzle_data = get_new_puzzle(level)
    puzzle = puzzle_data['puzzle']
    solution = puzzle_data['solution']
    current = [row[:] for row in puzzle]

    mistakes = 0
    hints = 0
    t0 = time.time()

    while True:
        print("\n" + format_board(current))
        print(f"Mistakes: {mistakes}/3 | Hints used: {hints}")

        # Check win
        if all(current[r][c] == solution[r][c] for r in range(9) for c in range(9)):
            elapsed = int(time.time() - t0)
            score = calculate_score(level, elapsed, mistakes, hints)
            print(f"\n🎉 Puzzle Solved in {elapsed // 60}m {elapsed % 60}s!")
            print(f"Score Awarded: {score:,} points")
            # Save record
            storage = load_zen_data()
            storage.history.append({
                'id': f"cli-{int(time.time())}",
                'date': time.strftime('%Y-%m-%d'),
                'level': level,
                'score': score,
                'timeSeconds': elapsed,
                'mistakes': mistakes,
                'hintsUsed': hints,
            })
            save_zen_data(storage)
            break

        cmd = input("\nEnter move (e.g. 'e5 9', 'hint', or 'quit'): ").strip().lower()
        if cmd == 'quit':
            print("Game exited.")
            break
        elif cmd == 'hint':
            # Find first empty cell
            for r in range(9):
                for c in range(9):
                    if current[r][c] == 0:
                        current[r][c] = solution[r][c]
                        hints += 1
                        print(f"Hint placed at row {r+1}, col {c+1}: {solution[r][c]}")
                        break
                else:
                    continue
                break
        else:
            parts = cmd.split()
            if len(parts) == 2 and len(parts[0]) == 2 and parts[1].isdigit():
                col_char = parts[0][0]
                row_char = parts[0][1]
                val = int(parts[1])
                c = ord(col_char) - ord('a')
                r = int(row_char) - 1
                if 0 <= r < 9 and 0 <= c < 9 and 1 <= val <= 9:
                    if puzzle[r][c] != 0:
                        print("Cannot modify given clue!")
                    elif val != solution[r][c]:
                        mistakes += 1
                        print(f"❌ Incorrect digit! ({mistakes}/3 mistakes)")
                        if mistakes >= 3:
                            print("\n💔 3 Mistakes reached. Game over.")
                            break
                    else:
                        current[r][c] = val
                        print("✓ Placed correctly.")
                else:
                    print("Invalid coordinate or digit.")
            else:
                print("Format: <col><row> <digit> (e.g., 'a1 5')")


def cmd_stats():
    storage = load_zen_data()
    report = AnalyticsReport(storage.history)
    summary = report.get_summary()

    print("\nZenSudoku Statistics")
    print("=" * 45)
    print(f"Total Games Completed: {summary['total_games']}")
    print(f"Total Score:           {summary['total_score']:,} pts")
    print(f"Active Streak:         {summary['streaks']['active_streak']} days")
    print(f"Best Streak:           {summary['streaks']['best_streak']} days")
    print("\nBreakdown by Level:")
    for diff, data in summary['level_breakdown'].items():
        print(f"  {diff.title():<8}: {data['count']:2d} wins | Best: {data['best_time_seconds']}s | Avg: {data['avg_score']:,} pts")


def cmd_backup(export_path: Optional[str] = None, import_path: Optional[str] = None):
    storage = load_zen_data()
    if export_path:
        binary = create_backup_binary(storage.history, storage.settings)
        with open(export_path, 'wb') as f:
            f.write(binary)
        print(f"✓ Backup exported to {export_path} ({len(binary)} bytes, HMAC-SHA256 signed)")
    elif import_path:
        with open(import_path, 'rb') as f:
            data = f.read()
        try:
            records, settings = validate_and_parse_backup(data)
            storage.history = records
            storage.settings = settings
            save_zen_data(storage)
            print(f"✓ Successfully restored {len(records)} history records from {import_path}")
        except Exception as ex:
            print(f"❌ Failed to restore backup: {ex}")


def main():
    parser = argparse.ArgumentParser(description="ZenSudoku CLI - Minimalist Sudoku")
    subparsers = parser.add_subparsers(dest="subcommand")

    # play
    play_p = subparsers.add_parser("play", help="Start a new game")
    play_p.add_argument("--level", choices=['easy', 'medium', 'hard', 'expert', 'master'], default='easy')

    # stats
    subparsers.add_parser("stats", help="Display solving statistics")

    # benchmark
    subparsers.add_parser("benchmark", help="Run solver benchmark suite")

    # backup
    bak_p = subparsers.add_parser("backup", help="Manage .sudokubak backups")
    bak_p.add_argument("--export", dest="export_file", help="Export to .sudokubak")
    bak_p.add_argument("--import", dest="import_file", help="Import from .sudokubak")

    args = parser.parse_args()
    if args.subcommand == "play":
        cmd_play(args.level)
    elif args.subcommand == "stats":
        cmd_stats()
    elif args.subcommand == "benchmark":
        results = run_full_suite()
        for diff, data in results.items():
            print(f"[{diff.upper():<7}] Avg: {data['avg_ms']:.3f} ms")
    elif args.subcommand == "backup":
        cmd_backup(export_path=args.export_file, import_path=args.import_file)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
