# logic/optimizer_packing.py
"""Bin packing helpers (FFD/BFD) and MIP availability."""
from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any, Union
from collections import defaultdict

from config import DEFAULT_REBAR_GRADE
from utils.logger import setup_logger
from logic.optimizer_metrics import _effective_piece_length

logger = setup_logger("RebarAgent.OptimizerPack")

MIP_AVAILABLE = False
_mip_lib = None
PULP_AVAILABLE = False
try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    pulp = None


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
    buckets: Dict[int, List[int]] = defaultdict(list)
    for idx, l in enumerate(lengths):
        buckets[int(round(l * scale))].append(idx)
    for k in buckets:
        buckets[k].sort()
        buckets[k].reverse()
    out: List[List[int]] = []
    for b in bins:
        idxs: List[int] = []
        for l in b:
            key = int(round(l * scale))
            if not buckets[key]:
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


def _best_fit_decreasing(
    items: List[Tuple[float, dict]],
    scrap_infos: Union[List[Tuple[Union[int, str], float]], List[float]]
) -> Tuple[List[Dict], List[Tuple[float, dict]]]:
    scrap_infos, temp_ids_used = _normalize_scrap_infos(scrap_infos)
    if not scrap_infos:
        return [], items
    items_with_id = [(i, l, lbl) for i, (l, lbl) in enumerate(items)]
    items_with_id.sort(key=lambda x: x[1], reverse=True)
    scrap_pool = sorted(scrap_infos, key=lambda x: x[1])
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


def _pack_one_bar_ffd(
    items: List[Tuple[float, dict]],
    bar_length: float,
    kerf_m: float = 0.0,
) -> Tuple[List[Tuple[float, dict]], List[Tuple[float, dict]], float]:
    remaining = list(items)
    packed: List[Tuple[float, dict]] = []
    used = 0.0
    still = []
    for length, label in remaining:
        need = _effective_piece_length(length, kerf_m)
        if used + need <= bar_length + 1e-9:
            packed.append((length, label))
            used += need
        else:
            still.append((length, label))
    cut = sum(l for l, _ in packed)
    waste = max(0.0, bar_length - cut)
    return packed, still, waste
