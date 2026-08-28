# logic/project_kpi.py
"""Project-level KPIs: tonnage, length by diameter, rough bar estimate."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict

from db.models import RebarModel
from logic.calculator import calculate_weight
from shapes.definitions import default_shape_registry
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.KPI")


def _bar_unit_length_mm(shape_name, dims_raw, diameter) -> float:
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
        return float(
            default_shape_registry.calc_shape_length(shape_name or "00", dims, float(diameter)) or 0
        )
    except Exception:
        return 0.0


def compute_project_kpi(project_id: int, stock_bar_m: float = 12.0) -> Dict[str, Any]:
    rows = list(RebarModel.get_for_project(project_id) or [])
    by_dia: Dict[float, Dict[str, float]] = defaultdict(lambda: {"qty": 0, "len_m": 0.0, "weight_kg": 0.0})
    total_len = 0.0
    total_w = 0.0
    line_count = 0

    for row in rows:
        try:
            # row layout depends on model; try flexible indices
            dia = float(row[4] if len(row) > 4 else row[3])
            shape = row[5] if len(row) > 5 else "00"
            dims = row[6] if len(row) > 6 else "{}"
            qty = int(row[7] if len(row) > 7 else 1)
            unit = _bar_unit_length_mm(shape, dims, dia)
            lm = (unit / 1000.0) * max(0, qty)
            _, w1 = calculate_weight(dia, unit) if unit > 0 else (0, 0)
            wk = float(w1) * max(0, qty)
            by_dia[dia]["qty"] += qty
            by_dia[dia]["len_m"] += lm
            by_dia[dia]["weight_kg"] += wk
            total_len += lm
            total_w += wk
            line_count += 1
        except Exception as e:
            logger.debug("kpi row: %s", e)

    est_bars = int((total_len / stock_bar_m) + 0.999) if stock_bar_m > 0 and total_len > 0 else 0
    return {
        "line_count": line_count,
        "total_length_m": total_len,
        "total_weight_kg": total_w,
        "by_diameter": dict(by_dia),
        "est_12m_bars": est_bars,
        "stock_bar_m": stock_bar_m,
    }


def format_kpi_report(kpi: Dict[str, Any]) -> str:
    lines = [
        f"Lines: {kpi.get('line_count', 0)}",
        f"Total length: {kpi.get('total_length_m', 0):.2f} m",
        f"Total weight: {kpi.get('total_weight_kg', 0):.1f} kg",
        f"Rough estimate (@{kpi.get('stock_bar_m', 12):g} m bars): {kpi.get('est_12m_bars', 0)} bars",
        "",
        "By diameter:",
    ]
    for dia, d in sorted((kpi.get("by_diameter") or {}).items()):
        lines.append(
            f"  Ø{dia:g}: qty={int(d.get('qty', 0))}  len={d.get('len_m', 0):.1f} m  "
            f"w={d.get('weight_kg', 0):.1f} kg"
        )
    return "\n".join(lines)
