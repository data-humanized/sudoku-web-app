/**
 * ZenSudoku - Desktop Minimalist Sudoku Application
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Difficulty,
  GameState,
  HistoryRecord,
  MoveAction,
  UserSettings,
  DEFAULT_SETTINGS,
  calculateDailyScore,
  calculateStreak,
  getLevelUnlockStatus,
  generateProceduralPuzzle,
  isCellLocked,
  calculateLiveScore,
  migrateHistoryRecord,
  cloneGrid,
  cloneNotes,
  cloneBoolGrid,
  createEmptyBoolGrid,
  createEmptyNotes,
  getPeers,
  MAX_SCORE,
  getLocalDateString,
  isWonRecord,
} from './logic/sudokuLogic';
import {
  loadZenData,
  saveZenData,
  downloadBackupFile,
  createBackupBinary,
  parseAndValidateBackup,
  saveRollbackCopy,
  restoreRollbackCopy,
  loadStoredFingerprints,
  saveStoredFingerprint,
  loadRecentPlayedGrids,
  savePlayedGrid,
} from './utils/storage';
import { sounds } from './utils/soundEffects';
import { Header } from './components/Header';
import { DifficultyInlineTabs } from './components/DifficultySelector';
import { SudokuGrid } from './components/SudokuGrid';
import { HomeScreen } from './components/HomeScreen';
import { LivesModal } from './components/LivesModal';
import { CompletionModal } from './components/CompletionModal';
import { AnalyticsModal } from './components/AnalyticsModal';
import { SettingsModal } from './components/SettingsModal';
import { MenuDrawer } from './components/MenuDrawer';
import { PrintPuzzlesModal } from './components/PrintPuzzlesModal';
import {
  InGameHeader,
  LiveScoreLine,
  SlimStatsRow,
  ToolButtonsRow,
  NumberPadRow,
  Keypad3x3,
} from './components/InGameControls';

export default function App() {
  // --- Persistent Storage State ---
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [activeGame, setActiveGame] = useState<GameState | null>(null);

  // --- UI Views & Modals ---
  const [currentView, setCurrentView] = useState<'home' | 'game'>('home');
  const [isMenuDrawerOpen, setIsMenuDrawerOpen] = useState(false);
  const [analyticsInitialTab, setAnalyticsInitialTab] = useState<'analytics' | 'history'>('analytics');
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isPrintModalOpen, setIsPrintModalOpen] = useState(false);
  const [isLivesModalOpen, setIsLivesModalOpen] = useState(false);
  const [isCompletionModalOpen, setIsCompletionModalOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [pendingBackupRestore, setPendingBackupRestore] = useState<{
    records: HistoryRecord[];
    settings: UserSettings;
  } | null>(null);

  // --- Responsive Window Dimensions for Layout ---
  const [windowDimensions, setWindowDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  });

  useEffect(() => {
    const handleResize = () => {
      setWindowDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isLandscape = windowDimensions.width > windowDimensions.height;
  const isTwoColumn = windowDimensions.width >= 1024 || (isLandscape && windowDimensions.width >= 700);
  const showInlineTabs =
    (windowDimensions.width >= 1024 && windowDimensions.height >= 560) ||
    (isLandscape && windowDimensions.width >= 700 && windowDimensions.height >= 540);

  // --- Interactive Board State ---
  const [currentLevel, setCurrentLevel] = useState<Difficulty>('easy');
  const [selectedCell, setSelectedCell] = useState<[number, number] | null>([0, 0]);
  const [isNotesMode, setIsNotesMode] = useState(false);
  const [tooltip, setTooltip] = useState<{ cell: [number, number]; text: string } | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const tooltipTimerRef = useRef<NodeJS.Timeout | null>(null);
  const toastTimerRef = useRef<NodeJS.Timeout | null>(null);

  // --- Initialize from Local Storage on mount ---
  useEffect(() => {
    const data = loadZenData();
    // Migrate old history records to new scoring scale
    const migratedHistory = (data.history || []).map(migrateHistoryRecord);
    setHistory(migratedHistory);
    setSettings(data.settings || DEFAULT_SETTINGS);
    sounds.enabled = data.settings?.soundEffects ?? true;

    // Check URL parameters for autostart
    const urlParams = new URLSearchParams(window.location.search);
    const autostart = urlParams.get('autostart');

    if (data.activeGame && !data.activeGame.isCompleted) {
      setActiveGame(data.activeGame);
      setCurrentLevel(data.activeGame.level);
      if (autostart === '1') {
        setCurrentView('game');
      }
    } else if (autostart === '1') {
      startNewGame('easy');
    }
  }, []);

  // --- Sync with localStorage ---
  const syncStorage = useCallback(
    (newHistory: HistoryRecord[], newActiveGame: GameState | null, newSettings: UserSettings) => {
      saveZenData({
        version: 1,
        history: newHistory,
        activeGame: newActiveGame,
        settings: newSettings,
      });
    },
    []
  );

  const getTodayISO = (): string => {
    return getLocalDateString();
  };

  const { currentStreak, bestStreak } = calculateStreak(history);
  const dailyScore = calculateDailyScore(history);
  const unlockStatus = getLevelUnlockStatus(history);

  const todayGames = useMemo(() => {
    const today = getTodayISO();
    return history.filter(r => r.date === today && isWonRecord(r));
  }, [history]);

  // --- Show Tooltip on Cell ---
  const triggerTooltip = useCallback((cell: [number, number], text: string) => {
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    setTooltip({ cell, text });
    tooltipTimerRef.current = setTimeout(() => {
      setTooltip(null);
    }, 2000);
  }, []);

  // --- Show Toast Notification ---
  const triggerToast = useCallback((msg: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  }, []);

  // --- Section 8: Live Score Calculation ---
  const { liveScore } = useMemo(() => {
    if (!activeGame) return { liveScore: 0, isComplete: false };
    return calculateLiveScore(
      activeGame.initialGrid,
      activeGame.currentGrid,
      activeGame.solutionGrid,
      activeGame.mistakes,
      activeGame.hintsUsed,
      activeGame.level,
      activeGame.earnedComboUnits || 0
    );
  }, [activeGame]);

  // --- Start a New Game ---
  const startNewGame = useCallback((level: Difficulty) => {
    setIsGenerating(true);

    // Use requestAnimationFrame / setTimeout to allow UI render of loading state if generation takes time
    setTimeout(() => {
      try {
        const storedFingerprints = loadStoredFingerprints();
        const recentGrids = loadRecentPlayedGrids();

        const { puzzle, solution, fingerprint } = generateProceduralPuzzle(
          level,
          storedFingerprints,
          recentGrids
        );

        // Save fingerprint and grid to local storage
        saveStoredFingerprint(fingerprint);
        savePlayedGrid(puzzle);

        const newGame: GameState = {
          id: `game-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
          level,
          initialGrid: puzzle,
          solutionGrid: solution,
          currentGrid: cloneGrid(puzzle),
          notes: createEmptyNotes(),
          hintedCells: createEmptyBoolGrid(),
          mistakes: 0,
          totalMistakes: 0,
          hintsUsed: 0,
          elapsedSeconds: 0,
          isPaused: false,
          isCompleted: false,
          undoStack: [],
          redoStack: [],
          startTime: Date.now(),
          finalScore: 0,
          earnedComboUnits: 0,
        };

        setActiveGame(newGame);
        setCurrentLevel(level);
        setSelectedCell([0, 0]);
        setIsNotesMode(false);
        setIsLivesModalOpen(false);
        setIsCompletionModalOpen(false);
        setCurrentView('game');
        syncStorage(history, newGame, settings);
      } finally {
        setIsGenerating(false);
      }
    }, 20);
  }, [history, settings, syncStorage]);

  // --- Game Timer Loop ---
  useEffect(() => {
    if (currentView !== 'game' || !activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) {
      return;
    }

    const timer = setInterval(() => {
      setActiveGame(prev => {
        if (!prev || prev.isPaused || prev.isCompleted) return prev;
        const updated = {
          ...prev,
          elapsedSeconds: prev.elapsedSeconds + 1,
        };
        // Auto-persist periodically
        if (updated.elapsedSeconds % 5 === 0) {
          syncStorage(history, updated, settings);
        }
        return updated;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [currentView, activeGame?.isPaused, activeGame?.isCompleted, isLivesModalOpen, history, settings, syncStorage]);

  // --- Check Completion ---
  const checkCompletion = useCallback((grid: number[][], solution: number[][]) => {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (grid[r][c] !== solution[r][c]) {
          return false;
        }
      }
    }
    return true;
  }, []);

  // --- Handle Game Completion ---
  const handleVictory = useCallback((finalGame: GameState) => {
    sounds.playVictory();
    const { liveScore: finalScore } = calculateLiveScore(
      finalGame.initialGrid,
      finalGame.currentGrid,
      finalGame.solutionGrid,
      finalGame.mistakes,
      finalGame.hintsUsed,
      finalGame.level,
      finalGame.earnedComboUnits || 0
    );

    const totalMistakesCount = finalGame.totalMistakes ?? finalGame.mistakes;
    const record: HistoryRecord = {
      id: finalGame.id,
      date: getTodayISO(),
      timestamp: Date.now(),
      level: finalGame.level,
      timeSeconds: finalGame.elapsedSeconds,
      seconds: finalGame.elapsedSeconds,
      score: finalScore,
      hintsUsed: finalGame.hintsUsed,
      mistakes: totalMistakesCount,
      won: true,
    };

    const newHistory = [...history, record];
    const completedGameState: GameState = {
      ...finalGame,
      isCompleted: true,
      finalScore,
      completedTime: Date.now(),
      mistakes: totalMistakesCount,
      totalMistakes: totalMistakesCount,
    };

    setHistory(newHistory);
    setActiveGame(completedGameState);
    setIsCompletionModalOpen(true);
    syncStorage(newHistory, null, settings);
  }, [history, settings, syncStorage]);

  // Helper: check if a specific unit (row, col, or box) was already complete before a placement
  const isRowComplete = (grid: number[][], solution: number[][], row: number) => {
    for (let c = 0; c < 9; c++) {
      if (grid[row][c] === 0 || grid[row][c] !== solution[row][c]) return false;
    }
    return true;
  };

  const isColComplete = (grid: number[][], solution: number[][], col: number) => {
    for (let r = 0; r < 9; r++) {
      if (grid[r][col] === 0 || grid[r][col] !== solution[r][col]) return false;
    }
    return true;
  };

  const isBoxComplete = (grid: number[][], solution: number[][], br: number, bc: number) => {
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        const row = br * 3 + r;
        const col = bc * 3 + c;
        if (grid[row][col] === 0 || grid[row][col] !== solution[row][col]) return false;
      }
    }
    return true;
  };

  // --- Input a Digit (or Note) ---
  const handleInputDigit = useCallback((digit: number) => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select a cell first');
      return;
    }

    const [r, c] = selectedCell;

    // Section 3: Correct digits locked
    // Once a correct digit is placed (or if cell was an initial clue), it cannot be changed, overwritten, erased, noted, or undone.
    if (isCellLocked(r, c, activeGame.initialGrid, activeGame.currentGrid, activeGame.solutionGrid)) {
      triggerTooltip([r, c], "Cell is locked");
      return;
    }

    if (isNotesMode) {
      // Toggle pencil candidate note
      sounds.playNote();
      const newNotes = cloneNotes(activeGame.notes);
      const prevNotesSet = new Set(newNotes[r][c]);
      if (newNotes[r][c].has(digit)) {
        newNotes[r][c].delete(digit);
      } else {
        newNotes[r][c].add(digit);
      }

      const moveAction: MoveAction = {
        actionType: 'note',
        row: r,
        col: c,
        prevVal: activeGame.currentGrid[r][c],
        newVal: activeGame.currentGrid[r][c],
        prevNotes: Array.from(prevNotesSet),
        newNotes: Array.from(newNotes[r][c]),
      };

      const updatedGame: GameState = {
        ...activeGame,
        notes: newNotes,
        undoStack: [...activeGame.undoStack, moveAction],
        redoStack: [],
      };
      setActiveGame(updatedGame);
      syncStorage(history, updatedGame, settings);
      return;
    }

    // Digit Entry Mode
    const prevVal = activeGame.currentGrid[r][c];
    if (prevVal === digit) {
      return;
    }

    const isCorrect = digit === activeGame.solutionGrid[r][c];

    if (!isCorrect) {
      // Section 4: Wrong input: red only (#dc2626), NO shake, wobble, or movement animation
      // Section 5: Plays existing erase sound
      sounds.playWrongDigit();
      if (settings.hapticFeedback && navigator.vibrate) {
        navigator.vibrate(200);
      }

      const newMistakes = activeGame.mistakes + 1;
      const newTotalMistakes = (activeGame.totalMistakes ?? activeGame.mistakes) + 1;
      const newGrid = cloneGrid(activeGame.currentGrid);
      newGrid[r][c] = digit; // Remains editable & visible in red (not locked)

      const moveAction: MoveAction = {
        actionType: 'digit',
        row: r,
        col: c,
        prevVal,
        newVal: digit,
        prevNotes: Array.from(activeGame.notes[r][c]),
        newNotes: Array.from(activeGame.notes[r][c]),
      };

      const updatedGame: GameState = {
        ...activeGame,
        currentGrid: newGrid,
        mistakes: newMistakes,
        totalMistakes: newTotalMistakes,
        undoStack: [...activeGame.undoStack, moveAction],
        redoStack: [],
      };

      setActiveGame(updatedGame);
      syncStorage(history, updatedGame, settings);

      if (newMistakes >= 3) {
        setIsLivesModalOpen(true);
      }
      return;
    }

    // Correct entry!
    // Section 5: Play clean pop/tick
    sounds.playCorrect();

    // Check combos before applying move
    const prevRowDone = isRowComplete(activeGame.currentGrid, activeGame.solutionGrid, r);
    const prevColDone = isColComplete(activeGame.currentGrid, activeGame.solutionGrid, c);
    const br = Math.floor(r / 3);
    const bc = Math.floor(c / 3);
    const prevBoxDone = isBoxComplete(activeGame.currentGrid, activeGame.solutionGrid, br, bc);

    const newGrid = cloneGrid(activeGame.currentGrid);
    newGrid[r][c] = digit;

    const nextRowDone = isRowComplete(newGrid, activeGame.solutionGrid, r);
    const nextColDone = isColComplete(newGrid, activeGame.solutionGrid, c);
    const nextBoxDone = isBoxComplete(newGrid, activeGame.solutionGrid, br, bc);

    let newlyCompletedUnits = 0;
    if (!prevRowDone && nextRowDone) newlyCompletedUnits++;
    if (!prevColDone && nextColDone) newlyCompletedUnits++;
    if (!prevBoxDone && nextBoxDone) newlyCompletedUnits++;

    let comboBonusUnits = 0;
    if (newlyCompletedUnits === 2) comboBonusUnits = 20;
    else if (newlyCompletedUnits === 3) comboBonusUnits = 50;

    const newNotes = cloneNotes(activeGame.notes);
    const prevCellNotes = Array.from(newNotes[r][c]);
    newNotes[r][c].clear();

    // Section 3: Correctly placing a digit automatically removes that digit
    // from the pencil notes of all cells in the same row, column, and 3x3 box
    const peerChanges: { row: number; col: number; removedNote: number }[] = [];
    for (const [pr, pc] of getPeers(r, c)) {
      if (newNotes[pr][pc].has(digit)) {
        newNotes[pr][pc].delete(digit);
        peerChanges.push({ row: pr, col: pc, removedNote: digit });
      }
    }

    const moveAction: MoveAction = {
      actionType: 'digit',
      row: r,
      col: c,
      prevVal,
      newVal: digit,
      prevNotes: prevCellNotes,
      newNotes: [],
      peerNotesChanges: peerChanges,
    };

    const updatedGame: GameState = {
      ...activeGame,
      currentGrid: newGrid,
      notes: newNotes,
      earnedComboUnits: (activeGame.earnedComboUnits || 0) + comboBonusUnits,
      undoStack: [...activeGame.undoStack, moveAction],
      redoStack: [],
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);

    if (checkCompletion(newGrid, activeGame.solutionGrid)) {
      handleVictory(updatedGame);
    }
  }, [
    activeGame,
    isLivesModalOpen,
    selectedCell,
    isNotesMode,
    settings,
    triggerToast,
    triggerTooltip,
    history,
    syncStorage,
    checkCompletion,
    handleVictory,
  ]);

  // --- Erase Cell ---
  const handleErase = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) return;

    const [r, c] = selectedCell;

    // Section 3: Pressing Erase on a locked cell does nothing and makes NO sound
    if (isCellLocked(r, c, activeGame.initialGrid, activeGame.currentGrid, activeGame.solutionGrid)) {
      return;
    }

    const prevVal = activeGame.currentGrid[r][c];
    const prevNotes = Array.from(activeGame.notes[r][c]);

    if (prevVal === 0 && prevNotes.length === 0) return;

    // Section 5: Play new realistic pencil scribble sound
    sounds.playErase();
    const newGrid = cloneGrid(activeGame.currentGrid);
    newGrid[r][c] = 0;
    const newNotes = cloneNotes(activeGame.notes);
    newNotes[r][c].clear();

    const moveAction: MoveAction = {
      actionType: 'erase',
      row: r,
      col: c,
      prevVal,
      newVal: 0,
      prevNotes,
      newNotes: [],
    };

    const updatedGame: GameState = {
      ...activeGame,
      currentGrid: newGrid,
      notes: newNotes,
      undoStack: [...activeGame.undoStack, moveAction],
      redoStack: [],
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [activeGame, isLivesModalOpen, selectedCell, history, settings, syncStorage]);

  // --- Undo Action ---
  const handleUndo = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (activeGame.undoStack.length === 0) return;

    const undoStack = [...activeGame.undoStack];
    const lastAction = undoStack.pop()!;

    // Section 3: Correct digits cannot be undone
    if (
      lastAction.newVal !== 0 &&
      lastAction.newVal === activeGame.solutionGrid[lastAction.row][lastAction.col]
    ) {
      return;
    }

    const newGrid = cloneGrid(activeGame.currentGrid);
    const newNotes = cloneNotes(activeGame.notes);

    newGrid[lastAction.row][lastAction.col] = lastAction.prevVal;
    newNotes[lastAction.row][lastAction.col] = new Set(lastAction.prevNotes);

    if (lastAction.peerNotesChanges) {
      for (const change of lastAction.peerNotesChanges) {
        newNotes[change.row][change.col].add(change.removedNote);
      }
    }

    const updatedGame: GameState = {
      ...activeGame,
      currentGrid: newGrid,
      notes: newNotes,
      undoStack,
      redoStack: [lastAction, ...activeGame.redoStack],
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [activeGame, isLivesModalOpen, history, settings, syncStorage]);

  // --- Hint Fill Number ---
  const handleHintFillNumber = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select an empty cell first');
      return;
    }

    const [r, c] = selectedCell;
    if (isCellLocked(r, c, activeGame.initialGrid, activeGame.currentGrid, activeGame.solutionGrid)) {
      triggerTooltip([r, c], "Cell is already filled");
      return;
    }

    const correctNum = activeGame.solutionGrid[r][c];
    const newGrid = cloneGrid(activeGame.currentGrid);
    newGrid[r][c] = correctNum;

    const newHinted = cloneBoolGrid(activeGame.hintedCells);
    newHinted[r][c] = true;

    const newNotes = cloneNotes(activeGame.notes);
    newNotes[r][c].clear();
    for (const [pr, pc] of getPeers(r, c)) {
      newNotes[pr][pc].delete(correctNum);
    }

    const updatedGame: GameState = {
      ...activeGame,
      currentGrid: newGrid,
      notes: newNotes,
      hintedCells: newHinted,
      hintsUsed: activeGame.hintsUsed + 1,
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);

    if (checkCompletion(newGrid, activeGame.solutionGrid)) {
      handleVictory(updatedGame);
    }
  }, [activeGame, isLivesModalOpen, selectedCell, triggerToast, triggerTooltip, history, settings, syncStorage, checkCompletion, handleVictory]);

  // --- Hint Fill Possibilities ---
  const handleHintFillPossibilities = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select an empty cell first');
      return;
    }

    const [r, c] = selectedCell;
    if (isCellLocked(r, c, activeGame.initialGrid, activeGame.currentGrid, activeGame.solutionGrid)) {
      triggerTooltip([r, c], "Cell is already filled");
      return;
    }

    const validNums = new Set<number>();
    for (let n = 1; n <= 9; n++) {
      let valid = true;
      for (const [pr, pc] of getPeers(r, c)) {
        if (activeGame.currentGrid[pr][pc] === n) {
          valid = false;
          break;
        }
      }
      if (valid) validNums.add(n);
    }

    const newNotes = cloneNotes(activeGame.notes);
    newNotes[r][c] = validNums;

    const updatedGame: GameState = {
      ...activeGame,
      notes: newNotes,
      hintsUsed: activeGame.hintsUsed + 1,
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [activeGame, isLivesModalOpen, selectedCell, triggerToast, triggerTooltip, history, settings, syncStorage]);

  // --- Toggle Pause ---
  const handleTogglePause = useCallback(() => {
    if (!activeGame || activeGame.isCompleted || isLivesModalOpen) return;
    setActiveGame(prev => {
      if (!prev) return null;
      const updated = {
        ...prev,
        isPaused: !prev.isPaused,
      };
      syncStorage(history, updated, settings);
      return updated;
    });
  }, [activeGame, isLivesModalOpen, history, settings, syncStorage]);

  // --- Reset Progress ---
  const handleResetProgress = useCallback(() => {
    saveRollbackCopy({
      version: 1,
      history,
      activeGame,
      settings,
    });
    setHistory([]);
    setActiveGame(null);
    setCurrentView('home');
    syncStorage([], null, settings);
    setIsSettingsOpen(false);
    triggerToast('All progress reset. Rollback copy preserved.');
  }, [history, activeGame, settings, syncStorage, triggerToast]);

  return (
    <div className="w-full min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans select-none">
      {/* Drawer menu */}
      <MenuDrawer
        isOpen={isMenuDrawerOpen}
        onClose={() => setIsMenuDrawerOpen(false)}
        currentStreak={currentStreak}
        dailyScore={dailyScore}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenAnalytics={() => {
          setAnalyticsInitialTab('analytics');
          setIsAnalyticsOpen(true);
        }}
        onOpenHistory={() => {
          setAnalyticsInitialTab('history');
          setIsAnalyticsOpen(true);
        }}
        onGoHome={() => setCurrentView('home')}
      />

      {/* View routing: HOME vs GAME */}
      {currentView === 'home' ? (
        <>
          {/* Section 0: Header unchanged */}
          <Header
            currentView="home"
            onNavigateHome={() => setCurrentView('home')}
            currentStreak={currentStreak}
            dailyScore={dailyScore}
            onOpenAnalytics={() => {
              setAnalyticsInitialTab('analytics');
              setIsAnalyticsOpen(true);
            }}
            onOpenSettings={() => setIsSettingsOpen(true)}
          />

          <HomeScreen
            history={history}
            currentStreak={currentStreak}
            bestStreak={bestStreak}
            todayScore={dailyScore}
            todayGames={todayGames}
            activeGame={activeGame}
            unlockStatus={unlockStatus}
            onStartGame={level => startNewGame(level)}
            onResumeActiveGame={() => setCurrentView('game')}
            onOpenPrintModal={() => setIsPrintModalOpen(true)}
          />
        </>
      ) : (
        <>
          {/* In-Game Header */}
          <InGameHeader
            onOpenMenu={() => setIsMenuDrawerOpen(true)}
            onNewGame={() => startNewGame(currentLevel)}
          />

          <main className="flex-1 w-full flex flex-col items-center justify-between p-2 sm:p-3 overflow-hidden">
            {/* Loading Overlay if puzzle generation is executing */}
            {isGenerating && (
              <div className="absolute inset-0 bg-white/75 backdrop-blur-xs z-50 flex flex-col items-center justify-center gap-2">
                <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent animate-spin rounded-full" />
                <span className="text-xs font-semibold text-slate-700 tracking-wide uppercase">
                  Generating Puzzle...
                </span>
              </div>
            )}

            {!isTwoColumn ? (
              /* A) MOBILE / NARROW SCREEN LAYOUT */
              <div className="w-full h-full flex flex-col justify-between items-center max-w-[500px] mx-auto min-h-0">
                <LiveScoreLine score={liveScore} />

                {activeGame && (
                  <SlimStatsRow
                    currentLevel={currentLevel}
                    unlockStatus={unlockStatus}
                    onSelectLevel={level => startNewGame(level)}
                    mistakes={activeGame.mistakes}
                    elapsedSeconds={activeGame.elapsedSeconds}
                    isPaused={activeGame.isPaused}
                    onTogglePause={handleTogglePause}
                    showDropdown={true}
                    showTimer={settings.showTimer}
                  />
                )}

                <div className="flex-1 min-h-0 flex items-center justify-center w-full py-1">
                  {activeGame && (
                    <div className="w-full max-w-[min(calc(100vw-16px),calc(100dvh-215px),520px)] aspect-square flex items-center justify-center">
                      <SudokuGrid
                        initialGrid={activeGame.initialGrid}
                        currentGrid={activeGame.currentGrid}
                        solutionGrid={activeGame.solutionGrid}
                        notes={activeGame.notes}
                        hintedCells={activeGame.hintedCells}
                        selectedCell={selectedCell}
                        onSelectCell={(r, c) => setSelectedCell([r, c])}
                        isPaused={activeGame.isPaused}
                        onResume={handleTogglePause}
                        settings={settings}
                        tooltip={tooltip}
                        className="w-full h-full"
                      />
                    </div>
                  )}
                </div>

                {activeGame && (
                  <ToolButtonsRow
                    onUndo={handleUndo}
                    canUndo={activeGame.undoStack.length > 0}
                    onErase={handleErase}
                    isNotesMode={isNotesMode}
                    onToggleNotesMode={() => setIsNotesMode(!isNotesMode)}
                    onHintFillNumber={handleHintFillNumber}
                    onHintFillPossibilities={handleHintFillPossibilities}
                    hintsUsed={activeGame.hintsUsed}
                    isPaused={activeGame.isPaused}
                  />
                )}

                {activeGame && (
                  <NumberPadRow
                    onInputDigit={handleInputDigit}
                    isPaused={activeGame.isPaused}
                  />
                )}
              </div>
            ) : (
              /* B) DESKTOP / TABLET TWO-COLUMN LAYOUT */
              <div className="w-full h-full flex items-center justify-center gap-6 lg:gap-10 max-w-[1300px] mx-auto px-4 py-2 min-h-0">
                <div className="h-full flex flex-col items-center justify-center min-h-0">
                  {showInlineTabs && (
                    <div className="mb-2 shrink-0 self-start">
                      <DifficultyInlineTabs
                        currentLevel={currentLevel}
                        unlockStatus={unlockStatus}
                        onSelectLevel={level => startNewGame(level)}
                        disabled={activeGame?.isPaused || false}
                      />
                    </div>
                  )}

                  {activeGame && (
                    <div
                      className="flex items-center justify-center aspect-square"
                      style={{
                        height: showInlineTabs
                          ? 'min(calc(100dvh - 120px), 740px, 48vw)'
                          : 'min(calc(100dvh - 80px), 740px, 48vw)',
                        width: showInlineTabs
                          ? 'min(calc(100dvh - 120px), 740px, 48vw)'
                          : 'min(calc(100dvh - 80px), 740px, 48vw)',
                      }}
                    >
                      <SudokuGrid
                        initialGrid={activeGame.initialGrid}
                        currentGrid={activeGame.currentGrid}
                        solutionGrid={activeGame.solutionGrid}
                        notes={activeGame.notes}
                        hintedCells={activeGame.hintedCells}
                        selectedCell={selectedCell}
                        onSelectCell={(r, c) => setSelectedCell([r, c])}
                        isPaused={activeGame.isPaused}
                        onResume={handleTogglePause}
                        settings={settings}
                        tooltip={tooltip}
                        className="w-full h-full"
                      />
                    </div>
                  )}
                </div>

                {activeGame && (
                  <div
                    className="w-full max-w-[390px] min-w-[310px] flex flex-col justify-between min-h-0 py-1"
                    style={{
                      height: showInlineTabs
                        ? 'min(calc(100dvh - 120px), 740px, 48vw)'
                        : 'min(calc(100dvh - 80px), 740px, 48vw)',
                    }}
                  >
                    <LiveScoreLine score={liveScore} />

                    <SlimStatsRow
                      currentLevel={currentLevel}
                      unlockStatus={unlockStatus}
                      onSelectLevel={level => startNewGame(level)}
                      mistakes={activeGame.mistakes}
                      elapsedSeconds={activeGame.elapsedSeconds}
                      isPaused={activeGame.isPaused}
                      onTogglePause={handleTogglePause}
                      showDropdown={!showInlineTabs}
                      showTimer={settings.showTimer}
                    />

                    <ToolButtonsRow
                      onUndo={handleUndo}
                      canUndo={activeGame.undoStack.length > 0}
                      onErase={handleErase}
                      isNotesMode={isNotesMode}
                      onToggleNotesMode={() => setIsNotesMode(!isNotesMode)}
                      onHintFillNumber={handleHintFillNumber}
                      onHintFillPossibilities={handleHintFillPossibilities}
                      hintsUsed={activeGame.hintsUsed}
                      isPaused={activeGame.isPaused}
                    />

                    <div className="py-1">
                      <Keypad3x3
                        onInputDigit={handleInputDigit}
                        isPaused={activeGame.isPaused}
                        buttonHeight={windowDimensions.height < 500 ? '40px' : 'clamp(52px, 9vh, 88px)'}
                        fontSize={windowDimensions.height < 500 ? '22px' : 'clamp(26px, 4vh, 42px)'}
                      />
                    </div>

                    <button
                      onClick={() => startNewGame(currentLevel)}
                      aria-label="Start New Game"
                      className="w-full py-2.5 sm:py-3 px-4 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-xs sm:text-sm tracking-wide uppercase transition-colors shadow-sm cursor-pointer shrink-0"
                      style={{ borderRadius: '0px' }}
                    >
                      New Game
                    </button>
                  </div>
                )}
              </div>
            )}
          </main>
        </>
      )}

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white text-xs font-semibold px-4 py-2.5 shadow-xl animate-in fade-in duration-200"
          style={{ borderRadius: '0px' }}
        >
          {toastMessage}
        </div>
      )}

      {/* Modals */}
      <LivesModal
        isOpen={isLivesModalOpen}
        onGetLife={() => {
          if (!activeGame) return;
          const revivedGame: GameState = {
            ...activeGame,
            mistakes: 0,
            totalMistakes: activeGame.totalMistakes ?? activeGame.mistakes,
            isPaused: false,
          };
          setActiveGame(revivedGame);
          setIsLivesModalOpen(false);
          syncStorage(history, revivedGame, settings);
        }}
      />

      {activeGame && (
        <CompletionModal
          isOpen={isCompletionModalOpen}
          level={activeGame.level}
          score={activeGame.finalScore}
          currentStreak={currentStreak}
          seconds={activeGame.elapsedSeconds}
          hintsUsed={activeGame.hintsUsed}
          mistakes={activeGame.totalMistakes ?? activeGame.mistakes}
          onNewGame={() => startNewGame(currentLevel)}
          onGoHome={() => {
            setIsCompletionModalOpen(false);
            setCurrentView('home');
          }}
        />
      )}

      <AnalyticsModal
        isOpen={isAnalyticsOpen}
        onClose={() => setIsAnalyticsOpen(false)}
        history={history}
        currentStreak={currentStreak}
        bestStreak={bestStreak}
        initialTab={analyticsInitialTab}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onUpdateSettings={newSettings => {
          setSettings(newSettings);
          syncStorage(history, activeGame, newSettings);
        }}
        onExportData={() => {
          createBackupBinary(history, settings)
            .then(fileBytes => {
              downloadBackupFile(fileBytes, 'zensudoku.sudokubak');
              triggerToast('Backup downloaded');
            })
            .catch(err => {
              console.error('Export error:', err);
              triggerToast('Failed to export backup');
            });
        }}
        onImportBackupFile={async (fileBytes: Uint8Array) => {
          const parsed = await parseAndValidateBackup(fileBytes);
          setPendingBackupRestore(parsed);
        }}
        onResetProgress={handleResetProgress}
        onOpenPrintModal={() => setIsPrintModalOpen(true)}
      />

      <PrintPuzzlesModal
        isOpen={isPrintModalOpen}
        onClose={() => setIsPrintModalOpen(false)}
        onShowToast={triggerToast}
      />

      {/* Backup Restore Confirmation Dialog with Automatic Rollback Copy */}
      {pendingBackupRestore && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 select-none"
          style={{ borderRadius: '0px' }}
        >
          <div
            className="w-full max-w-md bg-white border border-slate-300 shadow-2xl p-6 space-y-4"
            style={{ borderRadius: '0px' }}
          >
            <h4 className="text-lg font-bold font-mono-numbers text-slate-900">
              Restore Backup?
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              This will replace your current game history and settings with{' '}
              <span className="font-bold text-slate-900">
                {pendingBackupRestore.records.length} completed puzzle records
              </span>
              . An automatic rollback copy of your current data will be saved.
            </p>
            <div className="flex gap-2 justify-end pt-3">
              <button
                onClick={() => setPendingBackupRestore(null)}
                className="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors cursor-pointer"
                style={{ borderRadius: '0px' }}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  try {
                    saveRollbackCopy({
                      version: 1,
                      history,
                      activeGame,
                      settings,
                    });

                    setHistory(pendingBackupRestore.records);
                    setSettings(pendingBackupRestore.settings);
                    setActiveGame(null);
                    syncStorage(pendingBackupRestore.records, null, pendingBackupRestore.settings);

                    setPendingBackupRestore(null);
                    setIsSettingsOpen(false);
                    setCurrentView('home');
                    triggerToast('Backup restored successfully');
                  } catch (err) {
                    console.error('Failed to apply restore:', err);
                    triggerToast('Failed to restore backup');
                  }
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-colors cursor-pointer"
                style={{ borderRadius: '0px' }}
              >
                Confirm Restore
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
