import test from 'node:test';
import assert from 'node:assert/strict';
import {
  solveSudoku,
  countSolutions,
  hasUniqueSolution,
  gradePuzzleDifficulty,
  generatePuzzle,
  calculateScore,
  calculateDailyScore,
  getLevelUnlockStatus,
  calculateStreak,
  CURATED_PUZZLES,
  LEVELS_LOCKED,
  HistoryRecord,
} from './sudokuLogic';

test('solveSudoku solves puzzle correctly and validates uniqueness', () => {
  const sample = CURATED_PUZZLES.easy[0];
  const sol = solveSudoku(sample.puzzle);
  assert.ok(sol !== null);
  assert.deepEqual(sol, sample.solution);
  assert.equal(countSolutions(sample.puzzle, 2), 1);
  assert.equal(hasUniqueSolution(sample.puzzle), true);
});

test('recalibrated curated puzzle targets match specifications', () => {
  // Easy: 42-46 givens, technique is 'easy' (only naked/hidden singles)
  for (const entry of CURATED_PUZZLES.easy) {
    const givens = entry.puzzle.flat().filter(v => v !== 0).length;
    assert.ok(givens >= 42 && givens <= 46, `Expected 42-46 givens, got ${givens}`);
    assert.equal(gradePuzzleDifficulty(entry.puzzle), 'easy');

    // No row, col or box with fewer than 2 givens
    for (let r = 0; r < 9; r++) {
      const rowCnt = entry.puzzle[r].filter(v => v !== 0).length;
      assert.ok(rowCnt >= 2, `Row ${r} has ${rowCnt} < 2 givens`);
    }
    for (let c = 0; c < 9; c++) {
      let colCnt = 0;
      for (let r = 0; r < 9; r++) if (entry.puzzle[r][c] !== 0) colCnt++;
      assert.ok(colCnt >= 2, `Col ${c} has ${colCnt} < 2 givens`);
    }
    for (let br = 0; br < 3; br++) {
      for (let bc = 0; bc < 3; bc++) {
        let boxCnt = 0;
        for (let dr = 0; dr < 3; dr++) {
          for (let dc = 0; dc < 3; dc++) {
            if (entry.puzzle[br * 3 + dr][bc * 3 + dc] !== 0) boxCnt++;
          }
        }
        assert.ok(boxCnt >= 2, `Box (${br},${bc}) has ${boxCnt} < 2 givens`);
      }
    }
  }

  // Medium: 36-40 givens
  for (const entry of CURATED_PUZZLES.medium) {
    const givens = entry.puzzle.flat().filter(v => v !== 0).length;
    assert.ok(givens >= 36 && givens <= 40, `Expected 36-40 givens, got ${givens}`);
  }

  // Hard: 30-34 givens
  for (const entry of CURATED_PUZZLES.hard) {
    const givens = entry.puzzle.flat().filter(v => v !== 0).length;
    assert.ok(givens >= 30 && givens <= 34, `Expected 30-34 givens, got ${givens}`);
  }

  // Expert: 25-29 givens
  for (const entry of CURATED_PUZZLES.expert) {
    const givens = entry.puzzle.flat().filter(v => v !== 0).length;
    assert.ok(givens >= 25 && givens <= 29, `Expected 25-29 givens, got ${givens}`);
  }
});

test('generatePuzzle creates valid unique single-solution recalibrated puzzle', () => {
  const { puzzle, solution } = generatePuzzle('easy', 50);
  const givens = puzzle.flat().filter(v => v !== 0).length;
  assert.ok(givens >= 42 && givens <= 46);
  assert.equal(gradePuzzleDifficulty(puzzle), 'easy');
  assert.equal(hasUniqueSolution(puzzle), true);
  assert.ok(solution !== null);
});

test('calculateScore respects base, time penalty, hint/mistake penalty and 20% floor', () => {
  const score = calculateScore('easy', 100, 1, 2);
  assert.equal(score, 935);

  const floorScore = calculateScore('easy', 10000, 10, 5);
  assert.equal(floorScore, 200);

  const medScore = calculateScore('medium', 50, 0, 0);
  assert.equal(medScore, 1990);
});

test('getLevelUnlockStatus unlocks all levels when LEVELS_LOCKED is false', () => {
  const history: HistoryRecord[] = [];
  assert.equal(LEVELS_LOCKED, false);
  const status = getLevelUnlockStatus(history);

  assert.equal(status.easy.unlocked, true);
  assert.equal(status.medium.unlocked, true);
  assert.equal(status.hard.unlocked, true);
  assert.equal(status.expert.unlocked, true);
  assert.equal(status.medium.progressLabel, 'Unlocked');
  assert.equal(status.hard.progressLabel, 'Unlocked');
  assert.equal(status.expert.progressLabel, 'Unlocked');
});

test('calculateStreak tracks active and best streak according to rules', () => {
  const history: HistoryRecord[] = [
    { id: '1', date: '2026-10-24', timestamp: 1, level: 'easy', seconds: 100, score: 900, hintsUsed: 0, mistakes: 0 },
    { id: '2', date: '2026-10-25', timestamp: 2, level: 'easy', seconds: 100, score: 900, hintsUsed: 0, mistakes: 0 },
  ];
  const s1 = calculateStreak(history, '2026-10-26');
  assert.equal(s1.currentStreak, 2);
  assert.equal(s1.bestStreak, 2);

  history.push({ id: '3', date: '2026-10-26', timestamp: 3, level: 'easy', seconds: 100, score: 900, hintsUsed: 0, mistakes: 0 });
  const s2 = calculateStreak(history, '2026-10-26');
  assert.equal(s2.currentStreak, 3);
  assert.equal(s2.bestStreak, 3);

  const s3 = calculateStreak(history, '2026-10-29');
  assert.equal(s3.currentStreak, 0);
  assert.equal(s3.bestStreak, 3);
});

test('calculateDailyScore sums daily records accurately', () => {
  const history: HistoryRecord[] = [
    { id: '1', date: '2026-10-26', timestamp: 1, level: 'easy', seconds: 100, score: 920, hintsUsed: 0, mistakes: 0 },
    { id: '2', date: '2026-10-26', timestamp: 2, level: 'medium', seconds: 200, score: 1850, hintsUsed: 0, mistakes: 0 },
    { id: '3', date: '2026-10-25', timestamp: 3, level: 'easy', seconds: 110, score: 940, hintsUsed: 0, mistakes: 0 },
  ];
  const daily = calculateDailyScore(history, '2026-10-26');
  assert.equal(daily, 920 + 1850);
});
