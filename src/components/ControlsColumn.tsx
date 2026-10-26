import React, { useState, useRef, useEffect } from 'react';
import {
  RotateCcw,
  Eraser,
  PenTool,
  Lightbulb,
  Play,
  Pause,
  ChevronDown,
} from 'lucide-react';

interface ControlsColumnProps {
  dailyScore: number;
  mistakes: number;
  elapsedSeconds: number;
  isPaused: boolean;
  onTogglePause: () => void;
  onUndo: () => void;
  canUndo: boolean;
  onErase: () => void;
  isNotesMode: boolean;
  onToggleNotesMode: () => void;
  onHintFillNumber: () => void;
  onHintFillPossibilities: () => void;
  onInputDigit: (digit: number) => void;
  onNewGame: () => void;
  showTimer: boolean;
}

export const ControlsColumn: React.FC<ControlsColumnProps> = ({
  dailyScore,
  mistakes,
  elapsedSeconds,
  isPaused,
  onTogglePause,
  onUndo,
  canUndo,
  onErase,
  isNotesMode,
  onToggleNotesMode,
  onHintFillNumber,
  onHintFillPossibilities,
  onInputDigit,
  onNewGame,
  showTimer,
}) => {
  const [hintMenuOpen, setHintMenuOpen] = useState(false);
  const hintRef = useRef<HTMLDivElement>(null);

  // Close hint dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (hintRef.current && !hintRef.current.contains(e.target as Node)) {
        setHintMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full flex flex-col justify-between h-full space-y-4 lg:min-w-[420px] select-none">
      {/* 1. Stats Row: Daily Score (XXX pts), Mistakes (n/3), and Time with Play/Pause toggle */}
      <div className="grid grid-cols-3 gap-2 bg-white border border-slate-200 p-3 shadow-xs">
        {/* Daily Score */}
        <div className="flex flex-col items-center justify-center border-r border-slate-100 pr-2">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
            Score
          </span>
          <span className="text-base sm:text-lg font-bold font-mono-numbers text-slate-800">
            {dailyScore.toLocaleString()} <span className="text-xs font-normal text-slate-400">pts</span>
          </span>
        </div>

        {/* Mistakes Counter: real-time "Mistakes: n/3" */}
        <div className="flex flex-col items-center justify-center border-r border-slate-100 px-2">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
            Mistakes
          </span>
          <span
            className={`text-base sm:text-lg font-bold font-mono-numbers ${
              mistakes > 0 ? 'text-red-600' : 'text-slate-800'
            }`}
          >
            {mistakes}/3
          </span>
        </div>

        {/* Time with Play/Pause button */}
        <div className="flex items-center justify-center gap-2 pl-2">
          {showTimer && (
            <div className="flex flex-col items-start">
              <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                Time
              </span>
              <span className="text-base sm:text-lg font-bold font-mono-numbers text-slate-800">
                {formatTime(elapsedSeconds)}
              </span>
            </div>
          )}
          <button
            onClick={onTogglePause}
            aria-label={isPaused ? 'Resume Game' : 'Pause Game'}
            title={isPaused ? 'Resume (Space)' : 'Pause (Space)'}
            className="p-2 text-slate-600 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
            style={{ borderRadius: '0px' }}
          >
            {isPaused ? <Play className="w-4 h-4 fill-slate-700" /> : <Pause className="w-4 h-4 fill-slate-700" />}
          </button>
        </div>
      </div>

      {/* 2. Four Tool Action Buttons: Undo, Erase, Notes, Hint */}
      <div className="grid grid-cols-4 gap-2">
        {/* Undo */}
        <button
          disabled={isPaused || !canUndo}
          onClick={onUndo}
          title="Undo (Ctrl+Z or U)"
          aria-label="Undo move"
          className={`
            flex flex-col items-center justify-center py-2.5 px-2 bg-white border border-slate-200 text-slate-700 transition-all
            ${isPaused || !canUndo
              ? 'opacity-40 cursor-not-allowed bg-slate-50'
              : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
            }
          `}
          style={{ borderRadius: '0px' }}
        >
          <RotateCcw className="w-5 h-5 mb-1" />
          <span className="text-xs font-medium">Undo</span>
        </button>

        {/* Erase */}
        <button
          disabled={isPaused}
          onClick={onErase}
          title="Erase (Backspace or Del)"
          aria-label="Erase cell"
          className={`
            flex flex-col items-center justify-center py-2.5 px-2 bg-white border border-slate-200 text-slate-700 transition-all
            ${isPaused
              ? 'opacity-40 cursor-not-allowed bg-slate-50'
              : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
            }
          `}
          style={{ borderRadius: '0px' }}
        >
          <Eraser className="w-5 h-5 mb-1" />
          <span className="text-xs font-medium">Erase</span>
        </button>

        {/* Notes Mode Toggle */}
        <button
          disabled={isPaused}
          onClick={onToggleNotesMode}
          title="Toggle Pencil Notes (N)"
          aria-label={`Pencil notes ${isNotesMode ? 'active' : 'inactive'}`}
          className={`
            relative flex flex-col items-center justify-center py-2.5 px-2 border transition-all
            ${isNotesMode
              ? 'bg-blue-50 border-blue-600 text-blue-700 font-bold shadow-xs'
              : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-xs'
            }
            ${isPaused ? 'opacity-40 cursor-not-allowed bg-slate-50' : 'cursor-pointer active:translate-y-0.5'}
          `}
          style={{ borderRadius: '0px' }}
        >
          <PenTool className="w-5 h-5 mb-1" />
          <span className="text-xs font-medium">Notes</span>
          {/* Active status indicator badge */}
          <span
            className={`absolute top-1 right-1 text-[9px] px-1 py-0.2 font-mono uppercase font-bold tracking-tight ${
              isNotesMode ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'
            }`}
          >
            {isNotesMode ? 'ON' : 'OFF'}
          </span>
        </button>

        {/* Hint Dropdown */}
        <div className="relative" ref={hintRef}>
          <button
            disabled={isPaused}
            onClick={() => setHintMenuOpen(!hintMenuOpen)}
            title="Hint (H)"
            aria-label="Hint actions"
            aria-expanded={hintMenuOpen}
            className={`
              w-full h-full flex flex-col items-center justify-center py-2.5 px-2 bg-white border border-slate-200 text-slate-700 transition-all
              ${isPaused
                ? 'opacity-40 cursor-not-allowed bg-slate-50'
                : 'hover:bg-slate-50 hover:text-slate-900 cursor-pointer shadow-xs active:translate-y-0.5'
              }
            `}
            style={{ borderRadius: '0px' }}
          >
            <div className="flex items-center gap-0.5">
              <Lightbulb className="w-5 h-5 mb-1 text-amber-500 fill-amber-500/20" />
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </div>
            <span className="text-xs font-medium">Hint</span>
          </button>

          {/* Strict Hint Menu Dropdown */}
          {hintMenuOpen && !isPaused && (
            <div
              className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 shadow-xl z-30 py-1"
              style={{ borderRadius: '0px' }}
            >
              <button
                onClick={() => {
                  setHintMenuOpen(false);
                  onHintFillNumber();
                }}
                className="w-full text-left px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50 transition-colors flex flex-col cursor-pointer"
              >
                <span>Fill number</span>
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
                <span>Fill possible numbers</span>
                <span className="text-[10px] text-slate-400 font-normal">
                  Pencil notes for selected cell
                </span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 3. Number Pad:
          - Desktop (>= 1024px): 3x3 keypad, height clamp(88px, 11vh, 106px), font clamp(32px, 4.5vh, 48px), 12px gap.
          - Mobile (< 1024px): 1x9 row, height >= 56px.
          - Permanently visible and enabled.
      */}
      <div className="w-full">
        {/* Desktop 3x3 layout */}
        <div className="hidden lg:grid grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
            <button
              key={num}
              disabled={isPaused}
              onClick={() => onInputDigit(num)}
              aria-label={`Input number ${num}`}
              className={`
                w-full bg-white border border-slate-200 text-slate-900 font-mono-numbers font-bold transition-all shadow-xs
                ${isPaused
                  ? 'opacity-40 cursor-not-allowed bg-slate-50'
                  : 'hover:bg-slate-50 hover:border-blue-400 active:bg-blue-50 active:scale-[0.98] cursor-pointer'
                }
              `}
              style={{
                height: 'clamp(88px, 11vh, 106px)',
                fontSize: 'clamp(32px, 4.5vh, 48px)',
                borderRadius: '0px',
              }}
            >
              {num}
            </button>
          ))}
        </div>

        {/* Compact/Mobile 1x9 layout */}
        <div className="grid lg:hidden grid-cols-9 gap-1.5">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
            <button
              key={num}
              disabled={isPaused}
              onClick={() => onInputDigit(num)}
              aria-label={`Input number ${num}`}
              className={`
                h-14 bg-white border border-slate-200 text-slate-900 font-mono-numbers text-xl font-bold transition-all shadow-xs
                ${isPaused
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:bg-slate-50 active:bg-blue-50 cursor-pointer'
                }
              `}
              style={{ borderRadius: '0px' }}
            >
              {num}
            </button>
          ))}
        </div>
      </div>

      {/* 4. Full-Width "New Game" Button (prominent blue accent #2563eb) */}
      <button
        onClick={onNewGame}
        aria-label="Start New Game"
        className="w-full py-3.5 px-4 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm tracking-wide uppercase transition-colors shadow-sm cursor-pointer"
        style={{ borderRadius: '0px' }}
      >
        New Game
      </button>
    </div>
  );
};
