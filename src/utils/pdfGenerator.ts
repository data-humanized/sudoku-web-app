/**
 * Pure offline PDF 1.4 binary writer for ZenSudoku Printables.
 * No external PDF libraries or servers.
 *
 * Specifications:
 * - A4 Portrait (595.28 x 841.89 pt), ~15mm (42.52 pt) margins
 * - First all PUZZLES, then all SOLUTIONS
 * - Order: Easy -> Medium -> Hard -> Expert -> Master
 * - Each level starts on a new page
 * - Two grids per page (top and bottom)
 * - Labels: "Level - Puzzle N" and "Level - Solution N"
 * - First solutions page has "Solutions" header
 * - Centered small page numbers at bottom
 * - 9x9 grid with thick lines for 3x3 boxes and outer border, thin lines for inner cells
 * - Given digits: bold black (0 0 0 rg)
 * - Solved digits: medium grey (0.5 0.5 0.5 rg)
 * - Android wrapper & browser download support
 */

import { Difficulty, generateProceduralPuzzle } from '../logic/sudokuLogic';
import { loadStoredFingerprints, loadRecentPlayedGrids, saveStoredFingerprint } from './storage';

export const PRINT_LEVELS: Difficulty[] = ['easy', 'medium', 'hard', 'expert', 'master'];

export const PRINT_LEVEL_LABELS: Record<Difficulty, string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
  expert: 'Expert',
  master: 'Master',
};

const PAGE_WIDTH = 595.28;
const PAGE_HEIGHT = 841.89;

const GRID_SIZE = 216.0; // 9 * 24 pt
const CELL_SIZE = 24.0;

// 2 columns horizontally (Page width = 595.28 pt):
const GRID_COLS_X = [50.0, 329.28];

// 3 rows vertically (Page height = 841.89 pt, PDF Y=0 is bottom):
const GRID_ROWS_Y = [546.0, 292.0, 38.0];
const TITLE_ROWS_Y = [769.0, 515.0, 261.0];

const PAGE_NUM_Y = 18.0;
const SOLUTIONS_HEADER_Y = 802.0;

function escapePdfText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
}

function renderPdfGrid(
  gridLeft: number,
  gridBottom: number,
  puzzleGrid: number[][],
  solutionGrid?: number[][],
  isSolutionMode = false
): string {
  const cmd: string[] = [];

  // 1. Thin inner cell lines
  cmd.push('q');
  cmd.push('0.4 0.4 0.4 RG');
  cmd.push('0.5 w');
  for (let i = 1; i < 9; i++) {
    if (i % 3 !== 0) {
      const y = gridBottom + i * CELL_SIZE;
      cmd.push(`${gridLeft.toFixed(2)} ${y.toFixed(2)} m ${(gridLeft + GRID_SIZE).toFixed(2)} ${y.toFixed(2)} l S`);
      const x = gridLeft + i * CELL_SIZE;
      cmd.push(`${x.toFixed(2)} ${gridBottom.toFixed(2)} m ${x.toFixed(2)} ${(gridBottom + GRID_SIZE).toFixed(2)} l S`);
    }
  }
  cmd.push('Q');

  // 2. Thick 3x3 block lines & outer border
  cmd.push('q');
  cmd.push('0 0 0 RG');
  cmd.push('1.5 w');
  for (const b of [3, 6]) {
    const y = gridBottom + b * CELL_SIZE;
    cmd.push(`${gridLeft.toFixed(2)} ${y.toFixed(2)} m ${(gridLeft + GRID_SIZE).toFixed(2)} ${y.toFixed(2)} l S`);
    const x = gridLeft + b * CELL_SIZE;
    cmd.push(`${x.toFixed(2)} ${gridBottom.toFixed(2)} m ${x.toFixed(2)} ${(gridBottom + GRID_SIZE).toFixed(2)} l S`);
  }
  cmd.push(`${gridLeft.toFixed(2)} ${gridBottom.toFixed(2)} ${GRID_SIZE.toFixed(2)} ${GRID_SIZE.toFixed(2)} re S`);
  cmd.push('Q');

  // 3. Cell numbers
  const charW = 7.5;
  const charH = 9.5;
  const dx = (CELL_SIZE - charW) / 2.0;
  const dy = (CELL_SIZE - charH) / 2.0 + 1.0;

  for (let r = 0; r < 9; r++) {
    for (let c = 0; c < 9; c++) {
      const givenVal = puzzleGrid[r][c];
      const rowFromBottom = 8 - r;
      const cellX = gridLeft + c * CELL_SIZE;
      const cellY = gridBottom + rowFromBottom * CELL_SIZE;
      const tx = cellX + dx;
      const ty = cellY + dy;

      if (!isSolutionMode) {
        if (givenVal !== 0) {
          cmd.push('BT');
          cmd.push('/F2 13 Tf');
          cmd.push('0 0 0 rg');
          cmd.push(`${tx.toFixed(2)} ${ty.toFixed(2)} Td`);
          cmd.push(`(${givenVal}) Tj`);
          cmd.push('ET');
        }
      } else {
        const solVal = solutionGrid ? solutionGrid[r][c] : givenVal;
        if (solVal !== 0) {
          const isGiven = givenVal !== 0;
          const fontRef = isGiven ? '/F2' : '/F1';
          const colorStr = isGiven ? '0 0 0 rg' : '0.5 0.5 0.5 rg';

          cmd.push('BT');
          cmd.push(`${fontRef} 13 Tf`);
          cmd.push(colorStr);
          cmd.push(`${tx.toFixed(2)} ${ty.toFixed(2)} Td`);
          cmd.push(`(${solVal}) Tj`);
          cmd.push('ET');
        }
      }
    }
  }

  return cmd.join('\n');
}

