import React from 'react';
import { Flame, BarChart2, Settings, Home } from 'lucide-react';

interface HeaderProps {
  currentView: 'home' | 'game';
  onNavigateHome: () => void;
  currentStreak: number;
  dailyScore?: number;
  onOpenAnalytics: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  onNavigateHome,
  currentStreak,
  dailyScore,
  onOpenAnalytics,
  onOpenSettings,
}) => {
  return (
    <header className="w-full max-w-[1300px] mx-auto px-4 sm:px-6 py-4 flex items-center justify-between border-b border-slate-200">
      <div className="flex items-center gap-3">
        {currentView === 'game' && (
          <button
            onClick={onNavigateHome}
            title="Return to Home"
            aria-label="Return to Home"
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            <Home className="w-4 h-4" />
            <span className="hidden sm:inline">Home</span>
          </button>
        )}
        <div className="flex items-baseline gap-2">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 font-mono-numbers">
            Zen<span className="text-blue-600">Sudoku</span>
          </h1>
          <span className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
            DESKTOP
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* Streak Indicator */}
        <div
          title={`Current Streak: ${currentStreak} days`}
          className="flex items-center gap-1.5 px-3 py-1 bg-white border border-slate-200 text-slate-700 text-sm font-semibold shadow-xs"
        >
          <Flame className={`w-4 h-4 ${currentStreak > 0 ? 'text-amber-500 fill-amber-500' : 'text-slate-400'}`} />
          <span className="font-mono-numbers">{currentStreak}</span>
          <span className="text-xs text-slate-400 font-normal hidden sm:inline">streak</span>
        </div>


        {/* Analytics & Stats Button */}
        <button
          onClick={onOpenAnalytics}
          title="View Analytics & History"
          aria-label="View Analytics and History"
          className="p-2 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
        >
          <BarChart2 className="w-4.5 h-4.5" />
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          title="Game Settings"
          aria-label="Game Settings"
          className="p-2 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
        >
          <Settings className="w-4.5 h-4.5" />
        </button>
      </div>
    </header>
  );
};
