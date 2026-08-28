# shapes/standards/mabhas9.py
"""
Iranian Mabhas 9 (1400) – Comprehensive Rebar Shapes with Live Preview Drawing.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import math
# Note: no top-level tkinter — registry loads in headless environments

# ----------------------------------------------------------------------
# Geometry helpers based on Mabhas 9
# ----------------------------------------------------------------------
def _safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _get_mabhas9_radius(d: float, is_stirrup: bool = False) -> float:
    if is_stirrup:
        return 2.0 * d
    if d <= 16:
        return 2.0 * d
    elif d <= 25:
        return 3.0 * d
    else:
        return 4.0 * d


def _get_bend_deduction(d: float, angle: float, is_stirrup: bool = False) -> float:
    if angle <= 0:
        return 0.0
    r = _get_mabhas9_radius(d, is_stirrup)
    rad = math.radians(angle)
    r_out = r + d
    deduction = 2 * r_out * math.tan(rad / 2) - rad * (r + 0.5 * d)
    return max(0.0, deduction)


def _get_standard_hook(d: float, angle: float, is_stirrup: bool = True) -> float:
    if is_stirrup:
        if angle == 135:
            return max(6 * d, 75.0)
        if angle == 90:
            return max(6 * d, 75.0) if d <= 16 else 12 * d
    else:
        if angle == 90:
            return 12 * d
        if angle == 180:
            return max(4 * d, 60.0)
    return 0.0


@dataclass
class _ShapeDef:
    code: str
    name: str
    params: List[str]
    formula: callable
    description: str


_REGISTRY: Dict[str, _ShapeDef] = {}


def _register(code, name, params, formula, desc=""):
    _REGISTRY[code] = _ShapeDef(code, name, params, formula, desc)


_register("IR-01", "Straight bar", ["L"], lambda dims, d: _safe_float(dims["L"]))
_register("IR-02", "Straight with 90° hook at one end", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 90))
_register("IR-03", "Straight with 135° hook at one end", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 135))
_register("IR-04", "Straight with 180° hook at one end", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 180))
_register("IR-05", "Straight with two 90° hooks", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 90))
_register("IR-06", "Straight with two 135° hooks", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 135))
_register("IR-07", "Straight with two 180° hooks", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 180))
_register("IR-11", "L-bar (90° bend)", ["A", "B"], lambda dims, d: _safe_float(dims["A"]) + _safe_float(dims["B"]) - _get_bend_deduction(d, 90))
_register("IR-12", "U-bar (open)", ["A", "B", "C"], lambda dims, d: _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) - 2 * _get_bend_deduction(d, 90))
_register("IR-13", "U-bar with 135° hooks", ["A", "B", "C"], lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) + 2 * _get_standard_hook(d, 135, is_stirrup=False) - 2 * _get_bend_deduction(d, 90) - 2 * _get_bend_deduction(d, 135)))
_register("IR-14", "Z-bar (two 45° bends)", ["A", "H", "B"], lambda dims, d: _safe_float(dims["A"]) + _safe_float(dims["B"]) + math.sqrt(2) * _safe_float(dims["H"]) - 2 * _get_bend_deduction(d, 45))
_register("IR-15", "Single-cranked bar (45° bend)", ["A", "H", "B"], lambda dims, d: _safe_float(dims["A"]) + _safe_float(dims["B"]) + math.sqrt(2) * _safe_float(dims["H"]) - 2 * _get_bend_deduction(d, 45))
_register("IR-16", "Double-cranked bar (two 45° bends)", ["A", "H1", "B", "H2", "C"], lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"]) + _safe_float(dims["C"]) + math.sqrt(2) * (_safe_float(dims["H1"]) + _safe_float(dims["H2"])) - 4 * _get_bend_deduction(d, 45)))
_register("IR-21", "Closed rectangular stirrup (no hooks)", ["A", "B"], lambda dims, d: 2 * (_safe_float(dims["A"]) + _safe_float(dims["B"])) - 4 * _get_bend_deduction(d, 90, is_stirrup=True))
_register("IR-22", "Closed rectangular stirrup (135° hooks)", ["A", "B"], lambda dims, d: (2 * (_safe_float(dims["A"]) + _safe_float(dims["B"])) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - 3 * _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-23", "Closed square stirrup", ["A"], lambda dims, d: (4 * _safe_float(dims["A"]) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - 3 * _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-24", "Open tie (135° hooks both ends)", ["A", "B"], lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-25", "Three-leg stirrup", ["A", "B", "C", "D"], lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) + _safe_float(dims["D"]) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - 5 * _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-26", "Four-leg stirrup", ["A", "B", "C", "D", "E"], lambda dims, d: (2 * _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + 2 * _safe_float(dims["C"]) + _safe_float(dims["D"]) + _safe_float(dims["E"]) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - 6 * _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-27", "S-shaped link (135° hook)", ["A", "B", "C", "H1"], lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"]) + _safe_float(dims["C"]) + math.sqrt(2) * _safe_float(dims["H1"]) - 4 * _get_bend_deduction(d, 45, is_stirrup=True)))
_register("IR-31", "Circular tie (lap splice)", ["D", "Lap"], lambda dims, d: math.pi * (_safe_float(dims["D"]) + d) + _safe_float(dims.get("Lap", 0)))
_register("IR-32", "Circular tie with 135° hooks", ["D"], lambda dims, d: math.pi * (_safe_float(dims["D"]) + d) + 2 * _get_standard_hook(d, 135, is_stirrup=True))
_register("IR-33", "Spiral (helical)", ["D", "P", "N"], lambda dims, d: (_safe_float(dims["N"]) * math.sqrt((math.pi * (_safe_float(dims["D"]) + d)) ** 2 + _safe_float(dims["P"]) ** 2)))
_register("IR-41", "Single-leg chair", ["A", "B", "C"], lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) - 2 * _get_bend_deduction(d, 90)))
_register("IR-42", "Continuous chair", ["A", "B", "C", "D", "E"], lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) + 2 * _safe_float(dims["D"]) + _safe_float(dims["E"]) - 4 * _get_bend_deduction(d, 90)))
_register("IR-43", "T-headed bar (mechanical anchor)", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + 4 * _safe_float(dims["A"]))
_register("IR-44", "Lap splice bar", ["L"], lambda dims, d: _safe_float(dims["L"]))
_register("IR-45", "Welded anchor plate bar", ["L", "W", "H"], lambda dims, d: _safe_float(dims["L"]) + 2 * (_safe_float(dims["W"]) + _safe_float(dims["H"])))
_register("IR-46", "Link bar (135° hooks)", ["A", "B"], lambda dims, d: (_safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + 2 * _get_standard_hook(d, 135, is_stirrup=True) - _get_bend_deduction(d, 90, is_stirrup=True) - 2 * _get_bend_deduction(d, 135, is_stirrup=True)))
_register("IR-47", "L-bar with 135° hook", ["A", "B"], lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"]) + _get_standard_hook(d, 135, is_stirrup=False) - _get_bend_deduction(d, 90) - _get_bend_deduction(d, 135)))
_register("IR-48", "Z-bar with 90° hook", ["A", "H", "B", "A_hook"], lambda dims, d: (_safe_float(dims["A"]) + _safe_float(dims["B"]) + math.sqrt(2) * _safe_float(dims["H"]) + _safe_float(dims.get("A_hook", 0)) - 2 * _get_bend_deduction(d, 45) - _get_bend_deduction(d, 90)))


def _make_calc_fn(code):
    def calc(params, d):
        return calculate_length(code, params, d)
    return calc


SHAPES = {}
for code, shape in _REGISTRY.items():
    key = f"{shape.code} - {shape.name}"
    SHAPES[key] = {
        "code": shape.code,
        "params": shape.params,
        "calc_length": _make_calc_fn(code),
        "draw_func": "draw_mabhas9_shape",
        "standard_code": "ir",
    }


def calculate_length(code: str, dims: dict, d: float) -> float:
    s = _REGISTRY.get(code)
    if not s:
        raise KeyError(f"Unknown Mabhas 9 shape code: {code}")
    cleaned = {k: _safe_float(v) for k, v in dims.items()}
    return s.formula(cleaned, d)


def get_all_codes() -> List[str]:
    return sorted(_REGISTRY.keys())


def get_shape_params(code: str) -> List[str]:
    s = _REGISTRY.get(code)
    return s.params if s else []


def list_all_shapes() -> List[Dict]:
    return [{"code": s.code, "name": s.name, "params": s.params, "description": s.description} for s in _REGISTRY.values()]


def draw_mabhas9_shape(canvas, shape_key, params, diameter):
    """Draw reinforcement shape on the given Canvas (tkinter)."""
    code = shape_key.split(" - ")[0]
    try:
        total_len = calculate_length(code, params, diameter)
    except Exception:
        total_len = 500
    cw = canvas.winfo_width()
    ch = canvas.winfo_height()
    margin = 40
    scale = min((cw - 2 * margin) / total_len, 1.0) if total_len > 0 else 1.0
    ox, oy = margin, ch / 2

    def draw_line(x1, y1, x2, y2, **kwargs):
        canvas.create_line(ox + x1 * scale, oy - y1 * scale, ox + x2 * scale, oy - y2 * scale, **kwargs)

    if code == "IR-01":
        L = params.get("L", 200)
        draw_line(0, 0, L, 0, fill="#22d3ee", width=3)
    elif code == "IR-02":
        L, A = params.get("L", 200), params.get("A", 100)
        draw_line(0, 0, L, 0, fill="#22d3ee", width=3)
        draw_line(L, 0, L, -A, fill="#22d3ee", width=3)
    elif code == "IR-11":
        A, B = params.get("A", 200), params.get("B", 200)
        draw_line(0, 0, A, 0, fill="#22d3ee", width=3)
        draw_line(A, 0, A, -B, fill="#22d3ee", width=3)
    elif code == "IR-12":
        A, B, C = params.get("A", 200), params.get("B", 150), params.get("C", 200)
        draw_line(0, 0, 0, -B, fill="#22d3ee", width=3)
        draw_line(0, -B, A, -B, fill="#22d3ee", width=3)
        draw_line(A, -B, A, -B - C, fill="#22d3ee", width=3)
    elif code == "IR-22":
        A, B = params.get("A", 200), params.get("B", 150)
        draw_line(0, 0, A, 0, fill="#22d3ee", width=3)
        draw_line(A, 0, A, -B, fill="#22d3ee", width=3)
        draw_line(A, -B, 0, -B, fill="#22d3ee", width=3)
        draw_line(0, -B, 0, 0, fill="#22d3ee", width=3)
    else:
        draw_line(0, 0, total_len, 0, fill="#22d3ee", width=3)
    canvas.create_text(cw / 2, ch - 20, text=f"{shape_key}", fill="#e2e8f0", font=("Segoe UI", 9, "bold"))
    dims_str = ", ".join(f"{k}={_safe_float(v):.0f}" for k, v in params.items())
    canvas.create_text(cw / 2, ch - 5, text=dims_str, fill="#94a3b8", font=("Segoe UI", 7))
