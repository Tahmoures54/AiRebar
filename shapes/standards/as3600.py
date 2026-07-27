# shapes/standards/as3600.py
"""
Australian Standard AS 3600 – Reinforcement Shapes
--------------------------------------------------
Typical reinforcement shapes used in Australian concrete design.
Uses the active design standard (shapes.constants.set_standard) for bending radii
and hook lengths.
Exports SHAPES for integration with ShapeRegistry/UI.
"""

from typing import Dict, List
from dataclasses import dataclass
import math

import shapes.constants as constants


@dataclass
class ShapeDefinition:
    code: str
    name: str
    params: List[str]
    formula: callable
    description: str


_REGISTRY: Dict[str, ShapeDefinition] = {}


def register(code, name, params, formula, desc=""):
    _REGISTRY[code] = ShapeDefinition(code, name, params, formula, desc)


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except Exception:
        return default


# ----------------------------------------------------------------------
# 1. Straight Bars
# ----------------------------------------------------------------------
register("AS-01", "Straight bar", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)),
         "Plain straight bar")

# ----------------------------------------------------------------------
# 2. Straight Bars with End Hooks
# ----------------------------------------------------------------------
register("AS-02", "Bar with 90° hook (one end)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with one 90° hook")

register("AS-03", "Bar with 135° hook (one end)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with one 135° hook")

register("AS-04", "Bar with 180° hook (one end)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with one 180° hook")

register("AS-05", "Bar with two 90° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Straight bar with 90° hooks at both ends")

register("AS-06", "Bar with two 135° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Straight bar with 135° hooks at both ends")

register("AS-07", "Bar with two 180° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Straight bar with 180° hooks at both ends")

# ----------------------------------------------------------------------
# 3. Bent Bars
# ----------------------------------------------------------------------
register("AS-11", "L‑bar (90° bend)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "L-bar")

register("AS-12", "Z‑bar (double 45° bend)", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Z-bar with two 45° bends")

register("AS-13", "U‑bar (open, without hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "Open U-bar")

register("AS-14", "U‑bar with 135° hooks", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "U-bar with 135° hooks both ends")

register("AS-15", "Single‑crank bar", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Single crank bar")

register("AS-16", "Double‑crank bar", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Double crank bar")

# ----------------------------------------------------------------------
# 4. Stirrups & Ties
# ----------------------------------------------------------------------
register("AS-21", "Rectangular closed stirrup (no hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Closed rectangular stirrup (no hooks)")

register("AS-22", "Rectangular stirrup with 135° hooks", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Rectangular stirrup with 135° hooks")

register("AS-23", "Square stirrup (135° hooks)", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Square stirrup with 135° hooks")

register("AS-24", "Open link (two 135° hooks)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Open link with two 135° hooks")

register("AS-25", "Three‑leg stirrup", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 4 * constants.default_standard.get_bending_radius(d) - 8 * d),
         "Three-leg stirrup")

register("AS-26", "Four‑leg stirrup", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * _safe_float(dims.get("C")) + _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 5 * constants.default_standard.get_bending_radius(d) - 10 * d),
         "Four-leg stirrup")

# FIXED: wrong sum("ABCH1H2") + double-counting
register("AS-27", "S‑shaped tie", ["A", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(2) * (_safe_float(dims.get("H1")) + _safe_float(dims.get("H2")))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "S-shaped tie (support/holding bar)")

# ----------------------------------------------------------------------
# 5. Circular & Spiral
# ----------------------------------------------------------------------
register("AS-31", "Circular tie (lapped)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + _safe_float(dims.get("Lap", 0))),
         "Circular tie with lap splice")

register("AS-32", "Circular tie with 135° hooks", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + 2 * constants.default_standard.get_hook_length(d, 135)),
         "Circular tie with 135° hooks")

register("AS-33", "Spiral (helical coil)", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)),
         "Helical spiral")

# ----------------------------------------------------------------------
# 6. Chairs & Specials
# ----------------------------------------------------------------------
register("AS-41", "Single bar chair", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Single chair")

register("AS-42", "Continuous bar chair", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Continuous chair")

register("AS-43", "T‑headed bar", ["L", "A"],
         lambda dims, d: _safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A")),
         "T-headed bar")

register("AS-44", "Lap splice bar", ["L"],
         lambda dims, d: _safe_float(dims.get("L")),
         "Lap splice bar")


# ---------- API ----------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown AS shape code: {code}")
    cleaned = {k: _safe_float(v) for k, v in (dims or {}).items()}
    return s.formula(cleaned, d)


def list_all_shapes():
    return [
        {"code": s.code, "name": s.name, "params": s.params, "description": s.description}
        for s in _REGISTRY.values()
    ]


# ---------- SHAPES (for ShapeRegistry/UI) ----------
def _make_calc_fn(code):
    def calc(params, d, _code=code):
        return calculate_length(_code, params, d)
    return calc


_AS_DRAW_MAP = {
    "AS-01": "draw_straight",
    "AS-02": "draw_straight_with_90_hook",
    "AS-03": "draw_straight_with_135_hook",
    "AS-04": "draw_straight_with_180_hook",
    "AS-05": "draw_double_hook_90",
    "AS-06": "draw_double_135_hook",
    "AS-07": "draw_double_180_hook",
    "AS-11": "draw_l_bar",
    "AS-12": "draw_z_bar",
    "AS-13": "draw_u_bar",
    "AS-14": "draw_u_bar_with_hooks",
    "AS-15": "draw_s_bar",
    "AS-16": "draw_double_cranked_bar",
    "AS-21": "draw_closed_stirrup_90",
    "AS-22": "draw_closed_stirrup_90",
    "AS-23": "draw_square_stirrup",
    "AS-24": "draw_u_bar_with_hooks",
    "AS-31": "draw_circular_tie",
    "AS-32": "draw_circular_tie",
    "AS-33": "draw_helical",
    "AS-41": "draw_chair",
    "AS-42": "draw_chair",
    "AS-43": "draw_t_headed_bar",
    "AS-44": "draw_straight",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _AS_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "as",
    }