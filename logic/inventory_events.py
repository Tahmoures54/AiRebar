# logic/inventory_events.py
"""Emit concurrent-safe inventory / cutting events."""

from __future__ import annotations
from typing import Any, Dict, Optional


def emit_cut_confirmed(project_id: int, ledger: Optional[Dict[str, Any]] = None) -> None:
    from utils.events import bus
    ledger = ledger or {}
    with bus:
        bus.emit("cut.confirmed", {
            "project_id": project_id,
            "ledger": {"stock_bars_consumed": ledger.get("stock_bars_consumed", 0)},
        })
        bus.emit("stock.changed", {"project_id": project_id, "reason": "cut_confirm"})
        bus.emit("scrap.changed", {"project_id": project_id, "reason": "cut_confirm"})
        bus.emit_ui("ui.refresh_request", {"reason": "cut_confirmed", "project_id": project_id})


def emit_cut_rolled_back(project_id: int, restored_stock: int = 0) -> None:
    from utils.events import bus
    with bus:
        bus.emit("cut.rolled_back", {"project_id": project_id, "restored_stock": restored_stock})
        bus.emit("stock.changed", {"project_id": project_id, "reason": "cut_rollback"})
        bus.emit("scrap.changed", {"project_id": project_id, "reason": "cut_rollback"})
        bus.emit_ui("ui.refresh_request", {"reason": "cut_rolled_back", "project_id": project_id})
