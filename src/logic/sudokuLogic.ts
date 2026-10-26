/**
 * sudokuLogic.ts
 * Pure TypeScript Sudoku engine matching sudoku_logic.py:
 * Data models, Backtracking solver, Uniqueness validation, Difficulty grader,
 * Scoring formula, Level progression unlock rules, and Daily streak calculations.
 */

export type Difficulty = 'easy' | 'medium' | 'hard' | 'expert';

export type Grid = number[][]; // 9x9 matrix (0 = empty, 1-9 = placed)
export type Notes = Set<number>[][]; // 9x9 matrix of candidate sets
export type BoolGrid = boolean[][];

export interface MoveAction {
  actionType: 'digit' | 'note' | 'erase' | 'auto_notes' | 'hint';
  row: number;
  col: number;
  prevVal: number;
  newVal: number;
  prevNotes: number[];
  newNotes: number[];
  peerNotesChanges?: {
    row: number;
    col: number;
    removedNote: number;
  }[];
}

export interface HistoryRecord {
  id: string;
  date: string; // ISO format 'YYYY-MM-DD'
  timestamp: number;
  level: Difficulty;
  seconds: number;
  score: number;
  hintsUsed: number;
  mistakes: number;
}

export interface GameState {
  id: string;
  level: Difficulty;
  initialGrid: Grid;
  solutionGrid: Grid;
  currentGrid: Grid;
  notes: Notes;
  hintedCells: BoolGrid;
  mistakes: number;
  hintsUsed: number;
  elapsedSeconds: number;
  isPaused: boolean;
  isCompleted: boolean;
  undoStack: MoveAction[];
  redoStack: MoveAction[];
  startTime: number;
  completedTime?: number;
  finalScore: number;
}

export interface UserSettings {
  numberSize: 'small' | 'medium' | 'large';
  showTimer: boolean;
  highlightSameNumbers: boolean;
  colorFeedback: boolean; // default true (green correct, red wrong)
  autoRemoveNotes: boolean; // auto-clear peer notes on correct entry
  soundEffects: boolean;
  hapticFeedback: boolean;
}

export const DEFAULT_SETTINGS: UserSettings = {
  numberSize: 'medium',
  showTimer: true,
  highlightSameNumbers: true,
  colorFeedback: true,
  autoRemoveNotes: true,
  soundEffects: true,
  hapticFeedback: true,
};

export const BASE_SCORES: Record<Difficulty, number> = {
  easy: 1000,
  medium: 2000,
  hard: 4000,
  expert: 8000,
};

// Set to true for the Android release.
export const LEVELS_LOCKED = false;

export const UNLOCK_REQUIREMENTS: Record<Difficulty, { prereq: Difficulty | null; count: number }> = {
  easy: { prereq: null, count: 0 },
  medium: { prereq: 'easy', count: 2 },
  hard: { prereq: 'medium', count: 4 },
  expert: { prereq: 'hard', count: 16 },
};

export function createEmptyGrid(): Grid {
  return Array.from({ length: 9 }, () => Array(9).fill(0));
}

export function createEmptyNotes(): Notes {
  return Array.from({ length: 9 }, () =>
    Array.from({ length: 9 }, () => new Set<number>())
  );
}

export function createEmptyBoolGrid(): BoolGrid {
  return Array.from({ length: 9 }, () => Array(9).fill(false));
}

export function cloneGrid(grid: Grid): Grid {
  return grid.map(row => [...row]);
}

export function cloneNotes(notes: Notes): Notes {
  return notes.map(row => row.map(s => new Set(s)));
}

export function cloneBoolGrid(bg: BoolGrid): BoolGrid {
  return bg.map(row => [...row]);
}

