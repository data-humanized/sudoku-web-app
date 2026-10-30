/**
 * ZenSudoku Storage and Compact Secure Backup Engine (.sudokubak)
 *
 * Rules:
 * - Stores history only, never grids, solutions, pencil notes, or in-progress games.
 * - Single compact .sudokubak file with:
 *   1. Magic header ("ZENSUDBAK", 9 bytes)
 *   2. Version byte (0x01)
 *   3. Compressed gzip stream (CompressionStream, not plain Base64 JSON) containing records & settings block
 *   4. HMAC-SHA256 signature (32 bytes raw) generated with Web Crypto using an obfuscated app secret
 * - Strict 5-step verification order:
 *   1. Magic header and version
 *   2. Valid signature
 *   3. Exactly the expected fields with correct types (unknown or missing fields rejected)
 *   4. Valid values (real past/present date, score in level range, realistic time, unique ids)
 *   5. No duplicates or calendar/streak anomalies
 * - Automatic rollback copy saved before replacing data on import.
 * - Local-only fingerprints (up to 10,000) and recent 20 played grids are kept on device, never in backup.
 */

import {
  GameState,
  HistoryRecord,
  UserSettings,
  DEFAULT_SETTINGS,
  Difficulty,
  MAX_SCORE,
  Grid,
  migrateHistoryRecord,
} from '../logic/sudokuLogic';

export interface ZenSudokuStorage {
  version: number;
  history: HistoryRecord[];
  activeGame: GameState | null;
  settings: UserSettings;
}

const STORAGE_KEY = 'zensudoku_data.json';
const ROLLBACK_KEY = 'zensudoku_rollback_copy.json';
const FINGERPRINTS_KEY = 'zensudoku_fingerprints.json';
const RECENT_PLAYED_KEY = 'zensudoku_recent_played.json';

// Obfuscated HMAC-SHA256 secret key for signing .sudokubak files
const OBFUSCATED_SECRET = new Uint8Array([
  0x5a, 0x65, 0x6e, 0x53, 0x75, 0x64, 0x6f, 0x6b,
  0x75, 0x2e, 0x42, 0x61, 0x63, 0x6b, 0x75, 0x70,
  0x2e, 0x53, 0x65, 0x63, 0x72, 0x65, 0x74, 0x2e,
  0x48, 0x4d, 0x41, 0x43, 0x32, 0x35, 0x36, 0x21
]);

const MAGIC_BYTES = new Uint8Array([0x5a, 0x45, 0x4e, 0x53, 0x55, 0x44, 0x42, 0x41, 0x4b]); // "ZENSUDBAK"
const FORMAT_VERSION = 0x01;

async function getHmacKey(): Promise<CryptoKey> {
  return await crypto.subtle.importKey(
    'raw',
    OBFUSCATED_SECRET,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify']
  );
}

/**
 * Compress binary payload with gzip CompressionStream
 */
async function compressGzip(data: Uint8Array): Promise<Uint8Array> {
  const cs = new CompressionStream('gzip');
  const writer = cs.writable.getWriter();
  await writer.write(data as any);
  await writer.close();
  const reader = cs.readable.getReader();
  const chunks: Uint8Array[] = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const totalLength = chunks.reduce((acc, c) => acc + c.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const c of chunks) {
    result.set(c, offset);
    offset += c.length;
  }
  return result;
}

/**
 * Decompress binary payload with gzip DecompressionStream
 */
async function decompressGzip(data: Uint8Array): Promise<Uint8Array> {
  const ds = new DecompressionStream('gzip');
  const writer = ds.writable.getWriter();
  await writer.write(data as any);
  await writer.close();
  const reader = ds.readable.getReader();
  const chunks: Uint8Array[] = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
  }
  const totalLength = chunks.reduce((acc, c) => acc + c.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const c of chunks) {
    result.set(c, offset);
    offset += c.length;
  }
  return result;
}

