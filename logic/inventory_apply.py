# logic/inventory_apply.py
"""Apply / revert cutting plan effects on scrap & stock (ledger) + event emits."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("RebarAgent.InventoryApply")


def apply_cutting_plan_inventory(
    project_id: int,
    plans_per_group: dict,
    stock_len_m: float,
) -> dict:
    """
    Apply a confirmed cutting plan to inventory and return a reversible ledger.
    """
    from db.models import ScrapModel, StockModel
    from logic.inventory_core import InventoryManager

    scraps_marked_used: List[int] = []
    scraps_added_ids: List[int] = []
    stock_ledger: List[dict] = []

    inv = InventoryManager(project_id)

    # plans_per_group structure is flexible — iterate bars/pieces best-effort
    groups = plans_per_group or {}
    if isinstance(groups, dict) and "plans" in groups:
        iterable = groups.get("plans") or []
    elif isinstance(groups, dict):
        iterable = list(groups.values())
    else:
        iterable = groups

    for group in iterable:
        if not isinstance(group, dict):
            continue
        bars = group.get("bars") or group.get("stock_bars") or []
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            # mark used scraps referenced by plan
            for sid in bar.get("scrap_ids") or bar.get("used_scrap_ids") or []:
                try:
                    if _mark_scrap_used_raw(int(sid)):
                        scraps_marked_used.append(int(sid))
                except Exception as e:
                    logger.warning("mark scrap used: %s", e)
            # bank offcuts
            for off in bar.get("offcuts") or bar.get("scraps") or []:
                try:
                    if isinstance(off, dict):
                        dia = float(off.get("diameter") or off.get("dia") or 0)
                        length = float(off.get("length_mm") or off.get("length") or 0)
                        grade = off.get("grade")
                        if dia > 0 and length > 0:
                            sid = ScrapModel.add_scrap(project_id, dia, length, grade=grade)
                            if sid:
                                scraps_added_ids.append(int(sid))
                except Exception as e:
                    logger.warning("add offcut: %s", e)
            # consume stock bars
            try:
                dia = float(bar.get("diameter") or bar.get("dia") or 0)
                length_mm = float(bar.get("length_mm") or (bar.get("length_m") or stock_len_m) * 1000)
                qty = int(bar.get("quantity") or 1)
                grade = bar.get("grade")
                if dia > 0 and qty > 0 and not bar.get("is_scrap"):
                    _consume_stock_bar(project_id, dia, length_mm, qty, grade)
                    stock_ledger.append(
                        {"diameter": dia, "length_mm": length_mm, "quantity": qty, "grade": grade}
                    )
            except Exception as e:
                logger.warning("consume stock: %s", e)

    ledger = {
        "project_id": project_id,
        "scraps_marked_used": scraps_marked_used,
        "scraps_added_ids": scraps_added_ids,
        "stock_consumed": stock_ledger,
        "stock_bars_consumed": sum(x["quantity"] for x in stock_ledger),
    }
    try:
        from utils.events import bus
        bus.emit("cut.confirmed", {"project_id": project_id, "ledger": {"stock_bars_consumed": ledger.get("stock_bars_consumed", 0)}})
        bus.emit("stock.changed", {"project_id": project_id, "reason": "cut_confirm"})
        bus.emit("scrap.changed", {"project_id": project_id, "reason": "cut_confirm"})
        bus.emit("ui.refresh_request", {"reason": "cut_confirmed", "project_id": project_id})
    except Exception:
        pass
    return ledger


def revert_cutting_plan_inventory(project_id: int, ledger: dict) -> dict:
    """Reverse a previous apply_cutting_plan_inventory ledger."""
    from db.models import ScrapModel, StockModel

    if not ledger:
        return {"ok": True, "restored_scraps": 0, "deleted_offcuts": 0, "restored_stock": 0, "errors": ["empty ledger"]}

    errors = []
    restored_scraps = 0
    deleted_offcuts = 0
    restored_stock = 0

    for sid in ledger.get("scraps_marked_used") or []:
        try:
            _mark_scrap_unused_raw(int(sid))
            restored_scraps += 1
        except Exception as e:
            errors.append(f"unmark scrap {sid}: {e}")

    for sid in ledger.get("scraps_added_ids") or []:
        try:
            ScrapModel.delete_scrap(int(sid))
            deleted_offcuts += 1
        except Exception as e:
            errors.append(f"delete offcut {sid}: {e}")

    for item in ledger.get("stock_consumed") or []:
        try:
            dia = float(item["diameter"])
            grade = item.get("grade")
            length_mm = float(item["length_mm"])
            qty = int(item["quantity"])
            if qty <= 0:
                continue
            ok = _restore_stock_bar(project_id, dia, length_mm, qty, grade)
            if ok:
                restored_stock += qty
            else:
                try:
                    StockModel.add(project_id, dia, length_mm, qty, grade=grade)
                    restored_stock += qty
                except Exception as e:
                    errors.append(f"restore stock Ø{dia}: {e}")
        except Exception as e:
            errors.append(f"restore stock item: {e}")

    try:
        from utils.events import bus
        bus.emit("cut.rolled_back", {"project_id": project_id, "restored_stock": restored_stock})
        bus.emit("stock.changed", {"project_id": project_id, "reason": "cut_rollback"})
        bus.emit("scrap.changed", {"project_id": project_id, "reason": "cut_rollback"})
        bus.emit("ui.refresh_request", {"reason": "cut_rolled_back", "project_id": project_id})
    except Exception:
        pass

    return {
        "ok": len(errors) == 0,
        "restored_scraps": restored_scraps,
        "deleted_offcuts": deleted_offcuts,
        "restored_stock": restored_stock,
        "errors": errors,
    }


def _mark_scrap_used_raw(scrap_id: int) -> bool:
    from db.models import ScrapModel
    try:
        ScrapModel.mark_as_used(int(scrap_id))
        return True
    except Exception:
        return False


def _mark_scrap_unused_raw(scrap_id: int) -> bool:
    try:
        import db.database as database
        database.db.execute(
            "UPDATE scraps SET used = 0 WHERE id = ?",
            (int(scrap_id),),
            commit=True,
        )
        return True
    except Exception:
        return False


def _consume_stock_bar(project_id, diameter, length_mm, quantity, grade=None) -> bool:
    from db.models import StockModel
    try:
        rows = StockModel.get_for_diameter(project_id, diameter, grade)
        for r in rows:
            parsed = _parse_stock_row(r)
            if not parsed:
                continue
            stock_id, L, qty = parsed
            if abs(L - float(length_mm)) < 1e-3 and int(qty) >= int(quantity):
                StockModel.update_quantity(stock_id, int(qty) - int(quantity))
                return True
        return False
    except Exception as e:
        logger.error("consume stock failed: %s", e)
        return False


def _parse_stock_row(r):
    try:
        # (id, project_id, diameter, length, quantity, grade?)
        return int(r[0]), float(r[3]), int(r[4] or 0)
    except Exception:
        return None


def _restore_stock_bar(project_id, diameter, length_mm, quantity, grade=None) -> bool:
    from db.models import StockModel
    try:
        rows = StockModel.get_for_diameter(project_id, diameter, grade)
        for r in rows:
            parsed = _parse_stock_row(r)
            if not parsed:
                continue
            stock_id, L, qty = parsed
            if abs(L - float(length_mm)) < 1e-3:
                StockModel.update_quantity(stock_id, int(qty) + int(quantity))
                return True
        return False
    except Exception as e:
        logger.error("restore stock failed: %s", e)
        return False