export function getPeers(row: number, col: number): [number, number][] {
  const peerMap = new Map<string, [number, number]>();
  for (let c = 0; c < 9; c++) {
    if (c !== col) peerMap.set(`${row},${c}`, [row, c]);
  }
  for (let r = 0; r < 9; r++) {
    if (r !== row) peerMap.set(`${r},${col}`, [r, col]);
  }
  const br = Math.floor(row / 3) * 3;
  const bc = Math.floor(col / 3) * 3;
  for (let r = br; r < br + 3; r++) {
    for (let c = bc; c < bc + 3; c++) {
      if (r !== row || c !== col) {
        peerMap.set(`${r},${c}`, [r, c]);
      }
    }
  }
  return Array.from(peerMap.values());
}

export function isValidPlacement(grid: Grid, row: number, col: number, val: number): boolean {
  if (val < 1 || val > 9) return false;
  // Row check
  for (let c = 0; c < 9; c++) {
    if (c !== col && grid[row][c] === val) return false;
  }
  // Col check
  for (let r = 0; r < 9; r++) {
    if (r !== row && grid[r][col] === val) return false;
  }
  // Box check
  const br = Math.floor(row / 3) * 3;
  const bc = Math.floor(col / 3) * 3;
  for (let r = br; r < br + 3; r++) {
    for (let c = bc; c < bc + 3; c++) {
      if ((r !== row || c !== col) && grid[r][c] === val) return false;
    }
  }
  return true;
}

export function getCandidates(grid: Grid, row: number, col: number): Set<number> {
  if (grid[row][col] !== 0) return new Set();
  const used = new Set<number>();
  for (let c = 0; c < 9; c++) {
    if (grid[row][c] !== 0) used.add(grid[row][c]);
  }
  for (let r = 0; r < 9; r++) {
    if (grid[r][col] !== 0) used.add(grid[r][col]);
  }
  const br = Math.floor(row / 3) * 3;
  const bc = Math.floor(col / 3) * 3;
  for (let r = br; r < br + 3; r++) {
    for (let c = bc; c < bc + 3; c++) {
      if (grid[r][c] !== 0) used.add(grid[r][c]);
    }
  }
  const candidates = new Set<number>();
  for (let d = 1; d <= 9; d++) {
    if (!used.has(d)) candidates.add(d);
  }
  return candidates;
}

/**
 * Backtracking solver
 */
export function solveSudoku(grid: Grid): Grid | null {
  const sol = cloneGrid(grid);

  function backtrack(): boolean {
    let minCand = 10;
    let bestCell: { r: number; c: number; cand: Set<number> } | null = null;

    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (sol[r][c] === 0) {
          const cand = getCandidates(sol, r, c);
          if (cand.size === 0) return false;
          if (cand.size < minCand) {
            minCand = cand.size;
            bestCell = { r, c, cand };
            if (minCand === 1) break;
          }
        }
      }
      if (minCand === 1) break;
    }

    if (!bestCell) return true; // all filled

    const { r, c, cand } = bestCell;
    for (const val of cand) {
      sol[r][c] = val;
      if (backtrack()) return true;
      sol[r][c] = 0;
    }
    return false;
  }

  return backtrack() ? sol : null;
}

/**
 * Counts solutions up to limit to verify uniqueness
 */
export function countSolutions(grid: Grid, limit = 2): number {
  const work = cloneGrid(grid);
  let count = 0;

  function backtrack(): boolean {
    let minCand = 10;
    let bestCell: { r: number; c: number; cand: Set<number> } | null = null;

    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (work[r][c] === 0) {
          const cand = getCandidates(work, r, c);
          if (cand.size === 0) return false;
          if (cand.size < minCand) {
            minCand = cand.size;
            bestCell = { r, c, cand };
            if (minCand === 1) break;
          }
        }
      }
      if (minCand === 1) break;
    }

    if (!bestCell) {
      count++;
      return count >= limit;
    }

    const { r, c, cand } = bestCell;
    for (const val of cand) {
      work[r][c] = val;
      if (backtrack()) return true;
      work[r][c] = 0;
    }
    return false;
  }

  backtrack();
  return count;
}

export function hasUniqueSolution(grid: Grid): boolean {
  return countSolutions(grid, 2) === 1;
}

