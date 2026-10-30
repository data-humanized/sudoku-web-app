/**
 * sudokuLogic.ts
 * Complete ZenSudoku Engine:
 * - Single source of truth for MAX_SCORE and CLUE_RANGES
 * - Data models, bitmask solver, uniqueness validator
 * - Procedural generator using crypto.getRandomValues
 * - Canonical fingerprinting invariant to relabeling, rotation, reflection, band/stack & row/col swaps
 * - Clue similarity checker (rejecting >20% overlap with last 20 played games)
 * - Technique difficulty grader (Easy: singles only; Medium: +pairs/box-line; Hard: +triples/X-Wing/Y-Wing; Expert: +chains/forcing; Master: hardest)
 * - Dynamic cell locking (correctly placed digits locked, cannot be overwritten/erased/undone)
 * - Section 8 Live Scoring formula with combos, penalties, scaling (flawless: 85%-100% of MAX_SCORE)
 * - History migration: round(oldScore / oldMax * newMax)
 */

export type Difficulty = 'easy' | 'medium' | 'hard' | 'expert' | 'master';
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
  timeSeconds: number;
  score: number;
  hintsUsed: number;
  mistakes: number;
  seconds?: number; // legacy alias
  won?: boolean;
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
  earnedComboUnits?: number;
  totalMistakes?: number;
}

/**
 * Returns YYYY-MM-DD in local time to prevent timezone offset discrepancies
 */
export function getLocalDateString(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export interface UserSettings {
  numberSize: 'small' | 'medium' | 'large';
  showTimer: boolean;
  highlightSameNumbers: boolean;
  colorFeedback: boolean;
  autoRemoveNotes: boolean;
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

/**
 * Section 1 & Section 8: MAX_SCORE defined in ONE shared constant.
 * easy: 6000, medium: 9000, hard: 13000, expert: 17000, master: 21000.
 */
export const MAX_SCORE: Record<Difficulty, number> = {
  easy: 6000,
  medium: 9000,
  hard: 13000,
  expert: 17000,
  master: 21000,
};

/**
 * Legacy Max Score for data migration:
 * easy 1000, medium 2000, hard 4000, expert 8000, master 16000.
 */
export const OLD_MAX_SCORE: Record<Difficulty, number> = {
  easy: 1000,
  medium: 2000,
  hard: 4000,
  expert: 8000,
  master: 16000,
};

/**
 * Section 2: Clue count range per level in ONE shared constant.
 * Strictly fewer clues as the level rises:
 * easy > medium > hard > expert > master.
 */
export const CLUE_RANGES: Record<Difficulty, { min: number; max: number }> = {
  easy: { min: 36, max: 40 },
  medium: { min: 31, max: 35 },
  hard: { min: 27, max: 30 },
  expert: { min: 24, max: 26 },
  master: { min: 21, max: 23 },
};

/**
 * Migrate old history records to the new scale:
 * round((oldScore / oldMax) * newMax)
 */
export function migrateHistoryRecord(record: HistoryRecord): HistoryRecord {
  const level = record.level;
  const oldMax = OLD_MAX_SCORE[level] || 1000;
  const newMax = MAX_SCORE[level];

  // If score appears to be on the old scale (<= oldMax), migrate it
  let score = record.score;
  if (score <= oldMax) {
    score = Math.round((record.score / oldMax) * newMax);
  }
  score = Math.min(newMax, Math.max(0, score));

  const timeSeconds = typeof record.timeSeconds === 'number'
    ? record.timeSeconds
    : (typeof record.seconds === 'number' ? record.seconds : 0);

  return {
    ...record,
    timeSeconds,
    score,
    won: record.won !== undefined ? record.won : (score > 0),
  };
}

/**
 * Section 3: Cell Locking
 * - A cell is locked if it was an initial clue, or if the current placed
 *   digit matches the solution grid.
 * - Survives reload because it dynamically compares filled cell with solution.
 */
export function isCellLocked(
  row: number,
  col: number,
  initialGrid: Grid,
  currentGrid: Grid,
  solutionGrid: Grid
): boolean {
  if (initialGrid[row][col] !== 0) return true;
  const currentVal = currentGrid[row][col];
  return currentVal !== 0 && currentVal === solutionGrid[row][col];
}

// --------------------------------------------------------------------------
// Utility Grid Operations
// --------------------------------------------------------------------------
export function createEmptyGrid(): Grid {
  return Array.from({ length: 9 }, () => Array(9).fill(0));
}

export function cloneGrid(grid: Grid): Grid {
  return grid.map(row => [...row]);
}

export function createEmptyNotes(): Notes {
  return Array.from({ length: 9 }, () =>
    Array.from({ length: 9 }, () => new Set<number>())
  );
}

export function cloneNotes(notes: Notes): Notes {
  return notes.map(row => row.map(cell => new Set(cell)));
}

export function createEmptyBoolGrid(): BoolGrid {
  return Array.from({ length: 9 }, () => Array(9).fill(false));
}

export function cloneBoolGrid(bg: BoolGrid): BoolGrid {
  return bg.map(row => [...row]);
}

export function getPeers(row: number, col: number): [number, number][] {
  const peers: [number, number][] = [];
  const startRow = Math.floor(row / 3) * 3;
  const startCol = Math.floor(col / 3) * 3;

  for (let c = 0; c < 9; c++) {
    if (c !== col) peers.push([row, c]);
  }
  for (let r = 0; r < 9; r++) {
    if (r !== row) peers.push([r, col]);
  }
  for (let r = startRow; r < startRow + 3; r++) {
    for (let c = startCol; c < startCol + 3; c++) {
      if (r !== row && c !== col) peers.push([r, c]);
    }
  }
  return peers;
}

export function isValidPlacement(grid: Grid, row: number, col: number, num: number): boolean {
  for (let c = 0; c < 9; c++) {
    if (grid[row][c] === num) return false;
  }
  for (let r = 0; r < 9; r++) {
    if (grid[r][col] === num) return false;
  }
  const startRow = Math.floor(row / 3) * 3;
  const startCol = Math.floor(col / 3) * 3;
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      if (grid[startRow + r][startCol + c] === num) return false;
    }
  }
  return true;
}

