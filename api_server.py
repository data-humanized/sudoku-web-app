"""
api_server.py
FastAPI REST and WebSocket API Server for ZenSudoku.
Exposes endpoints for:
- Puzzle Generation (/api/puzzle/new)
- Backtracking Solver & Uniqueness (/api/puzzle/solve)
- Strict .sudokubak Backup Verification and Signing (/api/backup/verify, /api/backup/create)
- Analytics and Progress Auditing (/api/analytics/summary)
"""

from __future__ import annotations
import base64
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    class FastAPI:  # type: ignore
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return lambda f: f
        def post(self, *args, **kwargs): return lambda f: f
    class HTTPException(Exception):  # type: ignore
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
    def Field(*args, **kwargs): return None

from sudoku_logic import (
    Difficulty,
    Grid,
    HistoryRecord,
    SCORE_RANGES,
    calculate_daily_score,
    calculate_score,
    calculate_streak,
    get_level_unlock_status,
    get_new_puzzle,
    solve_sudoku,
)
from storage import (
    create_backup_binary,
    validate_and_parse_backup,
)
from puzzle_generator import generate_full_board, grade_puzzle_techniques, remove_clues_with_symmetry

app = FastAPI(
    title='ZenSudoku API',
    description='Pure Python backend API for ZenSudoku logic, backup verification, and puzzle generation',
    version='2.0.0',
)


class PuzzleRequest(BaseModel):
    level: Difficulty = Field(..., description='Difficulty tier: easy, medium, hard, expert, master')


class SolveRequest(BaseModel):
    grid: Grid = Field(..., description='9x9 board with 0 for empty cells')


class ScoreRequest(BaseModel):
    level: Difficulty
    elapsed_seconds: int
    mistakes: int
    hints_used: int


class BackupCreateRequest(BaseModel):
    records: List[Dict[str, Any]]
    settings: Optional[Dict[str, Any]] = None


class BackupVerifyRequest(BaseModel):
    base64_data: str


@app.get('/api/health')
def health_check():
    return {'status': 'healthy', 'engine': 'ZenSudoku Python Core'}


@app.post('/api/puzzle/new')
def api_new_puzzle(req: PuzzleRequest):
    """Returns a curated or procedurally generated puzzle with verified unique solution."""
    puzzle_data = get_new_puzzle(req.level)
    givens = sum(1 for row in puzzle_data['puzzle'] for cell in row if cell != 0)
    return {
        'level': req.level,
        'givens': givens,
        'puzzle': puzzle_data['puzzle'],
        'solution': puzzle_data['solution'],
        'score_range': SCORE_RANGES[req.level],
    }


@app.post('/api/puzzle/solve')
def api_solve_puzzle(req: SolveRequest):
    """Solves any valid 9x9 Sudoku and checks solution uniqueness."""
    count, solution = solve_sudoku(req.grid, count_limit=2)
    if not solution:
        raise HTTPException(status_code=400, detail='Puzzle has no valid solution.')
    return {
        'solutions_count': count,
        'is_unique': count == 1,
        'solution': solution,
    }


@app.post('/api/puzzle/grade')
def api_grade_puzzle(req: SolveRequest):
    """Analyzes a puzzle with human solving techniques."""
    grade = grade_puzzle_techniques(req.grid)
    return grade


@app.post('/api/score/calculate')
def api_calculate_score(req: ScoreRequest):
    """Calculates game score adhering to level ranges and penalty floors."""
    score = calculate_score(
        level=req.level,
        elapsed_seconds=req.elapsed_seconds,
        mistakes=req.mistakes,
        hints_used=req.hints_used,
    )
    return {
        'score': score,
        'score_range': SCORE_RANGES[req.level],
        'is_valid_range': SCORE_RANGES[req.level]['min'] <= score <= SCORE_RANGES[req.level]['max'],
    }


@app.post('/api/backup/create')
def api_create_backup(req: BackupCreateRequest):
    """Creates a compact gzip-compressed HMAC-signed .sudokubak binary payload."""
    try:
        binary = create_backup_binary(req.records, req.settings)
        b64 = base64.b64encode(binary).decode('utf-8')
        return {
            'success': True,
            'base64': b64,
            'size_bytes': len(binary),
        }
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))


@app.post('/api/backup/verify')
def api_verify_backup(req: BackupVerifyRequest):
    """Performs strict 5-step import verification on a .sudokubak backup."""
    try:
        raw_bytes = base64.b64decode(req.base64_data)
        records, settings = validate_and_parse_backup(raw_bytes)
        streaks = calculate_streak(records)
        unlocks = get_level_unlock_status(records)
        daily_score = calculate_daily_score(records)
        return {
            'valid': True,
            'records_count': len(records),
            'records': records,
            'settings': settings,
            'streaks': streaks,
            'unlocks': unlocks,
            'daily_score': daily_score,
        }
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception:
        raise HTTPException(status_code=400, detail='Invalid or modified backup file')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
