"""Two-way sensitivity analysis of intrinsic value to WACC and terminal growth."""

from __future__ import annotations

import math
from dataclasses import replace

from .dcf import DCFAssumptions, run_dcf


def sensitivity_table(
    base: DCFAssumptions,
    wacc_range: list[float],
    terminal_growth_range: list[float],
) -> dict[float, dict[float, float]]:
    """Recompute intrinsic value per share across a WACC x terminal-growth grid.

    Cells where WACC <= terminal growth are non-convergent for the Gordon
    Growth model and are reported as NaN rather than raising, so the caller
    can render a full rectangular grid (e.g. as a heatmap) without special-casing.
    """
    table: dict[float, dict[float, float]] = {}
    for w in wacc_range:
        row: dict[float, float] = {}
        for g in terminal_growth_range:
            if w <= g:
                row[g] = math.nan
                continue
            scenario = replace(base, wacc=w, terminal_growth=g)
            row[g] = run_dcf(scenario).intrinsic_value_per_share
        table[w] = row
    return table
