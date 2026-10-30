"""
storage.py
Persistence manager and strict compact binary backup engine for ZenSudoku.

Backup File Format (.sudokubak):
- Magic Header: 9 bytes 'ZENSUDBAK'
- Format Version: 1 byte (0x01)
- Payload: Gzip-compressed JSON block containing:
    {
      "records": [ { id, date, level, score, timeSeconds, mistakes, hintsUsed }, ... ],
      "settings": { theme, sound_effects, haptics, font_size, show_timer, ... }
    }
- HMAC-SHA256 Signature: 32 bytes calculated over [Header + Version + Compressed Payload]
  using app secret b"zen_sudoku_compact_strict_secret_2025"

Strict 5-step import validation:
1. Magic header and version check
2. Valid HMAC-SHA256 signature check
3. JSON decompression & structure check
4. Record field validation (exact keys, types, valid score range, no future date, unique IDs)
5. Rollback copy preservation and recovery
"""

from __future__ import annotations
import gzip
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sudoku_logic import (
    DEFAULT_SETTINGS,
    GameState,
    HistoryRecord,
    SCORE_RANGES,
    UserSettings,
)

BACKUP_MAGIC = b'ZENSUDBAK'
BACKUP_VERSION = 1
BACKUP_SECRET = b'zen_sudoku_compact_strict_secret_2025'
BACKUP_ERROR_MSG = 'Invalid or modified backup file'


