# logic/inventory.py
"""Facade: re-exports inventory APIs for backward-compatible imports."""
from __future__ import annotations

from logic.inventory_core import InventoryManager, _parse_stock_row
from logic.stock_intelligence import (
    analyze_stock_intelligence,
    format_stock_intelligence_report,
)
from logic.inventory_apply import (
    apply_cutting_plan_inventory,
    revert_cutting_plan_inventory,
)

__all__ = [
    "InventoryManager",
    "_parse_stock_row",
    "analyze_stock_intelligence",
    "format_stock_intelligence_report",
    "apply_cutting_plan_inventory",
    "revert_cutting_plan_inventory",
]
