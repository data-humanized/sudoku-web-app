import React, { useState } from 'react';
import { Flame, Award, Play, ArrowRight, Trophy, Check, Printer } from 'lucide-react';
import {
  Difficulty,
  UnlockStatus,
  HistoryRecord,
  GameState,
  getLocalDateString,
  isWonRecord,
  formatPoints,
} from '../logic/sudokuLogic';

interface HomeScreenProps {
  history?: HistoryRecord[];
  currentStreak: number;
  bestStreak: number;
  todayScore: number;
  todayGames: HistoryRecord[];
  activeGame: GameState | null;
  unlockStatus: Record<Difficulty, UnlockStatus>;
  onStartGame: (level: Difficulty) => void;
  onResumeActiveGame: () => void;
  onOpenPrintModal?: () => void;
}

const DIFFICULTIES: Difficulty[] = ['easy', 'medium', 'hard', 'expert', 'master'];

function getNiceScale(maxVal: number): { ticks: number[]; yMax: number } {
  if (maxVal <= 0) {
    return { ticks: [0, 1000, 2000, 3000], yMax: 3000 };
  }
  const roughStep = maxVal / 3;
  const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const normalized = roughStep / magnitude;
  let step: number;
  if (normalized <= 1) step = 1 * magnitude;
  else if (normalized <= 1.5) step = 1.5 * magnitude;
  else if (normalized <= 2) step = 2 * magnitude;
  else if (normalized <= 2.5) step = 2.5 * magnitude;
  else if (normalized <= 5) step = 5 * magnitude;
  else step = 10 * magnitude;

  let count = Math.ceil(maxVal / step);
  if (count < 3) count = 3;
  const yMax = count * step;
  const ticks: number[] = [];
  for (let i = 0; i <= count; i++) {
    ticks.push(i * step);
  }
  return { ticks, yMax };
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  history = [],
  currentStreak,
  todayScore,
  todayGames,
  activeGame,
  onStartGame,
  onResumeActiveGame,
  onOpenPrintModal,
}) => {
  const [activeTooltip, setActiveTooltip] = useState<{
    index: number;
    dateStr: string;
    score: number;
    gameCount: number;
    x: number;
    y: number;
  } | null>(null);

  // All-time won games across history
  const allTimeWonRecords = React.useMemo(() => {
    return history.filter(isWonRecord);
  }, [history]);

  const totalPoints = React.useMemo(() => {
    return allTimeWonRecords.reduce((sum, r) => sum + (r.score || 0), 0);
  }, [allTimeWonRecords]);

  const allTimeCompletedCount = allTimeWonRecords.length;

  // Compute 7 days ending today (e.g. Wed, Thu, Fri, Sat, Sun, Mon, Tue)
  const weeklyData = React.useMemo(() => {
    const days: {
      dateStr: string;
      weekdayName: string;
      displayLabel: string;
      score: number;
      gameCount: number;
    }[] = [];

    const now = new Date();

    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      const localDateKey = getLocalDateString(d);
      const weekdayName = d.toLocaleDateString('en-US', { weekday: 'short' });
      const isToday = i === 0;
      const displayLabel = isToday
        ? 'Today'
        : d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

      // Match records by local date key or timestamp
      const dayRecords = history.filter(r => {
        if (!isWonRecord(r)) return false;
        if (r.date === localDateKey) return true;
        if (r.timestamp) {
          const recDate = getLocalDateString(new Date(r.timestamp));
          if (recDate === localDateKey) return true;
        }
        return false;
      });

      const computedDayScore = dayRecords.reduce((sum, r) => sum + r.score, 0);
      const dayScore = isToday ? Math.max(todayScore, computedDayScore) : computedDayScore;

      days.push({
        dateStr: localDateKey,
        weekdayName,
        displayLabel,
        score: dayScore,
        gameCount: isToday ? Math.max(dayRecords.length, todayGames.length) : dayRecords.length,
      });
    }

    return days;
  }, [history, todayScore, todayGames]);

  // Dynamic Y-axis scale calculated to represent progress naturally
  const maxWeeklyScore = Math.max(...weeklyData.map(d => d.score), 0);
  const { ticks: yTicks, yMax: chartYMax } = getNiceScale(maxWeeklyScore);

  // Chart coordinate constants
  const chartW = 600;
  const chartH = 210;
  const padLeft = 60;
  const padRight = 35;
  const padTop = 25;
  const padBottom = 35;
  const innerW = chartW - padLeft - padRight;
  const innerH = chartH - padTop - padBottom;

  const points = weeklyData.map((d, i) => {
    const x = padLeft + (innerW / 6) * i;
    const ratio = chartYMax > 0 ? d.score / chartYMax : 0;
    const y = padTop + innerH * (1 - ratio);
    return { ...d, x, y };
  });

  const linePath = points.reduce((acc, p, idx) => {
    return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
  }, '');

  const areaPath = `${linePath} L ${points[points.length - 1].x} ${padTop + innerH} L ${points[0].x} ${padTop + innerH} Z`;

  return (
    <div className="w-full min-h-[calc(100vh-65px)] flex flex-col justify-between select-none">
      <div className="w-full max-w-[960px] mx-auto px-4 py-6 space-y-6 flex-1">
        {/* Top Banner / Hero Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Daily Streak Card */}
          <div className="bg-white border border-slate-200 p-5 flex items-center justify-between shadow-xs">
            <div className="space-y-1">
              <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                Daily Streak
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold text-slate-900 font-mono-numbers">
                  {currentStreak}
                </span>
                <span className="text-sm text-slate-500">
                  {currentStreak === 1 ? 'day' : 'days'}
                </span>
              </div>
            </div>
            <div className="p-3.5 bg-amber-50 text-amber-500">
              <Flame className="w-9 h-9 fill-amber-500/30" />
            </div>
          </div>

          {/* TOTAL POINTS Card (Replaces Today's Performance) */}
          <div className="bg-white border border-slate-200 p-5 flex items-center justify-between shadow-xs">
            <div className="space-y-1">
              <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                TOTAL POINTS
              </span>
              <div
                className="flex items-baseline gap-2 cursor-default"
                title={totalPoints.toLocaleString('en-US')}
              >
                <span className="text-4xl font-extrabold text-blue-600 font-mono-numbers">
                  {formatPoints(totalPoints)}
                </span>
                <span className="text-sm text-slate-500">points</span>
              </div>
              <p className="text-xs text-slate-500">
                Across all games: <span className="font-semibold text-slate-800 font-mono-numbers">{allTimeCompletedCount}</span>
              </p>
            </div>
            <div className="p-3.5 bg-blue-50 text-blue-600">
              <Award className="w-9 h-9" />
            </div>
          </div>
        </div>

        {/* Resume Unfinished Game CTA if present */}
        {activeGame && !activeGame.isCompleted && (
          <div className="bg-slate-900 text-white p-4.5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md">
            <div className="space-y-1 text-center sm:text-left">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-bold">
                  Game in Progress
                </span>
              </div>
              <p className="text-sm text-slate-300">
                {activeGame.level.toUpperCase()} difficulty puzzle with {Math.floor(activeGame.elapsedSeconds / 60)}m elapsed.
              </p>
            </div>
            <button
              onClick={onResumeActiveGame}
              className="w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs"
              style={{ borderRadius: '0px' }}
            >
              <Play className="w-4 h-4 fill-white" />
              Continue Game
            </button>
          </div>
        )}

        {/* Section 9: Level Selection Cards (All unlocked per user request) */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Select Difficulty
            </h2>
            {onOpenPrintModal && (
              <button
                onClick={onOpenPrintModal}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 transition-colors shadow-2xs active:translate-y-0.5 cursor-pointer"
                style={{ borderRadius: '0px' }}
                aria-label="Print Puzzles"
              >
                <Printer className="w-3.5 h-3.5 text-slate-600" />
                <span>Print</span>
              </button>
            )}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {DIFFICULTIES.map(lvl => {
              // Calculate Best Time and Games Won dynamically from stored history records
              const levelRecords = history.filter(r => r.level === lvl);
              const wonRecords = levelRecords.filter(isWonRecord);
              const wonCount = wonRecords.length;
              const totalCount = levelRecords.length;

              let bestTimeFormatted = '--:--';
              if (wonRecords.length > 0) {
                const minTime = Math.min(...wonRecords.map(r => r.timeSeconds ?? r.seconds ?? 0));
                const m = Math.floor(minTime / 60);
                const s = minTime % 60;
                bestTimeFormatted = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
              }
              const gamesWonFormatted = totalCount === 0 ? '0 / 0' : `${wonCount} / ${totalCount}`;

              return (
                <div
                  key={lvl}
                  className="bg-white border border-slate-200 hover:border-blue-400 p-3.5 flex flex-col justify-between transition-all h-[155px] shadow-xs"
                  style={{ borderRadius: '0px' }}
                >
                  <div>
                    {/* Card Title */}
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="capitalize font-bold text-base text-slate-900 tracking-tight">
                        {lvl}
                      </h3>
                    </div>

                    {/* Card Body: Best time & Games won */}
                    <div className="space-y-1.5 py-0.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 text-slate-500">
                          <Trophy className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>Best time</span>
                        </div>
                        <span className="font-mono-numbers text-xs font-semibold text-slate-700">
                          {bestTimeFormatted}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 text-slate-500">
                          <Check className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>Games won</span>
                        </div>
                        <span className="font-mono-numbers text-xs font-semibold text-slate-700">
                          {gamesWonFormatted}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Play button */}
                  <div className="pt-2 border-t border-slate-100">
                    <button
                      onClick={() => onStartGame(lvl)}
                      className="w-full py-1.5 px-3 font-semibold text-xs tracking-wider uppercase transition-colors flex items-center justify-center gap-1.5 bg-slate-900 hover:bg-blue-600 text-white cursor-pointer shadow-xs active:translate-y-0.5"
                      style={{ borderRadius: '0px' }}
                    >
                      <span>Play</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 10: WEEKLY PROGRESS Line Chart (7 days ending today) */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Weekly Progress
            </h2>
            <span className="text-xs text-slate-400 font-mono-numbers">Last 7 Days</span>
          </div>

          <div className="bg-white border border-slate-200 p-4 shadow-xs relative">
            <div className="w-full relative aspect-[600/210]">
              <svg
                viewBox={`0 0 ${chartW} ${chartH}`}
                className="w-full h-full overflow-visible"
                onClick={() => setActiveTooltip(null)}
              >
                <defs>
                  <linearGradient id="progressAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Y-Axis Horizontal Grid Lines and Ticks */}
                {yTicks.map(tickVal => {
                  const y = padTop + innerH * (1 - tickVal / chartYMax);
                  return (
                    <g key={tickVal}>
                      <line
                        x1={padLeft}
                        y1={y}
                        x2={padLeft + innerW}
                        y2={y}
                        stroke="#e2e8f0"
                        strokeDasharray={tickVal === 0 ? 'none' : '4 4'}
                        strokeWidth={tickVal === 0 ? 1.5 : 1}
                      />
                      <text
                        x={padLeft - 10}
                        y={y + 4}
                        textAnchor="end"
                        fontSize="11"
                        fill="#94a3b8"
                        className="font-mono-numbers select-none"
                      >
                        {tickVal.toLocaleString()}
                      </text>
                    </g>
                  );
                })}

                {/* Area fill under curve */}
                <path d={areaPath} fill="url(#progressAreaGradient)" />

                {/* Connected Progress Line */}
                <path
                  d={linePath}
                  fill="none"
                  stroke="#2563eb"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Data Points and X-Axis Weekday Labels (e.g. Wed, Thu, Fri, Sat, Sun, Mon, Tue) */}
                {points.map((p, idx) => {
                  const isToday = idx === 6;
                  return (
                    <g key={idx}>
                      {/* X-Axis weekday label */}
                      <text
                        x={p.x}
                        y={chartH - 8}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight={isToday ? 'bold' : '600'}
                        fill={isToday ? '#2563eb' : '#64748b'}
                        className="font-mono-numbers select-none"
                      >
                        {p.weekdayName}
                      </text>


                      {/* Outer hover/tap hit target */}
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r="16"
                        fill="transparent"
                        className="cursor-pointer"
                        onMouseEnter={() =>
                          setActiveTooltip({
                            index: idx,
                            dateStr: p.displayLabel,
                            score: p.score,
                            gameCount: p.gameCount,
                            x: p.x,
                            y: p.y,
                          })
                        }
                        onClick={e => {
                          e.stopPropagation();
                          setActiveTooltip({
                            index: idx,
                            dateStr: p.displayLabel,
                            score: p.score,
                            gameCount: p.gameCount,
                            x: p.x,
                            y: p.y,
                          });
                        }}
                      >
                        <title>{`${p.displayLabel}: ${formatPoints(p.score)} pts`}</title>
                      </circle>

                      {/* Dot */}
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={activeTooltip?.index === idx ? 6 : 4}
                        fill="#2563eb"
                        stroke="#ffffff"
                        strokeWidth={2}
                        className="transition-all pointer-events-none"
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Tooltip Overlay */}
              {activeTooltip && (
                <div
                  className="absolute pointer-events-none z-20 bg-slate-900 text-white px-2.5 py-1.5 shadow-lg border border-slate-700 text-xs transform -translate-x-1/2 -translate-y-full mb-2"
                  style={{
                    left: `${(activeTooltip.x / chartW) * 100}%`,
                    top: `${(activeTooltip.y / chartH) * 100}%`,
                    borderRadius: '0px',
                  }}
                >
                  <div className="font-semibold text-[11px] text-slate-300">
                    {activeTooltip.dateStr}
                  </div>
                  <div className="font-bold text-blue-400 font-mono-numbers">
                    {formatPoints(activeTooltip.score)} pts
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {activeTooltip.gameCount} game{activeTooltip.gameCount === 1 ? '' : 's'}
                  </div>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section 11: Sticky Footer "Sudoku - by Abhishek Pujari" */}
      <footer
        className="w-full text-center py-4 text-xs text-[#94a3b8] shrink-0 font-medium select-none"
        style={{
          paddingBottom: 'max(1rem, env(safe-area-inset-bottom))',
        }}
      >
        Sudoku - by Abhishek Pujari
      </footer>
    </div>
  );
};
