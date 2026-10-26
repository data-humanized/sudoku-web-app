import React from 'react';
import { Award, Clock, Flame, AlertCircle, Lightbulb, RotateCcw, Home } from 'lucide-react';
import { Difficulty } from '../logic/sudokuLogic';

interface CompletionModalProps {
  isOpen: boolean;
  level: Difficulty;
  score: number;
  currentStreak: number;
  seconds: number;
  hintsUsed: number;
  mistakes: number;
  onNewGame: () => void;
  onGoHome: () => void;
}

export const CompletionModal: React.FC<CompletionModalProps> = ({
  isOpen,
  level,
  score,
  currentStreak,
  seconds,
  hintsUsed,
  mistakes,
  onNewGame,
  onGoHome,
}) => {
  if (!isOpen) return null;

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 select-none"
      style={{ borderRadius: '0px' }}
    >
      <div
        className="w-full max-w-lg bg-white border border-slate-300 shadow-2xl p-6 sm:p-8 space-y-6 animate-in fade-in zoom-in-95 duration-200"
        style={{ borderRadius: '0px' }}
      >
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="mx-auto w-14 h-14 bg-blue-50 text-blue-600 flex items-center justify-center">
            <Award className="w-8 h-8" />
          </div>
          <span className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
            Puzzle Solved
          </span>
          <h2 className="text-3xl font-extrabold text-slate-900 capitalize">
            {level} Completed
          </h2>
          <div className="text-4xl font-extrabold font-mono-numbers text-blue-600 pt-1">
            +{score.toLocaleString()} <span className="text-lg font-bold text-slate-500">pts</span>
          </div>
        </div>

        {/* Breakdown Stats Grid */}
        <div className="grid grid-cols-2 gap-3 bg-slate-50 border border-slate-200 p-4 text-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white border border-slate-200 text-slate-600">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs text-slate-400">Time Taken</div>
              <div className="font-bold font-mono-numbers text-slate-800">
                {formatTime(seconds)}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-white border border-slate-200 text-amber-500">
              <Flame className="w-4 h-4 fill-amber-500" />
            </div>
            <div>
              <div className="text-xs text-slate-400">Daily Streak</div>
              <div className="font-bold font-mono-numbers text-slate-800">
                {currentStreak} {currentStreak === 1 ? 'day' : 'days'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-white border border-slate-200 text-slate-600">
              <Lightbulb className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs text-slate-400">Hints Used</div>
              <div className="font-bold font-mono-numbers text-slate-800">
                {hintsUsed}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 bg-white border border-slate-200 text-slate-600">
              <AlertCircle className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs text-slate-400">Mistakes</div>
              <div className="font-bold font-mono-numbers text-slate-800">
                {mistakes}/3
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <button
            onClick={onGoHome}
            className="py-3 px-4 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold text-sm tracking-wide transition-colors flex items-center justify-center gap-2 cursor-pointer"
            style={{ borderRadius: '0px' }}
          >
            <Home className="w-4 h-4" />
            <span>Home</span>
          </button>
          <button
            onClick={onNewGame}
            className="py-3 px-4 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm tracking-wide transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs"
            style={{ borderRadius: '0px' }}
          >
            <RotateCcw className="w-4 h-4" />
            <span>Next Puzzle</span>
          </button>
        </div>
      </div>
    </div>
  );
};
