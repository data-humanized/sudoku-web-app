import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { Difficulty, UnlockStatus } from '../logic/sudokuLogic';

const LEVELS: Difficulty[] = ['easy', 'medium', 'hard', 'expert', 'master'];

interface DifficultySelectorProps {
  currentLevel: Difficulty;
  unlockStatus: Record<Difficulty, UnlockStatus>;
  onSelectLevel: (level: Difficulty) => void;
  disabled?: boolean;
}

/**
 * Dropdown Mode for Compact / Single Column Layout:
 * Always unlocked per user request.
 */
export const DifficultyDropdown: React.FC<DifficultySelectorProps> = ({
  currentLevel,
  onSelectLevel,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Select difficulty"
        aria-expanded={isOpen}
        className={`
          flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider
          border transition-all
          ${disabled
            ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
            : 'bg-white hover:bg-slate-50 text-slate-800 border-slate-300 cursor-pointer shadow-xs active:translate-y-0.5'
          }
        `}
        style={{ borderRadius: '0px' }}
      >
        <span className="capitalize">{currentLevel}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div
          className="absolute left-0 mt-1 w-36 bg-white border border-slate-200 shadow-xl z-50 py-1"
          style={{ borderRadius: '0px' }}
        >
          {LEVELS.map(lvl => {
            const isSelected = currentLevel === lvl;

            return (
              <button
                key={lvl}
                onClick={() => {
                  onSelectLevel(lvl);
                  setIsOpen(false);
                }}
                className={`
                  w-full text-left px-3 py-2 text-xs font-semibold flex items-center justify-between transition-colors
                  ${isSelected ? 'bg-blue-50 text-blue-700 font-bold' : 'text-slate-800 hover:bg-slate-50 cursor-pointer'}
                `}
              >
                <span className="capitalize">{lvl}</span>
                {isSelected && (
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
 * "Difficulty: Easy Medium Hard Expert Master"
 * All games unlocked.
 */
export const DifficultyInlineTabs: React.FC<DifficultySelectorProps> = ({
  currentLevel,
  onSelectLevel,
  disabled = false,
}) => {
  return (
    <div className="flex items-center gap-2 select-none text-xs sm:text-sm">
      <span className="text-slate-400 font-semibold tracking-wide">Difficulty:</span>
      <div className="flex items-center gap-2">
        {LEVELS.map(lvl => {
          const isSelected = currentLevel === lvl;

          return (
            <button
              key={lvl}
              disabled={disabled}
              onClick={() => onSelectLevel(lvl)}
              title={`${lvl.toUpperCase()} Difficulty`}
              className={`
                px-2.5 py-1 capitalize transition-all cursor-pointer font-semibold relative
                ${isSelected
                  ? 'text-blue-600 font-bold border-b-2 border-blue-600'
                  : 'text-slate-600 hover:text-slate-900 border-b-2 border-transparent'
                }
              `}
            >
              <span>{lvl}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
