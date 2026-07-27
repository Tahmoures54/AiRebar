# shapes/standards/mabhas9.py
"""
Iranian Mabhas 9 (1400) – Comprehensive Rebar Shapes with Live Preview Drawing.
"""

from typing import Dict, List
from dataclasses import dataclass
import math
import tkinter as tk  # noqa: F401  (kept for compatibility / canvas typing)

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


# ----------------------------------------------------------------------
# Internal registry
# ----------------------------------------------------------------------
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


# ======================= Straight Bars =======================
_register("IR-01", "Straight bar", ["L"], lambda dims, d: _safe_float(dims["L"]))

_register(
    "IR-02",
    "Straight with 90° hook at one end",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 90),
)
_register(
    "IR-03",
    "Straight with 135° hook at one end",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 135),
)
_register(
    "IR-04",
    "Straight with 180° hook at one end",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + _safe_float(dims["A"]) - _get_bend_deduction(d, 180),
)
_register(
    "IR-05",
    "Straight with two 90° hooks",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 90),
)
_register(
    "IR-06",
    "Straight with two 135° hooks",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 135),
)
_register(
    "IR-07",
    "Straight with two 180° hooks",
    ["L", "A"],
    lambda dims, d: _safe_float(dims["L"]) + 2 * _safe_float(dims["A"]) - 2 * _get_bend_deduction(d, 180),
)

