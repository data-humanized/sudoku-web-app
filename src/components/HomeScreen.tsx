import React from 'react';
import { Flame, Award, Play, CheckCircle2, Lock, ArrowRight, Clock } from 'lucide-react';
import { Difficulty, UnlockStatus, HistoryRecord, GameState } from '../logic/sudokuLogic';

interface HomeScreenProps {
  currentStreak: number;
  bestStreak: number;
  todayScore: number;
  todayGames: HistoryRecord[];
  activeGame: GameState | null;
  unlockStatus: Record<Difficulty, UnlockStatus>;
  onStartGame: (level: Difficulty) => void;
  onResumeActiveGame: () => void;
}

const DIFFICULTIES: Difficulty[] = ['easy', 'medium', 'hard', 'expert'];

export const HomeScreen: React.FC<HomeScreenProps> = ({
  currentStreak,
  bestStreak,
  todayScore,
  todayGames,
  activeGame,
  unlockStatus,
  onStartGame,
  onResumeActiveGame,
}) => {
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  };

  return (
    <div className="w-full max-w-[900px] mx-auto px-4 py-8 space-y-8 select-none">
      {/* Top Banner / Hero Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Streak Card */}
        <div className="bg-white border border-slate-200 p-6 flex items-center justify-between shadow-xs">
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
            <p className="text-xs text-slate-500">
              All-time best streak: <span className="font-semibold text-slate-800">{bestStreak} days</span>
            </p>
          </div>
          <div className="p-4 bg-amber-50 text-amber-500">
            <Flame className="w-10 h-10 fill-amber-500/30" />
          </div>
        </div>

        {/* Today's Score & Game Count */}
        <div className="bg-white border border-slate-200 p-6 flex items-center justify-between shadow-xs">
          <div className="space-y-1">
            <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
              Today's Performance
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-extrabold text-blue-600 font-mono-numbers">
                {todayScore.toLocaleString()}
              </span>
              <span className="text-sm text-slate-500">points</span>
            </div>
            <p className="text-xs text-slate-500">
              Puzzles completed today: <span className="font-semibold text-slate-800">{todayGames.length}</span>
            </p>
          </div>
          <div className="p-4 bg-blue-50 text-blue-600">
            <Award className="w-10 h-10" />
          </div>
        </div>
      </div>

      {/* Resume Unfinished Game CTA if present */}
      {activeGame && !activeGame.isCompleted && (
        <div className="bg-slate-900 text-white p-5 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-md">
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
            className="w-full sm:w-auto px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs"
            style={{ borderRadius: '0px' }}
          >
            <Play className="w-4 h-4 fill-white" />
            Continue Game
          </button>
        </div>
      )}

      {/* Level Selection Cards */}
      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-900 uppercase tracking-wider text-xs">
          Select Difficulty
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {DIFFICULTIES.map(lvl => {
            const status = unlockStatus[lvl];
            const isUnlocked = status?.unlocked ?? true;

            return (
              <div
                key={lvl}
                className={`bg-white border p-5 flex flex-col justify-between transition-all ${
                  isUnlocked
                    ? 'border-slate-200 hover:border-blue-400 shadow-xs'
                    : 'border-slate-200/60 bg-slate-50/50 opacity-80'
                }`}
                style={{ borderRadius: '0px' }}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="capitalize font-bold text-lg text-slate-900">
                      {lvl}
                    </h3>
                    {!isUnlocked ? (
                      <span className="p-1.5 bg-slate-100 text-slate-400">
                        <Lock className="w-4 h-4" />
                      </span>
                    ) : (
                      <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-600 font-mono-numbers">
                        {lvl === 'easy' ? '1,000' : lvl === 'medium' ? '2,000' : lvl === 'hard' ? '4,000' : '8,000'} pts
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {lvl === 'easy' && 'Naked & hidden singles. Ideal for quick warmups.'}
                    {lvl === 'medium' && 'Naked/hidden pairs and box-line reductions.'}
                    {lvl === 'hard' && 'Naked/hidden triples, X-Wing, and Y-Wing techniques.'}
                    {lvl === 'expert' && 'Advanced multi-branch chains and forcing logic.'}
                  </p>
                </div>

                <div className="mt-6 pt-3 border-t border-slate-100">
                  {isUnlocked ? (
                    <button
                      onClick={() => onStartGame(lvl)}
                      className="w-full py-2 px-3 bg-slate-900 hover:bg-blue-600 text-white font-semibold text-xs tracking-wider uppercase transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                      style={{ borderRadius: '0px' }}
                    >
                      <span>Play</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <div className="text-center text-xs text-slate-500 font-medium py-1">
                      {status?.progressLabel}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Today's Completed Games List */}
      <div className="space-y-3">
        <h2 className="text-base font-bold text-slate-900 uppercase tracking-wider text-xs">
          Games Completed Today
        </h2>
        {todayGames.length === 0 ? (
          <div className="bg-white border border-slate-200 p-8 text-center text-slate-400 text-sm">
            No games completed today yet. Pick a difficulty above to begin your daily streak!
          </div>
        ) : (
          <div className="bg-white border border-slate-200 divide-y divide-slate-100">
            {todayGames.map((game, idx) => (
              <div key={game.id || idx} className="p-4 flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <div>
                    <span className="font-bold text-slate-900 capitalize mr-2">
                      {game.level}
                    </span>
                    <span className="text-xs text-slate-400 font-mono-numbers">
                      {new Date(game.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-1 text-slate-600 text-xs font-mono-numbers">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>{formatTime(game.seconds)}</span>
                  </div>
                  <div className="font-bold font-mono-numbers text-blue-600">
                    +{game.score.toLocaleString()} pts
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
