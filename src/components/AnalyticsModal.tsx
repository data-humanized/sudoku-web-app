import React, { useState } from 'react';
import { X, Calendar, BarChart2, Flame, Trophy, Clock, CheckCircle2 } from 'lucide-react';
import { HistoryRecord, Difficulty } from '../logic/sudokuLogic';

interface AnalyticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  history: HistoryRecord[];
  currentStreak: number;
  bestStreak: number;
  initialTab?: 'analytics' | 'history';
}

const DIFFICULTIES: Difficulty[] = ['easy', 'medium', 'hard', 'expert'];

export const AnalyticsModal: React.FC<AnalyticsModalProps> = ({
  isOpen,
  onClose,
  history,
  currentStreak,
  bestStreak,
  initialTab = 'analytics',
}) => {
  const [activeTab, setActiveTab] = useState<'analytics' | 'history'>(initialTab);

  React.useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);
  const [historyView, setHistoryView] = useState<'calendar' | 'list'>('calendar');
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );

  if (!isOpen) return null;

  const totalGames = history.length;
  const totalScore = history.reduce((sum, r) => sum + r.score, 0);

  // Per-level breakdown
  const statsByLevel = DIFFICULTIES.map(lvl => {
    const levelGames = history.filter(r => r.level === lvl);
    const count = levelGames.length;
    if (count === 0) {
      return {
        level: lvl,
        count: 0,
        bestTime: null,
        avgTime: null,
        bestScore: null,
        avgScore: null,
      };
    }
    const bestTime = Math.min(...levelGames.map(g => g.seconds));
    const avgTime = Math.round(levelGames.reduce((acc, g) => acc + g.seconds, 0) / count);
    const bestScore = Math.max(...levelGames.map(g => g.score));
    const avgScore = Math.round(levelGames.reduce((acc, g) => acc + g.score, 0) / count);
    return {
      level: lvl,
      count,
      bestTime,
      avgTime,
      bestScore,
      avgScore,
    };
  });

  const formatSeconds = (sec: number | null) => {
    if (sec === null) return '--:--';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}m ${s.toString().padStart(2, '0')}s`;
  };

  // Calendar dates generation (last 35 days grid)
  const today = new Date();
  const calendarDays: { dateStr: string; dayNum: number; hasGames: boolean; count: number }[] = [];
  for (let i = 34; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    const gamesOnDay = history.filter(r => r.date === dateStr);
    calendarDays.push({
      dateStr,
      dayNum: d.getDate(),
      hasGames: gamesOnDay.length > 0,
      count: gamesOnDay.length,
    });
  }

  const selectedDateGames = history.filter(r => r.date === selectedDate);
  const selectedDateScore = selectedDateGames.reduce((sum, r) => sum + r.score, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 select-none"
      style={{ borderRadius: '0px' }}
    >
      <div
        className="w-full max-w-2xl bg-white border border-slate-300 shadow-2xl flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-200"
        style={{ borderRadius: '0px' }}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-slate-900">
              Statistics & History
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-200 bg-slate-50 text-sm font-semibold">
          <button
            onClick={() => setActiveTab('analytics')}
            className={`flex-1 py-3 text-center border-b-2 flex items-center justify-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'analytics'
                ? 'border-blue-600 text-blue-600 bg-white font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <BarChart2 className="w-4 h-4" />
            <span>Analytics</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-3 text-center border-b-2 flex items-center justify-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'history'
                ? 'border-blue-600 text-blue-600 bg-white font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Calendar className="w-4 h-4" />
            <span>History & Calendar</span>
          </button>
        </div>

        {/* Tab Contents */}
        <div className="p-5 overflow-y-auto space-y-6">
          {activeTab === 'analytics' ? (
            <div className="space-y-6">
              {/* Overall Summary Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-50 border border-slate-200 p-3 text-center">
                  <div className="text-xs uppercase text-slate-400 font-bold">Games Completed</div>
                  <div className="text-2xl font-bold font-mono-numbers text-slate-900 mt-1">
                    {totalGames}
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 text-center">
                  <div className="text-xs uppercase text-slate-400 font-bold flex items-center justify-center gap-1">
                    <Flame className="w-3.5 h-3.5 text-amber-500" /> Current Streak
                  </div>
                  <div className="text-2xl font-bold font-mono-numbers text-slate-900 mt-1">
                    {currentStreak} <span className="text-xs font-normal text-slate-400">d</span>
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 text-center">
                  <div className="text-xs uppercase text-slate-400 font-bold flex items-center justify-center gap-1">
                    <Trophy className="w-3.5 h-3.5 text-amber-500" /> Best Streak
                  </div>
                  <div className="text-2xl font-bold font-mono-numbers text-slate-900 mt-1">
                    {bestStreak} <span className="text-xs font-normal text-slate-400">d</span>
                  </div>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 text-center">
                  <div className="text-xs uppercase text-slate-400 font-bold">Total Points</div>
                  <div className="text-2xl font-bold font-mono-numbers text-blue-600 mt-1">
                    {totalScore.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Per-Level Breakdown Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Performance by Difficulty
                </h4>
                <div className="border border-slate-200 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-100 text-slate-600 uppercase font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-2.5 px-3">Level</th>
                        <th className="py-2.5 px-3">Solved</th>
                        <th className="py-2.5 px-3">Best Time</th>
                        <th className="py-2.5 px-3">Avg Time</th>
                        <th className="py-2.5 px-3">Best Score</th>
                        <th className="py-2.5 px-3">Avg Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono-numbers">
                      {statsByLevel.map(s => (
                        <tr key={s.level} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-bold capitalize text-slate-800">
                            {s.level}
                          </td>
                          <td className="py-2.5 px-3 text-slate-700">{s.count}</td>
                          <td className="py-2.5 px-3 text-slate-700">{formatSeconds(s.bestTime)}</td>
                          <td className="py-2.5 px-3 text-slate-700">{formatSeconds(s.avgTime)}</td>
                          <td className="py-2.5 px-3 text-blue-600 font-semibold">
                            {s.bestScore ? s.bestScore.toLocaleString() : '--'}
                          </td>
                          <td className="py-2.5 px-3 text-slate-700">
                            {s.avgScore ? s.avgScore.toLocaleString() : '--'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* History Sub-View Toggle */}
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Activity Log
                </span>
                <div className="flex border border-slate-200 text-xs font-semibold">
                  <button
                    onClick={() => setHistoryView('calendar')}
                    className={`px-3 py-1 cursor-pointer ${
                      historyView === 'calendar' ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    Calendar
                  </button>
                  <button
                    onClick={() => setHistoryView('list')}
                    className={`px-3 py-1 cursor-pointer ${
                      historyView === 'list' ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    All List
                  </button>
                </div>
              </div>

              {historyView === 'calendar' ? (
                <div className="space-y-4">
                  {/* Calendar Grid */}
                  <div className="bg-slate-50 border border-slate-200 p-4">
                    <div className="text-xs text-slate-500 font-semibold mb-3">
                      Last 35 Days (dots indicate days with completed games)
                    </div>
                    <div className="grid grid-cols-7 gap-1.5 text-center">
                      {calendarDays.map(cd => {
                        const isSelected = cd.dateStr === selectedDate;
                        return (
                          <button
                            key={cd.dateStr}
                            onClick={() => setSelectedDate(cd.dateStr)}
                            className={`
                              p-2 flex flex-col items-center justify-center border transition-all cursor-pointer
                              ${isSelected
                                ? 'bg-blue-600 text-white border-blue-600 font-bold'
                                : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'
                              }
                            `}
                            style={{ borderRadius: '0px' }}
                          >
                            <span className="text-xs font-mono-numbers">{cd.dayNum}</span>
                            <div className="h-1.5 w-1.5 mt-1 flex items-center justify-center">
                              {cd.hasGames && (
                                <span
                                  className={`h-1.5 w-1.5 rounded-full ${
                                    isSelected ? 'bg-white' : 'bg-blue-600'
                                  }`}
                                />
                              )}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Selected Date Details */}
                  <div className="bg-white border border-slate-200 p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                        {selectedDate} Summary
                      </span>
                      <span className="text-xs font-mono-numbers font-bold text-blue-600">
                        {selectedDateScore.toLocaleString()} pts ({selectedDateGames.length} games)
                      </span>
                    </div>

                    {selectedDateGames.length === 0 ? (
                      <p className="text-xs text-slate-400 py-2">
                        No games played on this calendar day.
                      </p>
                    ) : (
                      <div className="divide-y divide-slate-100">
                        {selectedDateGames.map(game => (
                          <div key={game.id} className="py-2.5 flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              <span className="font-bold capitalize text-slate-800">
                                {game.level}
                              </span>
                              <span className="text-slate-400 font-mono-numbers">
                                {new Date(game.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 font-mono-numbers">
                              <span className="text-slate-500">
                                {formatSeconds(game.seconds)}
                              </span>
                              <span className="font-bold text-blue-600">
                                +{game.score} pts
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Chronological List View */
                <div className="border border-slate-200 divide-y divide-slate-100 max-h-72 overflow-y-auto">
                  {history.length === 0 ? (
                    <div className="p-6 text-center text-xs text-slate-400">
                      No games recorded yet.
                    </div>
                  ) : (
                    [...history]
                      .reverse()
                      .map(game => (
                        <div key={game.id} className="p-3 flex items-center justify-between text-xs hover:bg-slate-50">
                          <div>
                            <span className="font-bold capitalize text-slate-900 mr-2">
                              {game.level}
                            </span>
                            <span className="text-slate-400 font-mono-numbers">
                              {game.date}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 font-mono-numbers">
                            <span className="text-slate-500 flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              {formatSeconds(game.seconds)}
                            </span>
                            <span className="font-bold text-blue-600">
                              +{game.score.toLocaleString()} pts
                            </span>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
