# logic/optimizer_core.py
"""Core optimizer API (split into algorithms + stockflow)."""
from __future__ import annotations

from logic.optimizer_algorithms import (
    optimize_cuts,
    optimize_cuts_mip_indexed,
    optimize_labeled_cuts,
)
from logic.optimizer_stockflow import (
    optimize_remaining_multi_stock,
    optimize_with_scraps_and_stock,
    compute_plan_data_hash,
    store_cutting_assignments,
)

__all__ = [
    "optimize_cuts",
    "optimize_cuts_mip_indexed",
    "optimize_labeled_cuts",
    "optimize_remaining_multi_stock",
    "optimize_with_scraps_and_stock",
    "compute_plan_data_hash",
    "store_cutting_assignments",
]
