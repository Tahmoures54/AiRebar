# shapes/standards/nbr6118.py
"""
Brazilian Standard NBR 6118 – Reinforcement Shapes
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
register("NBR-01", "Barra reta (Straight)", ["L"],
         lambda dims, d: _safe_float(dims.get("L", 0.0)))

# ----------------------------------------------------------------------
# 2. Straight Bars with End Hooks
# ----------------------------------------------------------------------
register("NBR-02", "Gancho 90° (90° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("NBR-03", "Gancho 135° (135° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("NBR-04", "Gancho 180° (180° hook)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("A"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("NBR-05", "Dois ganchos 90°", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-06", "Dois ganchos 135°", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-07", "Dois ganchos 180°", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 2 * _safe_float(dims.get("A"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

# ----------------------------------------------------------------------
# 3. Bent Bars
# ----------------------------------------------------------------------
register("NBR-11", "Barra L (90° bend)", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          - 0.5 * constants.default_standard.get_bending_radius(d) - d))

register("NBR-12", "Barra Z (45° bend)", ["A", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B"))
                          + math.sqrt(2) * _safe_float(dims.get("H"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-13", "Barra U aberta", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d))

register("NBR-14", "Barra U com ganchos 135°", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d))

register("NBR-15", "Barra com uma dobra 45°", ["L", "H", "B"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B"))
                          + math.sqrt(_safe_float(dims.get("H")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-16", "Barra com duas dobras 45°", ["L", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("L")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(_safe_float(dims.get("H1")) ** 2 +
                                      (_safe_float(dims.get("L")) - _safe_float(dims.get("B"))) ** 2)
                          + math.sqrt(_safe_float(dims.get("H2")) ** 2 +
                                      (_safe_float(dims.get("C")) - _safe_float(dims.get("L"))) ** 2)
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

# ----------------------------------------------------------------------
# 4. Stirrups & Ties
# ----------------------------------------------------------------------
register("NBR-21", "Estribo retangular fechado", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("NBR-22", "Estribo retangular com ganchos 135°", ["A", "B"],
         lambda dims, d: (2 * (_safe_float(dims.get("A")) + _safe_float(dims.get("B")))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("NBR-23", "Estribo quadrado", ["A"],
         lambda dims, d: (4 * _safe_float(dims.get("A"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 3 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("NBR-24", "Estribo aberto", ["A", "B"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 2 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-25", "Estribo três pernas", ["A", "B", "C", "D"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + _safe_float(dims.get("C")) + _safe_float(dims.get("D"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 4 * constants.default_standard.get_bending_radius(d) - 8 * d))

register("NBR-26", "Estribo quatro pernas", ["A", "B", "C", "D", "E"],
         lambda dims, d: (2 * _safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B"))
                          + 2 * _safe_float(dims.get("C")) + _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          + 2 * constants.default_standard.get_hook_length(d, 135)
                          - 5 * constants.default_standard.get_bending_radius(d) - 10 * d))

# FIXED: wrong sum("ABCH1H2")
register("NBR-27", "Estribo S", ["A", "H1", "B", "H2", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + math.sqrt(2) * (_safe_float(dims.get("H1")) + _safe_float(dims.get("H2")))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

# ----------------------------------------------------------------------
# 5. Circular & Spiral
# ----------------------------------------------------------------------
register("NBR-31", "Estribo circular (traspasse)", ["D", "Lap"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + _safe_float(dims.get("Lap", 0))))

register("NBR-32", "Estribo circular com ganchos 135°", ["D"],
         lambda dims, d: (math.pi * (_safe_float(dims.get("D")) + d) + 2 * constants.default_standard.get_hook_length(d, 135)))

register("NBR-33", "Espiral (helicoidal)", ["D", "P", "N"],
         lambda dims, d: (_safe_float(dims.get("N"))
                          * math.sqrt((math.pi * (_safe_float(dims.get("D")) + d)) ** 2 + _safe_float(dims.get("P")) ** 2)))

# ----------------------------------------------------------------------
# 6. Chairs & Specials
# ----------------------------------------------------------------------
register("NBR-41", "Caranguejo simples", ["A", "B", "C"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d))

register("NBR-42", "Caranguejo contínuo", ["A", "B", "C", "D", "E"],
         lambda dims, d: (_safe_float(dims.get("A")) + 2 * _safe_float(dims.get("B")) + _safe_float(dims.get("C"))
                          + 2 * _safe_float(dims.get("D")) + _safe_float(dims.get("E"))
                          - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d))

register("NBR-43", "Barra T (ancoragem mecânica)", ["L", "A"],
         lambda dims, d: (_safe_float(dims.get("L")) + 4 * _safe_float(dims.get("A"))))

register("NBR-44", "Barra de emenda", ["L"],
         lambda dims, d: _safe_float(dims.get("L")))


# ---------- API ----------
def get_all_codes():
    return sorted(_REGISTRY.keys())


def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []


def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown NBR shape code: {code}")
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


_NBR_DRAW_MAP = {
    "NBR-01": "draw_straight",
    "NBR-02": "draw_straight_with_90_hook",
    "NBR-03": "draw_straight_with_135_hook",
    "NBR-04": "draw_straight_with_180_hook",
    "NBR-05": "draw_double_hook_90",
    "NBR-06": "draw_double_135_hook",
    "NBR-07": "draw_double_180_hook",
    "NBR-11": "draw_l_bar",
    "NBR-12": "draw_z_bar",
    "NBR-13": "draw_u_bar",
    "NBR-14": "draw_u_bar_with_hooks",
    "NBR-15": "draw_s_bar",
    "NBR-16": "draw_double_cranked_bar",
    "NBR-21": "draw_closed_stirrup_90",
    "NBR-22": "draw_closed_stirrup_90",
    "NBR-23": "draw_square_stirrup",
    "NBR-31": "draw_circular_tie",
    "NBR-32": "draw_circular_tie",
    "NBR-33": "draw_helical",
    "NBR-41": "draw_chair",
    "NBR-42": "draw_chair",
    "NBR-43": "draw_t_headed_bar",
    "NBR-44": "draw_straight",
}

SHAPES: Dict[str, dict] = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _NBR_DRAW_MAP.get(s.code, "draw_generic"),
        "standard_code": "nbr",
    }