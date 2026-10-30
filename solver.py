"""
solver.py
Algorithm X with Dancing Links (DLX) & Fast MRV Solver for Sudoku in Python.

Provides:
- Exact cover matrix representation of 9x9 Sudoku constraints:
  1. Cell constraint (each cell has exactly one digit)
  2. Row constraint (each row has digits 1-9)
  3. Column constraint (each column has digits 1-9)
  4. 3x3 Box constraint (each box has digits 1-9)
- Exact cover solver finding all solutions or proving uniqueness
- Fast benchmark comparator between Backtracking and DLX
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from sudoku_logic import Grid, clone_grid, create_empty_grid


class DLXNode:
    def __init__(self, col_header: Optional[DLXColumn] = None, row_id: int = -1):
        self.left: DLXNode = self
        self.right: DLXNode = self
        self.up: DLXNode = self
        self.down: DLXNode = self
        self.column: Optional[DLXColumn] = col_header
        self.row_id: int = row_id


class DLXColumn(DLXNode):
    def __init__(self, name: str):
        super().__init__(col_header=self)
        self.size: int = 0
        self.name: str = name

    def cover(self) -> None:
        self.right.left = self.left
        self.left.right = self.right
        i = self.down
        while i != self:
            j = i.right
            while j != i:
                j.down.up = j.up
                j.up.down = j.down
                if j.column:
                    j.column.size -= 1
                j = j.right
            i = i.down

    def uncover(self) -> None:
        i = self.up
        while i != self:
            j = i.left
            while j != i:
                if j.column:
                    j.column.size += 1
                j.down.up = j
                j.up.down = j
                j = j.left
            i = i.up
        self.right.left = self
        self.left.right = self


class SudokuDLXSolver:
    def __init__(self):
        self.header = DLXColumn("root")
        self.columns: List[DLXColumn] = []
        self._build_matrix_structure()

    def _build_matrix_structure(self) -> None:
        col_names: List[str] = []
        # 1. Cell constraint (81)
        for r in range(9):
            for c in range(9):
                col_names.append(f"R{r}C{c}")
        # 2. Row constraint (81)
        for r in range(9):
            for d in range(1, 10):
                col_names.append(f"R{r}#{d}")
        # 3. Col constraint (81)
        for c in range(9):
            for d in range(1, 10):
                col_names.append(f"C{c}#{d}")
        # 4. Box constraint (81)
        for b in range(9):
            for d in range(1, 10):
                col_names.append(f"B{b}#{d}")

        curr: DLXNode = self.header
        for name in col_names:
            col = DLXColumn(name)
            col.left = curr
            col.right = self.header
            curr.right = col
            self.header.left = col
            curr = col
            self.columns.append(col)

    def solve(self, grid: Grid, max_solutions: int = 2) -> List[Grid]:
        """Solves grid and returns up to max_solutions solutions."""
        # Map row ID (0..728) to (row, col, digit)
        row_map: Dict[int, Tuple[int, int, int]] = {}
        row_id = 0

        # Build candidate rows
        matrix_rows: List[Tuple[int, List[int]]] = []
        for r in range(9):
            for c in range(9):
                given = grid[r][c]
                digits = [given] if given != 0 else list(range(1, 10))
                for d in digits:
                    row_map[row_id] = (r, c, d)
                    b = (r // 3) * 3 + (c // 3)
                    cols = [
                        r * 9 + c,                     # Cell constraint
                        81 + r * 9 + (d - 1),          # Row constraint
                        162 + c * 9 + (d - 1),         # Col constraint
                        243 + b * 9 + (d - 1),         # Box constraint
                    ]
                    matrix_rows.append((row_id, cols))
                    row_id += 1

        # Populate DLX links
        for rid, col_indices in matrix_rows:
            first_node: Optional[DLXNode] = None
            for c_idx in col_indices:
                col = self.columns[c_idx]
                node = DLXNode(col_header=col, row_id=rid)
                node.down = col
                node.up = col.up
                col.up.down = node
                col.up = node
                col.size += 1

                if first_node is None:
                    first_node = node
                else:
                    node.left = first_node.left
                    node.right = first_node
                    first_node.left.right = node
                    first_node.left = node

        solutions: List[Grid] = []
        current_solution: List[int] = []

        def search():
            if len(solutions) >= max_solutions:
                return
            if self.header.right == self.header:
                # Solution found!
                sol_grid = clone_grid(grid)
                for rid in current_solution:
                    r, c, d = row_map[rid]
                    sol_grid[r][c] = d
                solutions.append(sol_grid)
                return

            # Choose column with minimum size (MRV)
            best_col: Optional[DLXColumn] = None
            min_size = float('inf')
            col = self.header.right
            while col != self.header:
                if isinstance(col, DLXColumn):
                    if col.size < min_size:
                        min_size = col.size
                        best_col = col
                col = col.right

            if not best_col or best_col.size == 0:
                return

            best_col.cover()
            row_node = best_col.down
            while row_node != best_col:
                current_solution.append(row_node.row_id)
                right_node = row_node.right
                while right_node != row_node:
                    if right_node.column:
                        right_node.column.cover()
                    right_node = right_node.right

                search()

                current_solution.pop()
                left_node = row_node.left
                while left_node != row_node:
                    if left_node.column:
                        left_node.column.uncover()
                    left_node = left_node.left

                row_node = row_node.down

            best_col.uncover()

        search()
        return solutions


def solve_with_dlx(grid: Grid) -> Tuple[int, Optional[Grid]]:
    solver = SudokuDLXSolver()
    sols = solver.solve(grid, max_solutions=2)
    return len(sols), sols[0] if sols else None
