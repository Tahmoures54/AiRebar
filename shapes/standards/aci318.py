# shapes/standards/aci318.py
"""
ACI 318-19 Common Rebar Shapes – Comprehensive Set
--------------------------------------------------
Typical reinforcement shapes used in ACI detailing.
Exports SHAPES for integration with ShapeRegistry.
"""

from typing import Dict, List
from dataclasses import dataclass
import math

import shapes.constants as constants  # IMPORTANT: keep in sync with set_standard()


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
register(
    "ACI-01", "Straight bar", ["L"],
    lambda dims, d: _safe_float(dims["L"]),
    "Simple straight bar without hooks"
)

register(
    "ACI-02", "Straight bar with 90° hook (one end)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + _safe_float(dims["A"])
        - 0.5 * constants.default_standard.get_bending_radius(d) - d
    ),
    "Bar with one 90° hook – typical end anchorage"
)

register(
    "ACI-03", "Straight bar with 135° hook (one end)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + _safe_float(dims["A"])
        - 0.5 * constants.default_standard.get_bending_radius(d) - d
    ),
    "Bar with one 135° hook"
)

register(
    "ACI-04", "Straight bar with 180° hook (one end)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + _safe_float(dims["A"])
        - 0.5 * constants.default_standard.get_bending_radius(d) - d
    ),
    "Bar with one 180° hook – typical column ties"
)

register(
    "ACI-05", "Straight bar with 90° hooks (both ends)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + 2 * _safe_float(dims["A"])
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Bar with 90° hooks at both ends"
)

register(
    "ACI-06", "Straight bar with 135° hooks (both ends)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + 2 * _safe_float(dims["A"])
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Bar with 135° hooks at both ends"
)

