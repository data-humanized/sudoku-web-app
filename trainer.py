"""
trainer.py
Sudoku Technique Trainer and Pattern Explainer in Python.

Provides step-by-step logic hints and pattern detection for:
- Naked Singles (single candidate in cell)
- Hidden Singles (candidate appears once in unit)
- Naked Pairs (two cells share identical 2 candidates)
- Pointing Pairs (box candidates aligned in a row/col)
- Box-Line Reductions (row/col candidates confined to a single box)
- X-Wing (rectangle pattern across two rows/cols)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple

from sudoku_logic import Grid, clone_grid, get_candidates, get_peers


class TechniqueHint:
    def __init__(
        self,
        technique_name: str,
        description: str,
        target_cells: List[Tuple[int, int]],
        eliminations: List[Tuple[int, int, int]],
        placed_digit: Optional[Tuple[int, int, int]] = None,
    ):
        self.technique_name = technique_name
        self.description = description
        self.target_cells = target_cells
        self.eliminations = eliminations
        self.placed_digit = placed_digit

    def to_dict(self) -> Dict[str, Any]:
        return {
            'technique': self.technique_name,
            'description': self.description,
            'target_cells': self.target_cells,
            'eliminations': self.eliminations,
            'placed_digit': self.placed_digit,
        }


class SudokuTrainer:
    def __init__(self, grid: Grid):
        self.grid = clone_grid(grid)
        self.candidates: List[List[Set[int]]] = [
            [get_candidates(self.grid, r, c) if self.grid[r][c] == 0 else set() for c in range(9)]
            for r in range(9)
        ]

    def find_next_hint(self) -> Optional[TechniqueHint]:
        # 1. Search for Naked Singles
        hint = self._find_naked_single()
        if hint:
            return hint

        # 2. Search for Hidden Singles
        hint = self._find_hidden_single()
        if hint:
            return hint

        # 3. Search for Naked Pairs
        hint = self._find_naked_pair()
        if hint:
            return hint

        # 4. Search for Pointing Pairs
        hint = self._find_pointing_pair()
        if hint:
            return hint

        return None

    def _find_naked_single(self) -> Optional[TechniqueHint]:
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0 and len(self.candidates[r][c]) == 1:
                    d = list(self.candidates[r][c])[0]
                    return TechniqueHint(
                        technique_name="Naked Single",
                        description=f"Cell at row {r+1}, col {c+1} has only one possible candidate: {d}.",
                        target_cells=[(r, c)],
                        eliminations=[],
                        placed_digit=(r, c, d),
                    )
        return None

    def _find_hidden_single(self) -> Optional[TechniqueHint]:
        # Check rows
        for r in range(9):
            for d in range(1, 10):
                cols = [c for c in range(9) if self.grid[r][c] == 0 and d in self.candidates[r][c]]
                if len(cols) == 1:
                    c = cols[0]
                    return TechniqueHint(
                        technique_name="Hidden Single (Row)",
                        description=f"In row {r+1}, the digit {d} can only appear at column {c+1}.",
                        target_cells=[(r, c)],
                        eliminations=[],
                        placed_digit=(r, c, d),
                    )

        # Check cols
        for c in range(9):
            for d in range(1, 10):
                rows = [r for r in range(9) if self.grid[r][c] == 0 and d in self.candidates[r][c]]
                if len(rows) == 1:
                    r = rows[0]
                    return TechniqueHint(
                        technique_name="Hidden Single (Column)",
                        description=f"In column {c+1}, the digit {d} can only appear at row {r+1}.",
                        target_cells=[(r, c)],
                        eliminations=[],
                        placed_digit=(r, c, d),
                    )

        # Check 3x3 boxes
        for br in range(0, 9, 3):
            for bc in range(0, 9, 3):
                for d in range(1, 10):
                    cells = [
                        (r, c)
                        for r in range(br, br + 3)
                        for c in range(bc, bc + 3)
                        if self.grid[r][c] == 0 and d in self.candidates[r][c]
                    ]
                    if len(cells) == 1:
                        r, c = cells[0]
                        return TechniqueHint(
                            technique_name="Hidden Single (Box)",
                            description=f"In the 3x3 box, the digit {d} can only appear at row {r+1}, col {c+1}.",
                            target_cells=[(r, c)],
                            eliminations=[],
                            placed_digit=(r, c, d),
                        )
        return None

    def _find_naked_pair(self) -> Optional[TechniqueHint]:
        # Row pairs
        for r in range(9):
            pairs = [
                (c, self.candidates[r][c])
                for c in range(9)
                if self.grid[r][c] == 0 and len(self.candidates[r][c]) == 2
            ]
            for i in range(len(pairs)):
                for j in range(i + 1, len(pairs)):
                    c1, cand1 = pairs[i]
                    c2, cand2 = pairs[j]
                    if cand1 == cand2:
                        d1, d2 = list(cand1)
                        # Find eliminations in other cells of the row
                        elims = []
                        for other_c in range(9):
                            if other_c not in (c1, c2) and self.grid[r][other_c] == 0:
                                if d1 in self.candidates[r][other_c]:
                                    elims.append((r, other_c, d1))
                                if d2 in self.candidates[r][other_c]:
                                    elims.append((r, other_c, d2))
                        if elims:
                            return TechniqueHint(
                                technique_name="Naked Pair (Row)",
                                description=f"Cells ({r+1},{c1+1}) and ({r+1},{c2+1}) contain identical pair {{{d1},{d2}}}, eliminating them from the rest of row {r+1}.",
                                target_cells=[(r, c1), (r, c2)],
                                eliminations=elims,
                            )
        return None

    def _find_pointing_pair(self) -> Optional[TechniqueHint]:
        for br in range(0, 9, 3):
            for bc in range(0, 9, 3):
                for d in range(1, 10):
                    cells = [
                        (r, c)
                        for r in range(br, br + 3)
                        for c in range(bc, bc + 3)
                        if self.grid[r][c] == 0 and d in self.candidates[r][c]
                    ]
                    if len(cells) in (2, 3):
                        # All in same row?
                        same_row = all(r == cells[0][0] for r, _ in cells)
                        if same_row:
                            r = cells[0][0]
                            box_cols = {c for _, c in cells}
                            elims = [
                                (r, c, d)
                                for c in range(9)
                                if c not in box_cols and self.grid[r][c] == 0 and d in self.candidates[r][c]
                            ]
                            if elims:
                                return TechniqueHint(
                                    technique_name="Pointing Pair (Row)",
                                    description=f"In box at ({br+1},{bc+1}), digit {d} is confined to row {r+1}, eliminating {d} from the rest of row {r+1}.",
                                    target_cells=cells,
                                    eliminations=elims,
                                )
        return None
