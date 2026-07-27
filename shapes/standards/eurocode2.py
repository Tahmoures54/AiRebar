# shapes/standards/eurocode2.py
"""
Eurocode 2 (EN 1992-1-1) – Comprehensive Reinforcement Shapes
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
register("EC2-01", "Straight bar", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)),
         "Plain straight bar without any bends")

# ----------------------------------------------------------------------
# 2. Straight Bars with End Hooks
# ----------------------------------------------------------------------
register("EC2-02", "Bar with one 90° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with a 90° hook at one end")

register("EC2-03", "Bar with one 135° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with a 135° hook at one end")

register("EC2-04", "Bar with one 180° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight bar with a 180° hook at one end")

register("EC2-05", "Bar with two 90° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Bar with 90° hooks at both ends")

register("EC2-06", "Bar with two 135° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Bar with 135° hooks at both ends")

register("EC2-07", "Bar with two 180° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Bar with 180° hooks at both ends")

# ----------------------------------------------------------------------
# 3. Bent Bars
# ----------------------------------------------------------------------
register("EC2-11", "L‑bar (90° bend)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Simple 90° corner bar")

register("EC2-12", "L‑bar with unequal legs", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Asymmetric L-bar")

register("EC2-13", "Z‑bar (double 45° bend)", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Z-bar")

register("EC2-14", "U‑bar (open, without hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "Open U-bar (no hooks)")

register("EC2-15", "U‑bar with 135° hooks", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "U-bar with 135° hooks both ends")

register("EC2-16", "Single‑crank bar", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Single crank")

register("EC2-17", "Double‑crank bar", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Double crank")

# ----------------------------------------------------------------------
# 4. Stirrups & Links
# ----------------------------------------------------------------------
register("EC2-21", "Rectangular closed stirrup (no hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Closed stirrup no hooks")

register("EC2-22", "Rectangular stirrup with 135° hooks", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Rectangular stirrup with hooks")

register("EC2-23", "Square stirrup (135° hooks)", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Square stirrup")

register("EC2-24", "Open link (two 135° hooks)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Open link")

register("EC2-25", "Three‑leg stirrup", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 4 * constants.default_standard.get_bending_radius(d) - 8 * d),
         "Three-leg stirrup")

register("EC2-26", "Four‑leg stirrup", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * _safe_float(dims.get("C")) + _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 5 * constants.default_standard.get_bending_radius(d) - 10 * d),
         "Four-leg stirrup")

register("EC2-27", "Link with crank", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "Link with crank")

# ----------------------------------------------------------------------
# 5. Circular & Spiral
# ----------------------------------------------------------------------
register("EC2-31", "Circular tie (lapped)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + _safe_float(dims.get("Lap", 0))),
         "Circular tie lap splice")

register("EC2-32", "Circular tie with 135° hooks", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + 2 * constants.default_standard.get_hook_length(d, 135)),
         "Circular tie with hooks")

register("EC2-33", "Spiral (helical coil)", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)),
         "Spiral")

# ----------------------------------------------------------------------
# 6. Chairs & Specials
# ----------------------------------------------------------------------
register("EC2-41", "Single bar chair", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Chair")

register("EC2-42", "Continuous bar chair", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Continuous chair")

register("EC2-43", "T‑headed bar (mechanical anchorage)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A"))),
         "T-headed")

register("EC2-44", "Splice bar (straight lap)", ["L"],
         lambda dims, d: _safe_float(dims.get("L")),
         "Splice bar")

register("EC2-45", "Welded anchorage plate (straight + plate)", ["L", "W", "H"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * (_safe_float(dims.get("W")) + _safe_float(dims.get("H")))),
         "Bar with end plate")


# ---------- API ----------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown Eurocode 2 shape code: {code}")
    cleaned = {k: _safe_float(v) for k, v in (dims or {}).items()}
    return s.formula(cleaned, d)


def list_all_shapes():
    return [
        {"code": s.code, "name": s.name, "params": s.params, "description": s.description}
        for s in _REGISTRY.values()
    ]


# ---------- SHAPES ----------
def _make_calc_fn(code):
    def calc(params, d, _code=code):
        return calculate_length(_code, params, d)
    return calc


_EC_DRAW_MAP = {
    "EC2-01": "draw_straight",
    "EC2-02": "draw_straight_with_90_hook",
    "EC2-03": "draw_straight_with_135_hook",
    "EC2-04": "draw_straight_with_180_hook",
    "EC2-05": "draw_double_hook_90",
    "EC2-06": "draw_double_135_hook",
    "EC2-07": "draw_double_180_hook",
    "EC2-11": "draw_l_bar",
    "EC2-13": "draw_z_bar",
    "EC2-14": "draw_u_bar",
    "EC2-15": "draw_u_bar_with_hooks",
    "EC2-16": "draw_s_bar",
    "EC2-17": "draw_double_cranked_bar",
    "EC2-21": "draw_closed_stirrup_90",
    "EC2-22": "draw_closed_stirrup_90",
    "EC2-23": "draw_square_stirrup",
    "EC2-31": "draw_circular_tie",
    "EC2-32": "draw_circular_tie",
    "EC2-33": "draw_helical",
    "EC2-41": "draw_chair",
    "EC2-42": "draw_chair",
    "EC2-43": "draw_t_headed_bar",
    "EC2-44": "draw_straight",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _EC_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "ec",
    }