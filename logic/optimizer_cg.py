# logic/optimizer_cg.py
"""Column-generation optimize_cuts."""
from __future__ import annotations

import threading
from collections import Counter
from typing import List, Optional

from utils.logger import setup_logger
from logic.optimizer_options import OptimizerOptions
from logic.optimizer_packing import (
    _validate_lengths, _ffd_bins, PULP_AVAILABLE,
)

logger = setup_logger("RebarAgent.OptimizerCG")

try:
    from pulp import LpProblem, LpVariable, LpMinimize, LpMaximize, lpSum, value, PULP_CBC_CMD
except ImportError:
    LpProblem = LpVariable = LpMinimize = LpMaximize = lpSum = value = PULP_CBC_CMD = None


def optimize_cuts(
    lengths: List[float],
    stock_length: float,
    opts: Optional[OptimizerOptions] = None,
    cancel_event: Optional[threading.Event] = None,
) -> List[List[float]]:
    opts = opts or OptimizerOptions()
    err = _validate_lengths(lengths, stock_length)
    if err:
        logger.error("optimize_cuts: %s", err)
        return []
    if cancel_event and cancel_event.is_set():
        return []
    if not PULP_AVAILABLE:
        return _ffd_bins(lengths, stock_length)

    scale = opts.scale_mm
    pieces_mm = [int(round(l * scale)) for l in lengths]
    stock_mm = int(round(stock_length * scale))
    demand = Counter(pieces_mm)
    types = sorted(demand.keys())
    m = len(types)
    if m == 0:
        return []

    patterns: List[List[int]] = []
    for i, L in enumerate(types):
        max_cnt = stock_mm // L
        vec = [0] * m
        vec[i] = int(max_cnt)
        patterns.append(vec)

    prob = LpProblem("CuttingStock_MasterLP", LpMinimize)
    p_vars = [LpVariable(f"p_{j}", lowBound=0, cat="Continuous") for j in range(len(patterns))]
    prob += lpSum(p_vars)
    constr_names: List[str] = []
    for i, L in enumerate(types):
        name = f"demand_{i}"
        prob += lpSum(patterns[j][i] * p_vars[j] for j in range(len(patterns))) >= demand[L], name
        constr_names.append(name)

    for _it in range(opts.max_column_generation_iters):
        if cancel_event and cancel_event.is_set():
            return []
        prob.solve(PULP_CBC_CMD(msg=1 if opts.verbose else 0, timeLimit=max(1, opts.mip_time_limit)))
        dual = []
        for cname in constr_names:
            c = prob.constraints.get(cname)
            dual.append(float(getattr(c, "pi", 0.0) or 0.0))
        sub = LpProblem("CuttingStock_Knapsack", LpMaximize)
        x = [LpVariable(f"x_{i}", lowBound=0, cat="Integer") for i in range(m)]
        sub += lpSum(dual[i] * x[i] for i in range(m))
        sub += lpSum(types[i] * x[i] for i in range(m)) <= stock_mm
        sub.solve(PULP_CBC_CMD(msg=0, timeLimit=max(1, opts.mip_time_limit)))
        sub_val = value(sub.objective) if sub.objective is not None else None
        if sub_val is None or sub_val <= 1.0 + 1e-6:
            break
        new_pat = [int(value(x[i]) or 0) for i in range(m)]
        if sum(new_pat) <= 0:
            break
        patterns.append(new_pat)
        pv = LpVariable(f"p_{len(patterns)-1}", lowBound=0, cat="Continuous")
        p_vars.append(pv)
        for i in range(m):
            prob.constraints[constr_names[i]] += new_pat[i] * pv
        prob.objective += pv

    master_int = LpProblem("CuttingStock_MasterINT", LpMinimize)
    z = [LpVariable(f"Z_{j}", lowBound=0, cat="Integer") for j in range(len(patterns))]
    master_int += lpSum(z)
    for i, L in enumerate(types):
        master_int += lpSum(patterns[j][i] * z[j] for j in range(len(patterns))) >= demand[L], f"dem_{i}"
    if cancel_event and cancel_event.is_set():
        return []
    master_int.solve(PULP_CBC_CMD(msg=1 if opts.verbose else 0, timeLimit=max(1, opts.mip_time_limit)))
    result_bins = _ffd_bins(lengths, stock_length)
    return result_bins if result_bins else _ffd_bins(lengths, stock_length)