/**
 * Scoring Formula:
 * - Base scores: Easy = 1,000; Medium = 2,000; Hard = 4,000; Expert = 8,000.
 * - Time penalty: Subtract 1 point per 5 seconds elapsed (floor(seconds / 5)).
 * - Hint penalty: Subtract 25 points per hint used.
 * - Mistake penalty: Subtract 10 points per mistake made.
 * - Score floor: Score cannot drop below 20% of base score (floor(0.2 * base)).
 */
export function calculateScore(level: Difficulty, seconds: number, hintsUsed: number, mistakes: number): number {
  const base = BASE_SCORES[level];
  const timePenalty = Math.floor(seconds / 5);
  const hintPenalty = 25 * hintsUsed;
  const mistakePenalty = 10 * mistakes;
  const rawScore = base - timePenalty - hintPenalty - mistakePenalty;
  const floorScore = Math.floor(0.2 * base);
  return Math.max(floorScore, rawScore);
}

export function calculateDailyScore(records: HistoryRecord[], targetDate: string): number {
  return records
    .filter(r => r.date === targetDate)
    .reduce((sum, r) => sum + r.score, 0);
}

/**
 * Level Unlock Progression:
 * - Easy: Unlocked by default.
 * - Medium: Unlocks after 2 completed Easy games.
 * - Hard: Unlocks after 4 completed Medium games.
 * - Expert: Unlocks after 16 completed Hard games.
 */
export interface UnlockStatus {
  unlocked: boolean;
  current: number;
  required: number;
  prereq: string | null;
  progressLabel: string;
}

export function getLevelUnlockStatus(historyRecords: HistoryRecord[]): Record<Difficulty, UnlockStatus> {
  const counts: Record<Difficulty, number> = {
    easy: 0,
    medium: 0,
    hard: 0,
    expert: 0,
  };
  for (const r of historyRecords) {
    if (counts[r.level] !== undefined) {
      counts[r.level]++;
    }
  }

  const result = {} as Record<Difficulty, UnlockStatus>;
  const diffs: Difficulty[] = ['easy', 'medium', 'hard', 'expert'];

  for (const lvl of diffs) {
    const req = UNLOCK_REQUIREMENTS[lvl];
    if (!req.prereq) {
      result[lvl] = {
        unlocked: true,
        current: 0,
        required: 0,
        prereq: null,
        progressLabel: 'Unlocked',
      };
    } else {
      const curr = counts[req.prereq];
      const meetsRequirement = curr >= req.count;
      const unlocked = LEVELS_LOCKED ? meetsRequirement : true;
      const capPrereq = req.prereq.charAt(0).toUpperCase() + req.prereq.slice(1);
      result[lvl] = {
        unlocked,
        current: curr,
        required: req.count,
        prereq: capPrereq,
        progressLabel: !LEVELS_LOCKED || unlocked ? 'Unlocked' : `${curr} / ${req.count} ${capPrereq} games`,
      };
    }
  }

  return result;
}

/**
 * Daily Streak Engine:
 * - A streak increment requires at least one completed game on that calendar day.
 * - If played yesterday but not yet today, the streak is maintained.
 * - If two or more calendar days pass without completing a game, the streak resets to 0.
 * - Tracks current streak and all-time best streak.
 */