# ======================= Bent Bars ===========================
_register(
    "IR-11",
    "L-bar (90° bend)",
    ["A", "B"],
    lambda dims, d: _safe_float(dims["A"]) + _safe_float(dims["B"]) - _get_bend_deduction(d, 90),
)
_register(
    "IR-12",
    "U-bar (open)",
    ["A", "B", "C"],
    lambda dims, d: _safe_float(dims["A"])
    + 2 * _safe_float(dims["B"])
    + _safe_float(dims["C"])
    - 2 * _get_bend_deduction(d, 90),
)
_register(
    "IR-13",
    "U-bar with 135° hooks",
    ["A", "B", "C"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + _safe_float(dims["C"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=False)
        - 2 * _get_bend_deduction(d, 90)
        - 2 * _get_bend_deduction(d, 135)
    ),
)
_register(
    "IR-14",
    "Z-bar (two 45° bends)",
    ["A", "H", "B"],
    lambda dims, d: _safe_float(dims["A"])
    + _safe_float(dims["B"])
    + math.sqrt(2) * _safe_float(dims["H"])
    - 2 * _get_bend_deduction(d, 45),
)
_register(
    "IR-15",
    "Single-cranked bar (45° bend)",
    ["A", "H", "B"],
    lambda dims, d: _safe_float(dims["A"])
    + _safe_float(dims["B"])
    + math.sqrt(2) * _safe_float(dims["H"])
    - 2 * _get_bend_deduction(d, 45),
)
_register(
    "IR-16",
    "Double-cranked bar (two 45° bends)",
    ["A", "H1", "B", "H2", "C"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + _safe_float(dims["B"])
        + _safe_float(dims["C"])
        + math.sqrt(2) * (_safe_float(dims["H1"]) + _safe_float(dims["H2"]))
        - 4 * _get_bend_deduction(d, 45)
    ),
)

# ===================== Stirrups & Ties =======================
_register(
    "IR-21",
    "Closed rectangular stirrup (no hooks)",
    ["A", "B"],
    lambda dims, d: 2 * (_safe_float(dims["A"]) + _safe_float(dims["B"]))
    - 4 * _get_bend_deduction(d, 90, is_stirrup=True),
)
_register(
    "IR-22",
    "Closed rectangular stirrup (135° hooks)",
    ["A", "B"],
    lambda dims, d: (
        2 * (_safe_float(dims["A"]) + _safe_float(dims["B"]))
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - 3 * _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-23",
    "Closed square stirrup",
    ["A"],
    lambda dims, d: (
        4 * _safe_float(dims["A"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - 3 * _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-24",
    "Open tie (135° hooks both ends)",
    ["A", "B"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-25",
    "Three-leg stirrup",
    ["A", "B", "C", "D"],
    lambda dims, d: (
        2 * _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + _safe_float(dims["C"])
        + _safe_float(dims["D"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - 5 * _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-26",
    "Four-leg stirrup",
    ["A", "B", "C", "D", "E"],
    lambda dims, d: (
        2 * _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + 2 * _safe_float(dims["C"])
        + _safe_float(dims["D"])
        + _safe_float(dims["E"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - 6 * _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-27",
    "S-shaped link (135° hook)",
    ["A", "B", "C", "H1"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + _safe_float(dims["B"])
        + _safe_float(dims["C"])
        + math.sqrt(2) * _safe_float(dims["H1"])
        - 4 * _get_bend_deduction(d, 45, is_stirrup=True)
    ),
)

# =================== Circular & Spiral =======================
_register(
    "IR-31",
    "Circular tie (lap splice)",
    ["D", "Lap"],
    lambda dims, d: math.pi * (_safe_float(dims["D"]) + d) + _safe_float(dims.get("Lap", 0)),
)
_register(
    "IR-32",
    "Circular tie with 135° hooks",
    ["D"],
    lambda dims, d: math.pi * (_safe_float(dims["D"]) + d) + 2 * _get_standard_hook(d, 135, is_stirrup=True),
)
_register(
    "IR-33",
    "Spiral (helical)",
    ["D", "P", "N"],
    lambda dims, d: (
        _safe_float(dims["N"])
        * math.sqrt((math.pi * (_safe_float(dims["D"]) + d)) ** 2 + _safe_float(dims["P"]) ** 2)
    ),
)

# =============== Chairs, Spacers & Specials ===================
_register(
    "IR-41",
    "Single-leg chair",
    ["A", "B", "C"],
    lambda dims, d: (
        _safe_float(dims["A"]) + 2 * _safe_float(dims["B"]) + _safe_float(dims["C"]) - 2 * _get_bend_deduction(d, 90)
    ),
)
_register(
    "IR-42",
    "Continuous chair",
    ["A", "B", "C", "D", "E"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + _safe_float(dims["C"])
        + 2 * _safe_float(dims["D"])
        + _safe_float(dims["E"])
        - 4 * _get_bend_deduction(d, 90)
    ),
)
_register("IR-43", "T-headed bar (mechanical anchor)", ["L", "A"], lambda dims, d: _safe_float(dims["L"]) + 4 * _safe_float(dims["A"]))
_register("IR-44", "Lap splice bar", ["L"], lambda dims, d: _safe_float(dims["L"]))
_register(
    "IR-45",
    "Welded anchor plate bar",
    ["L", "W", "H"],
    lambda dims, d: _safe_float(dims["L"]) + 2 * (_safe_float(dims["W"]) + _safe_float(dims["H"])),
)
_register(
    "IR-46",
    "Link bar (135° hooks)",
    ["A", "B"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + 2 * _safe_float(dims["B"])
        + 2 * _get_standard_hook(d, 135, is_stirrup=True)
        - _get_bend_deduction(d, 90, is_stirrup=True)
        - 2 * _get_bend_deduction(d, 135, is_stirrup=True)
    ),
)
_register(
    "IR-47",
    "L-bar with 135° hook",
    ["A", "B"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + _safe_float(dims["B"])
        + _get_standard_hook(d, 135, is_stirrup=False)
        - _get_bend_deduction(d, 90)
        - _get_bend_deduction(d, 135)
    ),
)
_register(
    "IR-48",
    "Z-bar with 90° hook",
    ["A", "H", "B", "A_hook"],
    lambda dims, d: (
        _safe_float(dims["A"])
        + _safe_float(dims["B"])
        + math.sqrt(2) * _safe_float(dims["H"])
        + _safe_float(dims.get("A_hook", 0))
        - 2 * _get_bend_deduction(d, 45)
        - _get_bend_deduction(d, 90)
    ),
)

# ----------------------------------------------------------------------
# Build SHAPES dictionary for ShapeRegistry
# ----------------------------------------------------------------------
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
    }


# ----------------------------------------------------------------------
# Backward-compatible API
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# DRAWING FUNCTION FOR ALL MABHAS9 SHAPES
# ----------------------------------------------------------------------
def draw_mabhas9_shape(canvas, shape_key, params, diameter):
    """Draw the actual reinforcement shape on the given tkinter Canvas."""
    code = shape_key.split(" - ")[0]

    # Get total length for scaling
    try:
        total_len = calculate_length(code, params, diameter)
    except Exception:
        total_len = 500

    cw = canvas.winfo_width()
    ch = canvas.winfo_height()
    margin = 40
    scale = min((cw - 2 * margin) / total_len, 1.0) if total_len > 0 else 1.0

    # origin at (margin, ch/2)
    ox, oy = margin, ch / 2

    def draw_line(x1, y1, x2, y2, **kwargs):
        canvas.create_line(
            ox + x1 * scale, oy - y1 * scale,
            ox + x2 * scale, oy - y2 * scale,
            **kwargs
        )

    def draw_arc(x1, y1, x2, y2, **kwargs):
        canvas.create_arc(
            ox + x1 * scale, oy - y2 * scale,
            ox + x2 * scale, oy - y1 * scale,
            **kwargs
        )

    # Normalized hook drawing (not used currently)
    def draw_hook(x, y, angle, length, dir=1):
        pass

    # Based on code, draw geometry
    if code == "IR-01":
        L = params.get("L", 200)
        draw_line(0, 0, L, 0, fill="#006064", width=3)

    elif code == "IR-02":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L, -A, fill="#006064", width=3)

    elif code == "IR-03":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L + A * 0.707, -A * 0.707, fill="#006064", width=3)

    elif code == "IR-04":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L, -A, fill="#006064", width=3)
        draw_line(L, -A, L - A, -A, fill="#006064", width=3)

    elif code == "IR-05":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, -A, 0, 0, fill="#006064", width=3)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L, -A, fill="#006064", width=3)

    elif code == "IR-06":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, -A * 0.707, 0, 0, fill="#006064", width=3)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L + A * 0.707, -A * 0.707, fill="#006064", width=3)

    elif code == "IR-07":
        L = params.get("L", 200)
        A = params.get("A", 100)
        draw_line(0, -A, 0, 0, fill="#006064", width=3)
        draw_line(0, 0, L, 0, fill="#006064", width=3)
        draw_line(L, 0, L, -A, fill="#006064", width=3)
        draw_line(L, -A, L - A, -A, fill="#006064", width=3)

    elif code == "IR-11":  # L-bar
        A = params.get("A", 200)
        B = params.get("B", 200)
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A, -B, fill="#006064", width=3)

    elif code == "IR-12":  # U-bar open
        A = params.get("A", 200)
        B = params.get("B", 150)
        C = params.get("C", 200)
        draw_line(0, 0, 0, -B, fill="#006064", width=3)
        draw_line(0, -B, A, -B, fill="#006064", width=3)
        draw_line(A, -B, A, -B - C, fill="#006064", width=3)

    elif code == "IR-13":  # U-bar with hooks
        A = params.get("A", 200)
        B = params.get("B", 150)
        C = params.get("C", 200)
        hook_len = _get_standard_hook(diameter, 135, False)
        draw_line(0, -hook_len, 0, -B, fill="#006064", width=3)
        draw_line(0, -B, A, -B, fill="#006064", width=3)
        draw_line(A, -B, A, -B - C, fill="#006064", width=3)
        draw_line(A, -B - C, A + hook_len * 0.707, -B - C - hook_len * 0.707, fill="#006064", width=3)

    elif code == "IR-14":  # Z-bar
        A = params.get("A", 200)
        H = params.get("H", 100)
        B = params.get("B", 200)
        dx = H * 0.707
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A + dx, -dx, fill="#006064", width=3)
        draw_line(A + dx, -dx, A + dx + B, -dx, fill="#006064", width=3)

    elif code == "IR-15":  # single crank
        A = params.get("A", 200)
        H = params.get("H", 100)
        B = params.get("B", 200)
        dx = H * 0.707
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A + dx, -dx, fill="#006064", width=3)
        draw_line(A + dx, -dx, A + dx + B, -dx, fill="#006064", width=3)

    elif code == "IR-16":  # double crank
        A = params.get("A", 200)
        H1 = params.get("H1", 80)
        B = params.get("B", 200)
        H2 = params.get("H2", 80)
        C = params.get("C", 200)
        dx1 = H1 * 0.707
        dx2 = H2 * 0.707
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A + dx1, -dx1, fill="#006064", width=3)
        draw_line(A + dx1, -dx1, A + dx1 + B, -dx1, fill="#006064", width=3)
        draw_line(A + dx1 + B, -dx1, A + dx1 + B + dx2, -dx1 - dx2, fill="#006064", width=3)
        draw_line(A + dx1 + B + dx2, -dx1 - dx2, A + dx1 + B + dx2 + C, -dx1 - dx2, fill="#006064", width=3)

    elif code == "IR-22":  # rect stirrup
        A = params.get("A", 200)
        B = params.get("B", 150)
        hook = _get_standard_hook(diameter, 135, True)
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A, -B, fill="#006064", width=3)
        draw_line(A, -B, 0, -B, fill="#006064", width=3)
        draw_line(0, -B, 0, 0, fill="#006064", width=3)
        draw_line(A, 0, A + hook * 0.707, hook * 0.707, fill="#006064", width=3)
        draw_line(0, -B, -hook * 0.707, -B - hook * 0.707, fill="#006064", width=3)

    elif code == "IR-23":  # square stirrup
        A = params.get("A", 200)
        hook = _get_standard_hook(diameter, 135, True)
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A, -A, fill="#006064", width=3)
        draw_line(A, -A, 0, -A, fill="#006064", width=3)
        draw_line(0, -A, 0, 0, fill="#006064", width=3)
        draw_line(A, 0, A + hook * 0.707, hook * 0.707, fill="#006064", width=3)
        draw_line(0, -A, -hook * 0.707, -A - hook * 0.707, fill="#006064", width=3)

    elif code == "IR-31":  # circular tie lap
        D = params.get("D", 200)
        _Lap = params.get("Lap", 50)
        r = D / 2 + diameter / 2
        draw_line(-r, 0, r, 0, fill="#006064", width=3)

    elif code == "IR-32":  # circular with hooks
        D = params.get("D", 200)
        r = D / 2 + diameter / 2
        hook = _get_standard_hook(diameter, 135, True)
        canvas.create_oval(
            ox - r * scale, oy - r * scale,
            ox + r * scale, oy + r * scale,
            outline="#006064", width=3
        )
        draw_line(r, 0, r + hook * 0.707, hook * 0.707, fill="#006064", width=3)
        draw_line(-r, 0, -r - hook * 0.707, hook * 0.707, fill="#006064", width=3)

    elif code == "IR-33":  # spiral (show turns as wavy line)
        D = params.get("D", 200)
        P = params.get("P", 80)
        N = params.get("N", 4)
        r = D / 2 + diameter / 2
        pts = []
        for i in range(int(N * 10)):
            angle = i * 2 * math.pi / 10
            x = r * math.cos(angle)
            y = r * math.sin(angle) + (i * P / 10)
            pts.extend([ox + x * scale, oy - y * scale])
        canvas.create_line(pts, fill="#006064", width=2)

    elif code == "IR-41":  # chair
        A = params.get("A", 200)
        B = params.get("B", 100)
        C = params.get("C", 50)
        draw_line(0, 0, A, 0, fill="#006064", width=3)
        draw_line(A, 0, A, -B, fill="#006064", width=3)
        draw_line(A, -B, A - C, -B, fill="#006064", width=3)

    elif code == "IR-44":  # splice
        L = params.get("L", 200)
        draw_line(0, 0, L, 0, fill="#006064", width=3)

    else:
        draw_line(0, 0, total_len, 0, fill="#006064", width=3)

    # Add dimension labels
    canvas.create_text(cw / 2, ch - 20, text=f"{shape_key}", fill="#006064", font=("Arial", 9, "bold"))
    dims_str = ", ".join(f"{k}={_safe_float(v):.0f}" for k, v in params.items())
    # --- FIX: dimps_str -> dims_str
    canvas.create_text(cw / 2, ch - 5, text=dims_str, fill="#333", font=("Arial", 7))