/**
 * ZenSudoku - Desktop Minimalist Sudoku Application
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Difficulty,
  GameState,
  HistoryRecord,
  MoveAction,
  UserSettings,
  DEFAULT_SETTINGS,
  calculateScore,
  calculateDailyScore,
  calculateStreak,
  getLevelUnlockStatus,
  getNewPuzzle,
  getCandidates,
  cloneGrid,
  cloneNotes,
  cloneBoolGrid,
  createEmptyBoolGrid,
  createEmptyNotes,
  getPeers,
} from './logic/sudokuLogic';
import {
  loadZenData,
  saveZenData,
  exportBackupJSON,
  importBackupJSON,
  ZenSudokuStorage,
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
import {
  InGameHeader,
  DailyScoreLine,
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
  const [isLivesModalOpen, setIsLivesModalOpen] = useState(false);
  const [isCompletionModalOpen, setIsCompletionModalOpen] = useState(false);

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
  const [shakingCell, setShakingCell] = useState<[number, number] | null>(null);
  const [tooltip, setTooltip] = useState<{ cell: [number, number]; text: string } | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const tooltipTimerRef = useRef<NodeJS.Timeout | null>(null);
  const toastTimerRef = useRef<NodeJS.Timeout | null>(null);

  // --- Initialize from Local Storage on mount ---
  useEffect(() => {
    const data = loadZenData();
    setHistory(data.history || []);
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

  // Update sound manager whenever settings change
  useEffect(() => {
    sounds.enabled = settings.soundEffects;
  }, [settings.soundEffects]);

  // Sync state to local storage
  const syncStorage = useCallback((
    newHistory: HistoryRecord[],
    newActiveGame: GameState | null,
    newSettings: UserSettings
  ) => {
    const storageData: ZenSudokuStorage = {
      version: 1,
      history: newHistory,
      activeGame: newActiveGame,
      settings: newSettings,
    };
    saveZenData(storageData);
  }, []);

  // Current local calendar date YYYY-MM-DD
  const getTodayISO = () => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const todayISO = getTodayISO();
  const { currentStreak, bestStreak } = calculateStreak(history, todayISO);
  const dailyScore = calculateDailyScore(history, todayISO);
  const unlockStatus = getLevelUnlockStatus(history);

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
      setToastMessage(null), 2500;
    });
  }, []);

  // --- Start a New Game ---
  const startNewGame = useCallback((level: Difficulty) => {
    const { puzzle, solution } = getNewPuzzle(level);
    const newGame: GameState = {
      id: `game-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      level,
      initialGrid: puzzle,
      solutionGrid: solution,
      currentGrid: cloneGrid(puzzle),
      notes: createEmptyNotes(),
      hintedCells: createEmptyBoolGrid(),
      mistakes: 0,
      hintsUsed: 0,
      elapsedSeconds: 0,
      isPaused: false,
      isCompleted: false,
      undoStack: [],
      redoStack: [],
      startTime: Date.now(),
      finalScore: 0,
    };

    setActiveGame(newGame);
    setCurrentLevel(level);
    setSelectedCell([0, 0]);
    setIsNotesMode(false);
    setIsLivesModalOpen(false);
    setIsCompletionModalOpen(false);
    setCurrentView('game');
    syncStorage(history, newGame, settings);
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
    const finalScore = calculateScore(
      finalGame.level,
      finalGame.elapsedSeconds,
      finalGame.hintsUsed,
      finalGame.mistakes
    );

    const record: HistoryRecord = {
      id: finalGame.id,
      date: getTodayISO(),
      timestamp: Date.now(),
      level: finalGame.level,
      seconds: finalGame.elapsedSeconds,
      score: finalScore,
      hintsUsed: finalGame.hintsUsed,
      mistakes: finalGame.mistakes,
    };

    const newHistory = [...history, record];
    const completedGameState: GameState = {
      ...finalGame,
      isCompleted: true,
      finalScore,
      completedTime: Date.now(),
    };

    setHistory(newHistory);
    setActiveGame(completedGameState);
    setIsCompletionModalOpen(true);
    syncStorage(newHistory, null, settings);
  }, [history, settings, syncStorage]);

  // --- Input a Digit (or Note) ---
  const handleInputDigit = useCallback((digit: number) => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select a cell first');
      return;
    }

    const [r, c] = selectedCell;

    // Check if cell is pre-filled initial clue
    if (activeGame.initialGrid[r][c] !== 0) {
      triggerTooltip([r, c], "Can't fill pre-filled box");
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
      // already contains this number
      return;
    }

    const isCorrect = digit === activeGame.solutionGrid[r][c];

    if (!isCorrect) {
      // Mistake!
      sounds.playError();
      if (settings.hapticFeedback && navigator.vibrate) {
        navigator.vibrate(200);
      }
      setShakingCell([r, c]);
      setTimeout(() => setShakingCell(null), 350);

      const newMistakes = activeGame.mistakes + 1;
      const newGrid = cloneGrid(activeGame.currentGrid);
      newGrid[r][c] = digit; // Remains editable & visible in red

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
        undoStack: [...activeGame.undoStack, moveAction],
        redoStack: [],
      };

      setActiveGame(updatedGame);
      syncStorage(history, updatedGame, settings);

      // Check if 3 mistakes reached -> trigger 5-second lives modal
      if (newMistakes >= 3) {
        setIsLivesModalOpen(true);
      }
      return;
    }

    // Correct entry!
    sounds.playClick();
    const newGrid = cloneGrid(activeGame.currentGrid);
    newGrid[r][c] = digit;

    const newNotes = cloneNotes(activeGame.notes);
    const prevCellNotes = Array.from(newNotes[r][c]);
    newNotes[r][c].clear(); // clear pencil notes in solved cell

    // Auto-remove notes in peers if enabled in settings
    const peerChanges: { row: number; col: number; removedNote: number }[] = [];
    if (settings.autoRemoveNotes) {
      for (const [pr, pc] of getPeers(r, c)) {
        if (newNotes[pr][pc].has(digit)) {
          newNotes[pr][pc].delete(digit);
          peerChanges.push({ row: pr, col: pc, removedNote: digit });
        }
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
      undoStack: [...activeGame.undoStack, moveAction],
      redoStack: [],
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);

    // Check if puzzle is solved!
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
    if (activeGame.initialGrid[r][c] !== 0) {
      triggerTooltip([r, c], "Can't fill pre-filled box");
      return;
    }

    const prevVal = activeGame.currentGrid[r][c];
    const prevNotes = Array.from(activeGame.notes[r][c]);

    if (prevVal === 0 && prevNotes.length === 0) return;

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
  }, [activeGame, isLivesModalOpen, selectedCell, triggerTooltip, history, settings, syncStorage]);

  // --- Undo Action ---
  const handleUndo = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (activeGame.undoStack.length === 0) return;

    const undoStack = [...activeGame.undoStack];
    const lastAction = undoStack.pop()!;
    const newGrid = cloneGrid(activeGame.currentGrid);
    const newNotes = cloneNotes(activeGame.notes);

    // Revert cell value
    newGrid[lastAction.row][lastAction.col] = lastAction.prevVal;
    // Revert cell notes
    newNotes[lastAction.row][lastAction.col] = new Set(lastAction.prevNotes);

    // Revert peer notes removals if any
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
      redoStack: [...activeGame.redoStack, lastAction],
    };

    setSelectedCell([lastAction.row, lastAction.col]);
    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [activeGame, isLivesModalOpen, history, settings, syncStorage]);

  // --- Strict Cell-Specific Hint: Fill Number ---
  const handleHintFillNumber = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select a cell first');
      return;
    }
    const [r, c] = selectedCell;

    if (activeGame.initialGrid[r][c] !== 0) {
      triggerTooltip([r, c], "Can't fill pre-filled box");
      return;
    }
    if (activeGame.currentGrid[r][c] !== 0) {
      triggerTooltip([r, c], 'Block already filled');
      return;
    }

    sounds.playClick();
    const correctVal = activeGame.solutionGrid[r][c];
    const newGrid = cloneGrid(activeGame.currentGrid);
    newGrid[r][c] = correctVal;

    const newNotes = cloneNotes(activeGame.notes);
    newNotes[r][c].clear();

    const newHintedCells = cloneBoolGrid(activeGame.hintedCells);
    newHintedCells[r][c] = true;

    // Auto-remove notes in peers
    if (settings.autoRemoveNotes) {
      for (const [pr, pc] of getPeers(r, c)) {
        newNotes[pr][pc].delete(correctVal);
      }
    }

    const updatedGame: GameState = {
      ...activeGame,
      currentGrid: newGrid,
      notes: newNotes,
      hintedCells: newHintedCells,
      hintsUsed: activeGame.hintsUsed + 1,
      undoStack: [],
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
    settings,
    triggerToast,
    triggerTooltip,
    history,
    syncStorage,
    checkCompletion,
    handleVictory,
  ]);

  // --- Strict Cell-Specific Hint: Fill Possible Numbers (Candidates) ---
  const handleHintFillPossibilities = useCallback(() => {
    if (!activeGame || activeGame.isPaused || activeGame.isCompleted || isLivesModalOpen) return;
    if (!selectedCell) {
      triggerToast('Select a cell first');
      return;
    }
    const [r, c] = selectedCell;

    if (activeGame.initialGrid[r][c] !== 0) {
      triggerTooltip([r, c], "Can't fill pre-filled box");
      return;
    }
    if (activeGame.currentGrid[r][c] !== 0) {
      triggerTooltip([r, c], 'Block already filled');
      return;
    }

    sounds.playNote();
    // Computes and populates pencil candidates into that cell only
    const candidates = getCandidates(activeGame.currentGrid, r, c);
    const newNotes = cloneNotes(activeGame.notes);
    newNotes[r][c] = candidates;

    const updatedGame: GameState = {
      ...activeGame,
      notes: newNotes,
      hintsUsed: activeGame.hintsUsed + 1,
    };

    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [
    activeGame,
    isLivesModalOpen,
    selectedCell,
    triggerToast,
    triggerTooltip,
    history,
    settings,
    syncStorage,
  ]);

  // --- Toggle Pause ---
  const handleTogglePause = useCallback(() => {
    if (!activeGame || activeGame.isCompleted || isLivesModalOpen) return;
    const isPaused = !activeGame.isPaused;
    const updatedGame = { ...activeGame, isPaused };
    setActiveGame(updatedGame);
    syncStorage(history, updatedGame, settings);
  }, [activeGame, isLivesModalOpen, history, settings, syncStorage]);

  // --- Keyboard Shortcuts ---
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in inputs or if any modal is open
      if (e.target instanceof HTMLInputElement || isSettingsOpen || isAnalyticsOpen || isCompletionModalOpen) {
        return;
      }

      if (isLivesModalOpen) return;

      const key = e.key;

      // Digits 1-9
      if (/^[1-9]$/.test(key)) {
        e.preventDefault();
        handleInputDigit(parseInt(key, 10));
        return;
      }

      // Erase (Backspace, Delete, 0)
      if (key === 'Backspace' || key === 'Delete' || key === '0') {
        e.preventDefault();
        handleErase();
        return;
      }

      // Notes mode toggle: 'N'
      if (key.toLowerCase() === 'n') {
        e.preventDefault();
        setIsNotesMode(prev => !prev);
        return;
      }

      // Undo: U or Ctrl+Z
      if ((e.ctrlKey || e.metaKey) && key.toLowerCase() === 'z') {
        e.preventDefault();
        handleUndo();
        return;
      }
      if (key.toLowerCase() === 'u') {
        e.preventDefault();
        handleUndo();
        return;
      }

      // Pause/Resume: Space or P
      if (key === ' ' || key.toLowerCase() === 'p') {
        e.preventDefault();
        handleTogglePause();
        return;
      }

      // Hint: H
      if (key.toLowerCase() === 'h') {
        e.preventDefault();
        handleHintFillNumber();
        return;
      }

      // Grid navigation: Arrows or WASD
      if (selectedCell) {
        const [r, c] = selectedCell;
        if (key === 'ArrowUp' || key.toLowerCase() === 'w') {
          e.preventDefault();
          setSelectedCell([Math.max(0, r - 1), c]);
        } else if (key === 'ArrowDown' || key.toLowerCase() === 's') {
          e.preventDefault();
          setSelectedCell([Math.min(8, r + 1), c]);
        } else if (key === 'ArrowLeft' || key.toLowerCase() === 'a') {
          e.preventDefault();
          setSelectedCell([r, Math.max(0, c - 1)]);
        } else if (key === 'ArrowRight' || key.toLowerCase() === 'd') {
          e.preventDefault();
          setSelectedCell([r, Math.min(8, c + 1)]);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    selectedCell,
    handleInputDigit,
    handleErase,
    handleUndo,
    handleTogglePause,
    handleHintFillNumber,
    isSettingsOpen,
    isAnalyticsOpen,
    isLivesModalOpen,
    isCompletionModalOpen,
  ]);

  // --- Reset All Progress ---
  const handleResetProgress = () => {
    setHistory([]);
    setActiveGame(null);
    saveZenData({
      version: 1,
      history: [],
      activeGame: null,
      settings,
    });
    setCurrentView('home');
    triggerToast('All progress reset');
  };

  const todayGames = history.filter(r => r.date === todayISO);

  return (
    <div
      className={`${
        currentView === 'home'
          ? 'min-h-screen overflow-y-auto'
          : 'h-[100dvh] max-h-[100dvh] overflow-hidden'
      } bg-[#f8fafc] text-[#0f172a] flex flex-col antialiased select-none`}
      style={{
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        paddingLeft: 'env(safe-area-inset-left, 0px)',
        paddingRight: 'env(safe-area-inset-right, 0px)',
      }}
    >
      {currentView === 'home' ? (
        <>
          {/* Top Bar for Home View */}
          <Header
            currentView={currentView}
            onNavigateHome={() => setCurrentView('home')}
            currentStreak={currentStreak}
            dailyScore={dailyScore}
            onOpenAnalytics={() => {
              setAnalyticsInitialTab('analytics');
              setIsAnalyticsOpen(true);
            }}
            onOpenSettings={() => setIsSettingsOpen(true)}
          />

          {/* Main Home Hub */}
          <main className="flex-1 flex flex-col items-center justify-center p-2 sm:p-4 lg:p-6 w-full">
            <HomeScreen
              currentStreak={currentStreak}
              bestStreak={bestStreak}
              todayScore={dailyScore}
              todayGames={todayGames}
              activeGame={activeGame}
              unlockStatus={unlockStatus}
              onStartGame={level => startNewGame(level)}
              onResumeActiveGame={() => setCurrentView('game')}
            />
          </main>
        </>
      ) : (
        /* IN-GAME VIEW: Guaranteed Fits on ONE Screen with ZERO Scrolling */
        <>
          {/* Menu Drawer */}
          <MenuDrawer
            isOpen={isMenuDrawerOpen}
            onClose={() => setIsMenuDrawerOpen(false)}
            onOpenAnalytics={() => {
              setAnalyticsInitialTab('analytics');
              setIsAnalyticsOpen(true);
            }}
            onOpenHistory={() => {
              setAnalyticsInitialTab('history');
              setIsAnalyticsOpen(true);
            }}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onGoHome={() => setCurrentView('home')}
            currentStreak={currentStreak}
            dailyScore={dailyScore}
          />

          {/* 1. Compact Header: menu hamburger icon, app name, New Game button */}
          <InGameHeader
            onOpenMenu={() => setIsMenuDrawerOpen(true)}
            onNewGame={() => startNewGame(currentLevel)}
          />

          {/* Main In-Game Viewport: Zero Scroll Flex Column */}
          <main className="flex-1 min-h-0 flex flex-col overflow-hidden w-full">
            {!isTwoColumn ? (
              /* A) COMPACT LAYOUT (Default: phones, narrow screens, tablet portrait) */
              <div className="w-full h-full flex flex-col justify-between items-center max-w-[540px] mx-auto px-2 pb-1 min-h-0">
                {/* 2. Daily score, small and centered above stats row (single line, no big card) */}
                <DailyScoreLine score={dailyScore} />

                {/* 3. One slim stats row with Difficulty dropdown, Mistakes 0/3, Time + round pause button */}
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

                {/* 4. The 9x9 grid: perfect square sized dynamically from remaining height */}
                <div className="flex-1 min-h-0 flex items-center justify-center w-full py-1">
                  {activeGame && (
                    <div
                      className="w-full max-w-[min(calc(100vw-16px),calc(100dvh-215px),520px)] aspect-square flex items-center justify-center"
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
                        shakingCell={shakingCell}
                        tooltip={tooltip}
                        className="w-full h-full"
                      />
                    </div>
                  )}
                </div>

                {/* 5. Row of four tool buttons directly under the grid (Undo, Erase, Notes ON/OFF, Hint badge) */}
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

                {/* 6. Single row of 9 number buttons directly under tools */}
                {activeGame && (
                  <NumberPadRow
                    onInputDigit={handleInputDigit}
                    isPaused={activeGame.isPaused}
                  />
                )}
              </div>
            ) : (
              /* C) LARGE SCREENS AND LANDSCAPE (Two-Column Side-by-Side Layout) */
              <div className="w-full h-full flex items-center justify-center gap-6 lg:gap-10 max-w-[1300px] mx-auto px-4 py-2 min-h-0">
                {/* Left Column: Inline Difficulty tabs (if roomy) + 9x9 Grid */}
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
                        shakingCell={shakingCell}
                        tooltip={tooltip}
                        className="w-full h-full"
                      />
                    </div>
                  )}
                </div>

                {/* Right Column: Score, Slim Stats, Tools, 3x3 Keypad, New Game */}
                {activeGame && (
                  <div
                    className="w-full max-w-[390px] min-w-[310px] flex flex-col justify-between min-h-0 py-1"
                    style={{
                      height: showInlineTabs
                        ? 'min(calc(100dvh - 120px), 740px, 48vw)'
                        : 'min(calc(100dvh - 80px), 740px, 48vw)',
                    }}
                  >
                    {/* Score */}
                    <DailyScoreLine score={dailyScore} />

                    {/* Slim stats row */}
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

                    {/* 4 Tool buttons */}
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

                    {/* 3x3 Keypad */}
                    <div className="py-1">
                      <Keypad3x3
                        onInputDigit={handleInputDigit}
                        isPaused={activeGame.isPaused}
                        buttonHeight={windowDimensions.height < 500 ? '40px' : 'clamp(52px, 9vh, 88px)'}
                        fontSize={windowDimensions.height < 500 ? '22px' : 'clamp(26px, 4vh, 42px)'}
                      />
                    </div>

                    {/* Prominent New Game button */}
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
          mistakes={activeGame.mistakes}
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
          exportBackupJSON({
            version: 1,
            history,
            activeGame,
            settings,
          });
        }}
        onImportData={content => {
          const restored = importBackupJSON(content);
          setHistory(restored.history);
          setSettings(restored.settings);
          if (restored.activeGame) {
            setActiveGame(restored.activeGame);
          }
        }}
        onResetProgress={handleResetProgress}
      />
    </div>
  );
}