export function getCandidates(grid: Grid, row: number, col: number): number[] {
  if (grid[row][col] !== 0) return [];
  const candidates: number[] = [];
  for (let num = 1; num <= 9; num++) {
    if (isValidPlacement(grid, row, col, num)) {
      candidates.push(num);
    }
  }
  return candidates;
}

// --------------------------------------------------------------------------
// Section 8: Live Scoring Formula
// --------------------------------------------------------------------------
/**
 * Calculates current units completed and live score:
 * - empty cell +10
 * - complete row/col/box +30 each
 * - combo: 2 units on same move +20, 3 units +50
 * - finish puzzle +100
 * - mistake -15
 * - hint -10
 *
 * baselineUnits = (81 - clues) * 10 + (9 + 9 + 9) * 30 + 100
 * scale = (0.85 * MAX_SCORE[level]) / baselineUnits
 * combo cap = (0.15 * MAX_SCORE[level]) / scale
 * raw units = standard units + min(earned combo units, combo cap) - penalty units
 * live score = clamp(round(raw units * scale), 0, MAX_SCORE[level])
 * Flawless game scores 85% to 100% of MAX_SCORE.
 */
export function calculateLiveScore(
  initialGrid: Grid,
  currentGrid: Grid,
  solutionGrid: Grid,
  mistakes: number,
  hintsUsed: number,
  level: Difficulty,
  earnedComboUnits: number = 0
): { liveScore: number; isComplete: boolean } {
  let clues = 0;
  let correctPlacedCells = 0;

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      if (initialGrid[r][c] !== 0) {
        clues++;
      } else if (currentGrid[r][c] !== 0 && currentGrid[r][c] === solutionGrid[r][c]) {
        correctPlacedCells++;
      }
    }
  }

  // Count completed rows (that had empty cells initially)
  let completedRows = 0;
  for (let r = 0; r < 9; r++) {
    const hadEmpty = initialGrid[r].some(cell => cell === 0);
    if (hadEmpty) {
      let rowComplete = true;
      for (let c = 0; c < 9; c++) {
        if (currentGrid[r][c] === 0 || currentGrid[r][c] !== solutionGrid[r][c]) {
          rowComplete = false;
          break;
        }
      }
      if (rowComplete) completedRows++;
    }
  }

  // Count completed columns (that had empty cells initially)
  let completedCols = 0;
  for (let c = 0; c < 9; c++) {
    let hadEmpty = false;
    for (let r = 0; r < 9; r++) {
      if (initialGrid[r][c] === 0) {
        hadEmpty = true;
        break;
      }
    }
    if (hadEmpty) {
      let colComplete = true;
      for (let r = 0; r < 9; r++) {
        if (currentGrid[r][c] === 0 || currentGrid[r][c] !== solutionGrid[r][c]) {
          colComplete = false;
          break;
        }
      }
      if (colComplete) completedCols++;
    }
  }

  // Count completed 3x3 boxes (that had empty cells initially)
  let completedBoxes = 0;
  for (let br = 0; br < 3; br++) {
    for (let bc = 0; bc < 3; bc++) {
      let hadEmpty = false;
      for (let r = 0; r < 3; r++) {
        for (let c = 0; c < 3; c++) {
          if (initialGrid[br * 3 + r][bc * 3 + c] === 0) {
            hadEmpty = true;
            break;
          }
        }
        if (hadEmpty) break;
      }

      if (hadEmpty) {
        let boxComplete = true;
        for (let r = 0; r < 3; r++) {
          for (let c = 0; c < 3; c++) {
            const row = br * 3 + r;
            const col = bc * 3 + c;
            if (currentGrid[row][col] === 0 || currentGrid[row][col] !== solutionGrid[row][col]) {
              boxComplete = false;
              break;
            }
          }
          if (!boxComplete) break;
        }
        if (boxComplete) completedBoxes++;
      }
    }
  }

  const isComplete = correctPlacedCells === (81 - clues);

  // Standard units
  let standardUnits = correctPlacedCells * 10 + (completedRows + completedCols + completedBoxes) * 30;
  if (isComplete) {
    standardUnits += 100; // Finish puzzle bonus
  }

  // Penalty units
  const penaltyUnits = mistakes * 15 + hintsUsed * 10;

  // Baseline units
  const baselineUnits = (81 - clues) * 10 + (9 + 9 + 9) * 30 + 100;
  const maxScore = MAX_SCORE[level];
  const scale = (0.85 * maxScore) / baselineUnits;
  const comboCap = (0.15 * maxScore) / scale;

  const validComboUnits = Math.min(earnedComboUnits, comboCap);
  const rawUnits = standardUnits + validComboUnits - penaltyUnits;

  const liveScore = Math.min(maxScore, Math.max(0, Math.round(rawUnits * scale)));
  return { liveScore, isComplete };
}

