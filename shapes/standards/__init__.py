# shapes/standards/__init__.py
"""
Aggregates all supported international design standards (except BS8666 which is handled separately).

Each standard module SHOULD export SHAPES.
If a module does not export SHAPES but has:
  - _REGISTRY (dict of code -> shape def with attributes: code, name, params)
  - calculate_length(code, dims, d)
then this loader auto-builds SHAPES from that registry.

Additionally:
- If module provides DRAW_MAP or _DRAW_MAP (code -> draw_func), it will be used.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("AI_Rebar.Standards")

STANDARDS_DICT: Dict[str, Dict[str, dict]] = {}
STANDARD_CODES: List[Tuple[str, str]] = []


def _make_calc_fn(mod, shape_code: str):
    def calc(params: dict, d: float):
        return mod.calculate_length(shape_code, params, d)
    return calc


def _get_draw_map(mod) -> dict:
    dm = getattr(mod, "DRAW_MAP", None)
    if isinstance(dm, dict):
        return dm
    dm = getattr(mod, "_DRAW_MAP", None)
    if isinstance(dm, dict):
        return dm
    return {}


def _build_shapes_from_registry(mod, standard_code: str) -> Dict[str, dict]:
    reg = getattr(mod, "_REGISTRY", None)
    calc_len = getattr(mod, "calculate_length", None)
    if not isinstance(reg, dict) or not callable(calc_len):
        return {}

    draw_map = _get_draw_map(mod)

    shapes: Dict[str, dict] = {}
    for _, s in reg.items():
        code = getattr(s, "code", None) or (s.get("code") if isinstance(s, dict) else None)
        name = getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else None)
        params = getattr(s, "params", None) or (s.get("params") if isinstance(s, dict) else None)

        if not code or not name:
            continue
        if not isinstance(params, list):
            params = []

        key = f"{code} - {name}"
        shapes[key] = {
            "code": code,
            "params": params,
            "calc_length": _make_calc_fn(mod, code),
            "draw_func": draw_map.get(code, "draw_generic"),
            "standard_code": standard_code,
        }

    return shapes


def _try_add(code: str, display: str, module_name: str):
    try:
        mod = __import__(f"{__name__}.{module_name}", fromlist=[module_name])

        shapes = getattr(mod, "SHAPES", None)
        if isinstance(shapes, dict) and shapes:
            # ensure standard_code exists for all
            fixed = {}
            for k, v in shapes.items():
                if not isinstance(v, dict):
                    continue
                vv = dict(v)
                vv.setdefault("draw_func", "draw_generic")
                vv.setdefault("standard_code", code)
                fixed[k] = vv
            STANDARDS_DICT[code] = fixed
            STANDARD_CODES.append((code, display))
            logger.info(f"Loaded standard '{code}' shapes from SHAPES: {len(fixed)}")
            return

        built = _build_shapes_from_registry(mod, code)
        if built:
            STANDARDS_DICT[code] = built
            STANDARD_CODES.append((code, display))
            logger.info(f"Loaded standard '{code}' shapes from _REGISTRY: {len(built)}")
            return

        logger.warning(f"Standard '{code}' loaded but has no SHAPES and no usable _REGISTRY (module={module_name})")

    except Exception as e:
        logger.warning(f"Standard '{code}' not loaded (module={module_name}): {e}")


_try_add("ir", "Iran – Mabhas 9", "mabhas9")
_try_add("aci", "ACI 318 – USA", "aci318")
_try_add("ec", "Eurocode 2", "eurocode2")
_try_add("is", "IS 2502 – India", "is2502")
_try_add("gb", "GB 50010 – China", "gb50010")
_try_add("jis", "JIS G 3112 – Japan", "jis")
_try_add("as", "AS 3600 – Australia", "as3600")
_try_add("nbr", "NBR 6118 – Brazil", "nbr6118")