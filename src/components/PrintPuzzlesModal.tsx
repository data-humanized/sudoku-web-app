import React, { useState, useRef, useEffect, useCallback } from 'react';
import { X, Check } from 'lucide-react';
import { Difficulty, generateProceduralPuzzle, getLocalDateString } from '../logic/sudokuLogic';
import { loadStoredFingerprints, loadRecentPlayedGrids, saveStoredFingerprint } from '../utils/storage';
import {
  PRINT_LEVELS,
  PRINT_LEVEL_LABELS,
  buildPdfDocument,
  downloadOrSharePdf,
} from '../utils/pdfGenerator';

interface PrintPuzzlesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onShowToast?: (msg: string) => void;
}

interface LevelRowState {
  checked: boolean;
  count: number;
}

const PICKER_VALUES = [0, 1, 2, 3, 4, 5, 6];
const ITEM_HEIGHT = 28; // Height in px for each number row

interface ScrollPickerProps {
  value: number;
  disabled: boolean;
  onChange: (val: number) => void;
}

const ScrollPicker: React.FC<ScrollPickerProps> = ({ value, disabled, onChange }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isUserScrollingRef = useRef(false);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Sync scroll position when value changes externally
  useEffect(() => {
    if (isUserScrollingRef.current) return;
    const container = containerRef.current;
    if (!container) return;
    const targetScrollTop = value * ITEM_HEIGHT;
    if (Math.abs(container.scrollTop - targetScrollTop) > 2) {
      container.scrollTop = targetScrollTop;
    }
  }, [value]);

  const handleScroll = () => {
    const container = containerRef.current;
    if (!container || disabled) return;

    isUserScrollingRef.current = true;
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);

    scrollTimeoutRef.current = setTimeout(() => {
      const scrollTop = container.scrollTop;
      const index = Math.round(scrollTop / ITEM_HEIGHT);
      const clampedIndex = Math.max(0, Math.min(6, index));
      if (clampedIndex !== value) {
        onChange(clampedIndex);
      }
      container.scrollTo({ top: clampedIndex * ITEM_HEIGHT, behavior: 'smooth' });
      isUserScrollingRef.current = false;
    }, 80);
  };

  const handleWheel = (e: React.WheelEvent) => {
    if (disabled) return;
    e.preventDefault();
    if (e.deltaY > 0) {
      if (value < 6) onChange(value + 1);
    } else if (e.deltaY < 0) {
      if (value > 0) onChange(value - 1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      if (value < 6) onChange(value + 1);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      if (value > 0) onChange(value - 1);
    }
  };

  return (
    <div
      tabIndex={disabled ? -1 : 0}
      onKeyDown={handleKeyDown}
      onWheel={handleWheel}
      className={`
        relative w-14 h-[84px] overflow-hidden select-none outline-none transition-all
        rounded-lg border
        ${disabled
          ? 'bg-slate-50/60 border-slate-200/50 cursor-not-allowed opacity-60'
          : 'bg-white border-slate-200 hover:border-slate-300 shadow-2xs focus:border-blue-400'
        }
      `}
    >
      {/* Center selection highlight */}
      <div
        className={`
          absolute left-1 right-1 top-[28px] h-[28px] rounded pointer-events-none transition-colors
          ${disabled ? 'bg-transparent' : 'bg-blue-50/90'}
        `}
      />

      {/* Scrollable list */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="w-full h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar py-[28px]"
        style={{
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
        }}
      >
        {PICKER_VALUES.map(num => {
          const isSelected = num === value;
          return (
            <div
              key={num}
              onClick={() => {
                if (!disabled) {
                  onChange(num);
                }
              }}
              className={`
                h-[28px] flex items-center justify-center snap-center text-sm font-mono-numbers transition-all
                ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
                ${isSelected
                  ? disabled
                    ? 'text-slate-400 font-semibold'
                    : 'text-slate-900 font-extrabold scale-110'
                  : 'text-slate-300 font-medium text-xs scale-90'
                }
              `}
            >
              {num}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const PrintPuzzlesModal: React.FC<PrintPuzzlesModalProps> = ({
  isOpen,
  onClose,
  onShowToast,
}) => {
  const [levelStates, setLevelStates] = useState<Record<Difficulty, LevelRowState>>({
    easy: { checked: false, count: 0 },
    medium: { checked: false, count: 0 },
    hard: { checked: false, count: 0 },
    expert: { checked: false, count: 0 },
    master: { checked: false, count: 0 },
  });

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const cancelGenerationRef = useRef(false);

  // Reset dialog state when modal opens
  useEffect(() => {
    if (isOpen) {
      setLevelStates({
        easy: { checked: false, count: 0 },
        medium: { checked: false, count: 0 },
        hard: { checked: false, count: 0 },
        expert: { checked: false, count: 0 },
        master: { checked: false, count: 0 },
      });
      setIsGenerating(false);
      cancelGenerationRef.current = false;
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Toggle checkbox
  const handleToggleCheck = (lvl: Difficulty) => {
    setLevelStates(prev => {
      const current = prev[lvl];
      const nextChecked = !current.checked;
      return {
        ...prev,
        [lvl]: {
          checked: nextChecked,
          // Unticking resets count to 0; ticking keeps count at 0 until scrolled
          count: nextChecked ? current.count : 0,
        },
      };
    });
  };

  // Change count
  const handleChangeCount = (lvl: Difficulty, newCount: number) => {
    setLevelStates(prev => ({
      ...prev,
      [lvl]: {
        ...prev[lvl],
        count: Math.max(0, Math.min(6, newCount)),
      },
    }));
  };

  // Calculate live total: level is included only if checked AND count >= 1
  const totalPuzzles = PRINT_LEVELS.reduce((acc, lvl) => {
    const s = levelStates[lvl];
    return acc + (s.checked && s.count >= 1 ? s.count : 0);
  }, 0);

  const canCreatePdf = totalPuzzles > 0 && !isGenerating;

  // Generate & Download PDF
  const handleCreatePdf = async () => {
    if (!canCreatePdf) return;

    setIsGenerating(true);
    cancelGenerationRef.current = false;
    setProgress({ current: 0, total: totalPuzzles });

    try {
      const storedFingerprints = loadStoredFingerprints();
      const recentGrids = loadRecentPlayedGrids();
      const newFingerprints: string[] = [];
      const sessionFingerprints = new Set<string>(storedFingerprints);

      const puzzlesByLevel: Partial<Record<Difficulty, Array<{ puzzle: number[][]; solution: number[][] }>>> = {};
      let generatedSoFar = 0;

      for (const lvl of PRINT_LEVELS) {
        const state = levelStates[lvl];
        if (!state.checked || state.count < 1) continue;

        puzzlesByLevel[lvl] = [];

        for (let i = 0; i < state.count; i++) {
          if (cancelGenerationRef.current) {
            setIsGenerating(false);
            return;
          }

          generatedSoFar++;
          setProgress({ current: generatedSoFar, total: totalPuzzles });

          // Non-blocking break so UI can update smoothly
          await new Promise(r => setTimeout(r, 20));

          if (cancelGenerationRef.current) {
            setIsGenerating(false);
            return;
          }

          // Generate a fresh unique procedural puzzle
          let attempts = 0;
          let puzzleResult: ReturnType<typeof generateProceduralPuzzle> | null = null;

          while (attempts < 25) {
            attempts++;
            const candidate = generateProceduralPuzzle(
              lvl,
              sessionFingerprints,
              recentGrids
            );

            if (!sessionFingerprints.has(candidate.fingerprint)) {
              puzzleResult = candidate;
              sessionFingerprints.add(candidate.fingerprint);
              newFingerprints.push(candidate.fingerprint);
              break;
            }
          }

          if (!puzzleResult) {
            puzzleResult = generateProceduralPuzzle(lvl, new Set<string>(), recentGrids);
            sessionFingerprints.add(puzzleResult.fingerprint);
            newFingerprints.push(puzzleResult.fingerprint);
          }

          puzzlesByLevel[lvl]!.push({
            puzzle: puzzleResult.puzzle,
            solution: puzzleResult.solution,
          });
        }
      }

      if (cancelGenerationRef.current) {
        setIsGenerating(false);
        return;
      }

      // Build PDF binary
      const pdfBytes = buildPdfDocument(puzzlesByLevel);

      // Save all newly generated fingerprints so they cannot repeat in future games
      for (const fp of newFingerprints) {
        saveStoredFingerprint(fp);
      }

      // File name: Sudoku-Printables-YYYY-MM-DD.pdf
      const todayIso = getLocalDateString();
      const fileName = `Sudoku-Printables-${todayIso}.pdf`;

      const success = await downloadOrSharePdf(pdfBytes, fileName);
      if (success) {
        if (onShowToast) onShowToast('Printable PDF created successfully');
        onClose();
      } else {
        if (onShowToast) onShowToast('Failed to save PDF');
      }
    } catch (err) {
      console.error('Error generating PDF:', err);
      if (onShowToast) onShowToast('Error generating PDF. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-[420px] bg-white border border-slate-200 shadow-2xl rounded-2xl p-6 flex flex-col justify-between gap-3.5 relative animate-in zoom-in-95 duration-150 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 tracking-tight">
            Print puzzles
          </h2>
          <button
            onClick={() => {
              if (isGenerating) cancelGenerationRef.current = true;
              onClose();
            }}
            disabled={isGenerating}
            className="p-1 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer rounded-lg"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Level Rows */}
        <div className="flex flex-col divide-y divide-slate-100">
          {PRINT_LEVELS.map(lvl => {
            const { checked, count } = levelStates[lvl];
            return (
              <div
                key={lvl}
                className="py-1.5 flex items-center justify-between transition-colors"
              >
                {/* Checkbox and Label */}
                <label className="flex items-center gap-3 cursor-pointer select-none">
                  <div
                    onClick={() => handleToggleCheck(lvl)}
                    className={`
                      w-5 h-5 rounded-md flex items-center justify-center border transition-all cursor-pointer
                      ${checked
                        ? 'bg-slate-900 border-slate-900 text-white'
                        : 'bg-white border-slate-300 hover:border-slate-400 text-transparent'
                      }
                    `}
                  >
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">
                    {PRINT_LEVEL_LABELS[lvl]}
                  </span>
                </label>

                {/* Vertical Scroll-Snap Picker */}
                <ScrollPicker
                  value={count}
                  disabled={!checked}
                  onChange={newVal => handleChangeCount(lvl, newVal)}
                />
              </div>
            );
          })}
        </div>

        {/* Footer Notes & Live Total */}
        <div className="space-y-0.5 pt-0.5 text-xs">
          <p className="text-slate-500">
            Up to 6 per level. For more, print again.
          </p>
          <p className="font-bold font-mono-numbers text-slate-900">
            Total: {totalPuzzles} {totalPuzzles === 1 ? 'puzzle' : 'puzzles'}
          </p>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={() => {
              if (isGenerating) cancelGenerationRef.current = true;
              onClose();
            }}
            disabled={isGenerating}
            className="flex-1 py-2.5 px-4 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold text-xs uppercase tracking-wider rounded-xl transition-colors cursor-pointer text-center"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleCreatePdf}
            disabled={!canCreatePdf}
            className={`
              flex-1 py-2.5 px-4 font-bold text-xs uppercase tracking-wider rounded-xl transition-colors text-center shadow-xs
              ${canCreatePdf
                ? 'bg-slate-900 hover:bg-slate-800 text-white cursor-pointer active:translate-y-0.5'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200/60'
              }
            `}
          >
            Create PDF
          </button>
        </div>

        {/* Progress Overlay when generating */}
        {isGenerating && (
          <div className="absolute inset-0 bg-white/90 backdrop-blur-xs flex flex-col items-center justify-center p-6 gap-3 z-20 rounded-2xl">
            <div className="w-7 h-7 border-3 border-slate-900 border-t-transparent animate-spin rounded-full" />
            <div className="text-center space-y-1">
              <p className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {`Creating puzzle ${progress.current} of ${progress.total}...`}
              </p>
              <p className="text-[11px] text-slate-500">
                Generating unique procedural puzzles offline
              </p>
            </div>
            <button
              onClick={() => {
                cancelGenerationRef.current = true;
                setIsGenerating(false);
              }}
              className="mt-2 px-4 py-1.5 border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer rounded-lg"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