class ZenSudokuStorage:
    def __init__(
        self,
        version: int = 1,
        history: Optional[List[HistoryRecord]] = None,
        active_game: Optional[GameState] = None,
        settings: Optional[UserSettings] = None,
    ):
        self.version = version
        self.history: List[HistoryRecord] = history or []
        self.active_game: Optional[GameState] = active_game
        self.settings: UserSettings = settings or dict(DEFAULT_SETTINGS)

    def to_dict(self) -> Dict[str, Any]:
        serialized_active = None
        if self.active_game:
            serialized_active = dict(self.active_game)
            if 'notes' in self.active_game and self.active_game['notes']:
                serialized_active['notes'] = [
                    [list(cell) if isinstance(cell, set) else cell for cell in row]
                    for row in self.active_game['notes']
                ]
        return {
            'version': self.version,
            'history': self.history,
            'active_game': serialized_active,
            'settings': self.settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ZenSudokuStorage:
        history = data.get('history', [])
        # Ensure migration: timeSeconds field normalized
        for r in history:
            if 'timeSeconds' not in r and 'seconds' in r:
                r['timeSeconds'] = r['seconds']
        active = data.get('active_game')
        if active and 'notes' in active and active['notes']:
            active['notes'] = [
                [set(cell) if isinstance(cell, list) else set() for cell in row]
                for row in active['notes']
            ]
        settings = dict(DEFAULT_SETTINGS)
        settings.update(data.get('settings', {}))
        return cls(
            version=data.get('version', 1),
            history=history,
            active_game=active,
            settings=settings,
        )


def compute_hmac(data: bytes) -> bytes:
    return hmac.new(BACKUP_SECRET, data, hashlib.sha256).digest()


def create_backup_binary(
    records: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Serializes history records and settings into a compact signed .sudokubak binary file.
    Does NOT store grids, solutions, or in-progress games.
    """
    clean_records = []
    for r in records:
        # Preserve record keys for strict verification
        clean_records.append(dict(r))

    clean_settings = dict(settings or DEFAULT_SETTINGS)
    payload_dict = {
        'records': clean_records,
        'settings': clean_settings,
    }

    # Minified JSON payload
    raw_json = json.dumps(payload_dict, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    # Gzip compression
    compressed_payload = gzip.compress(raw_json, compresslevel=9)

    # Magic header (9 bytes) + version (1 byte)
    header = BACKUP_MAGIC + bytes([BACKUP_VERSION])
    content_to_sign = header + compressed_payload

    signature = compute_hmac(content_to_sign)
    return content_to_sign + signature


def validate_and_parse_backup(
    backup_data: bytes,
) -> Tuple[List[HistoryRecord], UserSettings]:
    """
    Strict 5-step import verification in order.
    Raises ValueError(BACKUP_ERROR_MSG) if any check fails.
    """
    # 1. Header and Version check
    min_len = len(BACKUP_MAGIC) + 1 + 32  # header (9) + version (1) + signature (32)
    if len(backup_data) < min_len:
        raise ValueError(BACKUP_ERROR_MSG)

    magic = backup_data[:len(BACKUP_MAGIC)]
    version = backup_data[len(BACKUP_MAGIC)]
    if magic != BACKUP_MAGIC or version != BACKUP_VERSION:
        raise ValueError(BACKUP_ERROR_MSG)

    # 2. Signature verification
    content_signed = backup_data[:-32]
    expected_sig = backup_data[-32:]
    actual_sig = compute_hmac(content_signed)

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise ValueError(BACKUP_ERROR_MSG)

    # 3. Decompression & JSON structure check
    compressed_payload = content_signed[len(BACKUP_MAGIC) + 1:]
    try:
        raw_json = gzip.decompress(compressed_payload)
        parsed = json.loads(raw_json.decode('utf-8'))
    except Exception:
        raise ValueError(BACKUP_ERROR_MSG)

    if not isinstance(parsed, dict) or 'records' not in parsed:
        raise ValueError(BACKUP_ERROR_MSG)

    records_raw = parsed['records']
    if not isinstance(records_raw, list):
        raise ValueError(BACKUP_ERROR_MSG)

    # 4. Strict record field validation
    required_keys = {'id', 'date', 'level', 'score', 'timeSeconds', 'mistakes', 'hintsUsed'}
    valid_levels = {'easy', 'medium', 'hard', 'expert', 'master'}
    date_regex = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    today_iso = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    seen_ids = set()
    validated_records: List[HistoryRecord] = []

    for r in records_raw:
        if not isinstance(r, dict):
            raise ValueError(BACKUP_ERROR_MSG)

        # Exact keys: no missing or extra fields allowed
        if set(r.keys()) != required_keys:
            raise ValueError(BACKUP_ERROR_MSG)

        # Field types
        if not isinstance(r['id'], str) or not r['id'].strip():
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['date'], str) or not date_regex.match(r['date']):
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['level'], str) or r['level'] not in valid_levels:
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['score'], (int, float)) or isinstance(r['score'], bool):
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['timeSeconds'], (int, float)) or isinstance(r['timeSeconds'], bool):
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['mistakes'], int) or isinstance(r['mistakes'], bool):
            raise ValueError(BACKUP_ERROR_MSG)
        if not isinstance(r['hintsUsed'], int) or isinstance(r['hintsUsed'], bool):
            raise ValueError(BACKUP_ERROR_MSG)

        # No future dates
        if r['date'] > today_iso:
            raise ValueError(BACKUP_ERROR_MSG)

        # Score within valid SCORE_RANGES
        lvl: Any = r['level']
        score_val = int(r['score'])
        score_spec = SCORE_RANGES[lvl]
        if score_val < score_spec['min'] or score_val > score_spec['max']:
            raise ValueError(BACKUP_ERROR_MSG)

        # Unique IDs
        if r['id'] in seen_ids:
            raise ValueError(BACKUP_ERROR_MSG)
        seen_ids.add(r['id'])

        validated_records.append({
            'id': r['id'],
            'date': r['date'],
            'level': lvl,
            'score': score_val,
            'timeSeconds': int(r['timeSeconds']),
            'mistakes': int(r['mistakes']),
            'hintsUsed': int(r['hintsUsed']),
        })

    # Validate settings block
    settings_raw = parsed.get('settings', {})
    clean_settings = dict(DEFAULT_SETTINGS)
    if isinstance(settings_raw, dict):
        clean_settings.update(settings_raw)

    return validated_records, clean_settings


# Rollback copy support
_ROLLBACK_COPY: Optional[ZenSudokuStorage] = None


def save_rollback_copy(storage: ZenSudokuStorage) -> None:
    global _ROLLBACK_COPY
    _ROLLBACK_COPY = ZenSudokuStorage.from_dict(storage.to_dict())


def restore_rollback_copy() -> Optional[ZenSudokuStorage]:
    global _ROLLBACK_COPY
    return _ROLLBACK_COPY


def load_zen_data(file_path: str = 'zen_sudoku_data.json') -> ZenSudokuStorage:
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ZenSudokuStorage.from_dict(data)
        except Exception:
            pass
    return ZenSudokuStorage()


def save_zen_data(storage: ZenSudokuStorage, file_path: str = 'zen_sudoku_data.json') -> None:
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(storage.to_dict(), f, indent=2)
    except Exception:
        pass


def export_backup_json(storage: ZenSudokuStorage) -> str:
    return json.dumps(storage.to_dict(), indent=2)
