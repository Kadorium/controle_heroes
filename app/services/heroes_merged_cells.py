"""Propagação de células mescladas em grids openpyxl."""

from __future__ import annotations

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet


def count_merged_cells(ws: Worksheet) -> int:
    try:
        return len(list(ws.merged_cells.ranges))
    except AttributeError:
        return 0


def apply_merged_cells_to_grid(grid: list[list[Any]], ws: Worksheet) -> int:
    """Preenche células cobertas por merge com o valor da âncora. Retorna quantidade de merges."""
    merges = list(getattr(ws.merged_cells, "ranges", []))
    if not merges:
        return 0

    max_cols = max((len(r) for r in grid), default=0)
    for row in grid:
        while len(row) < max_cols:
            row.append(None)

    for merged in merges:
        min_col, min_row, max_col, max_row = merged.min_col, merged.min_row, merged.max_col, merged.max_row
        if min_row - 1 >= len(grid):
            continue
        anchor_row = grid[min_row - 1]
        anchor_col = min_col - 1
        if anchor_col >= len(anchor_row):
            continue
        anchor_val = anchor_row[anchor_col]
        for r in range(min_row, max_row + 1):
            ri = r - 1
            if ri >= len(grid):
                grid.append([])
            while len(grid[ri]) <= max_col - 1:
                grid[ri].append(None)
            for c in range(min_col, max_col + 1):
                ci = c - 1
                if r == min_row and c == min_col:
                    continue
                grid[ri][ci] = anchor_val

    return len(merges)