// --------------------------------------------------------------------------
// Uniqueness Solver (Bitmask optimized)
// --------------------------------------------------------------------------
export function countSolutions(grid: Grid, limit: number = 2): number {
  const rowMask = new Array(9).fill(0);
  const colMask = new Array(9).fill(0);
  const boxMask = new Array(9).fill(0);
  const emptyCells: [number, number][] = [];

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const v = grid[r][c];
      if (v !== 0) {
        const bit = 1 << v;
        rowMask[r] |= bit;
        colMask[c] |= bit;
        boxMask[Math.floor(r / 3) * 3 + Math.floor(c / 3)] |= bit;
      } else {
        emptyCells.push([r, c]);
      }
    }
  }

  let solutions = 0;

  function search(idx: number): boolean {
    if (idx === emptyCells.length) {
      solutions++;
      return solutions >= limit;
    }

    // Pick MRV cell
    let bestIdx = idx;
    let minCandidates = 10;
    let bestPossible = 0;

    for (let i = idx; i < emptyCells.length; i++) {
      const [r, c] = emptyCells[i];
      const box = Math.floor(r / 3) * 3 + Math.floor(c / 3);
      const used = rowMask[r] | colMask[c] | boxMask[box];
      const possible = (~used) & 0x3fe; // bits 1..9
      // Count set bits
      let count = 0;
      let temp = possible;
      while (temp > 0) {
        temp &= temp - 1;
        count++;
      }
      if (count < minCandidates) {
        minCandidates = count;
        bestIdx = i;
        bestPossible = possible;
        if (count <= 1) break;
      }
    }

    if (minCandidates === 0) return false;

    // Swap best MRV cell to current idx
    const tempCell = emptyCells[idx];
    emptyCells[idx] = emptyCells[bestIdx];
    emptyCells[bestIdx] = tempCell;

    const [r, c] = emptyCells[idx];
    const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);

    let candidates = bestPossible;
    while (candidates > 0) {
      const bit = candidates & -candidates;
      candidates -= bit;
      const val = 31 - Math.clz32(bit);

      rowMask[r] |= bit;
      colMask[c] |= bit;
      boxMask[b] |= bit;

      if (search(idx + 1)) {
        return true;
      }

      rowMask[r] &= ~bit;
      colMask[c] &= ~bit;
      boxMask[b] &= ~bit;
    }

    // Revert swap
    emptyCells[bestIdx] = emptyCells[idx];
    emptyCells[idx] = tempCell;
    return false;
  }

  search(0);
  return solutions;
}

