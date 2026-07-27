# shapes/standards/gb50010.py
"""
Chinese Standard GB 50010 – Comprehensive Reinforcement Shapes
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
register("GB-01", "直钢筋 (Straight bar)", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)),
         "Plain straight bar")

# ----------------------------------------------------------------------
# 2. Straight Bars with End Hooks
# ----------------------------------------------------------------------
register("GB-02", "90°弯钩钢筋 (Bar with one 90° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight with one 90° hook")

register("GB-03", "135°弯钩钢筋 (Bar with one 135° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight with one 135° hook")

register("GB-04", "180°弯钩钢筋 (Bar with one 180° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight with one 180° hook")

register("GB-05", "两端90°弯钩钢筋 (Bar with two 90° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Two 90° hooks")

register("GB-06", "两端135°弯钩钢筋 (Bar with two 135° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Two 135° hooks")

register("GB-07", "两端180°弯钩钢筋 (Bar with two 180° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Two 180° hooks")

# ----------------------------------------------------------------------
# 3. Bent Bars
# ----------------------------------------------------------------------
register("GB-11", "L形钢筋 (L‑bar, 90° bend)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "L-bar")

register("GB-12", "不等边L形钢筋 (L‑bar with unequal legs)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Asymmetric L-bar")

register("GB-13", "Z形钢筋 (Z‑bar, double 45° bend)", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Z-bar")

register("GB-14", "U形钢筋 (U‑bar, open without hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "Open U-bar")

register("GB-15", "U形钢筋带135°弯钩 (U‑bar with 135° hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d),
         "U-bar with hooks")

register("GB-16", "单弯起钢筋 (Single‑crank bar)", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Single crank")

register("GB-17", "双弯起钢筋 (Double‑crank bar)", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Double crank")

# ----------------------------------------------------------------------
# 4. Stirrups & Ties
# ----------------------------------------------------------------------
register("GB-21", "矩形封闭箍筋 (Rectangular closed stirrup, no hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Rectangular closed stirrup (no hooks)")

register("GB-22", "矩形箍筋带135°弯钩 (Rectangular stirrup with 135° hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Rectangular stirrup with hooks")

register("GB-23", "正方形箍筋 (Square stirrup)", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Square stirrup")

register("GB-24", "开口箍筋 (Open link with two 135° hooks)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Open link")

register("GB-25", "三肢箍 (Three‑leg stirrup)", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 4 * constants.default_standard.get_bending_radius(d) - 8 * d),
         "Three-leg stirrup")

register("GB-26", "四肢箍 (Four‑leg stirrup)", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * _safe_float(dims.get("C")) + _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 5 * constants.default_standard.get_bending_radius(d) - 10 * d),
         "Four-leg stirrup")

register("GB-27", "拉筋 (Single‑leg tie)", ["A"],
         lambda dims, d: (_safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d),
         "Straight tie with hooks")

# FIXED: wrong sum("ABCH1H2") + double-counting
register("GB-28", "S形拉筋 (S‑shaped tie)", ["A", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(2) * (_safe_float(dims.get("H1")) + _safe_float(dims.get("H2")))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "S-shaped tie")

# ----------------------------------------------------------------------
# 5. Circular & Spiral
# ----------------------------------------------------------------------
register("GB-31", "圆形箍筋 (Circular tie, lapped)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + _safe_float(dims.get("Lap", 0))),
         "Circular tie (lap)")

register("GB-32", "圆形箍筋带135°弯钩 (Circular tie with 135° hooks)", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + 2 * constants.default_standard.get_hook_length(d, 135)),
         "Circular tie with hooks")

register("GB-33", "螺旋箍筋 (Spiral, helical coil)", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)),
         "Spiral")

# ----------------------------------------------------------------------
# 6. Chairs & Specials
# ----------------------------------------------------------------------
register("GB-41", "单腿支撑 (Single bar chair)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d),
         "Chair")

register("GB-42", "连续支撑 (Continuous bar chair)", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d),
         "Continuous chair")

register("GB-43", "T形锚固钢筋 (T‑headed bar)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A"))),
         "T-headed")

register("GB-44", "搭接钢筋 (Lap splice bar)", ["L"],
         lambda dims, d: _safe_float(dims.get("L")),
         "Lap splice")

register("GB-45", "焊接锚板钢筋 (Bar with welded end plate)", ["L", "W", "H"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * (_safe_float(dims.get("W")) + _safe_float(dims.get("H")))),
         "End plate bar")


# ---------- API ----------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown GB shape code: {code}")
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


_GB_DRAW_MAP = {
    "GB-01": "draw_straight",
    "GB-02": "draw_straight_with_90_hook",
    "GB-03": "draw_straight_with_135_hook",
    "GB-04": "draw_straight_with_180_hook",
    "GB-05": "draw_double_hook_90",
    "GB-06": "draw_double_135_hook",
    "GB-07": "draw_double_180_hook",
    "GB-11": "draw_l_bar",
    "GB-13": "draw_z_bar",
    "GB-14": "draw_u_bar",
    "GB-15": "draw_u_bar_with_hooks",
    "GB-16": "draw_s_bar",
    "GB-17": "draw_double_cranked_bar",
    "GB-21": "draw_closed_stirrup_90",
    "GB-22": "draw_closed_stirrup_90",
    "GB-23": "draw_square_stirrup",
    "GB-31": "draw_circular_tie",
    "GB-32": "draw_circular_tie",
    "GB-33": "draw_helical",
    "GB-41": "draw_chair",
    "GB-42": "draw_chair",
    "GB-43": "draw_t_headed_bar",
    "GB-44": "draw_straight",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _GB_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "gb",
    }