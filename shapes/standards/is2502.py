# shapes/standards/is2502.py
"""
Indian Standard IS 2502:1963 – Reinforcement Shapes (Python)
Exports SHAPES for integration with ShapeRegistry/UI.

Notes:
- Uses shapes.constants.default_standard for deductions/hooks so it tracks set_standard().
- Fixes wrong summations like sum(... for k in "ABCH1H2") which is invalid.
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
# Table III – Straight and Bent‑up Bars
# ----------------------------------------------------------------------
register("S01", "S01 – Straight bar", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)))

register("S02", "S02 – Straight bar with one 90° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - constants.default_standard.bend_deduction(d, 90)))

register("S03", "S03 – Straight bar with one 135° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - constants.default_standard.bend_deduction(d, 135)))

register("S04", "S04 – Straight bar with one 180° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - constants.default_standard.bend_deduction(d, 180)))

register("S05", "S05 – Straight bar with two 90° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * constants.default_standard.bend_deduction(d, 90)))

register("S06", "S06 – Straight bar with two 135° hooks", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * constants.default_standard.bend_deduction(d, 135)))

register("S07", "S07 – Bent‑up bar (single)", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * constants.default_standard.bend_deduction(d, 45)))

register("S08", "S08 – Bent‑up bar (double)", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * constants.default_standard.bend_deduction(d, 45)))

# FIXED: wrong sum("ABCH1H2")
register("S09", "S09 – S‑shaped bar", ["A", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(2) * (_safe_float(dims.get("H1")) + _safe_float(dims.get("H2")))
                          - 4 * constants.default_standard.bend_deduction(d, 45)))

# ----------------------------------------------------------------------
# Table IV – Stirrups and Ties
# ----------------------------------------------------------------------
register("T01", "T01 – Rectangular stirrup", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("T02", "T02 – Square stirrup", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("T03", "T03 – Triangular stirrup", ["A", "B"],
         lambda dims, d: (2 * _safe_float(dims.get("A"))
                          + math.sqrt(_safe_float(dims.get("A")) ** 2 + _safe_float(dims.get("B")) ** 2)
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("T04", "T04 – Circular stirrup (hoop)", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d)
                          + 2 * constants.default_standard.get_hook_length(d, 135)))

register("T05", "T05 – Diamond stirrup", ["A"],
         lambda dims, d: (2 * math.sqrt(2) * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("T06", "T06 – Hexagonal stirrup", ["A"],
         lambda dims, d: (6 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("T07", "T07 – U‑shaped tie", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * constants.default_standard.bend_deduction(d, 90)))

register("T08", "T08 – U‑shaped tie with hooks", ["A", "B", "C", "A_hook"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("A_hook"))
                          - 4 * constants.default_standard.bend_deduction(d, 90)))

register("T09", "T09 – Double U tie", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          - 4 * constants.default_standard.bend_deduction(d, 90)))

# ----------------------------------------------------------------------
# Table V – Links
# ----------------------------------------------------------------------
register("L01", "L01 – Single link", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("L02", "L02 – Double link", ["A", "B", "C"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * (_safe_float(dims.get("C")) + _safe_float(dims.get("B")))
                          - 6 * constants.default_standard.bend_deduction(d, 90)
                          + 2 * constants.default_standard.get_hook_length(d, 135)))

register("L03", "L03 – Triple link", ["A", "B", "C", "D"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * (_safe_float(dims.get("C")) + _safe_float(dims.get("B")))
                          + 2 * (_safe_float(dims.get("D")) + _safe_float(dims.get("B")))
                          - 10 * constants.default_standard.bend_deduction(d, 90)
                          + 2 * constants.default_standard.get_hook_length(d, 135)))

# ----------------------------------------------------------------------
# Table VI – Column Ties
# ----------------------------------------------------------------------
register("CT01", "CT01 – Rectangular column tie", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.bend_deduction(d, 90)))

register("CT02", "CT02 – Cross tie", ["A", "B"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.bend_deduction(d, 90)))

# ----------------------------------------------------------------------
# Table VII – Special Shapes
# ----------------------------------------------------------------------
register("SS01", "SS01 – T‑headed bar", ["L", "A"],
         lambda dims, d: _safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A")))

register("SS02", "SS02 – L‑bar with unequal legs", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - constants.default_standard.bend_deduction(d, 90)))

register("SS03", "SS03 – U‑bar (hairpin)", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * constants.default_standard.bend_deduction(d, 90)))

register("SS04", "SS04 – Z‑bar", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * constants.default_standard.bend_deduction(d, 45)))

register("SS05", "SS05 – Spiral tie", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)))

# ----------------------------------------------------------------------
# Table VIII – Welded Wire Fabric
# ----------------------------------------------------------------------
register("WW01", "WW01 – Straight fabric", ["L"],
         lambda dims, d: _safe_float(dims.get("L")))

register("WW02", "WW02 – Bent fabric (L shape)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - constants.default_standard.bend_deduction(d, 90)))

# ----------------------------------------------------------------------
# Table IX – Pile Bars
# ----------------------------------------------------------------------
register("P01", "P01 – Straight pile bar", ["L"],
         lambda dims, d: _safe_float(dims.get("L")))

register("P02", "P02 – Pile bar with 90° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - constants.default_standard.bend_deduction(d, 90)))

register("P03", "P03 – Pile bar with 180° hook", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - constants.default_standard.bend_deduction(d, 180)))


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown IS 2502 shape code: {code}")
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


_IS_DRAW_MAP = {
    "S01": "draw_straight",
    "S02": "draw_straight_with_90_hook",
    "S03": "draw_straight_with_135_hook",
    "S04": "draw_straight_with_180_hook",
    "S05": "draw_double_hook_90",
    "S06": "draw_double_135_hook",
    "S07": "draw_s_bar",
    "S08": "draw_double_cranked_bar",
    "S09": "draw_s_bar",

    "T01": "draw_closed_stirrup_90",
    "T02": "draw_square_stirrup",
    "T04": "draw_circular_tie",
    "T07": "draw_u_bar",
    "T08": "draw_u_bar_with_hooks",

    "SS01": "draw_t_headed_bar",
    "SS02": "draw_l_bar",
    "SS03": "draw_u_bar",
    "SS04": "draw_z_bar",
    "SS05": "draw_helical",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _IS_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "is",
    }