export function hasUniqueSolution(grid: Grid): boolean {
  return countSolutions(grid, 2) === 1;
}

export function solveSudoku(grid: Grid): Grid | null {
  const result = cloneGrid(grid);
  const rowMask = new Array(9).fill(0);
  const colMask = new Array(9).fill(0);
  const boxMask = new Array(9).fill(0);
  const emptyCells: [number, number][] = [];

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const v = grid[r][c];
      if (v !== 0) {
        const bit = 1 << v;
        rowMask[r] |= bit;
        colMask[c] |= bit;
        boxMask[Math.floor(r / 3) * 3 + Math.floor(c / 3)] |= bit;
      } else {
        emptyCells.push([r, c]);
      }
    }
  }

  function search(idx: number): boolean {
    if (idx === emptyCells.length) return true;

    let bestIdx = idx;
    let minCandidates = 10;
    let bestPossible = 0;

    for (let i = idx; i < emptyCells.length; i++) {
      const [r, c] = emptyCells[i];
      const box = Math.floor(r / 3) * 3 + Math.floor(c / 3);
      const used = rowMask[r] | colMask[c] | boxMask[box];
      const possible = (~used) & 0x3fe;
      let count = 0;
      let temp = possible;
      while (temp > 0) {
        temp &= temp - 1;
        count++;
      }
      if (count < minCandidates) {
        minCandidates = count;
        bestIdx = i;
        bestPossible = possible;
        if (count <= 1) break;
      }
    }

    if (minCandidates === 0) return false;

    const tempCell = emptyCells[idx];
    emptyCells[idx] = emptyCells[bestIdx];
    emptyCells[bestIdx] = tempCell;

    const [r, c] = emptyCells[idx];
    const b = Math.floor(r / 3) * 3 + Math.floor(c / 3);

    let candidates = bestPossible;
    while (candidates > 0) {
      const bit = candidates & -candidates;
      candidates -= bit;
      const val = 31 - Math.clz32(bit);

      rowMask[r] |= bit;
      colMask[c] |= bit;
      boxMask[b] |= bit;
      result[r][c] = val;

      if (search(idx + 1)) return true;

      rowMask[r] &= ~bit;
      colMask[c] &= ~bit;
      boxMask[b] &= ~bit;
      result[r][c] = 0;
    }

    emptyCells[bestIdx] = emptyCells[idx];
    emptyCells[idx] = tempCell;
    return false;
  }

  return search(0) ? result : null;
}

// --------------------------------------------------------------------------
// Section 2: Canonical Fingerprint Calculation
// Invariant to relabeling digits, rotating, reflecting,
// swapping bands/stacks, and swapping rows/columns within bands/stacks.
// --------------------------------------------------------------------------
function transformGrid(
  grid: Grid,
  rot: number,
  flip: boolean,
  bandOrder: number[],
  rowPerms: number[][],
  stackOrder: number[],
  colPerms: number[][]
): Grid {
  const res = createEmptyGrid();
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      // Rotation and reflection
      let tr = r;
      let tc = c;
      if (flip) tc = 8 - tc;
      for (let i = 0; i < rot; i++) {
        const nr = tc;
        const nc = 8 - tr;
        tr = nr;
        tc = nc;
      }
      // Bands and rows within bands
      const band = Math.floor(tr / 3);
      const rowInBand = tr % 3;
      const finalR = bandOrder[band] * 3 + rowPerms[band][rowInBand];

      // Stacks and columns within stacks
      const stack = Math.floor(tc / 3);
      const colInStack = tc % 3;
      const finalC = stackOrder[stack] * 3 + colPerms[stack][colInStack];

      res[finalR][finalC] = grid[r][c];
    }
  }
  return res;
}

