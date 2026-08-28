# logic/optimizer_metrics.py
"""Plan metrics and stock/scrap queries for optimizer."""
from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from config import DEFAULT_REBAR_GRADE
from db.models import ScrapModel, StockModel
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.OptimizerMetrics")


def get_scrap_infos_for_dia_grade(project_id, diameter, grade=DEFAULT_REBAR_GRADE) -> List[Tuple[int, float]]:
    rows = ScrapModel.get_available_scraps(project_id, diameter, grade)
    return [(row[0], row[1] / 1000.0) for row in rows]


def get_available_stock_bars(project_id, diameter, grade=DEFAULT_REBAR_GRADE) -> Dict[float, int]:
    rows = StockModel.get_for_diameter(project_id, diameter, grade)
    stock: Dict[float, int] = {}
    for row in rows:
        length_mm = None
        qty = None
        if len(row) >= 6:
            length_mm = row[3]
            qty = row[4]
        elif len(row) >= 4:
            length_mm = row[2]
            qty = row[3]
        if length_mm is None or qty is None:
            continue
        try:
            qty = int(qty)
            if qty <= 0:
                continue
            bar_len_m = float(length_mm) / 1000.0
            key = round(bar_len_m, 6)
            stock[key] = stock.get(key, 0) + qty
        except Exception:
            continue
    return stock


def _effective_piece_length(length: float, kerf_m: float) -> float:
    return float(length) + max(0.0, float(kerf_m or 0.0))


def compute_plan_metrics(plans: List[Dict], demand_length_sum: float = 0.0) -> Dict[str, Any]:
    bars = 0
    total_bar_len = 0.0
    total_cut = 0.0
    scrap_bars = 0
    stock_bars = 0
    for p in plans or []:
        bars += 1
        bl = float(p.get("bar_length") or 0)
        total_bar_len += bl
        cut = sum(float(x[0]) for x in (p.get("bin") or []) if isinstance(x, (list, tuple)))
        total_cut += cut
        if p.get("scrap_id") is not None:
            scrap_bars += 1
        else:
            stock_bars += 1
    waste = max(0.0, total_bar_len - total_cut)
    util = (total_cut / total_bar_len * 100.0) if total_bar_len > 1e-9 else 0.0
    waste_pct = (waste / total_bar_len * 100.0) if total_bar_len > 1e-9 else 0.0
    return {
        "bars": bars,
        "stock_bars": stock_bars,
        "scrap_bars": scrap_bars,
        "total_bar_m": total_bar_len,
        "total_cut_m": total_cut,
        "waste_m": waste,
        "utilization_pct": util,
        "waste_pct": waste_pct,
        "demand_m": demand_length_sum,
    }
