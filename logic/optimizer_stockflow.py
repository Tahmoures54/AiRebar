# logic/optimizer_stockflow.py
"""Multi-stock packing and scrap+stock orchestration."""
from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any
from collections import defaultdict
import threading
import hashlib
import json
import sqlite3

from config import DEFAULT_REBAR_GRADE, DB_PATH
from utils.logger import setup_logger
from logic.optimizer_options import OptimizerOptions
from logic.optimizer_packing import (
    _best_fit_decreasing, _pack_one_bar_ffd, _pack_all_single_stock,
)
from logic.optimizer_metrics import (
    get_scrap_infos_for_dia_grade, get_available_stock_bars,
)

logger = setup_logger("RebarAgent.OptimizerStockflow")


def optimize_remaining_multi_stock(
    items: List[Tuple[float, dict]],
    stock_lengths_qty: Dict[float, int],
    default_stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[List[Dict], List[float]]:
    opts = opts or OptimizerOptions()
    if not items:
        return [], []
    pool: Dict[float, int] = {}
    for L, q in (stock_lengths_qty or {}).items():
        if L and q and q > 0:
            pool[float(L)] = int(q)
    if not pool:
        plans, scraps = _pack_all_single_stock(items, default_stock_length, opts, cancel_event, stock_limit=None)
        return plans, scraps
    remaining = sorted(items, key=lambda x: x[0], reverse=True)
    plans: List[Dict] = []
    new_scraps: List[float] = []
    seq = 1
    kerf = opts.kerf_m or 0.0
    min_scrap = opts.min_usable_scrap_m or 0.0
    guard = 0
    max_guard = max(500, len(items) * 3)
    while remaining and guard < max_guard:
        guard += 1
        if cancel_event and cancel_event.is_set():
            break
        longest = remaining[0][0]
        candidates = [L for L, q in pool.items() if q > 0 and L + 1e-9 >= longest]
        if not candidates:
            if opts.allow_stock_overuse and default_stock_length >= longest - 1e-9:
                candidates = [float(default_stock_length)]
                pool.setdefault(float(default_stock_length), 10**9)
            else:
                logger.warning("Cannot place remaining pieces – no stock length fits")
                break
        best_L = best_packed = best_still = None
        best_score = -1.0
        for L in candidates:
            packed, still, waste = _pack_one_bar_ffd(remaining, L, kerf)
            if not packed:
                continue
            cut = sum(x[0] for x in packed)
            fill = cut / L if L > 0 else 0
            score = fill * 1000 - L * 0.001
            if score > best_score:
                best_score, best_L, best_packed, best_still = score, L, packed, still
        if not best_packed or best_L is None:
            break
        plans.append({"bin": best_packed, "bar_length": best_L, "scrap_id": None, "stock_seq": seq})
        seq += 1
        cut = sum(x[0] for x in best_packed)
        waste = max(0.0, best_L - cut)
        if waste >= min_scrap - 1e-9 and waste > 1e-6:
            new_scraps.append(round(waste, 6))
        remaining = best_still if best_still is not None else []
        if best_L in pool:
            pool[best_L] = max(0, pool[best_L] - 1)
    return plans, new_scraps


def optimize_with_scraps_and_stock(
    project_id: int,
    diameter: float,
    grade: str,
    items: List[Tuple[float, dict]],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[List[Dict], List[float], Dict[float, int]]:
    opts = opts or OptimizerOptions()
    scrap_infos = get_scrap_infos_for_dia_grade(project_id, diameter, grade)
    stock_counts = get_available_stock_bars(project_id, diameter, grade)
    scrap_plans, remaining = _best_fit_decreasing(items, scrap_infos)
    use_multi = bool(opts.use_multi_stock) and bool(stock_counts)
    if use_multi and remaining:
        stock_map = dict(stock_counts)
        if opts.allow_stock_overuse:
            stock_map.setdefault(float(stock_length), stock_map.get(float(stock_length), 0))
            if stock_map.get(float(stock_length), 0) <= 0:
                stock_map[float(stock_length)] = 10**6
        stock_plans, new_scraps = optimize_remaining_multi_stock(
            remaining, stock_map, stock_length, opts, cancel_event
        )
    else:
        stock_limit = None
        for sl, qty in stock_counts.items():
            if abs(sl - stock_length) < 1e-6:
                stock_limit = qty
                break
        stock_plans, new_scraps = _pack_all_single_stock(
            remaining, stock_length, opts, cancel_event, stock_limit
        )
    plans = scrap_plans + stock_plans
    usage: Dict[float, int] = defaultdict(int)
    for p in stock_plans:
        bl = float(p.get("bar_length") or stock_length)
        usage[round(bl, 6)] += 1
    return plans, new_scraps, dict(usage)


def compute_plan_data_hash(project_id, listofer_filter, stock_length, data_by_key):
    hasher = hashlib.sha256()
    hasher.update(f"{project_id}|{listofer_filter}|{stock_length}".encode())
    for (dia, grade), items in sorted(data_by_key.items(), key=lambda x: (x[0][0], x[0][1])):
        sorted_items = sorted(items, key=lambda x: (x[0], json.dumps(x[1], sort_keys=True)))
        for length, label in sorted_items:
            hasher.update(f"{dia}|{grade}|{length}|{json.dumps(label, sort_keys=True)}".encode())
    return hasher.hexdigest()


def store_cutting_assignments(project_id, listofer_number, plans, rebar_id_map):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows_to_insert = []
    for plan in plans:
        source_type = "scrap" if plan.get("scrap_id") is not None else "stock"
        source_id = plan.get("stock_seq", 0) if source_type == "stock" else plan["scrap_id"]
        for _, label in plan["bin"]:
            item_idx = label.get("item_idx")
            if item_idx is None:
                continue
            rebar_id = rebar_id_map.get(item_idx)
            if rebar_id is None:
                continue
            rows_to_insert.append((project_id, listofer_number, rebar_id, source_type, source_id))
    if rows_to_insert:
        cur.executemany(
            "INSERT OR REPLACE INTO cutting_assignments "
            "(project_id, listofer_number, rebar_id, source_type, source_id) VALUES (?, ?, ?, ?, ?)",
            rows_to_insert,
        )
    conn.commit()
    conn.close()
    logger.info("Cutting assignments stored for %s rebars.", len(rows_to_insert))