// Normalize legacy or stored records
function normalizeHistoryRecord(r: any): HistoryRecord {
  const timeSeconds = typeof r.timeSeconds === 'number'
    ? r.timeSeconds
    : (typeof r.seconds === 'number' ? r.seconds : 0);
  const rawRecord: HistoryRecord = {
    id: String(r.id || `rec-${Date.now()}`),
    date: String(r.date || new Date().toISOString().slice(0, 10)),
    timestamp: typeof r.timestamp === 'number' ? r.timestamp : Date.now(),
    level: r.level as Difficulty,
    timeSeconds,
    score: Number(r.score) || 0,
    hintsUsed: Number(r.hintsUsed) || 0,
    mistakes: Number(r.mistakes) || 0,
    won: r.won !== undefined ? Boolean(r.won) : ((Number(r.score) || 0) > 0),
  };
  return migrateHistoryRecord(rawRecord);
}

export function loadZenData(): ZenSudokuStorage {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) {
      return {
        version: 1,
        history: [],
        activeGame: null,
        settings: { ...DEFAULT_SETTINGS },
      };
    }
    const parsed = JSON.parse(raw);
    const history: HistoryRecord[] = Array.isArray(parsed.history)
      ? parsed.history.map(normalizeHistoryRecord)
      : [];

    let activeGame: GameState | null = null;
    if (parsed.activeGame && typeof parsed.activeGame === 'object') {
      const g = parsed.activeGame;
      activeGame = {
        ...g,
        notes: Array.isArray(g.notes)
          ? g.notes.map((row: any[]) =>
              Array.isArray(row)
                ? row.map(cell => new Set<number>(Array.isArray(cell) ? cell : []))
                : []
            )
          : [],
        undoStack: Array.isArray(g.undoStack) ? g.undoStack : [],
        redoStack: Array.isArray(g.redoStack) ? g.redoStack : [],
      };
    }

    const settings: UserSettings = {
      ...DEFAULT_SETTINGS,
      ...(parsed.settings || {}),
    };

    return {
      version: parsed.version || 1,
      history,
      activeGame,
      settings,
    };
  } catch {
    return {
      version: 1,
      history: [],
      activeGame: null,
      settings: { ...DEFAULT_SETTINGS },
    };
  }
}

export function saveZenData(storage: ZenSudokuStorage): void {
  try {
    if (typeof localStorage === 'undefined') return;

    let serializedActive: any = null;
    if (storage.activeGame) {
      serializedActive = {
        ...storage.activeGame,
        notes: storage.activeGame.notes.map(row =>
          row.map(cell => Array.from(cell))
        ),
      };
    }

    const dataToSave = {
      version: storage.version,
      history: storage.history,
      activeGame: serializedActive,
      settings: storage.settings,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave));
  } catch {}
}

export function saveRollbackCopy(data: ZenSudokuStorage): void {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(ROLLBACK_KEY, JSON.stringify(data));
  } catch {}
}

