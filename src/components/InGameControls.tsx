import React, { useState, useRef, useEffect } from 'react';
import {
  Menu,
  RotateCcw,
  Eraser,
  PenTool,
  Lightbulb,
  Play,
  Pause,
  ChevronDown,
} from 'lucide-react';
import { Difficulty, UnlockStatus } from '../logic/sudokuLogic';
import { DifficultyDropdown } from './DifficultySelector';

interface InGameHeaderProps {
  onOpenMenu: () => void;
  onNewGame: () => void;
}

export const InGameHeader: React.FC<InGameHeaderProps> = ({
  onOpenMenu,
  onNewGame,
}) => {
  return (
    <header className="w-full h-12 flex items-center justify-between px-3 border-b border-slate-200 bg-white/90 shrink-0 select-none">
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenMenu}
          aria-label="Open menu"
          title="Open Menu"
          className="p-2 text-slate-700 hover:text-slate-950 hover:bg-slate-100 transition-colors cursor-pointer"
          style={{ borderRadius: '0px' }}
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-xl font-bold font-mono-numbers text-slate-900 tracking-tight">
          Zen<span className="text-blue-600">Sudoku</span>
        </span>
      </div>

      <button
        onClick={onNewGame}
        aria-label="Start new game"
        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-xs uppercase tracking-wide transition-colors cursor-pointer shadow-xs"
        style={{ borderRadius: '0px' }}
      >
        New Game
      </button>
    </header>
  );
};

interface ScoreLineProps {
  score: number;
}

export const LiveScoreLine: React.FC<ScoreLineProps> = ({ score }) => {
  return (
    <div className="w-full text-center py-1 text-xs sm:text-sm font-semibold text-slate-600 font-mono-numbers shrink-0 select-none">
      Score: <span className="font-extrabold text-blue-600 text-sm sm:text-base">{score.toLocaleString()}</span> pts
    </div>
  );
};

export const DailyScoreLine = LiveScoreLine;

interface SlimStatsRowProps {
  currentLevel: Difficulty;
  unlockStatus: Record<Difficulty, UnlockStatus>;
  onSelectLevel: (lvl: Difficulty) => void;
  mistakes: number;
  elapsedSeconds: number;
  isPaused: boolean;
  onTogglePause: () => void;
  showDropdown?: boolean;
  showTimer?: boolean;
}

export const SlimStatsRow: React.FC<SlimStatsRowProps> = ({
  currentLevel,
  unlockStatus,
  onSelectLevel,
  mistakes,
  elapsedSeconds,
  isPaused,
  onTogglePause,
  showDropdown = true,
  showTimer = true,
}) => {
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className={`w-full h-11 flex items-center ${showDropdown ? 'justify-between' : 'justify-around'} px-2 sm:px-4 bg-white border border-slate-200 text-xs sm:text-sm shrink-0 select-none shadow-xs`}>
      {/* Left: Difficulty dropdown (only shown when not using inline tabs) */}
      {showDropdown && (
        <div className="flex items-center justify-start shrink-0">
          <DifficultyDropdown
            currentLevel={currentLevel}
            unlockStatus={unlockStatus}
            onSelectLevel={onSelectLevel}
            disabled={isPaused}
          />
        </div>
      )}

      {/* Center: Mistakes 0/3 */}
      <div className="flex items-center justify-center font-mono-numbers font-semibold text-center whitespace-nowrap shrink-0 px-2">
        <span className="text-slate-500 mr-1 text-[11px] sm:text-xs">Mistakes</span>
        <span
          className={`font-bold text-xs sm:text-sm ${
            mistakes > 0 ? 'text-red-600' : 'text-slate-800'
          }`}
        >
          {mistakes}/3
        </span>
      </div>

      {/* Right: Time with round pause button beside it */}
      <div className="flex items-center gap-2 justify-end shrink-0">
        {showTimer && (
          <div className="flex items-center font-mono-numbers text-xs sm:text-sm font-semibold text-slate-800 whitespace-nowrap">
            <span className="text-slate-400 font-normal mr-1 text-[11px] sm:text-xs">Time</span>
            <span>{formatTime(elapsedSeconds)}</span>
          </div>
        )}

        <button
          onClick={onTogglePause}
          aria-label={isPaused ? 'Resume Game' : 'Pause Game'}
          title={isPaused ? 'Resume (Space)' : 'Pause (Space)'}
          className="w-7 h-7 rounded-full flex items-center justify-center bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 hover:text-slate-900 transition-colors cursor-pointer shadow-xs shrink-0"
        >
          {isPaused ? (
            <Play className="w-3.5 h-3.5 fill-slate-700 translate-x-0.5" />
          ) : (
            <Pause className="w-3.5 h-3.5 fill-slate-700" />
          )}
        </button>
      </div>
    </div>
  );
};

