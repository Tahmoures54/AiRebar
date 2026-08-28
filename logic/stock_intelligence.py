# logic/stock_intelligence.py
"""Demand vs stock/scrap analysis and order suggestions."""
from __future__ import annotations

from typing import Dict, Tuple

from db.models import RebarModel, ScrapModel, StockModel
from config import DEFAULT_REBAR_GRADE
from utils.logger import setup_logger
from logic.inventory_core import _parse_stock_row

logger = setup_logger("RebarAgent.StockIntel")


def _rebar_demand_by_key(project_id: int) -> Dict[Tuple[float, str], Dict[str, float]]:
    from db.models import RebarModel
    from shapes.definitions import default_shape_registry
    from logic.calculator import calculate_total_weight
    import json

    demand: Dict[Tuple[float, str], Dict[str, float]] = {}
    try:
        rows = RebarModel.get_for_project(project_id)
    except Exception as e:
        logger.error("Demand query failed: %s", e)
        return demand

    for row in rows or []:
        try:
            diameter = float(row[4])
            shape_name = (row[5] or "00").strip()
            dims_raw = row[6]
            qty = int(row[7] or 0)
            grade = str(row[12] if len(row) > 12 else DEFAULT_REBAR_GRADE) or DEFAULT_REBAR_GRADE
            if qty <= 0 or diameter <= 0:
                continue
            if isinstance(dims_raw, str):
                try:
                    dims = json.loads(dims_raw) if dims_raw else {}
                except Exception:
                    dims = {}
            elif isinstance(dims_raw, dict):
                dims = dims_raw
            else:
                dims = {}
            try:
                unit_len = float(default_shape_registry.calc_shape_length(shape_name, dims, diameter) or 0)
            except Exception:
                unit_len = 0.0
            total_len = unit_len * qty
            key = (diameter, grade)
            bucket = demand.setdefault(key, {"length_mm": 0.0, "pieces": 0.0, "weight_kg": 0.0})
            bucket["length_mm"] += total_len
            bucket["pieces"] += qty
            if unit_len > 0:
                bucket["weight_kg"] += calculate_total_weight(diameter, unit_len, qty)
        except Exception as e:
            logger.debug("Skip rebar row in demand: %s", e)
    return demand


def _stock_supply_by_key(project_id: int) -> Dict[Tuple[float, str], float]:
    supply: Dict[Tuple[float, str], float] = {}
    try:
        rows = StockModel.get_all(project_id=project_id)
    except Exception:
        rows = []
    for row in rows or []:
        try:
            dia = float(row[2])
            length_mm = float(row[3])
            qty = int(row[4])
            grade = str(row[5] if len(row) > 5 and row[5] else DEFAULT_REBAR_GRADE)
            if qty <= 0:
                continue
            key = (dia, grade)
            supply[key] = supply.get(key, 0.0) + length_mm * qty
        except Exception:
            continue
    return supply


def _scrap_supply_by_key(project_id: int) -> Dict[Tuple[float, str], float]:
    supply: Dict[Tuple[float, str], float] = {}
    try:
        rows = ScrapModel.get_all_scraps(project_id)
    except Exception:
        rows = []
    for row in rows or []:
        try:
            dia = float(row[2])
            length_mm = float(row[3])
            grade = str(row[4] if len(row) > 4 and row[4] else DEFAULT_REBAR_GRADE)
            used = 0
            if len(row) > 7:
                used = int(row[7] or 0)
            elif len(row) > 6 and str(row[6]) in ("1", "True", "true"):
                used = 1
            if used:
                continue
            key = (dia, grade)
            supply[key] = supply.get(key, 0.0) + length_mm
        except Exception:
            continue
    return supply


def analyze_stock_intelligence(
    project_id: int,
    preferred_bar_mm: float = 12000.0,
    waste_factor: float = 1.05,
) -> Dict:
    demand = _rebar_demand_by_key(project_id)
    stock = _stock_supply_by_key(project_id)
    scrap = _scrap_supply_by_key(project_id)
    lines = []
    shortages = []
    surplus = []
    order_suggestions = []
    all_keys = set(demand) | set(stock) | set(scrap)
    total_short_mm = 0.0
    total_demand_mm = 0.0
    total_cover_mm = 0.0
    for key in sorted(all_keys, key=lambda k: (k[0], k[1])):
        dia, grade = key
        d = demand.get(key, {}).get("length_mm", 0.0) * waste_factor
        s = stock.get(key, 0.0)
        c = scrap.get(key, 0.0)
        cover = s + c
        total_demand_mm += demand.get(key, {}).get("length_mm", 0.0)
        total_cover_mm += cover
        gap = d - cover
        if gap > 1.0:
            bars_needed = int((gap + preferred_bar_mm - 1) // preferred_bar_mm) if preferred_bar_mm > 0 else 0
            shortages.append({
                "diameter": dia, "grade": grade, "demand_mm": d, "stock_mm": s,
                "scrap_mm": c, "gap_mm": gap, "bars_to_order": bars_needed,
                "order_length_mm": preferred_bar_mm,
            })
            total_short_mm += gap
            order_suggestions.append(
                f"Ø{dia:g} {grade}: short {gap/1000:.1f} m → order ~{bars_needed}×{preferred_bar_mm/1000:.0f}m bars"
            )
            lines.append(
                f"⚠ Ø{dia:g} mm / {grade}: need {d/1000:.1f} m, have stock {s/1000:.1f} m + scrap {c/1000:.1f} m (gap {gap/1000:.1f} m)"
            )
        elif cover > d + preferred_bar_mm and d > 0:
            extra = cover - d
            surplus.append({"diameter": dia, "grade": grade, "extra_mm": extra})
            lines.append(f"✓ Ø{dia:g} mm / {grade}: OK — surplus ~{extra/1000:.1f} m (stock+scrap)")
        elif d > 0:
            lines.append(f"✓ Ø{dia:g} mm / {grade}: covered (need {d/1000:.1f} m, have {cover/1000:.1f} m)")
        elif cover > 0 and d <= 0:
            lines.append(f"• Ø{dia:g} mm / {grade}: stock/scrap on hand {cover/1000:.1f} m (no BBS demand yet)")
    if not demand:
        summary = "No BBS demand in this project yet. Add rebars to get procurement suggestions."
    elif not shortages:
        summary = (
            f"Stock looks sufficient for current BBS "
            f"(demand {total_demand_mm/1000:.1f} m, stock+scrap {total_cover_mm/1000:.1f} m, "
            f"incl. {int((waste_factor-1)*100)}% waste buffer)."
        )
    else:
        summary = (
            f"{len(shortages)} diameter/grade group(s) short — "
            f"about {total_short_mm/1000:.1f} m missing (with waste buffer)."
        )
    return {
        "summary": summary, "lines": lines, "shortages": shortages, "surplus": surplus,
        "order_suggestions": order_suggestions, "total_demand_mm": total_demand_mm,
        "total_cover_mm": total_cover_mm, "waste_factor": waste_factor, "preferred_bar_mm": preferred_bar_mm,
    }


def format_stock_intelligence_report(analysis: Dict) -> str:
    parts = [analysis.get("summary", ""), ""]
    if analysis.get("order_suggestions"):
        parts.append("Recommended orders:")
        parts.extend(f"  • {s}" for s in analysis["order_suggestions"])
        parts.append("")
    if analysis.get("lines"):
        parts.append("Detail:")
        parts.extend(analysis["lines"])
    return "\n".join(parts).strip()
