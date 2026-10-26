import { GameState, HistoryRecord, UserSettings, DEFAULT_SETTINGS } from '../logic/sudokuLogic';

export interface ZenSudokuStorage {
  version: number;
  history: HistoryRecord[];
  activeGame: GameState | null;
  settings: UserSettings;
}

const STORAGE_KEY = 'zensudoku_data.json';

export function loadZenData(): ZenSudokuStorage {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {
        version: 1,
        history: [],
        activeGame: null,
        settings: { ...DEFAULT_SETTINGS },
      };
    }
    const parsed = JSON.parse(raw);
    // Revive Sets in notes if activeGame exists
    if (parsed.activeGame && parsed.activeGame.notes) {
      parsed.activeGame.notes = parsed.activeGame.notes.map((row: any[]) =>
        row.map(cell => new Set(Array.isArray(cell) ? cell : Array.from(cell || [])))
      );
    }
    return {
      version: parsed.version || 1,
      history: parsed.history || [],
      activeGame: parsed.activeGame || null,
      settings: { ...DEFAULT_SETTINGS, ...(parsed.settings || {}) },
    };
  } catch (err) {
    console.error('Failed to load ZenSudoku storage:', err);
    return {
      version: 1,
      history: [],
      activeGame: null,
      settings: { ...DEFAULT_SETTINGS },
    };
  }
}

export function saveZenData(data: ZenSudokuStorage): void {
  try {
    // Convert Sets to Arrays for activeGame notes
    const serializable = {
      ...data,
      activeGame: data.activeGame
        ? {
            ...data.activeGame,
            notes: data.activeGame.notes.map(row => row.map(cell => Array.from(cell))),
          }
        : null,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
  } catch (err) {
    console.error('Failed to save ZenSudoku storage:', err);
  }
}

export function exportBackupJSON(data: ZenSudokuStorage): void {
  const serializable = {
    ...data,
    exportDate: new Date().toISOString(),
    activeGame: data.activeGame
      ? {
          ...data.activeGame,
          notes: data.activeGame.notes.map(row => row.map(cell => Array.from(cell))),
        }
      : null,
  };
  const jsonStr = JSON.stringify(serializable, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'zensudoku_data.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function importBackupJSON(fileContent: string): ZenSudokuStorage {
  const parsed = JSON.parse(fileContent);
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Invalid JSON format');
  }
  const history: HistoryRecord[] = Array.isArray(parsed.history) ? parsed.history : [];
  let activeGame: GameState | null = null;
  if (parsed.activeGame) {
    activeGame = {
      ...parsed.activeGame,
      notes: parsed.activeGame.notes.map((row: any[]) =>
        row.map(cell => new Set(Array.isArray(cell) ? cell : []))
      ),
    };
  }
  const settings: UserSettings = {
    ...DEFAULT_SETTINGS,
    ...(parsed.settings || {}),
  };

  const restored: ZenSudokuStorage = {
    version: parsed.version || 1,
    history,
    activeGame,
    settings,
  };
  saveZenData(restored);
  return restored;
}
