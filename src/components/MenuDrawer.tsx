import React from 'react';
import { X, BarChart2, Calendar, Settings, Home, Flame, Award, ShieldCheck } from 'lucide-react';

interface MenuDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAnalytics: () => void;
  onOpenHistory: () => void;
  onOpenSettings: () => void;
  onGoHome: () => void;
  currentStreak: number;
  dailyScore: number;
}

export const MenuDrawer: React.FC<MenuDrawerProps> = ({
  isOpen,
  onClose,
  onOpenAnalytics,
  onOpenHistory,
  onOpenSettings,
  onGoHome,
  currentStreak,
  dailyScore,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-72 max-w-[85vw] h-full bg-white border-r border-slate-200 shadow-2xl flex flex-col justify-between p-5 animate-in slide-in-from-left duration-250 select-none"
        onClick={e => e.stopPropagation()}
        style={{ borderRadius: '0px' }}
      >
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold font-mono-numbers text-slate-900">
                Zen<span className="text-blue-600">Sudoku</span>
              </span>
            </div>
            <button
              onClick={onClose}
              aria-label="Close menu"
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
              style={{ borderRadius: '0px' }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Quick Stats Badges */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-50 border border-slate-200 p-2.5 text-center">
              <div className="flex items-center justify-center gap-1 text-[11px] font-bold text-amber-500 uppercase tracking-wider">
                <Flame className="w-3.5 h-3.5 fill-amber-500" />
                <span>Streak</span>
              </div>
              <div className="text-lg font-bold font-mono-numbers text-slate-800 mt-0.5">
                {currentStreak} <span className="text-xs font-normal text-slate-500">d</span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 p-2.5 text-center">
              <div className="flex items-center justify-center gap-1 text-[11px] font-bold text-blue-600 uppercase tracking-wider">
                <Award className="w-3.5 h-3.5" />
                <span>Today</span>
              </div>
              <div className="text-lg font-bold font-mono-numbers text-slate-800 mt-0.5">
                {dailyScore.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <nav className="space-y-1.5 pt-2">
            <button
              onClick={() => {
                onClose();
                onOpenAnalytics();
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer text-left"
              style={{ borderRadius: '0px' }}
            >
              <BarChart2 className="w-4.5 h-4.5 text-slate-500" />
              <span>Analytics & Stats</span>
            </button>

            <button
              onClick={() => {
                onClose();
                onOpenHistory();
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer text-left"
              style={{ borderRadius: '0px' }}
            >
              <Calendar className="w-4.5 h-4.5 text-slate-500" />
              <span>History & Calendar</span>
            </button>

            <button
              onClick={() => {
                onClose();
                onOpenSettings();
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer text-left"
              style={{ borderRadius: '0px' }}
            >
              <Settings className="w-4.5 h-4.5 text-slate-500" />
              <span>Settings</span>
            </button>

            <button
              onClick={() => {
                onClose();
                onGoHome();
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer text-left"
              style={{ borderRadius: '0px' }}
            >
              <Home className="w-4.5 h-4.5 text-slate-500" />
              <span>Return to Home Hub</span>
            </button>
          </nav>
        </div>

        {/* Footer info moved into drawer */}
        <div className="pt-4 border-t border-slate-200 text-center">
          <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Distraction-free · Offline · Local</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            Zero ads · Zero accounts · Local JSON
          </div>
        </div>
      </div>
    </div>
  );
};