register(
    "ACI-07", "Straight bar with 180° hooks (both ends)", ["L", "A"],
    lambda dims, d: (
        _safe_float(dims["L"]) + 2 * _safe_float(dims["A"])
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Bar with 180° hooks at both ends"
)

# ----------------------------------------------------------------------
# 2. Bent Bars (L, U, Z, etc.)
# ----------------------------------------------------------------------
register(
    "ACI-10", "L‑bar (90° bend)", ["A", "B"],
    lambda dims, d: (
        _safe_float(dims["A"]) + _safe_float(dims["B"])
        - 0.5 * constants.default_standard.get_bending_radius(d) - d
    ),
    "Simple 90° corner bar"
)

register(
    "ACI-11", "L‑bar with unequal legs (135° bend)", ["A", "B"],
    lambda dims, d: (
        _safe_float(dims["A"]) + _safe_float(dims["B"])
        - 0.5 * constants.default_standard.get_bending_radius(d) - d
    ),
    "Similar to L‑bar (still treated as corner bend)"
)

register(
    "ACI-12", "Z‑bar (double 90° offset)", ["A", "H", "B"],
    lambda dims, d: (
        _safe_float(dims["A"]) + _safe_float(dims["B"])
        + math.sqrt(2) * _safe_float(dims["H"])
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Bar with two 45° bends (Z‑shape)"
)

register(
    "ACI-13", "U‑bar (open stirrup without hooks)", ["A", "B", "C"],
    lambda dims, d: (
        _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"])
        - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d
    ),
    "Open U‑shape, used for beam links"
)

register(
    "ACI-14", "U‑bar with 135° hooks", ["A", "B", "C"],
    lambda dims, d: (
        _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"])
        + 2 * constants.default_standard.get_hook_length(d, 135)
        - 2.5 * constants.default_standard.get_bending_radius(d) - 5 * d
    ),
    "Open U‑shape with 135° hooks at both ends"
)

register(
    "ACI-15", "Bent‑up bar (single crank)", ["L", "H", "B"],
    lambda dims, d: (
        _safe_float(dims["L"]) + _safe_float(dims["B"])
        + math.sqrt(_safe_float(dims["H"]) ** 2 + (_safe_float(dims["L"]) - _safe_float(dims["B"])) ** 2)
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Bar with a single crank"
)

register(
    "ACI-16", "Bent‑up bar (double crank)", ["L", "H1", "B", "H2", "C"],
    lambda dims, d: (
        _safe_float(dims["L"]) + _safe_float(dims["B"]) + _safe_float(dims["C"])
        + math.sqrt(_safe_float(dims["H1"]) ** 2 + (_safe_float(dims["L"]) - _safe_float(dims["B"])) ** 2)
        + math.sqrt(_safe_float(dims["H2"]) ** 2 + (_safe_float(dims["C"]) - _safe_float(dims["L"])) ** 2)
        - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d
    ),
    "Bar with two cranks"
)

# ----------------------------------------------------------------------
# 3. Stirrups and Ties
# ----------------------------------------------------------------------
register(
    "ACI-20", "Rectangular stirrup (135° hooks)", ["A", "B"],
    lambda dims, d: (
        2 * (_safe_float(dims["A"]) + _safe_float(dims["B"]))
        + 2 * constants.default_standard.get_hook_length(d, 135)
        - 3 * constants.default_standard.get_bending_radius(d) - 4 * d
    ),
    "Closed rectangular stirrup with 135° hooks"
)

register(
    "ACI-21", "Square stirrup (135° hooks)", ["A"],
    lambda dims, d: (
        4 * _safe_float(dims["A"])
        + 2 * constants.default_standard.get_hook_length(d, 135)
        - 3 * constants.default_standard.get_bending_radius(d) - 4 * d
    ),
    "Square stirrup (A×A)"
)

register(
    "ACI-22", "Circular tie (135° hooks)", ["D"],
    lambda dims, d: (
        math.pi * (_safe_float(dims["D"]) + d)
        + 2 * constants.default_standard.get_hook_length(d, 135)
    ),
    "Circular tie with 135° hooks"
)

register(
    "ACI-23", "Circular tie (lapped)", ["D", "Lap"],
    lambda dims, d: (
        math.pi * (_safe_float(dims["D"]) + d) + _safe_float(dims.get("Lap", 0))
    ),
    "Circular tie with lap splice (no hooks)"
)

register(
    "ACI-24", "Spiral (continuous)", ["D", "P", "N"],
    lambda dims, d: (
        _safe_float(dims["N"])
        * math.sqrt((math.pi * (_safe_float(dims["D"]) + d)) ** 2 + _safe_float(dims["P"]) ** 2)
    ),
    "Helical spiral for columns"
)

# ----------------------------------------------------------------------
# 4. Special Shapes
# ----------------------------------------------------------------------
register(
    "ACI-30", "Bar chair (single leg)", ["A", "B", "C"],
    lambda dims, d: (
        _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"])
        - 2 * 0.5 * constants.default_standard.get_bending_radius(d) - 2 * d
    ),
    "Simple chair for slab reinforcement"
)

register(
    "ACI-31", "Continuous chair (multiple legs)", ["A", "B", "C", "D", "E"],
    lambda dims, d: (
        _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"])
        + 2 * _safe_float(dims["D"]) + _safe_float(dims["E"])
        - 4 * 0.5 * constants.default_standard.get_bending_radius(d) - 4 * d
    ),
    "Multi‑leg continuous chair"
)

register(
    "ACI-32", "T‑headed bar", ["L", "A"],
    lambda dims, d: (_safe_float(dims["L"]) + 4 * _safe_float(dims["A"])),
    "T‑headed bar (mechanical anchorage)"
)

register(
    "ACI-33", "Splice bar (straight)", ["L"],
    lambda dims, d: _safe_float(dims["L"]),
    "Lap splice bar – straight"
)

# ----------------------------------------------------------------------
# Public API (optional helpers)
# ----------------------------------------------------------------------
def get_all_codes():
    return sorted(_REGISTRY.keys())

def get_shape_params(code):
    s = _REGISTRY.get(code)
    return s.params if s else []

def calculate_length(code, dims, d):
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown ACI shape code: {code}")
    cleaned = {k: _safe_float(v) for k, v in dims.items()}
    return s.formula(cleaned, d)

def list_all_shapes():
    return [
        {"code": s.code, "name": s.name, "params": s.params, "description": s.description}
        for s in _REGISTRY.values()
    ]

# ----------------------------------------------------------------------
# SHAPES export (REQUIRED by standards/__init__.py and ShapeRegistry)
# ----------------------------------------------------------------------
def _make_calc_fn(code):
    return lambda params, d: calculate_length(code, params, d)

# Optional: map to existing draw functions in shapes/drawing.py
_ACI_DRAW_MAP = {
    "ACI-01": "draw_straight",
    "ACI-02": "draw_straight_with_90_hook",
    "ACI-03": "draw_straight_with_135_hook",
    "ACI-04": "draw_straight_with_180_hook",
    "ACI-05": "draw_double_hook_90",
    "ACI-06": "draw_double_135_hook",
    "ACI-07": "draw_double_180_hook",
    "ACI-10": "draw_l_bar",
    "ACI-11": "draw_l_bar",
    "ACI-12": "draw_z_bar",
    "ACI-13": "draw_u_bar",
    "ACI-14": "draw_u_bar_with_hooks",
    "ACI-15": "draw_s_bar",
    "ACI-16": "draw_double_cranked_bar",
    "ACI-20": "draw_closed_stirrup_90",
    "ACI-21": "draw_generic",         # square: generic unless you add a specific function
    "ACI-22": "draw_circular_tie",
    "ACI-23": "draw_circular_tie",
    "ACI-24": "draw_helical",
    "ACI-30": "draw_chair",
    "ACI-31": "draw_chair",
    "ACI-32": "draw_t_headed_bar",
    "ACI-33": "draw_straight",
}

SHAPES = {}
for code, s in _REGISTRY.items():
    key = f"{s.code} - {s.name}"
    SHAPES[key] = {
        "code": s.code,
        "params": s.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": _ACI_DRAW_MAP.get(code, "draw_generic"),
        "standard_code": "aci",
    }