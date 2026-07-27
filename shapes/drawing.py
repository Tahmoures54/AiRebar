# shapes/drawing.py
"""
Tkinter canvas drawing functions for reinforcement bar shapes.

Supports:
- Built-in drawing functions by name (draw_l_bar, draw_u_bar, ...)
- SVG-template based shapes (from JSON standards)
- Custom segmented shapes (from custom designer)
- Robust generic fallback
- Smart inference: if a shape has draw_func='draw_generic' (or missing),
  tries to infer a better draw function from shape name / params.
"""

from __future__ import annotations

import math
import re
from typing import Dict, Callable, List, Tuple, Any

from shapes.constants import get_hook_length


def draw_shape_on_canvas(canvas, shape_key: str, params: dict, diameter_mm: float = 10.0):
    canvas.delete("all")
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w <= 1 or h <= 1:
        w, h = 640, 480

    lw = max(2, min(8, int(diameter_mm // 5)))

    canvas.create_rectangle(2, 2, w - 2, h - 2, outline="#e6e6e6", dash=(2, 4))

    try:
        from shapes.definitions import default_shape_registry
        shape_def = default_shape_registry.get_shape_def(shape_key)
    except Exception:
        shape_def = None

    if not shape_def:
        _draw_generic(canvas, shape_key, params, w, h, lw, "#1a1a1a", diameter_mm)
        return

    draw_func_name = shape_def.get("draw_func") or "draw_generic"

    if draw_func_name == "draw_custom_segmented":
        definition = shape_def.get("definition")
        if isinstance(definition, dict):
            _draw_custom_segmented(canvas, params, w, h, lw, "#1a1a1a", diameter_mm, definition)
        else:
            _draw_generic(canvas, shape_key, params, w, h, lw, "#1a1a1a", diameter_mm)
        return

    if draw_func_name == "draw_svg_template":
        svg_template = shape_def.get("svg_template", "")
        labels = shape_def.get("labels", [])
        code = shape_def.get("code", "")
        if svg_template:
            _draw_svg_template(canvas, params, w, h, lw, "#1a1a1a", diameter_mm, svg_template, labels, code)
        else:
            _draw_generic(canvas, shape_key, params, w, h, lw, "#1a1a1a", diameter_mm)
        return

    draw_fn = DRAW_FUNCTIONS.get(draw_func_name)

    if draw_fn is None or draw_func_name == "draw_generic":
        inferred_name = _infer_draw_func(shape_key, shape_def, params)
        draw_fn = DRAW_FUNCTIONS.get(inferred_name, _draw_generic_canvas_wrapper(shape_key))

    try:
        draw_fn(canvas, params, w, h, lw, "#1a1a1a", diameter_mm)
    except Exception:
        _draw_generic(canvas, shape_key, params, w, h, lw, "#1a1a1a", diameter_mm)


def _draw_generic_canvas_wrapper(shape_key: str):
    def _fn(canvas, params, w, h, lw, color, d):
        _draw_generic(canvas, shape_key, params, w, h, lw, color, d)
    return _fn


def _infer_draw_func(shape_key: str, shape_def: dict, params: dict) -> str:
    name = (shape_key or "").lower()
    code = str(shape_def.get("code", "") or "").lower()

    # IMPORTANT FIX: normalize params to lowercase
    pnames = [str(x).strip().lower() for x in (shape_def.get("params") or list((params or {}).keys()) or [])]
    pset = set(pnames)

    if any(k in name for k in ("spiral", "helical", "helix")) or ({"p", "n", "d"} <= pset):
        return "draw_helical"

    if any(k in name for k in ("circular", "circle")) or ("d" in pset and ("lap" in pset or len(pset) <= 2)):
        return "draw_circular_tie"

    if any(k in name for k in ("stirrup", "tie", "link", "closed", "箍", "スターラップ")):
        if "a" in pset and "b" in pset:
            return "draw_closed_stirrup_90"
        if "a" in pset and "b" not in pset:
            return "draw_square_stirrup"
        return "draw_closed_stirrup_90"

    if "chair" in name:
        return "draw_chair"

    if any(k in name for k in ("t-headed", "t headed", "thead", "t‑headed")):
        return "draw_t_headed_bar"

    if "straight" in name or (pset == {"l"} or ("l" in pset and len(pset) == 1)):
        if "135" in name or "135" in code:
            return "draw_straight_with_135_hook"
        if "180" in name or "180" in code:
            return "draw_straight_with_180_hook"
        if "90" in name or "90" in code:
            return "draw_straight_with_90_hook"
        return "draw_straight"

    if {"a", "b"} <= pset and "c" not in pset and "h" not in pset and "h1" not in pset:
        if "hook" in name:
            return "draw_l_bar_with_hook"
        return "draw_l_bar"

    if {"a", "h", "b"} <= pset:
        return "draw_z_bar"

    if {"a", "b", "c"} <= pset:
        if "hook" in name or "135" in name:
            return "draw_u_bar_with_hooks"
        return "draw_u_bar"

    if ("h1" in pset) or ("h2" in pset):
        return "draw_s_bar"

    if "d" in pset:
        return "draw_circular_tie"

    return "draw_generic"


def _calc_transform_bbox(points: List[Tuple[float, float]], w: int, h: int, margin: int = 60):
    xs = [p[0] for p in points] or [0.0]
    ys = [p[1] for p in points] or [0.0]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    width = max_x - min_x
    height = max_y - min_y
    if width == 0:
        width = 100.0
    if height == 0:
        height = 100.0

    scale = min((w - 2 * margin) / width, (h - 2 * margin) / height)
    ox = margin + (w - 2 * margin - width * scale) / 2 - min_x * scale
    oy = margin + (h - 2 * margin - height * scale) / 2 - min_y * scale

    def tr(x, y):
        return ox + x * scale, oy + y * scale

    return tr, scale


def _draw_text(canvas, x, y, text, color="#333"):
    canvas.create_text(x, y, text=text, fill=color, font=("Arial", 8), anchor="center")


def _draw_generic(canvas, shape_key, params, w, h, lw, color, d):
    x1, y1 = 40, h / 2
    x2, y2 = w - 40, h / 2
    canvas.create_line(x1, y1, x2, y2, fill="#006064", width=lw)
    canvas.create_text(w // 2, h // 2 - 22, text=f"{shape_key}", fill="#006064", font=("Arial", 10, "bold"))
    dim_text = ", ".join([f"{k}={float(v):.0f}" for k, v in (params or {}).items()])
    canvas.create_text(w // 2, h // 2 + 10, text=f"{dim_text}", fill="gray", font=("Arial", 9))
    canvas.create_text(w // 2, h // 2 + 30, text=f"Ø {d:.0f} mm", fill="gray", font=("Arial", 8))


def _draw_custom_segmented(canvas, params, w, h, lw, color, d, definition: dict):
    segments = definition.get("segments", [])
    if not segments:
        _draw_generic(canvas, "Custom Shape", params, w, h, lw, color, d)
        return

    x, y = 0.0, 0.0
    dirx, diry = 1.0, 0.0
    pts = [(x, y)]

    for seg in segments:
        st = seg.get("type", "line")
        if st == "line":
            pname = seg.get("param", "L")
            L = float(params.get(pname, 0.0) or 0.0)
            x += dirx * L
            y += diry * L
            pts.append((x, y))
        elif st == "arc":
            angle = float(seg.get("angle", 90.0) or 90.0)
            rp = seg.get("radius_param", "r")
            R = float(params.get(rp, 50.0) or 50.0) + d / 2.0
            direction = seg.get("direction", "cw")

            if direction == "cw":
                cx = x - diry * R
                cy = y + dirx * R
                delta = -math.radians(angle)
            else:
                cx = x + diry * R
                cy = y - dirx * R
                delta = math.radians(angle)

            start_ang = math.atan2(y - cy, x - cx)
            n = max(6, int(abs(angle) / 6))
            for i in range(1, n + 1):
                a = start_ang + delta * (i / n)
                pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))

            end_ang = start_ang + delta
            x = cx + R * math.cos(end_ang)
            y = cy + R * math.sin(end_ang)

            if direction == "cw":
                dirx = math.sin(end_ang)
                diry = -math.cos(end_ang)
            else:
                dirx = -math.sin(end_ang)
                diry = math.cos(end_ang)

    tr, _ = _calc_transform_bbox(pts, w, h, margin=70)
    flat = []
    for px, py in pts:
        X, Y = tr(px, py)
        flat.extend([X, Y])

    canvas.create_line(flat, fill="#006064", width=lw, smooth=True)
    _draw_text(canvas, w / 2, 16, "Custom Segmented Shape", "#006064")


def _eval_placeholder(expr_str, params, dia):
    def replacer(m):
        inner = m.group(1)
        try:
            return str(eval(inner, {"__builtins__": {}}, {"p": params, "dia": dia, "math": math}))
        except Exception:
            return "0"
    result = re.sub(r"{([^{}]*)}", replacer, expr_str)
    try:
        return float(eval(result, {"__builtins__": {}}, {"math": math}))
    except Exception:
        return 0.0


def _parse_svg_path(path_str: str):
    tokens = re.findall(r"[MLQAZ]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", path_str)
    points = []
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    i = 0

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "M":
            x = float(tokens[i]); y = float(tokens[i+1]); i += 2
            current = (x, y); start = current
            points.append(current)
        elif cmd == "L":
            x = float(tokens[i]); y = float(tokens[i+1]); i += 2
            current = (x, y)
            points.append(current)
        elif cmd == "Q":
            x1 = float(tokens[i]); y1 = float(tokens[i+1]); i += 2
            x2 = float(tokens[i]); y2 = float(tokens[i+1]); i += 2
            x0, y0 = current
            n = 20
            for t in range(1, n + 1):
                tt = t / n
                bx = (1-tt)**2 * x0 + 2*(1-tt)*tt * x1 + tt**2 * x2
                by = (1-tt)**2 * y0 + 2*(1-tt)*tt * y1 + tt**2 * y2
                points.append((bx, by))
            current = (x2, y2)
        elif cmd == "Z":
            points.append(start)
            current = start

    return points


def _draw_svg_template(canvas, params, w, h, lw, color, dia, svg_template, labels, code):
    def substitute(m):
        expr = m.group(1)
        return str(_eval_placeholder(expr, params, dia))

    try:
        pure_path = re.sub(r"\{([^{}]*)\}", substitute, svg_template)
        points = _parse_svg_path(pure_path)
    except Exception:
        points = [(0, 0), (100, 0)]

    if not points:
        points = [(0, 0), (100, 0)]

    tr, _ = _calc_transform_bbox(points, w, h, margin=60)
    flat = []
    for px, py in points:
        X, Y = tr(px, py)
        flat.extend([X, Y])

    canvas.create_line(flat, fill="#006064", width=lw)

    for label_def in labels or []:
        if not (isinstance(label_def, (list, tuple)) and len(label_def) == 3):
            continue
        x_str, y_str, text_str = label_def
        try:
            x_val = _eval_placeholder(x_str, params, dia)
            y_val = _eval_placeholder(y_str, params, dia)
            tx, ty = tr(x_val, y_val)
            text = re.sub(r"\{([^{}]*)\}", lambda m: str(params.get(m.group(1), m.group(0))), text_str)
            _draw_text(canvas, tx, ty, text, "#333")
        except Exception:
            pass

    if code:
        _draw_text(canvas, w / 2, 14, f"[ {code} ]", "#444")


# ---- Drawing primitives ----
def _draw_straight(canvas, params, w, h, lw, color, d):
    L = float(params.get("L", params.get("A", 200)) or 200)
    pts = [(0, 0), (L, 0)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    x1, y1 = tr(0, 0); x2, y2 = tr(L, 0)
    canvas.create_line(x1, y1, x2, y2, fill="#006064", width=lw)
    _draw_text(canvas, (x1 + x2) / 2, y1 - 14, f"L={L:.0f}", "#006064")


def _draw_straight_with_90_hook(canvas, params, w, h, lw, color, d):
    L = float(params.get("L", params.get("A", 200)) or 200)
    A = float(params.get("A", 100) or 100)
    pts = [(0, 0), (L, 0), (L, -A)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(L, 0); p2 = tr(L, -A)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)


def _draw_straight_with_135_hook(canvas, params, w, h, lw, color, d):
    L = float(params.get("L", params.get("A", 200)) or 200)
    A = float(params.get("A", 100) or 100)
    dx = A * 0.707
    pts = [(0, 0), (L, 0), (L + dx, -dx)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(L, 0); p2 = tr(L + dx, -dx)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)


def _draw_straight_with_180_hook(canvas, params, w, h, lw, color, d):
    L = float(params.get("L", params.get("A", 200)) or 200)
    A = float(params.get("A", 100) or 100)
    pts = [(0, 0), (L, 0), (L, -A), (L - A, -A)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(L, 0); p2 = tr(L, -A); p3 = tr(L - A, -A)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)


def _draw_double_hook_90(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    hook = float(params.get("Hook", get_hook_length(d, 90)) or get_hook_length(d, 90))
    pts = [(0, 0), (A, 0), (0, -hook), (A, -hook)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0)
    p2 = tr(0, -hook); p3 = tr(A, -hook)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p0, *p2, fill="#006064", width=lw)
    canvas.create_line(*p1, *p3, fill="#006064", width=lw)


def _draw_double_135_hook(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    hook = float(params.get("Hook", get_hook_length(d, 135)) or get_hook_length(d, 135))
    dx = hook * 0.707
    pts = [(0, 0), (A, 0), (dx, -dx), (A - dx, -dx)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0)
    p2 = tr(dx, -dx); p3 = tr(A - dx, -dx)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p0, *p2, fill="#006064", width=lw)
    canvas.create_line(*p1, *p3, fill="#006064", width=lw)


def _draw_double_180_hook(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    hook = float(params.get("Hook", get_hook_length(d, 180)) or get_hook_length(d, 180))
    pts = [(0, 0), (A, 0), (0, -hook), (hook, -hook), (A, -hook), (A - hook, -hook)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0)
    p2 = tr(0, -hook); p3 = tr(hook, -hook)
    p4 = tr(A, -hook); p5 = tr(A - hook, -hook)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p0, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)
    canvas.create_line(*p1, *p4, fill="#006064", width=lw)
    canvas.create_line(*p4, *p5, fill="#006064", width=lw)


def _draw_l_bar(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    B = float(params.get("B", 200) or 200)
    pts = [(0, 0), (A, 0), (A, -B)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0); p2 = tr(A, -B)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)


def _draw_l_bar_with_hook(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    B = float(params.get("B", 200) or 200)
    hook = float(params.get("Hook", get_hook_length(d, 90)) or get_hook_length(d, 90))
    pts = [(0, 0), (A, 0), (A, -B), (A + hook, -B)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0); p2 = tr(A, -B); p3 = tr(A + hook, -B)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)


def _draw_u_bar(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    B = float(params.get("B", 150) or 150)
    C = float(params.get("C", 200) or 200)
    pts = [(0, 0), (0, -B), (A, -B), (A, -B - C)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(0, -B); p2 = tr(A, -B); p3 = tr(A, -B - C)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)


def _draw_u_bar_with_hooks(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    B = float(params.get("B", 150) or 150)
    C = float(params.get("C", 200) or 200)
    hook = get_hook_length(d, 135)
    dx = hook * 0.707
    pts = [(0, -hook), (0, -B), (A, -B), (A, -B - C), (A + dx, -B - C - dx)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, -hook); p1 = tr(0, -B); p2 = tr(A, -B); p3 = tr(A, -B - C); p4 = tr(A + dx, -B - C - dx)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)
    canvas.create_line(*p3, *p4, fill="#006064", width=lw)


def _draw_z_bar(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    H = float(params.get("H", 100) or 100)
    B = float(params.get("B", 200) or 200)
    dx = H * 0.707
    pts = [(0, 0), (A, 0), (A + dx, -dx), (A + dx + B, -dx)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    p0 = tr(0, 0); p1 = tr(A, 0); p2 = tr(A + dx, -dx); p3 = tr(A + dx + B, -dx)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)


def _draw_s_bar(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 120) or 120)
    H1 = float(params.get("H1", params.get("H", 80)) or 80)
    B = float(params.get("B", 120) or 120)
    H2 = float(params.get("H2", 80) or 80)
    C = float(params.get("C", 120) or 120)
    pts = [(0, 0), (A, 0), (A, -H1), (A + B, -H1), (A + B, -(H1 - H2)), (A + B + C, -(H1 - H2))]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    flat = []
    for p in pts:
        X, Y = tr(p[0], p[1])
        flat.extend([X, Y])
    canvas.create_line(flat, fill="#006064", width=lw)


def _draw_closed_stirrup_90(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    B = float(params.get("B", 150) or 150)
    pts = [(0, 0), (A, 0), (A, -B), (0, -B), (0, 0)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=90)
    flat = []
    for p in pts:
        X, Y = tr(p[0], p[1])
        flat.extend([X, Y])
    canvas.create_line(flat, fill="#006064", width=lw)


def _draw_square_stirrup(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 200) or 200)
    pts = [(0, 0), (A, 0), (A, -A), (0, -A), (0, 0)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=90)
    flat = []
    for p in pts:
        X, Y = tr(p[0], p[1])
        flat.extend([X, Y])
    canvas.create_line(flat, fill="#006064", width=lw)


def _draw_circular_tie(canvas, params, w, h, lw, color, d):
    D = float(params.get("D", params.get("A", 200)) or 200)
    r = D / 2.0
    cx, cy = w / 2, h / 2
    mr = min((w - 140) / 2, (h - 140) / 2)
    rr = max(10.0, min(mr, r))
    canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline="#006064", width=lw)
    _draw_text(canvas, cx, cy + rr + 14, f"D={D:.0f}", "#006064")


def _draw_helical(canvas, params, w, h, lw, color, d):
    D = float(params.get("D", 200) or 200)
    P = float(params.get("P", 80) or 80)
    N = float(params.get("N", 4) or 4)
    turns = max(1, int(N))
    pts = []
    length = turns * P * 3
    amp = D / 4
    steps = 120
    for i in range(steps + 1):
        t = i / steps
        x = t * length
        y = amp * math.sin(t * turns * 2 * math.pi)
        pts.append((x, y))
    tr, _ = _calc_transform_bbox(pts, w, h, margin=80)
    flat = []
    for px, py in pts:
        X, Y = tr(px, py)
        flat.extend([X, Y])
    canvas.create_line(flat, fill="#006064", width=max(2, lw - 1), smooth=True)
    _draw_text(canvas, w / 2, 16, f"Helical: D={D:.0f} P={P:.0f} N={N:.0f}", "#006064")


def _draw_chair(canvas, params, w, h, lw, color, d):
    A = float(params.get("A", 150) or 150)
    B = float(params.get("B", 80) or 80)
    C = float(params.get("C", 60) or 60)
    pts = [(0, 0), (A, 0), (A, -B), (A - C, -B)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=90)
    p0 = tr(0, 0); p1 = tr(A, 0); p2 = tr(A, -B); p3 = tr(A - C, -B)
    canvas.create_line(*p0, *p1, fill="#006064", width=lw)
    canvas.create_line(*p1, *p2, fill="#006064", width=lw)
    canvas.create_line(*p2, *p3, fill="#006064", width=lw)


def _draw_t_headed_bar(canvas, params, w, h, lw, color, d):
    L = float(params.get("L", 250) or 250)
    head = 25
    pts = [(0, 0), (L, 0)]
    tr, _ = _calc_transform_bbox(pts, w, h, margin=90)
    x1, y1 = tr(0, 0); x2, y2 = tr(L, 0)
    canvas.create_line(x1, y1, x2, y2, fill="#006064", width=lw)
    canvas.create_line(x1 - head, y1, x1 + head, y1, fill="#006064", width=lw + 2)
    canvas.create_line(x2 - head, y2, x2 + head, y2, fill="#006064", width=lw + 2)


# ---- extra aliases for BS map safety ----
def _draw_spacer_bar(canvas, params, w, h, lw, color, d):
    _draw_generic(canvas, "Spacer bar", params, w, h, lw, color, d)

def _draw_multi_leg_stirrup(canvas, params, w, h, lw, color, d):
    _draw_closed_stirrup_90(canvas, params, w, h, lw, color, d)

def _draw_custom(canvas, params, w, h, lw, color, d):
    _draw_generic(canvas, "Custom", params, w, h, lw, color, d)


DRAW_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "draw_generic": _draw_generic,
    "draw_custom": _draw_custom,

    "draw_straight": _draw_straight,
    "draw_straight_with_90_hook": _draw_straight_with_90_hook,
    "draw_straight_with_135_hook": _draw_straight_with_135_hook,
    "draw_straight_with_180_hook": _draw_straight_with_180_hook,

    "draw_double_hook_90": _draw_double_hook_90,
    "draw_double_135_hook": _draw_double_135_hook,
    "draw_double_180_hook": _draw_double_180_hook,

    "draw_l_bar": _draw_l_bar,
    "draw_l_bar_with_hook": _draw_l_bar_with_hook,

    "draw_u_bar": _draw_u_bar,
    "draw_u_bar_with_hooks": _draw_u_bar_with_hooks,

    "draw_z_bar": _draw_z_bar,
    "draw_s_bar": _draw_s_bar,
    "draw_double_cranked_bar": _draw_s_bar,

    "draw_closed_stirrup_90": _draw_closed_stirrup_90,
    "draw_square_stirrup": _draw_square_stirrup,

    "draw_circular_tie": _draw_circular_tie,
    "draw_helical": _draw_helical,

    "draw_chair": _draw_chair,
    "draw_multi_leg_chair": _draw_chair,
    "draw_t_headed_bar": _draw_t_headed_bar,

    "draw_spacer_bar": _draw_spacer_bar,
    "draw_multi_leg_stirrup": _draw_multi_leg_stirrup,
}