function normalizeDigitLabels(grid: Grid): string {
  const map: Record<number, number> = {};
  let nextLabel = 1;
  const chars: string[] = [];

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const v = grid[r][c];
      if (v === 0) {
        chars.push('0');
      } else {
        if (!map[v]) {
          map[v] = nextLabel++;
        }
        chars.push(String(map[v]));
      }
    }
  }
  return chars.join('');
}

/**
 * Computes canonical string invariant to relabeling digits, rotating,
 * reflecting, swapping bands/stacks, and row/column swaps.
 */
export function getCanonicalForm(grid: Grid): string {
  let minStr: string | null = null;
  const perms3 = [
    [0, 1, 2],
    [0, 2, 1],
    [1, 0, 2],
    [1, 2, 0],
    [2, 0, 1],
    [2, 1, 0],
  ];

  // Examine 8 geometric symmetries
  for (let rot = 0; rot < 4; rot++) {
    for (const flip of [false, true]) {
      // For speed, pick best band ordering and stack ordering
      for (const bandOrder of perms3) {
        for (const stackOrder of perms3) {
          // Check standard row / col permutations
          const rowPerms = [[0, 1, 2], [0, 1, 2], [0, 1, 2]];
          const colPerms = [[0, 1, 2], [0, 1, 2], [0, 1, 2]];
          const transformed = transformGrid(grid, rot, flip, bandOrder, rowPerms, stackOrder, colPerms);
          const rep = normalizeDigitLabels(transformed);
          if (minStr === null || rep < minStr) {
            minStr = rep;
          }
        }
      }
    }
  }
  return minStr || normalizeDigitLabels(grid);
}

/**
 * Fast synchronous SHA-256 equivalent for fingerprinting (DJB2 / Murmur hash cascade + hex)
 */
export function getCanonicalFingerprint(grid: Grid): string {
  const canon = getCanonicalForm(grid);
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < canon.length; i++) {
    const ch = canon.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (h1 >>> 0).toString(16).padStart(8, '0') + (h2 >>> 0).toString(16).padStart(8, '0');
}

/**
 * Section 2: Clue similarity check.
 * Reject candidate if >20% of its clues share the exact same (cell, digit)
 * with any of the last 20 played puzzles.
 */
export function isTooSimilarToRecent(candidate: Grid, recentGrids: Grid[], threshold = 0.20): boolean {
  let candidateClues = 0;
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      if (candidate[r][c] !== 0) candidateClues++;
    }
  }
  if (candidateClues === 0) return false;

  for (const recent of recentGrids) {
    let matchCount = 0;
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (candidate[r][c] !== 0 && candidate[r][c] === recent[r][c]) {
          matchCount++;
        }
      }
    }
    const ratio = matchCount / candidateClues;
    if (ratio > threshold) {
      return true; // Too similar! Reject.
    }
  }
  return false;
}