export function calculateStreak(historyRecords: HistoryRecord[], currentDate: string): { currentStreak: number; bestStreak: number } {
  const dateSet = new Set<string>();
  for (const r of historyRecords) {
    dateSet.add(r.date);
  }
  const dates = Array.from(dateSet).sort();
  if (dates.length === 0) {
    return { currentStreak: 0, bestStreak: 0 };
  }

  const parseDays = (d: string): number => {
    const parts = d.split('-').map(Number);
    const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    return Math.floor(date.getTime() / (1000 * 60 * 60 * 24));
  };

  const dayNumbers = dates.map(parseDays).sort((a, b) => a - b);

  // Best streak calculation
  let bestStreak = 0;
  let run = 0;
  let prevDay: number | null = null;
  for (const day of dayNumbers) {
    if (prevDay === null) {
      run = 1;
    } else if (day === prevDay + 1) {
      run++;
    } else if (day === prevDay) {
      // same day duplicate
    } else {
      run = 1;
    }
    if (run > bestStreak) bestStreak = run;
    prevDay = day;
  }

  // Active streak calculation relative to currentDate
  const todayDay = parseDays(currentDate);
  const lastPlayedDay = dayNumbers[dayNumbers.length - 1];

  // If last played was 2 or more days ago, active streak is 0
  if (todayDay - lastPlayedDay >= 2) {
    return { currentStreak: 0, bestStreak };
  }

  let activeStreak = 1;
  let idx = dayNumbers.length - 1;
  while (idx > 0) {
    if (dayNumbers[idx] - dayNumbers[idx - 1] === 1) {
      activeStreak++;
      idx--;
    } else if (dayNumbers[idx] === dayNumbers[idx - 1]) {
      idx--;
    } else {
      break;
    }
  }

  if (activeStreak > bestStreak) {
    bestStreak = activeStreak;
  }

  return { currentStreak: activeStreak, bestStreak };
}

export function gradePuzzleDifficulty(initialGrid: Grid): Difficulty {
  const grid = cloneGrid(initialGrid);
  const candidates: Set<number>[][] = Array.from({ length: 9 }, (_, r) =>
    Array.from({ length: 9 }, (_, c) =>
      grid[r][c] === 0 ? getCandidates(grid, r, c) : new Set<number>()
    )
  );

  let highestTechnique: Difficulty = 'easy';

  const emptyCellsCount = () => {
    let count = 0;
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (grid[r][c] === 0) count++;
      }
    }
    return count;
  };

  while (emptyCellsCount() > 0) {
    let progress = false;

    // 1. Naked Singles
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (grid[r][c] === 0 && candidates[r][c].size === 1) {
          const val = candidates[r][c].values().next().value!;
          grid[r][c] = val;
          candidates[r][c].clear();
          for (const [pr, pc] of getPeers(r, c)) {
            candidates[pr][pc].delete(val);
          }
          progress = true;
          break;
        }
      }
      if (progress) break;
    }
    if (progress) continue;

    // 2. Hidden Singles
    const units: [number, number][][] = [];
    for (let r = 0; r < 9; r++) units.push(Array.from({ length: 9 }, (_, c) => [r, c]));
    for (let c = 0; c < 9; c++) units.push(Array.from({ length: 9 }, (_, r) => [r, c]));
    for (let br = 0; br < 3; br++) {
      for (let bc = 0; bc < 3; bc++) {
        const box: [number, number][] = [];
        for (let dr = 0; dr < 3; dr++) {
          for (let dc = 0; dc < 3; dc++) {
            box.push([br * 3 + dr, bc * 3 + dc]);
          }
        }
        units.push(box);
      }
    }

    for (const unit of units) {
      for (let d = 1; d <= 9; d++) {
        const possible = unit.filter(([r, c]) => grid[r][c] === 0 && candidates[r][c].has(d));
        if (possible.length === 1) {
          const [r, c] = possible[0];
          grid[r][c] = d;
          candidates[r][c].clear();
          for (const [pr, pc] of getPeers(r, c)) {
            candidates[pr][pc].delete(d);
          }
          progress = true;
          break;
        }
      }
      if (progress) break;
    }
    if (progress) continue;

    // 3. Medium Techniques: Naked Pairs
    for (const unit of units) {
      const pairs = unit.filter(([r, c]) => grid[r][c] === 0 && candidates[r][c].size === 2);
      for (let i = 0; i < pairs.length; i++) {
        for (let j = i + 1; j < pairs.length; j++) {
          const [r1, c1] = pairs[i];
          const [r2, c2] = pairs[j];
          const set1 = Array.from(candidates[r1][c1]).sort().join(',');
          const set2 = Array.from(candidates[r2][c2]).sort().join(',');
          if (set1 === set2) {
            const pairVals = Array.from(candidates[r1][c1]);
            let eliminated = false;
            for (const [r, c] of unit) {
              if ((r !== r1 || c !== c1) && (r !== r2 || c !== c2) && grid[r][c] === 0) {
                for (const v of pairVals) {
                  if (candidates[r][c].delete(v)) eliminated = true;
                }
              }
            }
            if (eliminated) {
              if (highestTechnique === 'easy') highestTechnique = 'medium';
              progress = true;
              break;
            }
          }
        }
        if (progress) break;
      }
      if (progress) break;
    }
    if (progress) continue;

    // Advanced: requires expert logic
    highestTechnique = 'expert';
    break;
  }

  return highestTechnique;
}