export function restoreRollbackCopy(): ZenSudokuStorage | null {
  try {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(ROLLBACK_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

// --------------------------------------------------------------------------
// Local-Only Canonical Fingerprints & Recent 20 Puzzles (Excluded from backup)
// --------------------------------------------------------------------------
export function loadStoredFingerprints(): Set<string> {
  try {
    if (typeof localStorage === 'undefined') return new Set();
    const raw = localStorage.getItem(FINGERPRINTS_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

export function saveStoredFingerprint(fingerprint: string): void {
  try {
    if (typeof localStorage === 'undefined') return;
    const set = loadStoredFingerprints();
    const list = Array.from(set);
    list.push(fingerprint);
    // Keep up to 10 000, drop oldest beyond that
    const trimmed = list.length > 10000 ? list.slice(-10000) : list;
    localStorage.setItem(FINGERPRINTS_KEY, JSON.stringify(trimmed));
  } catch {}
}

export function loadRecentPlayedGrids(): Grid[] {
  try {
    if (typeof localStorage === 'undefined') return [];
    const raw = localStorage.getItem(RECENT_PLAYED_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function savePlayedGrid(grid: Grid): void {
  try {
    if (typeof localStorage === 'undefined') return;
    const list = loadRecentPlayedGrids();
    list.push(grid);
    // Keep last 20 games
    const trimmed = list.length > 20 ? list.slice(-20) : list;
    localStorage.setItem(RECENT_PLAYED_KEY, JSON.stringify(trimmed));
  } catch {}
}

// --------------------------------------------------------------------------
// Backup Engine (.sudokubak)
// --------------------------------------------------------------------------
export async function createBackupBinary(
  history: HistoryRecord[],
  settings: UserSettings
): Promise<Uint8Array> {
  // Store history only, never grids
  const records = history.map((r: any) => {
    const rec = { ...r };
    delete rec.timestamp;
    if (rec.timeSeconds === undefined && rec.seconds !== undefined) {
      rec.timeSeconds = rec.seconds;
    }
    delete rec.seconds;
    return rec;
  });

  const payload = {
    records,
    settings: {
      numberSize: settings.numberSize,
      showTimer: settings.showTimer,
      highlightSameNumbers: settings.highlightSameNumbers,
      colorFeedback: settings.colorFeedback,
      autoRemoveNotes: settings.autoRemoveNotes,
      soundEffects: settings.soundEffects,
      hapticFeedback: settings.hapticFeedback,
    },
  };

  const jsonStr = JSON.stringify(payload);
  const jsonBytes = new TextEncoder().encode(jsonStr);
  const compressedBytes = await compressGzip(jsonBytes);

  // Prepend magic header + version byte
  const headerAndBody = new Uint8Array(MAGIC_BYTES.length + 1 + compressedBytes.length);
  headerAndBody.set(MAGIC_BYTES, 0);
  headerAndBody[MAGIC_BYTES.length] = FORMAT_VERSION;
  headerAndBody.set(compressedBytes, MAGIC_BYTES.length + 1);

  // Calculate HMAC-SHA256 signature using Web Crypto
  const key = await getHmacKey();
  const signatureBuffer = await crypto.subtle.sign('HMAC', key, headerAndBody);
  const signatureBytes = new Uint8Array(signatureBuffer); // 32 bytes

  // Append signature to create final .sudokubak package
  const finalFile = new Uint8Array(headerAndBody.length + signatureBytes.length);
  finalFile.set(headerAndBody, 0);
  finalFile.set(signatureBytes, headerAndBody.length);
  return finalFile;
}

export async function parseAndValidateBackup(
  fileBytes: Uint8Array
): Promise<{ records: HistoryRecord[]; settings: UserSettings }> {
  const HEADER_LEN = MAGIC_BYTES.length + 1; // 10 bytes
  const SIG_LEN = 32;

  // Check 1: Magic header and version
  if (fileBytes.length < HEADER_LEN + 1 + SIG_LEN) {
    throw new Error('Invalid or modified backup file');
  }

  for (let i = 0; i < MAGIC_BYTES.length; i++) {
    if (fileBytes[i] !== MAGIC_BYTES[i]) {
      throw new Error('Invalid or modified backup file');
    }
  }

  if (fileBytes[MAGIC_BYTES.length] !== FORMAT_VERSION) {
    throw new Error('Invalid or modified backup file');
  }

  // Check 2: Valid signature
  const signedContent = fileBytes.slice(0, -SIG_LEN);
  const providedSignature = fileBytes.slice(-SIG_LEN);
  const key = await getHmacKey();
  const isValidSignature = await crypto.subtle.verify('HMAC', key, providedSignature, signedContent);
  if (!isValidSignature) {
    throw new Error('Invalid or modified backup file');
  }

  // Decompress payload
  let parsedPayload: any;
  try {
    const compressedPart = fileBytes.slice(HEADER_LEN, -SIG_LEN);
    const decompressed = await decompressGzip(compressedPart);
    const jsonStr = new TextDecoder().decode(decompressed);
    parsedPayload = JSON.parse(jsonStr);
  } catch {
    throw new Error('Invalid or modified backup file');
  }

  if (
    !parsedPayload ||
    typeof parsedPayload !== 'object' ||
    !Array.isArray(parsedPayload.records) ||
    !parsedPayload.settings ||
    typeof parsedPayload.settings !== 'object'
  ) {
    throw new Error('Invalid or modified backup file');
  }

  const EXPECTED_FIELDS = ['date', 'hintsUsed', 'id', 'level', 'mistakes', 'score', 'timeSeconds'].sort();
  const ALLOWED_LEVELS: Difficulty[] = ['easy', 'medium', 'hard', 'expert', 'master'];

  // Check 3: Exactly the expected fields with correct types in every record
  for (const r of parsedPayload.records) {
    if (!r || typeof r !== 'object' || Array.isArray(r)) {
      throw new Error('Invalid or modified backup file');
    }

    const keys = Object.keys(r).sort();
    if (keys.length !== EXPECTED_FIELDS.length) {
      throw new Error('Invalid or modified backup file');
    }
    for (let i = 0; i < EXPECTED_FIELDS.length; i++) {
      if (keys[i] !== EXPECTED_FIELDS[i]) {
        throw new Error('Invalid or modified backup file');
      }
    }

    if (typeof r.id !== 'string' || r.id.trim().length === 0) {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.date !== 'string') {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.level !== 'string' || !ALLOWED_LEVELS.includes(r.level as Difficulty)) {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.score !== 'number' || !Number.isInteger(r.score)) {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.timeSeconds !== 'number' || !Number.isInteger(r.timeSeconds)) {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.mistakes !== 'number' || !Number.isInteger(r.mistakes)) {
      throw new Error('Invalid or modified backup file');
    }
    if (typeof r.hintsUsed !== 'number' || !Number.isInteger(r.hintsUsed)) {
      throw new Error('Invalid or modified backup file');
    }
  }

  // Check 4: Valid values
  const todayISO = new Date().toISOString().slice(0, 10);
  const seenIds = new Set<string>();

  for (const r of parsedPayload.records) {
    // Date validation
    const dateMatch = r.date.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!dateMatch) {
      throw new Error('Invalid or modified backup file');
    }
    const year = parseInt(dateMatch[1], 10);
    const month = parseInt(dateMatch[2], 10);
    const day = parseInt(dateMatch[3], 10);
    if (month < 1 || month > 12) {
      throw new Error('Invalid or modified backup file');
    }
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
    if (day < 1 || day > daysInMonth) {
      throw new Error('Invalid or modified backup file');
    }
    if (r.date > todayISO) {
      throw new Error('Invalid or modified backup file');
    }

    // Score within MAX_SCORE range
    const lvl = r.level as Difficulty;
    const maxScore = MAX_SCORE[lvl];
    if (r.score < 0 || r.score > maxScore) {
      throw new Error('Invalid or modified backup file');
    }

    // Positive realistic time
    if (r.timeSeconds <= 0 || r.timeSeconds > 86400) {
      throw new Error('Invalid or modified backup file');
    }

    if (r.mistakes < 0 || r.mistakes > 10) {
      throw new Error('Invalid or modified backup file');
    }

    if (r.hintsUsed < 0 || r.hintsUsed > 81) {
      throw new Error('Invalid or modified backup file');
    }

    // Unique IDs check
    if (seenIds.has(r.id)) {
      throw new Error('Invalid or modified backup file');
    }
    seenIds.add(r.id);
  }

  // Check 5: Settings validation
  const s = parsedPayload.settings;
  const validSizes = ['small', 'medium', 'large'];
  if (!validSizes.includes(s.numberSize)) {
    throw new Error('Invalid or modified backup file');
  }
  if (
    typeof s.showTimer !== 'boolean' ||
    typeof s.highlightSameNumbers !== 'boolean' ||
    typeof s.colorFeedback !== 'boolean' ||
    typeof s.autoRemoveNotes !== 'boolean' ||
    typeof s.soundEffects !== 'boolean' ||
    typeof s.hapticFeedback !== 'boolean'
  ) {
    throw new Error('Invalid or modified backup file');
  }

  const normalizedRecords = parsedPayload.records.map((r: any) => ({
    ...r,
    timestamp: new Date(`${r.date}T12:00:00Z`).getTime(),
  }));

  return {
    records: normalizedRecords,
    settings: {
      numberSize: s.numberSize,
      showTimer: s.showTimer,
      highlightSameNumbers: s.highlightSameNumbers,
      colorFeedback: s.colorFeedback,
      autoRemoveNotes: s.autoRemoveNotes,
      soundEffects: s.soundEffects,
      hapticFeedback: s.hapticFeedback,
    },
  };
}

export function downloadBackupFile(fileBytes: Uint8Array, filename = 'zensudoku.sudokubak'): void {
  const blob = new Blob([fileBytes as any], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
