import React from 'react';
import { Play } from 'lucide-react';
import { Grid, Notes, BoolGrid, UserSettings } from '../logic/sudokuLogic';

interface SudokuGridProps {
  initialGrid: Grid;
  currentGrid: Grid;
  solutionGrid: Grid;
  notes: Notes;
  hintedCells: BoolGrid;
  selectedCell: [number, number] | null;
  onSelectCell: (row: number, col: number) => void;
  isPaused: boolean;
  onResume: () => void;
  settings: UserSettings;
  shakingCell: [number, number] | null;
  tooltip: {
    cell: [number, number];
    text: string;
  } | null;
  className?: string;
  style?: React.CSSProperties;
}

export const SudokuGrid: React.FC<SudokuGridProps> = ({
  initialGrid,
  currentGrid,
  solutionGrid,
  notes,
  hintedCells,
  selectedCell,
  onSelectCell,
  isPaused,
  onResume,
  settings,
  shakingCell,
  tooltip,
  className = '',
  style,
}) => {
  const selectedRow = selectedCell ? selectedCell[0] : -1;
  const selectedCol = selectedCell ? selectedCell[1] : -1;
  const selectedVal = selectedCell && currentGrid[selectedRow][selectedCol] !== 0
    ? currentGrid[selectedRow][selectedCol]
    : null;

  const sizeMultiplier =
    settings.numberSize === 'small' ? 0.85 : settings.numberSize === 'large' ? 1.15 : 1.0;

  return (
    <div
      className={`relative select-none aspect-square ${className}`}
      style={style}
    >
      {/* 9x9 Grid Container with Sharp Corners (border-radius: 0) and 3px solid #0f172a */}
      <div
        className="w-full h-full bg-white grid grid-cols-9 grid-rows-9 relative"
        style={{
          border: '3px solid #0f172a',
          borderRadius: '0px',
        }}
      >
        {Array.from({ length: 9 }).map((_, r) =>
          Array.from({ length: 9 }).map((_, c) => {
            const isInitial = initialGrid[r][c] !== 0;
            const currentVal = currentGrid[r][c];
            const isSelected = selectedRow === r && selectedCol === c;
            const isSameRowOrCol = selectedRow === r || selectedCol === c;
            const isSameBox =
              selectedRow !== -1 &&
              Math.floor(selectedRow / 3) === Math.floor(r / 3) &&
              Math.floor(selectedCol / 3) === Math.floor(c / 3);
            const isPeer = isSameRowOrCol || isSameBox;
            const isSameVal =
              !isPaused &&
              settings.highlightSameNumbers &&
              selectedVal !== null &&
              currentVal === selectedVal;

            const isShaking =
              shakingCell && shakingCell[0] === r && shakingCell[1] === c;
            const hasTooltip =
              !isPaused && tooltip && tooltip.cell[0] === r && tooltip.cell[1] === c;

            // Borders: 3x3 block dividers (2px #0f172a), inner cell borders (1px #cbd5e1)
            const borderRight =
              c === 8 ? 'none' : c % 3 === 2 ? '2px solid #0f172a' : '1px solid #cbd5e1';
            const borderBottom =
              r === 8 ? 'none' : r % 3 === 2 ? '2px solid #0f172a' : '1px solid #cbd5e1';

            // Correctness check for color feedback
            const isFilled = currentVal !== 0;
            const isCorrect = isFilled && currentVal === solutionGrid[r][c];
            const isWrong = isFilled && !isInitial && currentVal !== solutionGrid[r][c];

            let textColor = '#0f172a';
            let cellBg = '#ffffff';

            if (!isPaused) {
              if (isInitial) {
                textColor = '#0f172a';
              } else if (settings.colorFeedback && isFilled) {
                if (isWrong) {
                  textColor = '#b91c1c';
                  cellBg = '#fef2f2';
                } else if (isCorrect) {
                  textColor = '#065f46';
                  cellBg = '#f0fdf4';
                }
              } else if (!isInitial && isFilled) {
                textColor = '#2563eb';
              }

              if (!isWrong && !(settings.colorFeedback && isCorrect && !isInitial)) {
                if (isSelected) {
                  cellBg = '#dbeafe';
                } else if (isSameVal) {
                  cellBg = '#e2e8f0';
                } else if (isPeer && selectedCell !== null) {
                  cellBg = '#f8fafc';
                }
              }
            }

            const cellNotes = notes[r][c];

            return (
              <div
                key={`${r}-${c}`}
                onClick={() => !isPaused && onSelectCell(r, c)}
                className={`
                  relative flex items-center justify-center cursor-pointer select-none
                  transition-colors duration-75
                  ${isShaking ? 'animate-shake' : ''}
                  ${!isPaused && isSelected ? 'ring-2 ring-blue-600 ring-inset z-10' : ''}
                `}
                style={{
                  borderRight,
                  borderBottom,
                  backgroundColor: cellBg,
                  borderRadius: '0px',
                }}
              >
                {/* Numbers and notes are hidden when paused so grid lines remain visible */}
                {!isPaused && (
                  <>
                    {/* Placed Digit */}
                    {isFilled ? (
                      <span
                        className="font-mono-numbers font-bold leading-none"
                        style={{
                          color: textColor,
                          fontSize: `calc(clamp(16px, 3.8vmin, 38px) * ${sizeMultiplier})`,
                          fontWeight: isInitial ? 800 : 700,
                        }}
                      >
                        {currentVal}
                      </span>
                    ) : (
                      /* 3x3 Pencil Notes */
                      <div className="w-full h-full p-0.5 sm:p-1 grid grid-cols-3 grid-rows-3 pointer-events-none">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => {
                          const hasNote = cellNotes.has(num);
                          const isHighlightedNote =
                            settings.highlightSameNumbers && selectedVal === num;
                          return (
                            <div
                              key={num}
                              className="flex items-center justify-center"
                            >
                              {hasNote && (
                                <span
                                  className={`font-mono-numbers font-semibold leading-none ${
                                    isHighlightedNote
                                      ? 'text-blue-700 font-bold scale-110'
                                      : 'text-slate-500'
                                  }`}
                                  style={{
                                    fontSize: `calc(clamp(8px, 1.4vmin, 16px) * ${sizeMultiplier})`,
                                  }}
                                >
                                  {num}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}

                {/* Tooltip Bubble for strict hint feedback */}
                {hasTooltip && (
                  <div
                    className="absolute z-30 bottom-[calc(100%+6px)] left-1/2 -translate-x-1/2 px-2.5 py-1 bg-slate-900 text-white text-[11px] font-medium whitespace-nowrap shadow-lg pointer-events-none animate-in fade-in duration-100"
                    style={{ borderRadius: '0px' }}
                  >
                    {tooltip.text}
                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Pause Overlay: Numbers hidden, grid lines visible, play button in center */}
        {isPaused && (
          <div
            onClick={onResume}
            className="absolute inset-0 flex flex-col items-center justify-center z-20 cursor-pointer bg-white/40 backdrop-blur-[2px] transition-all"
          >
            <div
              className="bg-[#0f172a] text-white p-4 sm:p-6 shadow-2xl flex flex-col items-center gap-3 border border-slate-700 max-w-[85%]"
              style={{ borderRadius: '0px' }}
              onClick={e => e.stopPropagation()}
            >
              <span className="text-[10px] uppercase tracking-widest text-slate-400 font-bold">
                Game Suspended
              </span>
              <h3 className="text-xl sm:text-2xl font-bold font-mono-numbers">
                Paused
              </h3>
              <button
                onClick={onResume}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs sm:text-sm tracking-wide transition-colors cursor-pointer shadow-sm"
                style={{ borderRadius: '0px' }}
              >
                <Play className="w-4 h-4 fill-white" />
                <span>Resume</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
