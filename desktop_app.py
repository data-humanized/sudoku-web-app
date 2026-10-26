"""
desktop_app.py - Standalone Python Desktop Application
Runs locally and offline with zero web dependencies.
Uses PySide6 / PyQt6 or CustomTkinter to render the ZenSudoku desktop GUI
connecting directly to the pure engine in sudoku_logic.py.

To run locally on your desktop (Windows / macOS / Linux):
    pip install PySide6
    python desktop_app.py
"""

import sys
import json
import time
from pathlib import Path

# Import our pure logic engine
from sudoku_logic import (
    solve_sudoku,
    calculate_score,
    calculate_streak,
    calculate_daily_score,
    getLevelUnlockStatus,
    get_level_unlock_status,
    CURATED_PUZZLES,
    HistoryRecord,
    GameState,
    MoveAction,
    get_candidates,
    get_peers,
    clone_grid,
    clone_notes,
    clone_bool_grid,
    empty_grid,
    empty_notes,
    empty_bool_grid,
)

DATA_FILE = Path("zensudoku_data.json")

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"history": [], "settings": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QPushButton, QLabel, QFrame, QMessageBox, QStackedWidget
    )
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QColor
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


class SudokuDesktopWindow:
    """
    ZenSudoku Desktop GUI implementation using PySide6.
    Follows all aesthetic guidelines:
      - Fixed clean light style (#f8fafc background, #ffffff surfaces, #0f172a text, #2563eb accents)
      - Sharp corners (border-radius: 0)
      - Large desktop layout
    """
    def __init__(self):
        if not PYSIDE_AVAILABLE:
            print("\n" + "=" * 60)
            print("To run the standalone Python desktop GUI, install PySide6:")
            print("    pip install PySide6")
            print("    python desktop_app.py")
            print("=" * 60 + "\n")
            return

        self.app = QApplication(sys.argv)
        self.data = load_data()
        self.history = [HistoryRecord(**h) for h in self.data.get("history", [])]
        
        self.window = QMainWindow()
        self.window.setWindowTitle("ZenSudoku - Offline Desktop")
        self.window.setMinimumSize(1200, 850)
        self.window.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
            QWidget {
                font-family: 'Segoe UI', system-ui, sans-serif;
                color: #0f172a;
            }
            QPushButton {
                border-radius: 0px;
                border: 1px solid #e2e8f0;
                background-color: #ffffff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
            }
        """)

        self.central_widget = QWidget()
        self.window.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(32, 24, 32, 24)

        # Build UI
        self.setup_header()
        self.setup_game_board()
        self.start_new_puzzle("easy")

    def setup_header(self):
        header = QHBoxLayout()
        title = QLabel("ZenSudoku")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setStyleSheet("color: #0f172a;")
        header.addWidget(title)
        header.addStretch()

        self.streak_lbl = QLabel(f"Streak: 0 d")
        self.streak_lbl.setStyleSheet("padding: 6px 12px; background: white; border: 1px solid #e2e8f0; font-weight: bold;")
        header.addWidget(self.streak_lbl)

        self.score_lbl = QLabel(f"Score: 0 pts")
        self.score_lbl.setStyleSheet("padding: 6px 12px; background: white; border: 1px solid #e2e8f0; font-weight: bold; color: #2563eb;")
        header.addWidget(self.score_lbl)

        self.main_layout.addLayout(header)

    def setup_game_board(self):
        body = QHBoxLayout()
        body.setSpacing(40)

        # Left Column: 9x9 Grid (sharp corners, 3px solid border)
        left_col = QVBoxLayout()
        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet("background: white; border: 3px solid #0f172a; border-radius: 0px;")
        grid_layout = QGridLayout(self.grid_frame)
        grid_layout.setSpacing(0)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.cells = []
        for r in range(9):
            row_cells = []
            for c in range(9):
                btn = QPushButton()
                btn.setFixedSize(64, 64)
                # Border rules for 3x3 blocks
                rb = "2px solid #0f172a" if c % 3 == 2 and c != 8 else "1px solid #cbd5e1"
                bb = "2px solid #0f172a" if r % 3 == 2 and r != 8 else "1px solid #cbd5e1"
                btn.setStyleSheet(f"""
                    QPushButton {{
                        border-right: {rb};
                        border-bottom: {bb};
                        border-top: none;
                        border-left: none;
                        border-radius: 0px;
                        background-color: #ffffff;
                        font-size: 24px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #f1f5f9;
                    }}
                """)
                grid_layout.addWidget(btn, r, c)
                row_cells.append(btn)
            self.cells.append(row_cells)

        left_col.addWidget(self.grid_frame)
        body.addLayout(left_col)

        # Right Column: Controls, 3x3 Number Pad, Actions
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Stats
        self.stats_row = QLabel("Mistakes: 0/3   |   Time: 00:00")
        self.stats_row.setStyleSheet("font-size: 16px; font-weight: bold; padding: 12px; background: white; border: 1px solid #e2e8f0;")
        right_col.addWidget(self.stats_row)

        # Keypad 3x3
        pad_grid = QGridLayout()
        pad_grid.setSpacing(12)
        for i in range(1, 10):
            r, c = (i - 1) // 3, (i - 1) % 3
            btn = QPushButton(str(i))
            btn.setFixedHeight(88)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 32px;
                    font-weight: bold;
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 0px;
                }
                QPushButton:hover {
                    background: #f8fafc;
                    border-color: #94a3b8;
                }
            """)
            pad_grid.addWidget(btn, r, c)
        right_col.addLayout(pad_grid)

        # New Game Button
        new_btn = QPushButton("NEW GAME")
        new_btn.setFixedHeight(50)
        new_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 0px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        new_btn.clicked.connect(lambda: self.start_new_puzzle("easy"))
        right_col.addWidget(new_btn)

        body.addLayout(right_col)
        self.main_layout.addLayout(body)

    def start_new_puzzle(self, level="easy"):
        puzzle_data = CURATED_PUZZLES[level][0]
        self.puzzle = puzzle_data["puzzle"]
        self.solution = puzzle_data["solution"]

        for r in range(9):
            for c in range(9):
                val = self.puzzle[r][c]
                btn = self.cells[r][c]
                if val != 0:
                    btn.setText(str(val))
                    btn.setStyleSheet(btn.styleSheet() + "color: #0f172a; font-weight: 800;")
                else:
                    btn.setText("")

    def run(self):
        if PYSIDE_AVAILABLE:
            self.window.show()
            sys.exit(self.app.exec())


if __name__ == "__main__":
    app = SudokuDesktopWindow()
    app.run()