interface ToolButtonsRowProps {
  onUndo: () => void;
  canUndo: boolean;
  onErase: () => void;
  isNotesMode: boolean;
  onToggleNotesMode: () => void;
  onHintFillNumber: () => void;
  onHintFillPossibilities: () => void;
  hintsUsed: number;
  isPaused: boolean;
}

export const ToolButtonsRow: React.FC<ToolButtonsRowProps> = ({
  onUndo,
  canUndo,
  onErase,
  isNotesMode,
  onToggleNotesMode,
  onHintFillNumber,
  onHintFillPossibilities,
  hintsUsed,
  isPaused,
}) => {
  const [hintMenuOpen, setHintMenuOpen] = useState(false);
  const hintRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (hintRef.current && !hintRef.current.contains(e.target as Node)) {
        setHintMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const remainingHints = Math.max(0, 3 - hintsUsed);

  return (
    <div className="w-full grid grid-cols-4 gap-2 shrink-0 select-none py-1">
      {/* Undo */}
      <button
        disabled={isPaused || !canUndo}
        onClick={onUndo}
        title="Undo (Ctrl+Z or U)"
        aria-label="Undo move"
        className={`
          flex flex-col items-center justify-center py-1.5 px-1 bg-white border border-slate-200 text-slate-700 transition-all
          ${isPaused || !canUndo
            ? 'opacity-40 cursor-not-allowed bg-slate-50'
            : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
          }
        `}
        style={{ borderRadius: '0px' }}
      >
        <RotateCcw className="w-6 h-6 sm:w-7 sm:h-7 mb-0.5" />
        <span className="text-[11px] sm:text-xs font-semibold text-slate-600">Undo</span>
      </button>

      {/* Erase */}
      <button
        disabled={isPaused}
        onClick={onErase}
        title="Erase (Backspace or Del)"
        aria-label="Erase cell"
        className={`
          flex flex-col items-center justify-center py-1.5 px-1 bg-white border border-slate-200 text-slate-700 transition-all
          ${isPaused
            ? 'opacity-40 cursor-not-allowed bg-slate-50'
            : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
          }
        `}
        style={{ borderRadius: '0px' }}
      >
        <Eraser className="w-6 h-6 sm:w-7 sm:h-7 mb-0.5" />
        <span className="text-[11px] sm:text-xs font-semibold text-slate-600">Erase</span>
      </button>

      {/* Notes */}
      <button
        disabled={isPaused}
        onClick={onToggleNotesMode}
        title="Toggle Notes Mode (N)"
        aria-label={`Pencil notes ${isNotesMode ? 'active' : 'inactive'}`}
        className={`
          relative flex flex-col items-center justify-center py-1.5 px-1 border transition-all
          ${isNotesMode
            ? 'bg-blue-50 border-blue-600 text-blue-700 font-bold shadow-xs'
            : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-xs'
          }
          ${isPaused ? 'opacity-40 cursor-not-allowed bg-slate-50' : 'cursor-pointer active:translate-y-0.5'}
        `}
        style={{ borderRadius: '0px' }}
      >
        <PenTool className="w-6 h-6 sm:w-7 sm:h-7 mb-0.5" />
        <span className="text-[11px] sm:text-xs font-semibold text-slate-600">Notes</span>
        {/* Active status indicator badge */}
        <span
          className={`absolute top-1 right-1 text-[9px] px-1 font-mono uppercase font-bold tracking-tight ${
            isNotesMode ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'
          }`}
        >
          {isNotesMode ? 'ON' : 'OFF'}
        </span>
      </button>

      {/* Hint with remaining-count badge */}
      <div className="relative" ref={hintRef}>
        <button
          disabled={isPaused}
          onClick={() => setHintMenuOpen(!hintMenuOpen)}
          title="Hint (H)"
          aria-label="Hint options"
          aria-expanded={hintMenuOpen}
          className={`
            w-full h-full relative flex flex-col items-center justify-center py-1.5 px-1 bg-white border border-slate-200 text-slate-700 transition-all
            ${isPaused
              ? 'opacity-40 cursor-not-allowed bg-slate-50'
              : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
            }
          `}
          style={{ borderRadius: '0px' }}
        >
          <div className="flex items-center gap-0.5">
            <Lightbulb className="w-6 h-6 sm:w-7 sm:h-7 mb-0.5 text-amber-500 fill-amber-500/20" />
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </div>
          <span className="text-[11px] sm:text-xs font-semibold text-slate-600">Hint</span>
          {/* Remaining hints count badge */}
          <span className="absolute top-1 right-1 text-[9px] px-1 font-mono font-bold bg-amber-500 text-white tracking-tight">
            {remainingHints}
          </span>
        </button>

        {/* Hint Dropdown Menu */}
        {hintMenuOpen && !isPaused && (
          <div
            className="absolute right-0 bottom-full mb-1 sm:top-full sm:bottom-auto sm:mt-1 w-48 bg-white border border-slate-200 shadow-xl z-30 py-1"
            style={{ borderRadius: '0px' }}
          >
            <button
              onClick={() => {
                setHintMenuOpen(false);
                onHintFillNumber();
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 transition-colors flex flex-col cursor-pointer"
            >
              <span>Fill Number</span>
              <span className="text-[10px] text-slate-400 font-normal">
                Fills correct digit in selected cell
              </span>
            </button>
            <div className="border-t border-slate-100 my-1" />
            <button
              onClick={() => {
                setHintMenuOpen(false);
                onHintFillPossibilities();
              }}
              className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 transition-colors flex flex-col cursor-pointer"
            >
              <span>Fill Possibilities</span>
              <span className="text-[10px] text-slate-400 font-normal">
                Calculates pencil candidates
              </span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

interface NumberPadRowProps {
  onInputDigit: (digit: number) => void;
  isPaused: boolean;
}

export const NumberPadRow: React.FC<NumberPadRowProps> = ({
  onInputDigit,
  isPaused,
}) => {
  return (
    <div className="w-full grid grid-cols-9 gap-1 sm:gap-1.5 shrink-0 select-none pb-1">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
        <button
          key={num}
          disabled={isPaused}
          onClick={() => onInputDigit(num)}
          aria-label={`Input digit ${num}`}
          className={`
            h-13 sm:h-14 bg-white border border-slate-200 text-slate-900 font-mono-numbers text-[26px] sm:text-[30px] font-bold flex items-center justify-center transition-all shadow-xs
            ${isPaused
              ? 'opacity-40 cursor-not-allowed bg-slate-50'
              : 'hover:bg-slate-50 hover:border-blue-400 active:bg-blue-50 active:scale-[0.98] cursor-pointer'
            }
          `}
          style={{
            minWidth: '34px',
            borderRadius: '0px',
          }}
        >
          {num}
        </button>
      ))}
    </div>
  );
};

interface Keypad3x3Props {
  onInputDigit: (digit: number) => void;
  isPaused: boolean;
  buttonHeight?: string;
  fontSize?: string;
}

export const Keypad3x3: React.FC<Keypad3x3Props> = ({
  onInputDigit,
  isPaused,
  buttonHeight = 'clamp(44px, 8vh, 88px)',
  fontSize = 'clamp(24px, 3.5vh, 40px)',
}) => {
  return (
    <div className="w-full grid grid-cols-3 gap-2 select-none">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
        <button
          key={num}
          disabled={isPaused}
          onClick={() => onInputDigit(num)}
          aria-label={`Input number ${num}`}
          className={`
            w-full bg-white border border-slate-200 text-slate-900 font-mono-numbers font-bold flex items-center justify-center transition-all shadow-xs
            ${isPaused
              ? 'opacity-40 cursor-not-allowed bg-slate-50'
              : 'hover:bg-slate-50 hover:border-blue-400 active:bg-blue-50 active:scale-[0.98] cursor-pointer'
            }
          `}
          style={{
            height: buttonHeight,
            fontSize: fontSize,
            borderRadius: '0px',
          }}
        >
          {num}
        </button>
      ))}
    </div>
  );
};
