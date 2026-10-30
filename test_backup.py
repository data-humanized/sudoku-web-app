"""
test_backup.py
Comprehensive test suite for ZenSudoku strict .sudokubak binary backup engine in Python.

Tests:
1. Round trip export/import succeeds with identical records and settings
2. Wrong magic or version is rejected
3. Bad HMAC signature is rejected
4. Tampered payload bytes are rejected
5. Missing or extra field in record is rejected
6. Wrong field type in record is rejected
7. Future date is rejected
8. Out-of-range score is rejected
9. Duplicate record IDs are rejected
10. Rollback copy stores and restores previous state on failure
"""

import gzip
import json
import unittest
from datetime import datetime, timezone

from storage import (
    BACKUP_MAGIC,
    BACKUP_VERSION,
    ZenSudokuStorage,
    compute_hmac,
    create_backup_binary,
    restore_rollback_copy,
    save_rollback_copy,
    validate_and_parse_backup,
)


class TestBackupBinary(unittest.TestCase):
    def setUp(self):
        self.sample_records = [
            {
                'id': 'rec-1',
                'date': '2025-01-01',
                'level': 'easy',
                'score': 800,
                'timeSeconds': 180,
                'mistakes': 0,
                'hintsUsed': 0,
            },
            {
                'id': 'rec-2',
                'date': '2025-01-02',
                'level': 'master',
                'score': 14500,
                'timeSeconds': 850,
                'mistakes': 1,
                'hintsUsed': 0,
            },
        ]
        self.sample_settings = {
            'theme': 'minimal_slate',
            'sound_effects': False,
            'haptics': True,
            'font_size': 'large',
            'show_timer': True,
            'show_mistakes': True,
            'auto_remove_notes': True,
        }

    def test_round_trip_success(self):
        binary = create_backup_binary(self.sample_records, self.sample_settings)
        records, settings = validate_and_parse_backup(binary)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['id'], 'rec-1')
        self.assertEqual(records[1]['level'], 'master')
        self.assertEqual(records[1]['score'], 14500)
        self.assertEqual(settings['sound_effects'], False)

    def test_wrong_magic_or_version_rejected(self):
        binary = bytearray(create_backup_binary(self.sample_records))
        binary[0] = ord('X')  # Alter magic
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bytes(binary))

        binary2 = bytearray(create_backup_binary(self.sample_records))
        binary2[len(BACKUP_MAGIC)] = 0x99  # Alter version
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bytes(binary2))

    def test_bad_signature_rejected(self):
        binary = bytearray(create_backup_binary(self.sample_records))
        binary[-1] ^= 0xFF  # Corrupt last signature byte
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bytes(binary))

    def test_tampered_payload_rejected(self):
        binary = bytearray(create_backup_binary(self.sample_records))
        # Corrupt byte inside the gzip compressed payload
        mid = len(binary) // 2
        binary[mid] ^= 0x42
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bytes(binary))

    def test_missing_or_extra_field_rejected(self):
        # Missing hintsUsed
        rec_missing = [{
            'id': 'rec-missing',
            'date': '2025-01-01',
            'level': 'easy',
            'score': 1500,
            'timeSeconds': 180,
            'mistakes': 0,
        }]
        bin_missing = create_backup_binary(rec_missing)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_missing)

        # Extra field
        rec_extra = [{
            'id': 'rec-extra',
            'date': '2025-01-01',
            'level': 'easy',
            'score': 1500,
            'timeSeconds': 180,
            'mistakes': 0,
            'hintsUsed': 0,
            'illegalField': 'forbidden',
        }]
        bin_extra = create_backup_binary(rec_extra)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_extra)

    def test_wrong_field_type_rejected(self):
        rec_bad_type = [{
            'id': 'rec-bad',
            'date': '2025-01-01',
            'level': 'easy',
            'score': 'not-a-number',
            'timeSeconds': 180,
            'mistakes': 0,
            'hintsUsed': 0,
        }]
        bin_bad = create_backup_binary(rec_bad_type)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_bad)

    def test_future_date_rejected(self):
        rec_future = [{
            'id': 'rec-future',
            'date': '2099-12-31',
            'level': 'easy',
            'score': 1500,
            'timeSeconds': 180,
            'mistakes': 0,
            'hintsUsed': 0,
        }]
        bin_future = create_backup_binary(rec_future)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_future)

    def test_out_of_range_score_rejected(self):
        # Master valid score is 12000 - 16000
        rec_too_high = [{
            'id': 'rec-high',
            'date': '2025-01-01',
            'level': 'master',
            'score': 99999,
            'timeSeconds': 180,
            'mistakes': 0,
            'hintsUsed': 0,
        }]
        bin_high = create_backup_binary(rec_too_high)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_high)

    def test_duplicate_record_ids_rejected(self):
        rec_dupe = [
            {'id': 'dup-1', 'date': '2025-01-01', 'level': 'easy', 'score': 1500, 'timeSeconds': 180, 'mistakes': 0, 'hintsUsed': 0},
            {'id': 'dup-1', 'date': '2025-01-02', 'level': 'easy', 'score': 1500, 'timeSeconds': 180, 'mistakes': 0, 'hintsUsed': 0},
        ]
        bin_dupe = create_backup_binary(rec_dupe)
        with self.assertRaises(ValueError):
            validate_and_parse_backup(bin_dupe)

    def test_rollback_copy_recovery(self):
        initial_storage = ZenSudokuStorage(version=1, history=self.sample_records)
        save_rollback_copy(initial_storage)

        # Attempt to parse corrupt file
        try:
            validate_and_parse_backup(b"corrupt_junk_bytes")
        except ValueError:
            pass

        restored = restore_rollback_copy()
        self.assertIsNotNone(restored)
        self.assertEqual(len(restored.history), 2)
        self.assertEqual(restored.history[0]['id'], 'rec-1')


if __name__ == '__main__':
    unittest.main()
