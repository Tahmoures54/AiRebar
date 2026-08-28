# logic/optimizer_mip.py
"""MIP indexed packing and labeled cuts."""
from __future__ import annotations

import threading
import numpy as np
from typing import List, Optional, Tuple, Dict, Any, Union

from utils.logger import setup_logger
from logic.optimizer_options import OptimizerOptions
from logic.optimizer_packing import (
    _ensure_mip_available, _validate_lengths, _bins_to_index_bins,
    _best_fit_decreasing, _pack_all_single_stock,
)
from logic.optimizer_cg import optimize_cuts

logger = setup_logger("RebarAgent.OptimizerMIP")


def optimize_cuts_mip_indexed(
    lengths: List[float],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    stock_count_limit: Optional[int] = None,
    cancel_event: Optional[threading.Event] = None,
) -> List[List[int]]:
    opts = opts or OptimizerOptions()
    err = _validate_lengths(lengths, stock_length)
    if err:
        logger.error("optimize_cuts_mip_indexed: %s", err)
        return []
    if cancel_event and cancel_event.is_set():
        return []
    if not _ensure_mip_available():
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, opts.scale_mm)

    import logic.optimizer_packing as _op
    mip = _op._mip_lib
    scale = opts.scale_mm
    pieces_mm = [int(round(l * scale)) for l in lengths]
    stock_mm = int(round(stock_length * scale))
    n = len(pieces_mm)
    total_length = sum(pieces_mm)
    lower_bound = int(np.ceil(total_length / stock_mm))
    max_bins = min(n, max(1, lower_bound + 8))
    if stock_count_limit is not None:
        max_bins = min(max_bins, stock_count_limit)
    if n > 140:
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, scale)

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
        bins = optimize_cuts(lengths, stock_length, opts, cancel_event)
        return _bins_to_index_bins(lengths, bins, scale)
    bins_idx: List[List[int]] = []
    for j in range(max_bins):
        if y[j].x >= 0.99:
            bins_idx.append([i for i in range(n) if x[i][j].x >= 0.99])
    return bins_idx


def optimize_labeled_cuts(
    items: List[Tuple[float, dict]],
    stock_length: float,
    scrap_infos: Optional[Union[List[Tuple[int, float]], List[float]]] = None,
    opts: Optional[OptimizerOptions] = None,
    stock_count_limit: Optional[int] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[List[Dict], List[float]]:
    opts = opts or OptimizerOptions()
    if not items:
        return [], []
    err = _validate_lengths([l for l, _ in items], stock_length)
    if err:
        logger.error("optimize_labeled_cuts: %s", err)
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
        stock_plans, more_scraps = _pack_all_single_stock(
            remaining_items, stock_length, opts, cancel_event, stock_count_limit
        )
        for p in stock_plans:
            p["stock_seq"] = stock_seq_counter
            stock_seq_counter += 1
        scrap_plans.extend(stock_plans)
        new_scraps.extend(more_scraps)
    return scrap_plans, new_scraps
