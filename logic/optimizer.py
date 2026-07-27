# logic/optimizer.py
"""
AI_Rebar.Optimizer
One-dimensional cutting stock optimization with scraps + MILP.

Fixes & upgrades:
- Column generation: master LP (continuous) to obtain duals, then final integer master
- Index-safe mapping using scaled integer lengths (no float matching)
- Robust validation
- Optional stock count limits
- Cancellation support via threading.Event (best-effort)
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Optional, Union, Any
from dataclasses import dataclass
import hashlib
import json
import sqlite3
import threading
from collections import Counter, defaultdict

import numpy as np

from config import DB_PATH, DEFAULT_REBAR_GRADE
from utils.logger import setup_logger
from db.models import ScrapModel, StockModel

logger = setup_logger("AI_Rebar.Optimizer")

try:
    from pulp import (
        LpProblem, LpMinimize, LpMaximize, LpVariable, lpSum,
        PULP_CBC_CMD, value
    )
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False

# Lazy MIP import
MIP_AVAILABLE = False
_mip_lib = None


# ----------------------------------------------------------------------
# Types / Options
# ----------------------------------------------------------------------
@dataclass
class OptimizerOptions:
    scale_mm: int = 1000
    mip_time_limit: int = 10
    allow_stock_overuse: bool = True
    max_column_generation_iters: int = 25
    verbose: bool = False


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _ensure_mip_available() -> bool:
    global MIP_AVAILABLE, _mip_lib
    if MIP_AVAILABLE and _mip_lib is not None:
        return True
    try:
        import mip as mip_lib
        _mip_lib = mip_lib
        MIP_AVAILABLE = True
        return True
    except ImportError:
        MIP_AVAILABLE = False
        _mip_lib = None
        return False


def _validate_lengths(lengths: List[float], stock_length: float) -> Optional[str]:
    if stock_length <= 0:
        return "stock_length must be > 0"
    for l in lengths:
        if l <= 0:
            return f"invalid length: {l}"
        if l > stock_length + 1e-9:
            return "some pieces exceed stock length"
    return None


def _normalize_scrap_infos(
    scrap_infos: Optional[Union[List[Tuple[int, float]], List[float]]]
) -> Tuple[List[Tuple[Union[int, str], float]], bool]:
    if not scrap_infos:
        return [], False
    if isinstance(scrap_infos[0], (int, float)):
        normalized = [(f"scrap_{i}", float(sl)) for i, sl in enumerate(scrap_infos)]
        return normalized, True
    return [(sid, float(sl)) for sid, sl in scrap_infos], False


def _ffd_bins(lengths: List[float], stock_length: float) -> List[List[float]]:
    """Simple First-Fit Decreasing fallback."""
    items = sorted(lengths, reverse=True)
    bins: List[List[float]] = []
    rem: List[float] = []
    for l in items:
        placed = False
        for i in range(len(bins)):
            if rem[i] + 1e-9 >= l:
                bins[i].append(l)
                rem[i] -= l
                placed = True
                break
        if not placed:
            bins.append([l])
            rem.append(stock_length - l)
    return bins


def _bins_to_index_bins(lengths: List[float], bins: List[List[float]], scale: int) -> List[List[int]]:
    """
    Convert bins of lengths to bins of original indices using scaled int buckets.
    This is robust and avoids float matching.
    """
    buckets: Dict[int, List[int]] = defaultdict(list)
    for idx, l in enumerate(lengths):
        buckets[int(round(l * scale))].append(idx)

    # pop from end = O(1)
    for k in buckets:
        buckets[k].sort()
        buckets[k].reverse()

    out: List[List[int]] = []
    for b in bins:
        idxs: List[int] = []
        for l in b:
            key = int(round(l * scale))
            if not buckets[key]:
                # fallback: should not happen, but don't crash
                # find closest key
                candidates = sorted(buckets.keys(), key=lambda kk: abs(kk - key))
                found = None
                for kk in candidates:
                    if buckets[kk]:
                        found = kk
                        break
                if found is None:
                    continue
                key = found
            idxs.append(buckets[key].pop())
        out.append(idxs)
    return out


# ----------------------------------------------------------------------
# Column Generation (PuLP) – correct dual extraction (LP master)
# ----------------------------------------------------------------------
def optimize_cuts(
    lengths: List[float],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    cancel_event: Optional[threading.Event] = None
) -> List[List[float]]:
    """
    Returns bins as lists of lengths (same unit as input).
    """
    opts = opts or OptimizerOptions()
    err = _validate_lengths(lengths, stock_length)
    if err:
        logger.error(f"optimize_cuts: {err}")
        return []

    if cancel_event and cancel_event.is_set():
        return []

    if not PULP_AVAILABLE:
        return _ffd_bins(lengths, stock_length)

    # work in integer mm to avoid float issues
    scale = opts.scale_mm
    pieces_mm = [int(round(l * scale)) for l in lengths]
    stock_mm = int(round(stock_length * scale))

    demand = Counter(pieces_mm)  # length_mm -> qty
    types = sorted(demand.keys())  # distinct lengths
    m = len(types)

    if m == 0:
        return []

    # initial patterns: each pattern is "all of one type"
    patterns: List[List[int]] = []
    for i, L in enumerate(types):
        max_cnt = stock_mm // L
        vec = [0] * m
        vec[i] = int(max_cnt)
        patterns.append(vec)

    # MASTER LP (continuous vars) to get duals
    prob = LpProblem("CuttingStock_MasterLP", LpMinimize)
    p_vars = [LpVariable(f"p_{j}", lowBound=0, cat="Continuous") for j in range(len(patterns))]
    prob += lpSum(p_vars)

    constr_names: List[str] = []
    for i, L in enumerate(types):
        name = f"demand_{i}"
        prob += lpSum(patterns[j][i] * p_vars[j] for j in range(len(patterns))) >= demand[L], name
        constr_names.append(name)

    # Column generation loop
    for _it in range(opts.max_column_generation_iters):
        if cancel_event and cancel_event.is_set():
            return []

        prob.solve(PULP_CBC_CMD(msg=1 if opts.verbose else 0, timeLimit=max(1, opts.mip_time_limit)))

        # duals
        dual = []
        for cname in constr_names:
            c = prob.constraints.get(cname)
            dual.append(float(getattr(c, "pi", 0.0) or 0.0))

        # KNAPSACK: maximize sum(dual_i * x_i) s.t. sum(L_i * x_i) <= stock
        sub = LpProblem("CuttingStock_Knapsack", LpMaximize)
        x = [LpVariable(f"x_{i}", lowBound=0, cat="Integer") for i in range(m)]
        sub += lpSum(dual[i] * x[i] for i in range(m))
        sub += lpSum(types[i] * x[i] for i in range(m)) <= stock_mm
        sub.solve(PULP_CBC_CMD(msg=0, timeLimit=max(1, opts.mip_time_limit)))

        sub_val = value(sub.objective) if sub.objective is not None else None
        if sub_val is None:
            break

        # reduced cost for master objective "min sum p" is: 1 - sub_val
        if sub_val <= 1.0 + 1e-6:
            break

        new_pat = [int(value(x[i]) or 0) for i in range(m)]
        if sum(new_pat) <= 0:
            break

        patterns.append(new_pat)
        pv = LpVariable(f"p_{len(patterns)-1}", lowBound=0, cat="Continuous")
        p_vars.append(pv)

        # add constraints incrementally (do not rebuild the entire model)
        for i in range(m):
            prob.constraints[constr_names[i]] += new_pat[i] * pv
        prob.objective += pv

    # FINAL INTEGER MASTER
    master_int = LpProblem("CuttingStock_MasterINT", LpMinimize)
    z = [LpVariable(f"Z_{j}", lowBound=0, cat="Integer") for j in range(len(patterns))]
    master_int += lpSum(z)

    for i, L in enumerate(types):
        master_int += lpSum(patterns[j][i] * z[j] for j in range(len(patterns))) >= demand[L], f"dem_{i}"

    if cancel_event and cancel_event.is_set():
        return []

    master_int.solve(PULP_CBC_CMD(msg=1 if opts.verbose else 0, timeLimit=max(1, opts.mip_time_limit)))

    # Extract bins
    result_bins: List[List[float]] = []
    for j, pat in enumerate(patterns):
        cnt = int(value(z[j]) or 0)
        if cnt <= 0:
            continue
        for _ in range(cnt):
            cuts = []
            for i, k in enumerate(pat):
                if k > 0:
                    cuts.extend([types[i] / scale] * int(k))
            result_bins.append(cuts)

    # If solver failed and returned nothing, fallback
    if not result_bins:
        return _ffd_bins(lengths, stock_length)

    return result_bins


# ----------------------------------------------------------------------
# MILP (python-mip) – index-based assignment
# ----------------------------------------------------------------------
def optimize_cuts_mip_indexed(
    lengths: List[float],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    stock_count_limit: Optional[int] = None,
    cancel_event: Optional[threading.Event] = None
) -> List[List[int]]:

    opts = opts or OptimizerOptions()
    err = _validate_lengths(lengths, stock_length)
    if err:
        logger.error(f"optimize_cuts_mip_indexed: {err}")
        return []

    if cancel_event and cancel_event.is_set():
        return []

    if not _ensure_mip_available():
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, opts.scale_mm)

    scale = opts.scale_mm
    pieces_mm = [int(round(l * scale)) for l in lengths]
    stock_mm = int(round(stock_length * scale))
    n = len(pieces_mm)

    total_length = sum(pieces_mm)
    lower_bound = int(np.ceil(total_length / stock_mm))
    max_bins = min(n, max(1, lower_bound + 8))

    if stock_count_limit is not None:
        max_bins = min(max_bins, stock_count_limit)

    # large instance -> use column generation + robust indexing
    if n > 140:
        logger.info("Large instance → using column generation fallback")
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, scale)

    mip = _mip_lib
    model = mip.Model("RebarCutting_MIP")
    model.verbose = 1 if opts.verbose else 0

    x = [[model.add_var(var_type=mip.BINARY) for _ in range(max_bins)] for _ in range(n)]
    y = [model.add_var(var_type=mip.BINARY) for _ in range(max_bins)]
    waste = [model.add_var(lb=0, var_type=mip.INTEGER) for _ in range(max_bins)]

    model.objective = mip.minimize(mip.xsum(waste[j] + 0.0001 * y[j] for j in range(max_bins)))

    for i in range(n):
        model += mip.xsum(x[i][j] for j in range(max_bins)) == 1

    for j in range(max_bins):
        model += mip.xsum(pieces_mm[i] * x[i][j] for i in range(n)) + waste[j] == stock_mm * y[j]

    for j in range(max_bins - 1):
        model += y[j] >= y[j + 1]

    if stock_count_limit is not None and not opts.allow_stock_overuse:
        model += mip.xsum(y[j] for j in range(max_bins)) <= stock_count_limit

    status = model.optimize(max_seconds=opts.mip_time_limit)

    if cancel_event and cancel_event.is_set():
        return []

    if status not in (mip.OptimizationStatus.OPTIMAL, mip.OptimizationStatus.FEASIBLE):
        logger.warning("MIP failed → fallback to column generation")
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, scale)

    bins_idx: List[List[int]] = []
    for j in range(max_bins):
        if y[j].x >= 0.99:
            bins_idx.append([i for i in range(n) if x[i][j].x >= 0.99])

    return bins_idx


# ----------------------------------------------------------------------
# Scrap usage (Best Fit Decreasing) + MILP on remainder
# ----------------------------------------------------------------------
def _best_fit_decreasing(
    items: List[Tuple[float, dict]],
    scrap_infos: Union[List[Tuple[Union[int, str], float]], List[float]]
) -> Tuple[List[Dict], List[Tuple[float, dict]]]:
    scrap_infos, temp_ids_used = _normalize_scrap_infos(scrap_infos)
    if not scrap_infos:
        return [], items

    items_with_id = [(i, l, lbl) for i, (l, lbl) in enumerate(items)]
    items_with_id.sort(key=lambda x: x[1], reverse=True)

    scrap_pool = sorted(scrap_infos, key=lambda x: x[1])  # ascending
    used_on_scrap = {sid: [] for sid, _ in scrap_infos}
    remaining = []

    for _, length, label in items_with_id:
        best_scrap_id = None
        min_waste = float("inf")

        for scrap_id, sl in scrap_pool:
            used_len = sum(item[0] for item in used_on_scrap[scrap_id])
            if used_len + length <= sl + 1e-9:
                waste = sl - (used_len + length)
                if waste < min_waste:
                    min_waste = waste
                    best_scrap_id = scrap_id

        if best_scrap_id is not None:
            used_on_scrap[best_scrap_id].append((length, label))
        else:
            remaining.append((length, label))

    plans = []
    for scrap_id, cut_list in used_on_scrap.items():
        if cut_list:
            scrap_length = next(sl for sid, sl in scrap_infos if sid == scrap_id)
            plan = {"bin": cut_list, "bar_length": scrap_length}
            if not (temp_ids_used and isinstance(scrap_id, str) and scrap_id.startswith("scrap_")):
                plan["scrap_id"] = scrap_id
            plans.append(plan)

    return plans, remaining


def optimize_labeled_cuts(
    items: List[Tuple[float, dict]],
    stock_length: float,
    scrap_infos: Optional[Union[List[Tuple[int, float]], List[float]]] = None,
    opts: Optional[OptimizerOptions] = None,
    stock_count_limit: Optional[int] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[List[Dict], List[float]]:

    opts = opts or OptimizerOptions()

    if not items:
        return [], []

    err = _validate_lengths([l for l, _ in items], stock_length)
    if err:
        logger.error(f"optimize_labeled_cuts: {err}")
        return [], []

    if cancel_event and cancel_event.is_set():
        return [], []

    if scrap_infos:
        scrap_plans, remaining_items = _best_fit_decreasing(items, scrap_infos)
    else:
        scrap_plans, remaining_items = [], items

    new_scraps: List[float] = []
    stock_seq_counter = 1

    if remaining_items:
        remaining_lengths = [l for l, _ in remaining_items]
        bins_idx = optimize_cuts_mip_indexed(
            remaining_lengths,
            stock_length,
            opts=opts,
            stock_count_limit=stock_count_limit,
            cancel_event=cancel_event
        )

        if cancel_event and cancel_event.is_set():
            return scrap_plans, []

        for b in bins_idx:
            bin_items = [remaining_items[i] for i in b]
            waste = stock_length - sum(l for l, _ in bin_items)
            if waste > 1e-6:
                new_scraps.append(round(waste, 6))

            scrap_plans.append({
                "bin": bin_items,
                "bar_length": stock_length,
                "scrap_id": None,
                "stock_seq": stock_seq_counter
            })
            stock_seq_counter += 1

    return scrap_plans, new_scraps


# ----------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------
def get_scrap_infos_for_dia_grade(project_id, diameter, grade=DEFAULT_REBAR_GRADE) -> List[Tuple[int, float]]:
    rows = ScrapModel.get_available_scraps(project_id, diameter, grade)
    return [(row[0], row[1] / 1000.0) for row in rows]


def get_available_stock_bars(project_id, diameter, grade=DEFAULT_REBAR_GRADE) -> Dict[float, int]:
    rows = StockModel.get_for_diameter(project_id, diameter, grade)

    stock: Dict[float, int] = {}
    for row in rows:
        # robust index handling:
        # - format A: (id, project_id, diameter, length_mm, qty, grade)
        # - format B: (id, diameter, length_mm, qty, grade) or similar
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


def optimize_with_scraps_and_stock(
    project_id: int,
    diameter: float,
    grade: str,
    items: List[Tuple[float, dict]],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    cancel_event: Optional[threading.Event] = None
) -> Tuple[List[Dict], List[float], Dict[float, int]]:

    opts = opts or OptimizerOptions()
    scrap_infos = get_scrap_infos_for_dia_grade(project_id, diameter, grade)
    stock_counts = get_available_stock_bars(project_id, diameter, grade)

    # float-safe match
    stock_limit = None
    for sl, qty in stock_counts.items():
        if abs(sl - stock_length) < 1e-6:
            stock_limit = qty
            break

    plans, new_scraps = optimize_labeled_cuts(
        items,
        stock_length,
        scrap_infos,
        opts=opts,
        stock_count_limit=stock_limit,
        cancel_event=cancel_event
    )

    full_bars_used = sum(
        1 for p in plans
        if p.get("scrap_id") is None and p.get("bar_length", 0) >= stock_length - 1e-6
    )
    stock_usage = {stock_length: full_bars_used}
    return plans, new_scraps, stock_usage


# ----------------------------------------------------------------------
# Hashing / persistence
# ----------------------------------------------------------------------
def compute_plan_data_hash(project_id, listofer_filter, stock_length, data_by_key):
    hasher = hashlib.sha256()
    hasher.update(f"{project_id}|{listofer_filter}|{stock_length}".encode())

    for (dia, grade), items in sorted(data_by_key.items(), key=lambda x: (x[0][0], x[0][1])):
        sorted_items = sorted(items, key=lambda x: (x[0], json.dumps(x[1], sort_keys=True)))
        for length, label in sorted_items:
            label_json = json.dumps(label, sort_keys=True)
            hasher.update(f"{dia}|{grade}|{length}|{label_json}".encode())
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
            "(project_id, listofer_number, rebar_id, source_type, source_id) "
            "VALUES (?, ?, ?, ?, ?)",
            rows_to_insert
        )

    conn.commit()
    conn.close()
    logger.info(f"Cutting assignments stored for {len(rows_to_insert)} rebars.")