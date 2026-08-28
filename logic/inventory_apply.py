# logic/inventory_apply.py
"""Apply / revert cutting plan effects on scrap & stock (ledger)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.models import ScrapModel, StockModel
from config import DEFAULT_REBAR_GRADE
from utils.logger import setup_logger
from logic.inventory_core import InventoryManager, _parse_stock_row

logger = setup_logger("RebarAgent.InventoryApply")


def apply_cutting_plan_inventory(project_id: int, plans_per_group: dict, stock_length_m: float) -> dict:
    marked_used_ids = []
    added_ids = []
    stock_ledger = []
    errors = []
    used_ids = set()
    inv = InventoryManager(project_id)

    for key, data in (plans_per_group or {}).items():
        try:
            dia, grade = key
        except Exception:
            continue
        dia = float(dia)
        grade = str(grade)
        plans = data.get("plans") or []
        new_scraps = data.get("new_scraps") or []
        stock_usage = data.get("stock_usage") or {}

        candidates = []
        for plan in plans:
            sid = plan.get("scrap_id")
            if sid is None:
                continue
            try:
                candidates.append(int(sid))
            except Exception:
                pass
        for sid in data.get("pending_scrap_updates") or []:
            try:
                candidates.append(int(sid))
            except Exception:
                pass
        for sid in candidates:
            if sid in used_ids:
                continue
            try:
                ScrapModel.mark_as_used(sid)
                marked_used_ids.append(sid)
                used_ids.add(sid)
            except Exception as e:
                errors.append(f"mark scrap {sid}: {e}")

        listofer_no = None
        if plans:
            bin0 = plans[0].get("bin") or []
            if bin0 and isinstance(bin0[0], (list, tuple)) and len(bin0[0]) > 1:
                listofer_no = (bin0[0][1] or {}).get("listofer_no")

        pending_adds = data.get("pending_scrap_additions")
        add_items = []
        if pending_adds:
            for item in pending_adds:
                try:
                    _, d, length_mm, g, lf = item
                    add_items.append((float(d), int(length_mm), g, lf))
                except Exception as e:
                    errors.append(f"parse pending add: {e}")
        else:
            for waste_m in new_scraps:
                try:
                    waste_mm = int(round(float(waste_m) * 1000))
                    if waste_mm > 0:
                        add_items.append((dia, waste_mm, grade, listofer_no))
                except Exception as e:
                    errors.append(f"parse waste: {e}")

        for d, length_mm, g, lf in add_items:
            try:
                sid = ScrapModel.add_scrap(project_id, d, length_mm, grade=g, listofer_number=lf)
                if sid:
                    added_ids.append(int(sid))
            except Exception as e:
                errors.append(f"add scrap: {e}")

        qty_map = dict(stock_usage) if stock_usage else {}
        if not qty_map:
            n_full = sum(
                1 for p in plans
                if p.get("scrap_id") is None
                and float(p.get("bar_length") or 0) >= float(stock_length_m) - 1e-6
            )
            if n_full:
                qty_map[float(stock_length_m)] = n_full

        for len_m, qty in qty_map.items():
            qty = int(qty or 0)
            if qty <= 0:
                continue
            length_mm = float(len_m) * 1000.0 if float(len_m) < 500 else float(len_m)
            consumed = 0
            left = qty
            while left > 0:
                if inv.consume_stock_bar(dia, length_mm, 1, grade=grade):
                    consumed += 1
                    left -= 1
                else:
                    errors.append(f"insufficient stock Ø{dia:g} {grade} ×{length_mm:.0f}mm")
                    break
            if consumed:
                stock_ledger.append({"diameter": dia, "grade": grade, "length_mm": length_mm, "quantity": consumed})

    return {
        "scraps_marked_used": marked_used_ids,
        "scraps_added_ids": added_ids,
        "stock_consumed": stock_ledger,
        "scraps_marked_used_count": len(marked_used_ids),
        "scraps_added": len(added_ids),
        "stock_bars_consumed": sum(x["quantity"] for x in stock_ledger),
        "errors": errors,
    }


def revert_cutting_plan_inventory(project_id: int, ledger: dict) -> dict:
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
    return {
        "ok": len(errors) == 0,
        "restored_scraps": restored_scraps,
        "deleted_offcuts": deleted_offcuts,
        "restored_stock": restored_stock,
        "errors": errors,
    }


def _mark_scrap_unused_raw(scrap_id: int) -> bool:
    try:
        import db.database as database
        database.db.execute("UPDATE scraps SET used = 0 WHERE id = ?", (int(scrap_id),), commit=True)
        return True
    except Exception:
        return False


def _restore_stock_bar(project_id, diameter, length_mm, quantity, grade=None) -> bool:
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
