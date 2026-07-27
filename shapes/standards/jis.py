# shapes/standards/jis.py
"""
Japanese Standard JIS G 3112 – Comprehensive Reinforcement Shapes
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
register("JIS-01", "直筋 (Straight bar)", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)))

register("JIS-02", "90°フック付き直筋 (Straight with one 90° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("JIS-03", "135°フック付き直筋 (Straight with one 135° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("JIS-04", "180°フック付き直筋 (Straight with one 180° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("JIS-05", "両端90°フック付き直筋 (Straight with two 90° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-06", "両端135°フック付き直筋 (Straight with two 135° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-07", "両端180°フック付き直筋 (Straight with two 180° hooks)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

# ----------------------------------------------------------------------
# 2. Bent Bars
# ----------------------------------------------------------------------
register("JIS-11", "L型筋 (L‑bar, 90° bend)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("JIS-12", "不等辺L型筋 (L‑bar with unequal legs)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("JIS-13", "Z型筋 (Z‑bar, double 45° bend)", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-14", "U型筋（フック無し） (U‑bar, open without hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d))

register("JIS-15", "U型筋（135°フック付き） (U‑bar with 135° hooks)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d))

register("JIS-16", "一本折り曲げ筋 (Single‑crank bar)", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-17", "二本折り曲げ筋 (Double‑crank bar)", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

# ----------------------------------------------------------------------
# 3. Stirrups & Ties
# ----------------------------------------------------------------------
register("JIS-21", "閉鎖スターラップ（フック無し） (Closed stirrup, no hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("JIS-22", "閉鎖スターラップ（135°フック付き） (Closed stirrup with 135° hooks)", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("JIS-23", "正方形スターラップ (Square stirrup)", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("JIS-24", "開口スターラップ (Open link with two 135° hooks)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-25", "三本足スターラップ (Three‑leg stirrup)", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 4 * constants.default_standard.get_bending_radius(d) - 8 * d))

register("JIS-26", "四本足スターラップ (Four‑leg stirrup)", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * _safe_float(dims.get("C")) + _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 5 * constants.default_standard.get_bending_radius(d) - 10 * d))

# FIXED: wrong sum("ABCH1H2")
register("JIS-27", "S字形スターラップ (S‑shaped tie)", ["A", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(2) * (_safe_float(dims.get("H1")) + _safe_float(dims.get("H2")))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

# ----------------------------------------------------------------------
# 4. Circular & Spiral
# ----------------------------------------------------------------------
register("JIS-31", "円形フープ（ラップ） (Circular tie, lapped)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + _safe_float(dims.get("Lap", 0))))

register("JIS-32", "円形フープ（135°フック付き） (Circular tie with 135° hooks)", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + 2 * constants.default_standard.get_hook_length(d, 135)))

register("JIS-33", "螺旋フープ (Spiral, helical coil)", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)))

# ----------------------------------------------------------------------
# 5. Chairs & Specials
# ----------------------------------------------------------------------
register("JIS-41", "単脚スペーサー (Single bar chair)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("JIS-42", "連続スペーサー (Continuous bar chair)", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("JIS-43", "Tヘッドバー (T‑headed bar)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A"))))

register("JIS-44", "重ね継手筋 (Lap splice bar)", ["L"],
         lambda dims, d: _safe_float(dims.get("L")))

register("JIS-45", "溶接プレート付き筋 (Bar with welded end plate)", ["L", "W", "H"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * (_safe_float(dims.get("W")) + _safe_float(dims.get("H")))))


# ---------- API ----------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown JIS shape code: {code}")
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


_JIS_DRAW_MAP = {
    "JIS-01": "draw_straight",
    "JIS-02": "draw_straight_with_90_hook",
    "JIS-03": "draw_straight_with_135_hook",
    "JIS-04": "draw_straight_with_180_hook",
    "JIS-05": "draw_double_hook_90",
    "JIS-06": "draw_double_135_hook",
    "JIS-07": "draw_double_180_hook",
    "JIS-11": "draw_l_bar",
    "JIS-13": "draw_z_bar",
    "JIS-14": "draw_u_bar",
    "JIS-15": "draw_u_bar_with_hooks",
    "JIS-16": "draw_s_bar",
    "JIS-17": "draw_double_cranked_bar",
    "JIS-21": "draw_closed_stirrup_90",
    "JIS-22": "draw_closed_stirrup_90",
    "JIS-23": "draw_square_stirrup",
    "JIS-31": "draw_circular_tie",
    "JIS-32": "draw_circular_tie",
    "JIS-33": "draw_helical",
    "JIS-41": "draw_chair",
    "JIS-42": "draw_chair",
    "JIS-43": "draw_t_headed_bar",
    "JIS-44": "draw_straight",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _JIS_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "jis",
    }