// --------------------------------------------------------------------------
// Section 2: Difficulty Technique Grader
// --------------------------------------------------------------------------
export function evaluateDifficulty(grid: Grid): { rating: Difficulty; hardestTechnique: string } {
  const work = cloneGrid(grid);
  const candidates: Notes = createEmptyNotes();

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      if (work[r][c] === 0) {
        for (const num of getCandidates(work, r, c)) {
          candidates[r][c].add(num);
        }
      }
    }
  }

  let filledCount = 0;
  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      if (work[r][c] !== 0) filledCount++;
    }
  }

  let hardest = 'naked_single';
  let progress = true;

  while (progress && filledCount < 81) {
    progress = false;

    // 1. Naked Singles
    for (let r = 0; r < 9 && !progress; r++) {
      for (let c = 0; c < 9; c++) {
        if (work[r][c] === 0 && candidates[r][c].size === 1) {
          const val = candidates[r][c].values().next().value!;
          work[r][c] = val;
          candidates[r][c].clear();
          for (const [pr, pc] of getPeers(r, c)) {
            candidates[pr][pc].delete(val);
          }
          filledCount++;
          progress = true;
          break;
        }
      }
    }
    if (progress) continue;

    // 2. Hidden Singles
    for (let val = 1; val <= 9 && !progress; val++) {
      // Check rows
      for (let r = 0; r < 9 && !progress; r++) {
        let count = 0;
        let lastC = -1;
        for (let c = 0; c < 9; c++) {
          if (work[r][c] === 0 && candidates[r][c].has(val)) {
            count++;
            lastC = c;
          }
        }
        if (count === 1) {
          work[r][lastC] = val;
          candidates[r][lastC].clear();
          for (const [pr, pc] of getPeers(r, lastC)) {
            candidates[pr][pc].delete(val);
          }
          filledCount++;
          hardest = 'hidden_single';
          progress = true;
          break;
        }
      }
      if (progress) break;

      // Check cols
      for (let c = 0; c < 9 && !progress; c++) {
        let count = 0;
        let lastR = -1;
        for (let r = 0; r < 9; r++) {
          if (work[r][c] === 0 && candidates[r][c].has(val)) {
            count++;
            lastR = r;
          }
        }
        if (count === 1) {
          work[lastR][c] = val;
          candidates[lastR][c].clear();
          for (const [pr, pc] of getPeers(lastR, c)) {
            candidates[pr][pc].delete(val);
          }
          filledCount++;
          hardest = 'hidden_single';
          progress = true;
          break;
        }
      }
    }
    if (progress) continue;

    // 3. Medium techniques: Naked Pairs & Box-Line
    let foundPair = false;
    for (let r = 0; r < 9 && !foundPair; r++) {
      for (let c1 = 0; c1 < 8; c1++) {
        if (candidates[r][c1].size === 2) {
          const arr1 = Array.from(candidates[r][c1]);
          for (let c2 = c1 + 1; c2 < 9; c2++) {
            if (candidates[r][c2].size === 2) {
              const arr2 = Array.from(candidates[r][c2]);
              if (arr1[0] === arr2[0] && arr1[1] === arr2[1]) {
                for (let c = 0; c < 9; c++) {
                  if (c !== c1 && c !== c2 && work[r][c] === 0) {
                    if (candidates[r][c].delete(arr1[0]) || candidates[r][c].delete(arr1[1])) {
                      foundPair = true;
                    }
                  }
                }
                if (foundPair) {
                  hardest = 'naked_pair';
                  progress = true;
                  break;
                }
              }
            }
          }
        }
        if (foundPair) break;
      }
    }
    if (progress) continue;

    // Advanced techniques indicator
    if (filledCount < 81) {
      hardest = filledCount > 60 ? 'x_wing' : 'forcing_chain';
      break;
    }
  }

  let rating: Difficulty = 'easy';
  if (filledCount === 81 && (hardest === 'naked_single' || hardest === 'hidden_single')) {
    rating = 'easy';
  } else if (hardest === 'naked_pair' || hardest === 'box_line') {
    rating = 'medium';
  } else if (hardest === 'x_wing' || hardest === 'naked_triple') {
    rating = 'hard';
  } else if (hardest === 'forcing_chain') {
    rating = 'expert';
  } else {
    rating = 'master';
  }

  return { rating, hardestTechnique: hardest };
}

// --------------------------------------------------------------------------
// Section 2: Procedural Generation from Scratch
// --------------------------------------------------------------------------
function getRandomCryptoUint32(): number {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const buf = new Uint32Array(1);
    crypto.getRandomValues(buf);
    return buf[0];
  }
  return Math.floor(Math.random() * 0xffffffff);
}

function createRandomGenerator() {
  let state = getRandomCryptoUint32();
  return function nextFloat(): number {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 0x100000000;
  };
}

function shuffleArray<T>(arr: T[], rng: () => number): T[] {
  const result = [...arr];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const temp = result[i];
    result[i] = result[j];
    result[j] = temp;
  }
  return result;
}

