import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Lock } from 'lucide-react';
import { Difficulty, UnlockStatus } from '../logic/sudokuLogic';

const LEVELS: Difficulty[] = ['easy', 'medium', 'hard', 'expert'];

interface DifficultySelectorProps {
  currentLevel: Difficulty;
  unlockStatus: Record<Difficulty, UnlockStatus>;
  onSelectLevel: (level: Difficulty) => void;
  disabled?: boolean;
}

/**
 * Dropdown Mode for compact spaces (phones, small viewports, or when area above grid is narrow)
 */
export const DifficultyDropdown: React.FC<DifficultySelectorProps> = ({
  currentLevel,
  unlockStatus,
  onSelectLevel,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Select difficulty level"
        aria-expanded={isOpen}
        className={`
          flex items-center gap-1.5 px-2 py-1 bg-white border border-slate-200 text-xs sm:text-sm font-semibold transition-colors
          ${disabled ? 'opacity-50 cursor-not-allowed bg-slate-50' : 'hover:bg-slate-50 text-slate-800 cursor-pointer shadow-xs'}
        `}
        style={{ borderRadius: '0px' }}
      >
        <span className="text-slate-400 font-normal">Diff:</span>
        <span className="capitalize font-bold text-slate-900">{currentLevel}</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
      </button>

      {isOpen && !disabled && (
        <div
          className="absolute left-0 top-full mt-1 w-40 bg-white border border-slate-200 shadow-xl z-30 py-1"
          style={{ borderRadius: '0px' }}
        >
          {LEVELS.map(lvl => {
            const status = unlockStatus[lvl];
            const isUnlocked = status?.unlocked ?? true;
            const isSelected = currentLevel === lvl;

            return (
              <button
                key={lvl}
                disabled={!isUnlocked}
                onClick={() => {
                  onSelectLevel(lvl);
                  setIsOpen(false);
                }}
                className={`
                  w-full text-left px-3 py-2 text-xs font-semibold flex items-center justify-between transition-colors
                  ${isSelected ? 'bg-blue-50 text-blue-700 font-bold' : isUnlocked ? 'text-slate-800 hover:bg-slate-50 cursor-pointer' : 'text-slate-400 bg-slate-50 cursor-not-allowed'}
                `}
              >
                <span className="capitalize">{lvl}</span>
                {!isUnlocked && (
                  <div className="flex items-center gap-1 text-[10px] text-slate-400 font-normal">
                    <Lock className="w-3 h-3 text-slate-400" />
                    <span>{status.current}/{status.required}</span>
                  </div>
                )}
                {isSelected && isUnlocked && (
                  <span className="w-1.5 h-1.5 bg-blue-600 rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

/**
 * Inline Text Tabs Mode:
 * Shown when there is enough room:
 * Viewport is 1024px or wider, or tablet/phone in landscape with >= 700px width AND >= 600px height.
 * "Difficulty:  Easy  Medium  Hard  Expert" (selected highlighted in blue with underline or bold).
 */
export const DifficultyInlineTabs: React.FC<DifficultySelectorProps> = ({
  currentLevel,
  unlockStatus,
  onSelectLevel,
  disabled = false,
}) => {
  return (
    <div className="flex items-center gap-2 select-none text-xs sm:text-sm">
      <span className="text-slate-400 font-semibold tracking-wide">Difficulty:</span>
      <div className="flex items-center gap-2">
        {LEVELS.map(lvl => {
          const status = unlockStatus[lvl];
          const isUnlocked = status?.unlocked ?? true;
          const isSelected = currentLevel === lvl;

          return (
            <button
              key={lvl}
              disabled={disabled || !isUnlocked}
              onClick={() => isUnlocked && onSelectLevel(lvl)}
              title={!isUnlocked ? status?.progressLabel : `${lvl.toUpperCase()} Difficulty`}
              className={`
                px-2.5 py-1 capitalize transition-all cursor-pointer font-semibold relative
                ${isSelected
                  ? 'text-blue-600 font-bold border-b-2 border-blue-600'
                  : isUnlocked
                    ? 'text-slate-600 hover:text-slate-900 border-b-2 border-transparent'
                    : 'text-slate-300 border-b-2 border-transparent cursor-not-allowed'
                }
              `}
            >
              <div className="flex items-center gap-1">
                {!isUnlocked && <Lock className="w-3 h-3 text-slate-400" />}
                <span>{lvl}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