export function buildPdfDocument(
  puzzlesByLevel: Partial<Record<Difficulty, Array<{ puzzle: number[][]; solution: number[][] }>>>
): Uint8Array {
  const activeLevels = PRINT_LEVELS.filter(lvl => puzzlesByLevel[lvl] && puzzlesByLevel[lvl]!.length > 0);

  const pagesContent: string[] = [];

  if (activeLevels.length === 0) {
    pagesContent.push('BT /F1 12 Tf 100 700 Td (No puzzles selected for printing) Tj ET');
  } else {
    // Collect all puzzle items in order: Easy -> Medium -> Hard -> Expert -> Master
    const allPuzzleItems: Array<{
      level: Difficulty;
      levelName: string;
      puzzleNum: number;
      puzzle: number[][];
      solution: number[][];
    }> = [];

    for (const lvl of activeLevels) {
      const items = puzzlesByLevel[lvl]!;
      const lvlName = PRINT_LEVEL_LABELS[lvl];
      for (let i = 0; i < items.length; i++) {
        allPuzzleItems.push({
          level: lvl,
          levelName: lvlName,
          puzzleNum: i + 1,
          puzzle: items[i].puzzle,
          solution: items[i].solution,
        });
      }
    }

    const totalPuzzles = allPuzzleItems.length;
    const puzPageCount = Math.ceil(totalPuzzles / 6);
    const solPageCount = Math.ceil(totalPuzzles / 6);
    const totalPages = puzPageCount + solPageCount;

    let currentPageNum = 1;

    // --- PART 1: PUZZLES (6 grids per page: 2 columns x 3 rows) ---
    for (let pageIdx = 0; pageIdx < puzPageCount; pageIdx++) {
      const chunk = allPuzzleItems.slice(pageIdx * 6, (pageIdx + 1) * 6);
      const stream: string[] = [];

      for (let slotIdx = 0; slotIdx < chunk.length; slotIdx++) {
        const puz = chunk[slotIdx];
        const rowIdx = Math.floor(slotIdx / 2);
        const colIdx = slotIdx % 2;
        const gx = GRID_COLS_X[colIdx];
        const gy = GRID_ROWS_Y[rowIdx];
        const ty = TITLE_ROWS_Y[rowIdx];

        // Label above grid
        stream.push('BT');
        stream.push('/F2 10 Tf');
        stream.push('0 0 0 rg');
        const labelText = escapePdfText(`${puz.levelName} - Puzzle ${puz.puzzleNum}`);
        stream.push(`${gx.toFixed(2)} ${ty.toFixed(2)} Td`);
        stream.push(`(${labelText}) Tj`);
        stream.push('ET');

        // Grid
        stream.push(renderPdfGrid(gx, gy, puz.puzzle, undefined, false));
      }

      // Page number
      stream.push('BT');
      stream.push('/F1 9 Tf');
      stream.push('0.4 0.4 0.4 rg');
      const pageText = escapePdfText(`Page ${currentPageNum} of ${totalPages}`);
      stream.push(`265.00 ${PAGE_NUM_Y.toFixed(2)} Td`);
      stream.push(`(${pageText}) Tj`);
      stream.push('ET');

      pagesContent.push(stream.join('\n'));
      currentPageNum++;
    }

    // --- PART 2: SOLUTIONS (6 grids per page, starting from next page) ---
    let isFirstSolutionsPage = true;
    for (let pageIdx = 0; pageIdx < solPageCount; pageIdx++) {
      const chunk = allPuzzleItems.slice(pageIdx * 6, (pageIdx + 1) * 6);
      const stream: string[] = [];

      if (isFirstSolutionsPage) {
        stream.push('BT');
        stream.push('/F2 14 Tf');
        stream.push('0 0 0 rg');
        const headerText = escapePdfText('Solutions');
        stream.push(`${GRID_COLS_X[0].toFixed(2)} ${SOLUTIONS_HEADER_Y.toFixed(2)} Td`);
        stream.push(`(${headerText}) Tj`);
        stream.push('ET');
        isFirstSolutionsPage = false;
      }

      for (let slotIdx = 0; slotIdx < chunk.length; slotIdx++) {
        const puz = chunk[slotIdx];
        const rowIdx = Math.floor(slotIdx / 2);
        const colIdx = slotIdx % 2;
        const gx = GRID_COLS_X[colIdx];
        const gy = GRID_ROWS_Y[rowIdx];
        const ty = TITLE_ROWS_Y[rowIdx];

        // Label above grid
        stream.push('BT');
        stream.push('/F2 10 Tf');
        stream.push('0 0 0 rg');
        const labelText = escapePdfText(`${puz.levelName} - Solution ${puz.puzzleNum}`);
        stream.push(`${gx.toFixed(2)} ${ty.toFixed(2)} Td`);
        stream.push(`(${labelText}) Tj`);
        stream.push('ET');

        // Grid
        stream.push(renderPdfGrid(gx, gy, puz.puzzle, puz.solution, true));
      }

      // Page number
      stream.push('BT');
      stream.push('/F1 9 Tf');
      stream.push('0.4 0.4 0.4 rg');
      const pageText = escapePdfText(`Page ${currentPageNum} of ${totalPages}`);
      stream.push(`265.00 ${PAGE_NUM_Y.toFixed(2)} Td`);
      stream.push(`(${pageText}) Tj`);
      stream.push('ET');

      pagesContent.push(stream.join('\n'));
      currentPageNum++;
    }
  }

  // Build standard PDF 1.4 binary
  const totalPages = pagesContent.length;
  const numObjects = 4 + 2 * totalPages;
  const objOffsets: number[] = new Array(numObjects + 1).fill(0);

  const parts: Uint8Array[] = [];
  const encoder = new TextEncoder();

  function appendStr(s: string) {
    parts.push(encoder.encode(s));
  }

  appendStr('%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');

  let currentLen = parts.reduce((acc, p) => acc + p.length, 0);

  // 1: Catalog
  objOffsets[1] = currentLen;
  appendStr('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');
  currentLen = parts.reduce((acc, p) => acc + p.length, 0);

  // 2: Pages
  const kidsRefs = Array.from({ length: totalPages }, (_, i) => `${5 + i} 0 R`).join(' ');
  objOffsets[2] = currentLen;
  appendStr(`2 0 obj\n<< /Type /Pages /Kids [${kidsRefs}] /Count ${totalPages} >>\nendobj\n`);
  currentLen = parts.reduce((acc, p) => acc + p.length, 0);

  // 3: Helvetica
  objOffsets[3] = currentLen;
  appendStr('3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n');
  currentLen = parts.reduce((acc, p) => acc + p.length, 0);

  // 4: Helvetica-Bold
  objOffsets[4] = currentLen;
  appendStr('4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n');
  currentLen = parts.reduce((acc, p) => acc + p.length, 0);

  // Page objects: 5 .. 4 + totalPages
  for (let i = 0; i < totalPages; i++) {
    const pageObjNum = 5 + i;
    const contentObjNum = 5 + totalPages + i;
    objOffsets[pageObjNum] = currentLen;
    appendStr(
      `${pageObjNum} 0 obj\n` +
      `<< /Type /Page /Parent 2 0 R\n` +
      `   /MediaBox [0 0 ${PAGE_WIDTH.toFixed(2)} ${PAGE_HEIGHT.toFixed(2)}]\n` +
      `   /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >>\n` +
      `   /Contents ${contentObjNum} 0 R\n` +
      `>>\nendobj\n`
    );
    currentLen = parts.reduce((acc, p) => acc + p.length, 0);
  }

  // Content streams: 5 + totalPages .. 4 + 2 * totalPages
  for (let i = 0; i < totalPages; i++) {
    const contentObjNum = 5 + totalPages + i;
    const contentBytes = encoder.encode(pagesContent[i]);
    objOffsets[contentObjNum] = currentLen;
    appendStr(`${contentObjNum} 0 obj\n<< /Length ${contentBytes.length} >>\nstream\n`);
    parts.push(contentBytes);
    appendStr('\nendstream\nendobj\n');
    currentLen = parts.reduce((acc, p) => acc + p.length, 0);
  }

  // XREF table
  const xrefOffset = currentLen;
  appendStr('xref\n');
  appendStr(`0 ${numObjects + 1}\n`);
  appendStr('0000000000 65535 f \r\n');
  for (let i = 1; i <= numObjects; i++) {
    appendStr(`${objOffsets[i].toString().padStart(10, '0')} 00000 n \r\n`);
  }

  // Trailer
  appendStr(
    `trailer\n` +
    `<< /Size ${numObjects + 1}\n` +
    `   /Root 1 0 R\n` +
    `>>\n` +
    `startxref\n` +
    `${xrefOffset}\n` +
    `%%EOF\n`
  );

  const totalByteLength = parts.reduce((acc, p) => acc + p.length, 0);
  const result = new Uint8Array(totalByteLength);
  let offset = 0;
  for (const part of parts) {
    result.set(part, offset);
    offset += part.length;
  }
  return result;
}

/**
 * Downloads or shares the PDF with robust Android WebView fallback
 */
export async function downloadOrSharePdf(pdfBytes: Uint8Array, fileName: string): Promise<boolean> {
  try {
    const blob = new Blob([pdfBytes as unknown as BlobPart], { type: 'application/pdf' });

    // 1. Check Android wrapper bridge if available
    const androidObj = (window as unknown as { Android?: { savePdf?: (b64: string, name: string) => boolean } }).Android;
    if (androidObj && typeof androidObj.savePdf === 'function') {
      let binary = '';
      const len = pdfBytes.byteLength;
      for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(pdfBytes[i]);
      }
      const b64 = window.btoa(binary);
      return androidObj.savePdf(b64, fileName);
    }

    // 2. Direct browser download into system files (works on PC, Mac, Linux, Android Web)
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 2000);
    return true;
  } catch (ex) {
    console.error('Failed to download PDF:', ex);
    return false;
  }
}