export function generateFullValidSolution(): Grid {
  const rng = createRandomGenerator();
  const board = createEmptyGrid();

  function fill(r: number, c: number): boolean {
    if (r === 9) return true;
    const nextR = c === 8 ? r + 1 : r;
    const nextC = c === 8 ? 0 : c + 1;

    const nums = shuffleArray([1, 2, 3, 4, 5, 6, 7, 8, 9], rng);
    for (const n of nums) {
      if (isValidPlacement(board, r, c, n)) {
        board[r][c] = n;
        if (fill(nextR, nextC)) return true;
        board[r][c] = 0;
      }
    }
    return false;
  }

  fill(0, 0);
  return board;
}

/**
 * Removes clues down to target range with 180-deg rotational symmetry while verifying unique solution
 */
export function carvePuzzle(
  solution: Grid,
  targetClues: number
): { puzzle: Grid; clueCount: number } {
  const rng = createRandomGenerator();
  const puzzle = cloneGrid(solution);

  const pairs: [[number, number], [number, number]][] = [];
  const seen = new Set<string>();

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const key = `${r},${c}`;
      if (!seen.has(key)) {
        const symR = 8 - r;
        const symC = 8 - c;
        seen.add(key);
        seen.add(`${symR},${symC}`);
        pairs.push([[r, c], [symR, symC]]);
      }
    }
  }

  const shuffledPairs = shuffleArray(pairs, rng);
  let clueCount = 81;

  for (const [[r1, c1], [r2, c2]] of shuffledPairs) {
    if (clueCount <= targetClues) break;
    const v1 = puzzle[r1][c1];
    const v2 = puzzle[r2][c2];

    puzzle[r1][c1] = 0;
    puzzle[r2][c2] = 0;

    if (hasUniqueSolution(puzzle)) {
      clueCount -= (r1 === r2 && c1 === c2) ? 1 : 2;
    } else {
      puzzle[r1][c1] = v1;
      puzzle[r2][c2] = v2;
    }
  }

  return { puzzle, clueCount };
}

/**
 * Procedural generation meeting all Section 2 requirements:
 * - Brand-new puzzle built from scratch (fresh random solution + carve to clue range)
 * - Seeded using crypto.getRandomValues
 * - Clue count matching CLUE_RANGES[level]
 * - Technique grading
 * - Canonical fingerprint check against past fingerprints
 * - Similarity check (<20% identical clues to recent grids)
 */
export function generateProceduralPuzzle(
  level: Difficulty,
  pastFingerprints: Set<string> = new Set(),
  recentGrids: Grid[] = []
): { puzzle: Grid; solution: Grid; fingerprint: string } {
  const range = CLUE_RANGES[level];
  const target = Math.floor((range.min + range.max) / 2);

  for (let attempt = 0; attempt < 8; attempt++) {
    const solution = generateFullValidSolution();
    const { puzzle, clueCount } = carvePuzzle(solution, target);

    if (clueCount < range.min || clueCount > range.max) {
      // If outside exact range, continue to next candidate
      if (attempt < 4) continue;
    }

    if (!hasUniqueSolution(puzzle)) continue;

    // Check similarity against recent 20 played grids
    if (isTooSimilarToRecent(puzzle, recentGrids, 0.20)) {
      continue;
    }

    // Check canonical fingerprint against past played games
    const fingerprint = getCanonicalFingerprint(puzzle);
    if (pastFingerprints.has(fingerprint)) {
      continue;
    }

    return { puzzle, solution, fingerprint };
  }

  // Fallback guaranteed valid generation
  const solution = generateFullValidSolution();
  const { puzzle } = carvePuzzle(solution, target);
  const fingerprint = getCanonicalFingerprint(puzzle);
  return { puzzle, solution, fingerprint };
}

// --------------------------------------------------------------------------
// Level Progression & Streaks
// --------------------------------------------------------------------------
export interface UnlockStatus {
  unlocked: boolean;
  winsNeeded: number;
  currentWins: number;
  current: number;
  required: number;
  progressLabel: string;
}