export const DIFFICULTY_TARGETS: Record<Difficulty, { minGivens: number; maxGivens: number; target: number; maxTechnique: Difficulty }> = {
  easy: { minGivens: 42, maxGivens: 46, target: 44, maxTechnique: 'easy' },
  medium: { minGivens: 36, maxGivens: 40, target: 38, maxTechnique: 'medium' },
  hard: { minGivens: 30, maxGivens: 34, target: 32, maxTechnique: 'hard' },
  expert: { minGivens: 25, maxGivens: 29, target: 27, maxTechnique: 'expert' },
};

export const TECHNIQUE_RANK: Record<Difficulty, number> = {
  easy: 1,
  medium: 2,
  hard: 3,
  expert: 4,
};

export function generateFullBoard(): Grid {
  const board = createEmptyGrid();
  function fill(): boolean {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (board[r][c] === 0) {
          const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9].sort(() => Math.random() - 0.5);
          for (const num of nums) {
            if (isValidPlacement(board, r, c, num)) {
              board[r][c] = num;
              if (fill()) return true;
              board[r][c] = 0;
            }
          }
          return false;
        }
      }
    }
    return true;
  }
  fill();
  return board;
}

export function generatePuzzle(level: Difficulty, maxAttempts = 50): { puzzle: Grid; solution: Grid } {
  const config = DIFFICULTY_TARGETS[level];
  const { minGivens, maxGivens, target, maxTechnique } = config;

  let bestPuzzle: Grid | null = null;
  let bestSolution: Grid | null = null;
  let bestRankDiff = 999;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const solution = generateFullBoard();
    const puzzle = cloneGrid(solution);

    const rowCounts = Array(9).fill(9);
    const colCounts = Array(9).fill(9);
    const boxCounts = Array(9).fill(9);

    const positions: [number, number][] = [];
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) positions.push([r, c]);
    }
    positions.sort(() => Math.random() - 0.5);

    let currentGivens = 81;
    for (const [r, c] of positions) {
      if (currentGivens <= target) break;
      const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);
      if (level === 'easy') {
        if (rowCounts[r] <= 2 || colCounts[c] <= 2 || boxCounts[b] <= 2) continue;
      }
      const val = puzzle[r][c];
      puzzle[r][c] = 0;
      if (hasUniqueSolution(puzzle)) {
        rowCounts[r]--;
        colCounts[c]--;
        boxCounts[b]--;
        currentGivens--;
      } else {
        puzzle[r][c] = val;
      }
    }

    if (currentGivens >= minGivens && currentGivens <= maxGivens) {
      if (level === 'easy') {
        if (Math.min(...rowCounts) < 2 || Math.min(...colCounts) < 2 || Math.min(...boxCounts) < 2) continue;
      }
      const tech = gradePuzzleDifficulty(puzzle);
      if (TECHNIQUE_RANK[tech] <= TECHNIQUE_RANK[maxTechnique]) {
        return { puzzle, solution };
      }
      const rankDiff = Math.abs(TECHNIQUE_RANK[tech] - TECHNIQUE_RANK[maxTechnique]);
      if (rankDiff < bestRankDiff) {
        bestPuzzle = cloneGrid(puzzle);
        bestSolution = cloneGrid(solution);
        bestRankDiff = rankDiff;
      }
    }
  }

  if (bestPuzzle && bestSolution) {
    return { puzzle: bestPuzzle, solution: bestSolution };
  }

  const pool = CURATED_PUZZLES[level];
  const choice = pool[Math.floor(Math.random() * pool.length)];
  return {
    puzzle: cloneGrid(choice.puzzle),
    solution: cloneGrid(choice.solution),
  };
}

