# logic/optimizer.py
"""Facade: cutting optimization API (split modules under logic/)."""
from __future__ import annotations

from logic.optimizer_options import OptimizerOptions
from logic.optimizer_core import (
    optimize_cuts,
    optimize_cuts_mip_indexed,
    optimize_labeled_cuts,
    optimize_remaining_multi_stock,
    optimize_with_scraps_and_stock,
    compute_plan_data_hash,
    store_cutting_assignments,
)
from logic.optimizer_metrics import (
    get_scrap_infos_for_dia_grade,
    get_available_stock_bars,
    compute_plan_metrics,
)

__all__ = [
    "OptimizerOptions",
    "optimize_cuts",
    "optimize_cuts_mip_indexed",
    "optimize_labeled_cuts",
    "optimize_remaining_multi_stock",
    "optimize_with_scraps_and_stock",
    "compute_plan_data_hash",
    "store_cutting_assignments",
    "get_scrap_infos_for_dia_grade",
    "get_available_stock_bars",
    "compute_plan_metrics",
]
