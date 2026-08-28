# logic/agent_brain.py
"""
Unified intelligence layer for RebarAgent.

Rule-based (transparent) agent: scores project health and emits prioritized actions.
Not a black-box ML model — recommendations are explainable for engineering trust.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from config import DEFAULT_REBAR_GRADE
from db.models import RebarModel, ListoferModel, ScrapModel, StockModel
from logic.inventory import analyze_stock_intelligence
from logic.project_kpi import compute_project_kpi
from shapes.definitions import default_shape_registry
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.AgentBrain")


@dataclass
class AgentAction:
    priority: int
    code: str
    title: str
    detail: str
    action: str
    severity: str = "info"


@dataclass
class AgentReport:
    health_score: int
    health_label: str
    headline: str
    actions: List[AgentAction] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    waste_hints: List[str] = field(default_factory=list)

    def top_tip(self) -> str:
        if self.actions:
            a = self.actions[0]
            return f"{a.title} — {a.detail}"
        return self.headline


def _unit_len(shape_name, dims_raw, diameter) -> float:
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


def analyze_project(project_id: int) -> AgentReport:
    actions: List[AgentAction] = []
    waste_hints: List[str] = []
    stats: Dict[str, Any] = {}

    rows = []
    try:
        rows = list(RebarModel.get_for_project(project_id) or [])
    except Exception as e:
        logger.error("rebars: %s", e)

    try:
        lf_count = len(ListoferModel.get_numbers(project_id) or [])
    except Exception:
        lf_count = 0

    lengths_m: List[float] = []
    by_dia = defaultdict(lambda: {"n": 0, "len_m": 0.0})
    zero_len = 0
    for row in rows:
        try:
            dia = float(row[4])
            shape = row[5]
            dims = row[6]
            qty = int(row[7] or 0)
            unit = _unit_len(shape, dims, dia)
            if unit <= 0:
                zero_len += max(1, qty)
            else:
                for _ in range(max(0, qty)):
                    lengths_m.append(unit / 1000.0)
                by_dia[dia]["n"] += qty
                by_dia[dia]["len_m"] += (unit / 1000.0) * qty
        except Exception:
            continue

    stats["line_count"] = len(rows)
    stats["listofer_count"] = lf_count
    stats["piece_count"] = len(lengths_m)
    stats["total_length_m"] = sum(lengths_m)
    stats["zero_length_pieces"] = zero_len

    stock_analysis = {}
    try:
        stock_analysis = analyze_stock_intelligence(project_id, preferred_bar_mm=12000.0)
        stats["stock_summary"] = stock_analysis.get("summary")
        stats["shortages"] = len(stock_analysis.get("shortages") or [])
    except Exception as e:
        logger.debug("stock intel: %s", e)
        stats["shortages"] = 0

    scrap_count = 0
    scrap_len_m = 0.0
    try:
        for s in ScrapModel.get_all_scraps(project_id) or []:
            used = s[5] if len(s) > 5 else 0
            if used in (1, True, "1"):
                continue
            scrap_count += 1
            try:
                scrap_len_m += float(s[2]) / 1000.0
            except Exception:
                pass
    except Exception:
        pass
    stats["scrap_pieces"] = scrap_count
    stats["scrap_length_m"] = scrap_len_m

    if not rows:
        actions.append(AgentAction(1, "empty_project", "Add your first positions", "The project has no rebars yet. Start with New Pos (Ctrl+N).", "add_pos", "critical"))
    else:
        if zero_len > 0:
            actions.append(AgentAction(1, "zero_length", "Fix shapes with zero cutting length", f"{zero_len} piece(s) have no computable length — check shape/dimensions.", "add_pos", "critical"))
        shortages = stock_analysis.get("shortages") or []
        if shortages:
            top = shortages[0]
            actions.append(AgentAction(2, "stock_short", "Stock may be short for current BBS", f"Ø{top['diameter']:g} {top['grade']}: gap ~{top['gap_mm']/1000:.1f} m (~{top['bars_to_order']}×12m bars). Open Stock Manager or Smart Advisor.", "stock", "warn"))
            for s in stock_analysis.get("order_suggestions") or []:
                waste_hints.append(s)
        if lengths_m and scrap_count == 0:
            actions.append(AgentAction(3, "no_scrap_bank", "Scrap bank is empty", "After cutting, confirm plans to bank offcuts — or add usable scraps manually.", "scrap", "info"))
        elif scrap_count > 0 and lengths_m:
            actions.append(AgentAction(3, "use_scraps", "Reuse available scraps in cutting", f"{scrap_count} scrap piece(s) (~{scrap_len_m:.1f} m). Run Cutting Plan with stock limits on.", "cutting", "info"))
        if lengths_m:
            long_n = sum(1 for L in lengths_m if L > 6.0)
            ratio = long_n / max(1, len(lengths_m))
            if ratio > 0.4:
                actions.append(AgentAction(4, "long_bars", "Many long pieces — expect more bars / less nesting", f"{long_n}/{len(lengths_m)} pieces are longer than 6 m. Multi-length stock (6+12m) can still help shorter companions.", "cutting", "info"))
                waste_hints.append("Prefer multi-length stock packing when short and long pieces mix.")
            short_n = sum(1 for L in lengths_m if L < 1.0)
            if short_n > len(lengths_m) * 0.25:
                waste_hints.append(f"{short_n} pieces under 1 m — good candidates to fill bars; enable scrap reuse.")
        if lengths_m and not shortages:
            actions.append(AgentAction(5, "run_cutting", "Run an optimized cutting plan", "Stock looks adequate. Generate a draft plan, check utilization %, then Confirm.", "cutting", "info"))
        if len(by_dia) >= 1:
            top_dia = max(by_dia.items(), key=lambda x: x[1]["len_m"])
            stats["dominant_diameter"] = top_dia[0]
            stats["dominant_length_m"] = top_dia[1]["len_m"]

    score = 100
    if not rows:
        score = 15
    else:
        if zero_len:
            score -= min(40, zero_len * 2)
        if stats.get("shortages", 0):
            score -= min(25, 10 + stats["shortages"] * 5)
        if scrap_count == 0 and lengths_m:
            score -= 5
        if lengths_m and stats.get("shortages", 0) == 0:
            score = min(100, score + 5)
    score = max(0, min(100, int(score)))

    if score >= 80:
        label, headline = "Strong", "Project data looks healthy — good time to optimize cutting."
    elif score >= 55:
        label, headline = "Fair", "A few improvements will reduce waste and buying risk."
    elif score >= 30:
        label, headline = "Needs attention", "Address the top actions before bulk cutting."
    else:
        label, headline = "Getting started", "Add positions to unlock smart cutting and stock advice."

    actions.sort(key=lambda a: (a.priority, a.severity != "critical"))
    return AgentReport(health_score=score, health_label=label, headline=headline, actions=actions[:8], stats=stats, waste_hints=waste_hints[:6])


def format_agent_report(report: AgentReport) -> str:
    lines = [f"Health: {report.health_score}/100 ({report.health_label})", report.headline, "", "Priority actions:"]
    if not report.actions:
        lines.append("  • None — looking good.")
    for a in report.actions:
        flag = {"critical": "!", "warn": "*", "info": "-"}.get(a.severity, "-")
        lines.append(f"  {flag} [{a.priority}] {a.title}")
        lines.append(f"      {a.detail}")
    if report.waste_hints:
        lines.extend(["", "Hints:"])
        for h in report.waste_hints:
            lines.append(f"  • {h}")
    st = report.stats
    lines.extend(["", f"Stats: {st.get('line_count', 0)} lines · {st.get('piece_count', 0)} pieces · {st.get('total_length_m', 0):.1f} m · scraps {st.get('scrap_pieces', 0)}"])
    return "\n".join(lines)