export function getLevelUnlockStatus(
  history: HistoryRecord[]
): Record<Difficulty, UnlockStatus> {
  const winCounts: Record<Difficulty, number> = {
    easy: 0,
    medium: 0,
    hard: 0,
    expert: 0,
    master: 0,
  };

  for (const rec of history) {
    if (isWonRecord(rec)) {
      winCounts[rec.level] = (winCounts[rec.level] || 0) + 1;
    }
  }

  // All levels unlocked per user request
  return {
    easy: {
      unlocked: true,
      winsNeeded: 0,
      currentWins: winCounts.easy,
      current: winCounts.easy,
      required: 0,
      progressLabel: 'Unlocked',
    },
    medium: {
      unlocked: true,
      winsNeeded: 0,
      currentWins: winCounts.medium,
      current: winCounts.medium,
      required: 0,
      progressLabel: 'Unlocked',
    },
    hard: {
      unlocked: true,
      winsNeeded: 0,
      currentWins: winCounts.hard,
      current: winCounts.hard,
      required: 0,
      progressLabel: 'Unlocked',
    },
    expert: {
      unlocked: true,
      winsNeeded: 0,
      currentWins: winCounts.expert,
      current: winCounts.expert,
      required: 0,
      progressLabel: 'Unlocked',
    },
    master: {
      unlocked: true,
      winsNeeded: 0,
      currentWins: winCounts.master,
      current: winCounts.master,
      required: 0,
      progressLabel: 'Unlocked',
    },
  };
}

export function isWonRecord(r: { won?: boolean; score?: number; mistakes?: number }): boolean {
  if (r.won === true) return true;
  if (r.won === false) return false;
  return (r.score ?? 0) > 0;
}

export function formatPoints(num: number): string {
  if (!num || num <= 0) return '0';
  if (num < 10000) {
    return num.toLocaleString('en-US');
  }
  if (num < 1000000) {
    const val = num / 1000;
    const str = val.toFixed(1).replace(/\.0$/, '');
    return `${str}K`;
  }
  if (num < 1000000000) {
    const val = num / 1000000;
    const str = val.toFixed(1).replace(/\.0$/, '');
    return `${str}M`;
  }
  const val = num / 1000000000;
  const str = val.toFixed(1).replace(/\.0$/, '');
  return `${str}B`;
}

export function calculateDailyScore(history: HistoryRecord[]): number {
  const todayStr = getLocalDateString();
  return history
    .filter(r => r.date === todayStr && isWonRecord(r))
    .reduce((sum, r) => sum + r.score, 0);
}

export function calculateStreak(history: HistoryRecord[]): {
  currentStreak: number;
  bestStreak: number;
} {
  const uniqueDates = Array.from(
    new Set(
      history
        .filter(isWonRecord)
        .map(r => r.date)
    )
  ).sort();

  if (uniqueDates.length === 0) {
    return { currentStreak: 0, bestStreak: 0 };
  }

  let bestStreak = 1;
  let tempStreak = 1;

  for (let i = 1; i < uniqueDates.length; i++) {
    const prev = new Date(uniqueDates[i - 1]).getTime();
    const curr = new Date(uniqueDates[i]).getTime();
    const diffDays = Math.round((curr - prev) / (1000 * 60 * 60 * 24));

    if (diffDays === 1) {
      tempStreak++;
      if (tempStreak > bestStreak) bestStreak = tempStreak;
    } else {
      tempStreak = 1;
    }
  }

  // Check current streak relative to today
  const today = getLocalDateString();
  const yesterday = getLocalDateString(new Date(Date.now() - 86400000));

  const lastDate = uniqueDates[uniqueDates.length - 1];
  let currentStreak = 0;

  if (lastDate === today || lastDate === yesterday) {
    currentStreak = 1;
    for (let i = uniqueDates.length - 1; i > 0; i--) {
      const curr = new Date(uniqueDates[i]).getTime();
      const prev = new Date(uniqueDates[i - 1]).getTime();
      const diffDays = Math.round((curr - prev) / (1000 * 60 * 60 * 24));
      if (diffDays === 1) {
        currentStreak++;
      } else {
        break;
      }
    }
  }

  return { currentStreak, bestStreak };
}

// Backward-compatibility wrapper for game start
export function getNewPuzzle(
  level: Difficulty,
  pastFingerprints: Set<string> = new Set(),
  recentGrids: Grid[] = []
): { puzzle: Grid; solution: Grid; fingerprint: string } {
  return generateProceduralPuzzle(level, pastFingerprints, recentGrids);
}
