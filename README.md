# ZenSudoku - Minimalist Desktop & Web Sudoku

A minimalist, distraction-free Sudoku application with clean slate aesthetics, quiet gamification, daily streaks, and an isolated pure logic engine.

---

## Running in VS Code on Your Local PC

You can run this project in two ways:
- **Method 1: The Modern Web App** (React + TypeScript + Vite) — Full UI with procedural audio, modals, analytics, responsive design.
- **Method 2: The Pure Python Desktop App** (`PySide6` + `sudoku_logic.py`) — Native OS desktop window, 100% Python with zero web dependencies.

---

### Method 1: Running the Web App (Recommended)

#### Prerequisites
- [Node.js](https://nodejs.org/) (Version 18 or higher)
- [VS Code](https://code.visualstudio.com/)

#### Steps in VS Code:
1. Open the project folder in VS Code (`File > Open Folder...`).
2. Open the built-in terminal in VS Code:
   - Shortcut: ``Ctrl + ` `` (Windows/Linux) or ``Cmd + ` `` (Mac), or click **Terminal > New Terminal**.
3. Install the dependencies:
   ```bash
   npm install
   ```
4. Start the local development server:
   ```bash
   npm run dev
   ```
5. Click the local URL in the terminal (usually `http://localhost:3000` or `http://localhost:5173`) or open it in your browser.

#### Building for Production:
To create an optimized production build:
```bash
npm run build
npm run preview
```
The compiled, static production files will be in the `dist/` directory.

---

### Method 2: Running the Pure Python Desktop App

#### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- Python extension installed in VS Code

#### Steps in VS Code:
1. Open the project folder in VS Code.
2. Open the terminal (``Ctrl + ` `` or **Terminal > New Terminal**).
3. (Optional but recommended) Create and activate a virtual environment:
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
4. Install PySide6 (Qt framework for Python):
   ```bash
   pip install PySide6
   ```
5. Run the unit test suite to verify the pure logic engine:
   ```bash
   python -m unittest test_sudoku_logic.py
   ```
6. Launch the desktop GUI:
   ```bash
   python desktop_app.py
   ```

---

## Project Structure

```
├── sudoku_logic.py          # 100% Pure Python engine (zero GUI/system imports)
├── test_sudoku_logic.py     # Python unit tests (backtracking, grader, streaks)
├── desktop_app.py           # Native desktop GUI using PySide6
│
├── src/
│   ├── logic/
│   │   ├── sudokuLogic.ts      # TypeScript logic engine matching Python module
│   │   └── sudokuLogic.test.ts # Unit tests for TS engine (node:test)
│   ├── components/
│   │   ├── Header.tsx          # Top bar with daily score & streak
│   │   ├── DifficultySelector.tsx # Level tabs with progressive locks
│   │   ├── SudokuGrid.tsx      # 9x9 sharp-corner board with color feedback
│   │   ├── ControlsColumn.tsx  # Circular tools, 3x3 large number pad
│   │   ├── HomeScreen.tsx      # Overview, stats, continue game
│   │   ├── LivesModal.tsx      # 3-mistakes modal with 5-second countdown
│   │   ├── CompletionModal.tsx # Solved recap and score breakdown
│   │   ├── AnalyticsModal.tsx  # Calendar history and difficulty stats
│   │   └── SettingsModal.tsx   # Sizing, audio, and JSON backup
│   ├── utils/
│   │   ├── soundEffects.ts     # Procedural Web Audio synthesizer
│   │   └── storage.ts          # LocalStorage manager (zensudoku_data.json)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── index.html
```