/**
 * Recalibrated Curated Puzzles for instantaneous loading
 * - Easy: 44 givens, singles only, no row/col/box < 2 givens.
 * - Medium: 38 givens.
 * - Hard: 32 givens.
 * - Expert: 27 givens.
 */
export const CURATED_PUZZLES: Record<Difficulty, { puzzle: Grid; solution: Grid }[]> = {
  easy: [
    {
      puzzle: [
        [9, 7, 0, 0, 0, 0, 0, 0, 3],
        [1, 0, 0, 4, 6, 0, 0, 5, 9],
        [5, 0, 0, 7, 0, 8, 4, 2, 1],
        [0, 0, 0, 6, 1, 7, 0, 3, 0],
        [3, 8, 1, 0, 4, 9, 0, 6, 7],
        [0, 0, 7, 8, 3, 0, 9, 0, 2],
        [6, 4, 5, 0, 7, 0, 3, 0, 8],
        [8, 0, 0, 0, 5, 4, 0, 0, 6],
        [0, 9, 0, 3, 0, 0, 1, 0, 5],
      ],
      solution: [
        [9, 7, 4, 5, 2, 1, 6, 8, 3],
        [1, 2, 8, 4, 6, 3, 7, 5, 9],
        [5, 3, 6, 7, 9, 8, 4, 2, 1],
        [2, 5, 9, 6, 1, 7, 8, 3, 4],
        [3, 8, 1, 2, 4, 9, 5, 6, 7],
        [4, 6, 7, 8, 3, 5, 9, 1, 2],
        [6, 4, 5, 1, 7, 2, 3, 9, 8],
        [8, 1, 3, 9, 5, 4, 2, 7, 6],
        [7, 9, 2, 3, 8, 6, 1, 4, 5],
      ],
    },
    {
      puzzle: [
        [6, 0, 9, 0, 0, 0, 8, 0, 5],
        [7, 0, 4, 0, 0, 0, 1, 9, 2],
        [0, 8, 0, 9, 2, 0, 0, 4, 7],
        [0, 1, 2, 3, 0, 8, 0, 5, 9],
        [0, 0, 0, 2, 9, 7, 0, 1, 6],
        [9, 6, 7, 0, 0, 1, 2, 8, 0],
        [0, 0, 0, 8, 4, 0, 5, 6, 0],
        [5, 9, 8, 0, 1, 6, 0, 0, 4],
        [0, 0, 0, 5, 3, 2, 0, 0, 0],
      ],
      solution: [
        [6, 2, 9, 1, 7, 4, 8, 3, 5],
        [7, 5, 4, 6, 8, 3, 1, 9, 2],
        [3, 8, 1, 9, 2, 5, 6, 4, 7],
        [4, 1, 2, 3, 6, 8, 7, 5, 9],
        [8, 3, 5, 2, 9, 7, 4, 1, 6],
        [9, 6, 7, 4, 5, 1, 2, 8, 3],
        [2, 7, 3, 8, 4, 9, 5, 6, 1],
        [5, 9, 8, 7, 1, 6, 3, 2, 4],
        [1, 4, 6, 5, 3, 2, 9, 7, 8],
      ],
    },
  ],
  medium: [
    {
      puzzle: [
        [9, 7, 0, 0, 0, 0, 0, 0, 3],
        [1, 0, 0, 0, 0, 0, 0, 5, 9],
        [5, 0, 0, 7, 0, 8, 4, 2, 1],
        [0, 0, 0, 6, 1, 7, 0, 3, 0],
        [0, 8, 1, 0, 4, 0, 0, 6, 7],
        [0, 0, 7, 8, 0, 0, 9, 0, 2],
        [6, 4, 5, 0, 7, 0, 3, 0, 8],
        [8, 0, 0, 0, 5, 4, 0, 0, 6],
        [0, 0, 0, 3, 0, 0, 1, 0, 5],
      ],
      solution: [
        [9, 7, 4, 5, 2, 1, 6, 8, 3],
        [1, 2, 8, 4, 6, 3, 7, 5, 9],
        [5, 3, 6, 7, 9, 8, 4, 2, 1],
        [2, 5, 9, 6, 1, 7, 8, 3, 4],
        [3, 8, 1, 2, 4, 9, 5, 6, 7],
        [4, 6, 7, 8, 3, 5, 9, 1, 2],
        [6, 4, 5, 1, 7, 2, 3, 9, 8],
        [8, 1, 3, 9, 5, 4, 2, 7, 6],
        [7, 9, 2, 3, 8, 6, 1, 4, 5],
      ],
    },
    {
      puzzle: [
        [0, 0, 9, 0, 0, 0, 8, 0, 5],
        [7, 0, 4, 0, 0, 0, 1, 9, 2],
        [0, 8, 0, 0, 2, 0, 0, 4, 7],
        [0, 1, 2, 3, 0, 8, 0, 5, 0],
        [0, 0, 0, 2, 9, 0, 0, 1, 6],
        [9, 6, 7, 0, 0, 1, 2, 8, 0],
        [0, 0, 0, 0, 4, 0, 5, 6, 0],
        [5, 9, 8, 0, 1, 6, 0, 0, 4],
        [0, 0, 0, 5, 3, 0, 0, 0, 0],
      ],
      solution: [
        [6, 2, 9, 1, 7, 4, 8, 3, 5],
        [7, 5, 4, 6, 8, 3, 1, 9, 2],
        [3, 8, 1, 9, 2, 5, 6, 4, 7],
        [4, 1, 2, 3, 6, 8, 7, 5, 9],
        [8, 3, 5, 2, 9, 7, 4, 1, 6],
        [9, 6, 7, 4, 5, 1, 2, 8, 3],
        [2, 7, 3, 8, 4, 9, 5, 6, 1],
        [5, 9, 8, 7, 1, 6, 3, 2, 4],
        [1, 4, 6, 5, 3, 2, 9, 7, 8],
      ],
    },
  ],
  hard: [
    {
      puzzle: [
        [9, 7, 0, 0, 0, 0, 0, 0, 3],
        [1, 0, 0, 0, 0, 0, 0, 5, 9],
        [0, 0, 0, 0, 0, 8, 4, 2, 1],
        [0, 0, 0, 6, 1, 0, 0, 3, 0],
        [0, 8, 0, 0, 4, 0, 0, 6, 0],
        [0, 0, 7, 8, 0, 0, 9, 0, 2],
        [6, 4, 5, 0, 7, 0, 3, 0, 8],
        [0, 0, 0, 0, 5, 4, 0, 0, 6],
        [0, 0, 0, 3, 0, 0, 1, 0, 5],
      ],
      solution: [
        [9, 7, 4, 5, 2, 1, 6, 8, 3],
        [1, 2, 8, 4, 6, 3, 7, 5, 9],
        [5, 3, 6, 7, 9, 8, 4, 2, 1],
        [2, 5, 9, 6, 1, 7, 8, 3, 4],
        [3, 8, 1, 2, 4, 9, 5, 6, 7],
        [4, 6, 7, 8, 3, 5, 9, 1, 2],
        [6, 4, 5, 1, 7, 2, 3, 9, 8],
        [8, 1, 3, 9, 5, 4, 2, 7, 6],
        [7, 9, 2, 3, 8, 6, 1, 4, 5],
      ],
    },
    {
      puzzle: [
        [0, 0, 9, 0, 0, 0, 8, 0, 0],
        [7, 0, 4, 0, 0, 0, 1, 0, 2],
        [0, 8, 0, 0, 2, 0, 0, 4, 0],
        [0, 1, 2, 3, 0, 8, 0, 5, 0],
        [0, 0, 0, 2, 9, 0, 0, 1, 6],
        [9, 6, 7, 0, 0, 1, 2, 8, 0],
        [0, 0, 0, 0, 0, 0, 5, 6, 0],
        [5, 9, 8, 0, 1, 6, 0, 0, 0],
        [0, 0, 0, 5, 0, 0, 0, 0, 0],
      ],
      solution: [
        [6, 2, 9, 1, 7, 4, 8, 3, 5],
        [7, 5, 4, 6, 8, 3, 1, 9, 2],
        [3, 8, 1, 9, 2, 5, 6, 4, 7],
        [4, 1, 2, 3, 6, 8, 7, 5, 9],
        [8, 3, 5, 2, 9, 7, 4, 1, 6],
        [9, 6, 7, 4, 5, 1, 2, 8, 3],
        [2, 7, 3, 8, 4, 9, 5, 6, 1],
        [5, 9, 8, 7, 1, 6, 3, 2, 4],
        [1, 4, 6, 5, 3, 2, 9, 7, 8],
      ],
    },
  ],
  expert: [
    {
      puzzle: [
        [9, 7, 0, 0, 0, 0, 0, 0, 3],
        [1, 0, 0, 0, 0, 0, 0, 5, 9],
        [0, 0, 0, 0, 0, 8, 4, 2, 0],
        [0, 0, 0, 6, 1, 0, 0, 3, 0],
        [0, 8, 0, 0, 4, 0, 0, 6, 0],
        [0, 0, 0, 0, 0, 0, 9, 0, 2],
        [6, 4, 0, 0, 7, 0, 3, 0, 8],
        [0, 0, 0, 0, 0, 4, 0, 0, 6],
        [0, 0, 0, 3, 0, 0, 1, 0, 5],
      ],
      solution: [
        [9, 7, 4, 5, 2, 1, 6, 8, 3],
        [1, 2, 8, 4, 6, 3, 7, 5, 9],
        [5, 3, 6, 7, 9, 8, 4, 2, 1],
        [2, 5, 9, 6, 1, 7, 8, 3, 4],
        [3, 8, 1, 2, 4, 9, 5, 6, 7],
        [4, 6, 7, 8, 3, 5, 9, 1, 2],
        [6, 4, 5, 1, 7, 2, 3, 9, 8],
        [8, 1, 3, 9, 5, 4, 2, 7, 6],
        [7, 9, 2, 3, 8, 6, 1, 4, 5],
      ],
    },
    {
      puzzle: [
        [0, 0, 9, 0, 0, 0, 8, 0, 0],
        [7, 0, 4, 0, 0, 0, 1, 0, 2],
        [0, 8, 0, 0, 2, 0, 0, 4, 0],
        [0, 1, 2, 3, 0, 8, 0, 5, 0],
        [0, 0, 0, 2, 9, 0, 0, 1, 0],
        [0, 6, 7, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 6, 0],
        [5, 9, 8, 0, 1, 6, 0, 0, 0],
        [0, 0, 0, 5, 0, 0, 0, 0, 0],
      ],
      solution: [
        [6, 2, 9, 1, 7, 4, 8, 3, 5],
        [7, 5, 4, 6, 8, 3, 1, 9, 2],
        [3, 8, 1, 9, 2, 5, 6, 4, 7],
        [4, 1, 2, 3, 6, 8, 7, 5, 9],
        [8, 3, 5, 2, 9, 7, 4, 1, 6],
        [9, 6, 7, 4, 5, 1, 2, 8, 3],
        [2, 7, 3, 8, 4, 9, 5, 6, 1],
        [5, 9, 8, 7, 1, 6, 3, 2, 4],
        [1, 4, 6, 5, 3, 2, 9, 7, 8],
      ],
    },
  ],
};

/**
 * Returns a new puzzle for the given level from cache or dynamic generator
 */
export function getNewPuzzle(level: Difficulty): { puzzle: Grid; solution: Grid } {
  // Use curated seed or generate on the fly
  const pool = CURATED_PUZZLES[level];
  const choice = pool[Math.floor(Math.random() * pool.length)];
  return {
    puzzle: cloneGrid(choice.puzzle),
    solution: cloneGrid(choice.solution),
  };
}
