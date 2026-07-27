"""
SVG Render Engine – AI Rebar
Generates inline SVG strings for shapes using the unified ShapeRegistry,
safe expression evaluation, scale clamping, and caching.
Supports BS8666, JSON standard, and custom segmented shapes.
"""

import math
import re
import ast
import operator
import logging
from functools import lru_cache

import svgwrite

from shapes.definitions import default_shape_registry
from shapes.constants import get_hook_length

logger = logging.getLogger('AI_Rebar.SVGRender')

# ----------------------------------------------------------------------
# Safe arithmetic expression evaluator (replaces eval)
# ----------------------------------------------------------------------
_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _safe_eval(expr: str, context: dict) -> float:
    """Evaluate a simple arithmetic expression using a context dict.
    Logs errors to help debug malformed formulas in shape definitions.
    """
    def _eval_node(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context.get(node.id, 0.0)
        if isinstance(node, ast.BinOp):
            op = _ALLOWED_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
            return op(_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_eval_node(node.operand)
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        raise ValueError(f"Unsupported AST node: {type(node)}")
    try:
        tree = ast.parse(expr.strip(), mode='eval')
        return float(_eval_node(tree.body))
    except Exception as e:
        logger.warning(f"Safe eval failed for expression '{expr}': {e}")
        return 0.0


# ----------------------------------------------------------------------
# Public entry point (cached for performance)
# ----------------------------------------------------------------------
@lru_cache(maxsize=256)
def generate_shape_svg(shape_code: str, params_json: str, diameter_mm: float,
                       width: int = 150, height: int = 100) -> str:
    """
    Return a complete SVG string for the given shape code.
    Cached based on shape_code, serialized params, and diameter.

    Parameters:
        shape_code: short code like '51', '13A', '99'
        params_json: JSON string of dimension values (e.g. '{"A":200,"B":150}')
        diameter_mm: bar diameter
        width, height: viewBox dimensions in SVG units
    """
    import json
    params = json.loads(params_json)

    # Find shape definition by short code
    shape_def = None
    for key, defn in default_shape_registry.flat_shapes.items():
        if defn.get('code') == shape_code:
            shape_def = defn
            break

    if shape_def is None:
        return _fallback_svg(shape_code, width, height)

    # Prepare drawing
    dwg = svgwrite.Drawing(size=(f"{width}px", f"{height}px"))
    dwg.viewbox(0, 0, width, height)

    lw = max(2, min(6, int(diameter_mm // 5)))
    color = "#1a1a8a"

    draw_func_name = shape_def.get("draw_func", "")

    # Route to the correct internal renderer
    if draw_func_name == "draw_svg_template":
        svg_template = shape_def.get("svg_template", "")
        labels = shape_def.get("labels", [])
        if svg_template:
            _draw_svg_template(dwg, params, diameter_mm, width, height, lw, color,
                               svg_template, labels, shape_code)
        else:
            _draw_generic(dwg, shape_code, params, width, height, lw, color)

    elif draw_func_name == "draw_custom_segmented":
        definition = shape_def.get("definition")
        if definition:
            _draw_custom_segmented(dwg, params, diameter_mm, width, height, lw, color, definition)
        else:
            _draw_generic(dwg, shape_code, params, width, height, lw, color)

    else:
        draw_fn = _SVG_DRAW_FUNCTIONS.get(draw_func_name)
        if draw_fn:
            draw_fn(dwg, params, diameter_mm, width, height, lw, color)
        else:
            _draw_generic(dwg, shape_code, params, width, height, lw, color)

    return dwg.tostring()


# ----------------------------------------------------------------------
# Coordinate transformation helpers (with scale clamping)
# ----------------------------------------------------------------------
def _tx(params, w, h, margin=40, min_scale=0.1, max_scale=10.0):
    keys = params.keys()
    max_x = max_y = 0.0
    for v in params.values():
        max_x = max(max_x, v)
        max_y = max(max_y, v)
    if max_x == 0:
        max_x = 100.0
    if max_y == 0:
        max_y = 100.0
    scale = min((w - 2 * margin) / max_x, (h - 2 * margin) / max_y)
    scale = max(min_scale, min(scale, max_scale))  # clamp
    offset_x = margin + (w - 2 * margin - max_x * scale) / 2
    offset_y = margin + (h - 2 * margin - max_y * scale) / 2

    def transform(x, y):
        return offset_x + x * scale, offset_y + y * scale
    return transform, scale


def _tx_from_bounds(min_x, max_x, min_y, max_y, w, h, margin=40, min_scale=0.1, max_scale=10.0):
    width_r = max_x - min_x
    height_r = max_y - min_y
    if width_r == 0:
        width_r = 100.0
    if height_r == 0:
        height_r = 100.0
    scale = min((w - 2 * margin) / width_r, (h - 2 * margin) / height_r)
    scale = max(min_scale, min(scale, max_scale))  # clamp
    offset_x = margin + (w - 2 * margin - width_r * scale) / 2 - min_x * scale
    offset_y = margin + (h - 2 * margin - height_r * scale) / 2 - min_y * scale

    def transform(x, y):
        return offset_x + x * scale, offset_y + y * scale
    return transform, scale


def _add_label(dwg, x, y, text, color):
    dwg.add(dwg.text(text, insert=(x, y), fill=color,
                     font_size="8px", font_family="Arial", text_anchor="middle"))


# ----------------------------------------------------------------------
# Fallback & generic renderers
# ----------------------------------------------------------------------
def _fallback_svg(shape_code, w, h):
    dwg = svgwrite.Drawing(size=(f"{w}px", f"{h}px"))
    dwg.viewbox(0, 0, w, h)
    dwg.add(dwg.text(f"Shape {shape_code} not found", insert=(w/2, h/2),
                     fill="red", font_size="10px", font_family="Arial", text_anchor="middle"))
    return dwg.tostring()


def _draw_generic(dwg, code, params, w, h, lw, color):
    dwg.add(dwg.line((30, h/2), (w-30, h/2), stroke=color, stroke_width=lw))
    param_str = ", ".join(f"{k}={v}" for k, v in params.items())
    _add_label(dwg, w/2, h/2-15, f"[{code}] {param_str}", color)


# ----------------------------------------------------------------------
# SVG Template renderer (for JSON standards)
# ----------------------------------------------------------------------
def _substitute_svg_template(template_str, params, dia):
    """Replace {expr} placeholders with evaluated values (safe)."""
    def replacer(m):
        expr = m.group(1)
        context = {**params, 'dia': dia, 'pi': math.pi}
        return str(_safe_eval(expr, context))
    return re.sub(r'\{([^{}]*)\}', replacer, template_str)


def _parse_svg_path_d(path_str):
    tokens = re.findall(r'[MLQAZ]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', path_str)
    points = []
    current = (0.0, 0.0)
    start_sub = (0.0, 0.0)
    i = 0
    while i < len(tokens):
        cmd = tokens[i]; i += 1
        if cmd == 'M':
            x = float(tokens[i]); y = float(tokens[i+1]); i += 2
            current = (x, y); start_sub = current; points.append(current)
        elif cmd == 'L':
            x = float(tokens[i]); y = float(tokens[i+1]); i += 2
            current = (x, y); points.append(current)
        elif cmd == 'Q':
            x1 = float(tokens[i]); y1 = float(tokens[i+1]); i += 2
            x2 = float(tokens[i]); y2 = float(tokens[i+1]); i += 2
            x0, y0 = current
            n = 20
            for t in range(1, n+1):
                t = t / n
                bx = (1-t)**2 * x0 + 2*(1-t)*t * x1 + t**2 * x2
                by = (1-t)**2 * y0 + 2*(1-t)*t * y1 + t**2 * y2
                points.append((bx, by))
            current = (x2, y2)
        elif cmd == 'A':
            rx = float(tokens[i]); ry = float(tokens[i+1]); i += 2
            rot = float(tokens[i]); i += 1
            large = float(tokens[i]); i += 1
            sweep = float(tokens[i]); i += 1
            x2 = float(tokens[i]); y2 = float(tokens[i+1]); i += 2
            x1, y1 = current
            dx = (x1 - x2) / 2
            dy = (y1 - y2) / 2
            x1p = math.cos(-rot)*dx - math.sin(-rot)*dy
            y1p = math.sin(-rot)*dx + math.cos(-rot)*dy
            rx2 = rx*rx; ry2 = ry*ry
            x1p2 = x1p*x1p; y1p2 = y1p*y1p
            rad_check = x1p2/rx2 + y1p2/ry2
            if rad_check > 1:
                rx *= math.sqrt(rad_check); ry *= math.sqrt(rad_check)
                rx2 = rx*rx; ry2 = ry*ry
            sign = -1 if large == sweep else 1
            num = rx2*ry2 - rx2*y1p2 - ry2*x1p2
            if num < 0:
                num = 0
            sqrt_num = math.sqrt(num / (rx2*y1p2 + ry2*x1p2))
            cxp = sign * sqrt_num * (rx*y1p/ry)
            cyp = sign * sqrt_num * (-ry*x1p/rx)
            cx = math.cos(rot)*cxp - math.sin(rot)*cyp + (x1+x2)/2
            cy = math.sin(rot)*cxp + math.cos(rot)*cyp + (y1+y2)/2
            start_angle = math.atan2((y1p-cyp)/ry, (x1p-cxp)/rx)
            delta_angle = math.atan2((-y1p-cyp)/ry, (-x1p-cxp)/rx) - start_angle
            if not sweep and delta_angle > 0:
                delta_angle -= 2*math.pi
            elif sweep and delta_angle < 0:
                delta_angle += 2*math.pi
            n = max(10, int(abs(delta_angle)*20/math.pi))
            for j in range(1, n+1):
                theta = start_angle + delta_angle * j / n
                x = cx + rx*math.cos(theta)
                y = cy + ry*math.sin(theta)
                points.append((x, y))
            current = (x2, y2)
        elif cmd == 'Z':
            points.append(start_sub)
            current = start_sub
    return points


def _draw_svg_template(dwg, params, dia, w, h, lw, color, template_str, labels, code):
    try:
        path_str = _substitute_svg_template(template_str, params, dia)
        points = _parse_svg_path_d(path_str)
    except Exception as e:
        logger.warning(f"SVG template error for code {code}: {e}")
        points = [(0, 0), (100, 0)]
    if not points:
        points = [(0, 0), (100, 0)]
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    trans, scale = _tx_from_bounds(min(xs), max(xs), min(ys), max(ys), w, h)
    poly_points = [trans(p[0], p[1]) for p in points]
    dwg.add(dwg.polyline(poly_points, stroke=color, fill="none", stroke_width=lw))
    for label_def in labels:
        if len(label_def) != 3:
            continue
        x_str, y_str, text_str = label_def
        x_val = _safe_eval(x_str.strip('{}'), {**params, 'dia': dia, 'pi': math.pi})
        y_val = _safe_eval(y_str.strip('{}'), {**params, 'dia': dia, 'pi': math.pi})
        text = re.sub(r'\{([^{}]*)\}', lambda m: str(params.get(m.group(1), m.group(0))), text_str)
        tx, ty = trans(x_val, y_val)
        _add_label(dwg, tx, ty, text, color)
    _add_label(dwg, w/2, 10, f"[ {code} ]", color)


# ----------------------------------------------------------------------
# Custom segmented shape renderer
# ----------------------------------------------------------------------
def _draw_custom_segmented(dwg, params, dia, w, h, lw, color, definition):
    segments = definition.get('segments', [])
    if not segments:
        _draw_generic(dwg, "CUSTOM", params, w, h, lw, color)
        return
    points = [(0.0, 0.0)]
    x, y = 0.0, 0.0
    dx, dy = 1.0, 0.0
    for seg in segments:
        stype = seg.get('type', 'line')
        if stype == 'line':
            L = float(params.get(seg.get('param', 'L'), 0))
            x += dx * L
            y += dy * L
            points.append((x, y))
        elif stype == 'arc':
            angle_deg = float(seg.get('angle', 90))
            R = float(params.get(seg.get('radius_param', 'r'), 10)) + dia / 2.0
            direction = seg.get('direction', 'cw')
            if direction == 'cw':
                cx = x - dy * R
                cy = y + dx * R
            else:
                cx = x + dy * R
                cy = y - dx * R
            start_ang = math.atan2(y - cy, x - cx)
            if direction == 'cw':
                delta = -math.radians(angle_deg)
            else:
                delta = math.radians(angle_deg)
            end_ang = start_ang + delta
            n = max(5, int(abs(angle_deg) / 5))
            for i in range(1, n + 1):
                t = i / n
                a = start_ang + delta * t
                points.append((cx + R * math.cos(a), cy + R * math.sin(a)))
            x = cx + R * math.cos(end_ang)
            y = cy + R * math.sin(end_ang)
            points.append((x, y))
            if direction == 'cw':
                dx = math.sin(end_ang)
                dy = -math.cos(end_ang)
            else:
                dx = -math.sin(end_ang)
                dy = math.cos(end_ang)
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    trans, _ = _tx_from_bounds(min(xs), max(xs), min(ys), max(ys), w, h)
    svg_pts = [trans(p[0], p[1]) for p in points]
    dwg.add(dwg.polyline(svg_pts, stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, w/2, 10, f"Custom {definition.get('code', '')}", color)


# ----------------------------------------------------------------------
# Standard shape drawing functions (SVG) – complete set
# ----------------------------------------------------------------------
def _draw_straight(dwg, p, dia, w, h, lw, color):
    A = p.get("A", p.get("L", 100))
    trans, _ = _tx({"A": A}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-12, f"A={A:.0f}", color)


def _draw_straight_180_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 180)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    r = min(20, hook/2) * sc
    dwg.add(dwg.path(d=f"M {x2-r} {y1-r} A {r} {r} 0 0 0 {x2+r} {y1+r}",
                     stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-15, f"A={A:.0f}", color)


def _draw_straight_90_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 90)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x2, y2), (x2, y2 - hook * sc), stroke=color, stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-12, f"A={A:.0f}", color)


def _draw_straight_135_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 135)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    dx = hook * sc * 0.7; dy = -hook * sc * 0.7
    dwg.add(dwg.line((x2, y2), (x2 + dx, y2 + dy), stroke=color, stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-12, f"A={A:.0f}", color)


def _draw_l_bar(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); B = p.get("B", 100)
    trans, _ = _tx({"A": A, "B": B}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(A, 0); x2, y2 = trans(A, B)
    dwg.add(dwg.line((x0, y0), (x1, y1), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    _add_label(dwg, (x0+x1)/2, y0-10, f"A={A}", color)
    _add_label(dwg, x2+10, (y1+y2)/2, f"B={B}", color)


def _draw_l_bar_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); B = p.get("B", 100)
    hook = get_hook_length(dia, 90)
    trans, sc = _tx({"A": A, "B": B, "hook": hook}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(A, 0); x2, y2 = trans(A, B)
    dwg.add(dwg.line((x0, y0), (x1, y1), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x2, y2), (x2 + hook * sc, y2), stroke=color, stroke_width=lw))
    _add_label(dwg, (x0+x1)/2, y0-10, f"A={A}", color)
    _add_label(dwg, x2+15, (y1+y2)/2, f"B={B}", color)


def _draw_u_bar(dwg, p, dia, w, h, lw, color):
    A = p.get("A", p.get("B", 100))
    if all(k in p for k in ("A", "B", "C")):
        A, B, C = p["A"], p["B"], p["C"]
    else:
        A, B, C = (p.get(k, 100) for k in ("A", "B", "C"))
    trans, _ = _tx({"A": A, "C": C, "B": B}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(0, B); x2, y2 = trans(C, B); x3, y3 = trans(C, 0)
    dwg.add(dwg.polyline([(x0, y0), (x1, y1), (x2, y2), (x3, y3)], stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, x0-15, (y0+y1)/2, f"A={A}", color)
    _add_label(dwg, (x1+x2)/2, y1+10, f"B={B}", color)
    _add_label(dwg, x3+10, (y2+y3)/2, f"C={C}", color)


def _draw_double_hook_90(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 90)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x1, y1), (x1, y1 - hook * sc), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x2, y2), (x2, y2 - hook * sc), stroke=color, stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-20, f"A={A}", color)


def _draw_double_135_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 135)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    dx = hook * sc * 0.7; dy = -hook * sc * 0.7
    dwg.add(dwg.line((x1, y1), (x1+dx, y1+dy), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x2, y2), (x2-dx, y2+dy), stroke=color, stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-20, f"A={A}", color)


def _draw_double_180_hook(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100); hook = get_hook_length(dia, 180)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    r = min(20, hook/2) * sc
    dwg.add(dwg.path(d=f"M {x1-r} {y1-r} A {r} {r} 0 0 0 {x1+r} {y1+r}",
                     stroke=color, fill="none", stroke_width=lw))
    dwg.add(dwg.path(d=f"M {x2-r} {y1-r} A {r} {r} 0 0 0 {x2+r} {y1+r}",
                     stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, (x1+x2)/2, y1-20, f"A={A}", color)


def _draw_chair(dwg, p, dia, w, h, lw, color):
    keys = list(p.keys())
    if len(keys) >= 5:
        A, B, C, D, E = (p.get(k, 50) for k in ('A', 'B', 'C', 'D', 'E'))
        trans, _ = _tx({"A": A, "B": B, "C": C, "D": D, "E": E}, w, h)
        pts = [trans(0, B), trans(A, B), trans(A, 0), trans(A+C, 0),
               trans(A+C, B), trans(A+C+D, B)]
        dwg.add(dwg.polyline(pts, stroke=color, fill="none", stroke_width=lw))
        _add_label(dwg, w/2, 10, f"A={A},B={B},C={C},D={D},E={E}", color)
    else:
        _draw_generic(dwg, "Chair", p, w, h, lw, color)


def _draw_s_bar(dwg, p, dia, w, h, lw, color):
    A, H1, B, H2, C = (p.get(k, 50) for k in ('A', 'H1', 'B', 'H2', 'C'))
    trans, _ = _tx({"max": A+B+C+max(H1, H2)}, w, h)
    pts = [trans(0, 0), trans(A, 0), trans(A, H1), trans(A+B, H1),
           trans(A+B, H1-H2), trans(A+B+C, H1-H2)]
    dwg.add(dwg.polyline(pts, stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, w/2, 10, f"A={A},H1={H1},B={B},H2={H2},C={C}", color)


def _draw_z_bar(dwg, p, dia, w, h, lw, color):
    A, H, B = p.get("A", 100), p.get("H", 100), p.get("B", 100)
    trans, _ = _tx({"A": A, "H": H, "B": B}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(A, 0); x2, y2 = trans(A+H, H); x3, y3 = trans(A+H+B, H)
    dwg.add(dwg.polyline([(x0, y0), (x1, y1), (x2, y2), (x3, y3)], stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, (x0+x1)/2, y0-10, f"A={A}", color)
    _add_label(dwg, (x1+x2)/2, (y1+y2)/2-10, f"H={H}", color)
    _add_label(dwg, (x2+x3)/2, y2+10, f"B={B}", color)


def _draw_closed_stirrup_90(dwg, p, dia, w, h, lw, color):
    A, B = p.get("A", 100), p.get("B", 100)
    trans, _ = _tx({"A": A, "B": B}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(A, B)
    dwg.add(dwg.rect(insert=(x0, y0), size=(x1-x0, y1-y0),
                     stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, (x0+x1)/2, y0-12, f"A={A}", color)
    _add_label(dwg, x1+22, (y0+y1)/2, f"B={B}", color)


def _draw_u_bar_with_hooks(dwg, p, dia, w, h, lw, color):
    A, B, C = (p.get(k, 100) for k in ('A', 'B', 'C'))
    hook = get_hook_length(dia, 135)
    trans, sc = _tx({"A": A, "B": B, "C": C, "hook": hook}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(0, B); x2, y2 = trans(C, B); x3, y3 = trans(C, 0)
    dwg.add(dwg.polyline([(x0, y0), (x1, y1), (x2, y2), (x3, y3)], stroke=color, fill="none", stroke_width=lw))
    dx = hook * sc * 0.7; dy = -hook * sc * 0.7
    dwg.add(dwg.line((x0, y0), (x0+dx, y0+dy), stroke=color, stroke_width=lw))
    dwg.add(dwg.line((x3, y3), (x3-dx, y3+dy), stroke=color, stroke_width=lw))
    _add_label(dwg, (x0+x3)/2, y1-20, f"A={A},B={B},C={C}", color)


def _draw_s_bar_link(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100)
    hook = get_hook_length(dia, 180)
    trans, sc = _tx({"A": A, "hook": hook}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(A, 0)
    dwg.add(dwg.line((x0, y0), (x1, y1), stroke=color, stroke_width=lw))
    r = min(20, hook/2) * sc
    dwg.add(dwg.path(d=f"M {x0-r} {y0-r} A {r} {r} 0 0 0 {x0+r} {y0+r}",
                     stroke=color, fill="none", stroke_width=lw))
    dwg.add(dwg.path(d=f"M {x1-r} {y0-r} A {r} {r} 0 0 0 {x1+r} {y0+r}",
                     stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, w/2, 15, f"A={A}", color)


def _draw_circular_tie(dwg, p, dia, w, h, lw, color):
    D = p.get("D", p.get("A", 100))
    trans, _ = _tx({"D": D}, w, h)
    cx, cy = trans(D/2, D/2)
    r = D/2 * min((w-120)/D, (h-120)/D, 1)
    dwg.add(dwg.circle(center=(cx, cy), r=r, stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, cx, cy, f"D={D} mm", color)
    if "Lap" in p:
        _add_label(dwg, cx, cy+15, f"Lap={p['Lap']:.0f}", color)
    elif "C" in p:
        _add_label(dwg, cx, cy+15, f"Lap={p['C']:.0f}", color)


def _draw_helical(dwg, p, dia, w, h, lw, color):
    D = p.get("D", 100); P = p.get("P", 50); N = p.get("N", 4)
    trans, sc = _tx({"D": D, "P": P*N}, w, h)
    cx, cy = trans(D/2, 0)
    points = []
    for i in range(int(N*20)):
        t = i/20.0
        x = cx + D/2 * sc * math.cos(t * 2 * math.pi)
        y = cy + t * P * sc
        points.append((x, y))
    dwg.add(dwg.polyline(points, stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, w/2, 10, f"D={D}, P={P}, N={N}", color)


def _draw_radius_bar(dwg, p, dia, w, h, lw, color):
    A, B, R = (p.get(k, 50) for k in ('A', 'B', 'R'))
    trans, _ = _tx({"A": A, "B": B, "R": R}, w, h)
    x0, y0 = trans(0, 0); x1, y1 = trans(0, B)
    dwg.add(dwg.line((x0, y0), (x1, y1), stroke=color, stroke_width=lw))
    dwg.add(dwg.path(d=f"M {x1} {y1} A {R} {R} 0 0 0 {x1+R} {y1-R}",
                     stroke=color, fill="none", stroke_width=lw))
    x3, y3 = trans(R+A, B)
    dwg.add(dwg.line((x1+R, y1-R), (x3, y3), stroke=color, stroke_width=lw))
    _add_label(dwg, w/2, 10, f"A={A},B={B},R={R}", color)


def _draw_polygonal_hoop(dwg, p, dia, w, h, lw, color):
    sides = int(p.get("Sides", 6)); side_len = p.get("SideLen", 50)
    D = side_len / (2 * math.sin(math.pi / sides))
    trans, _ = _tx({"D": 2*D}, w, h)
    cx, cy = trans(D, D)
    pts = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides - math.pi / 2
        pts.append((cx + D * math.cos(angle), cy + D * math.sin(angle)))
    dwg.add(dwg.polygon(pts, stroke=color, fill="none", stroke_width=lw))
    _add_label(dwg, w/2, 10, f"Sides={sides}, SideLen={side_len:.0f}", color)


def _draw_truss_bar(dwg, p, dia, w, h, lw, color):
    A, B, C, D, E = (p.get(k, 50) for k in ('A', 'B', 'C', 'D', 'E'))
    trans, _ = _tx({"A": A, "B": B, "C": C, "D": D, "E": E}, w, h)
    top = [trans(0, 0), trans(A, 0), trans(A+C, 0), trans(A+C+E, 0)]
    bot = [trans(0, B), trans(A, B), trans(A+C, B), trans(A+C+E, B)]
    for i in range(3):
        dwg.add(dwg.line(top[i], top[i+1], stroke=color, stroke_width=lw))
        dwg.add(dwg.line(bot[i], bot[i+1], stroke=color, stroke_width=lw))
        if i < 2:
            dwg.add(dwg.line(top[i+1], bot[i+1], stroke=color, stroke_width=lw))
    _add_label(dwg, w/2, 10, "Truss", color)


def _draw_t_headed_bar(dwg, p, dia, w, h, lw, color):
    A = p.get("A", 100)
    trans, _ = _tx({"A": A}, w, h)
    x1, y1 = trans(0, 0); x2, y2 = trans(A, 0)
    dwg.add(dwg.line((x1, y1), (x2, y2), stroke=color, stroke_width=lw))
    head = 20
    dwg.add(dwg.line((x1-head, y1), (x1+head, y1), stroke=color, stroke_width=lw+2))
    dwg.add(dwg.line((x2-head, y2), (x2+head, y2), stroke=color, stroke_width=lw+2))
    _add_label(dwg, (x1+x2)/2, y1-15, f"A={A}", color)


# ----------------------------------------------------------------------
# Drawing function dispatch table (complete and correct mapping)
# ----------------------------------------------------------------------
_SVG_DRAW_FUNCTIONS = {
    "draw_straight":                  _draw_straight,
    "draw_straight_with_180_hook":    _draw_straight_180_hook,
    "draw_straight_with_90_hook":     _draw_straight_90_hook,
    "draw_straight_with_135_hook":    _draw_straight_135_hook,
    "draw_l_bar":                     _draw_l_bar,
    "draw_l_bar_with_hook":           _draw_l_bar_hook,
    "draw_l_bar_with_135_hook":       _draw_l_bar_hook,   # same visual form
    "draw_u_bar":                     _draw_u_bar,
    "draw_double_hook_90":            _draw_double_hook_90,
    "draw_double_135_hook":           _draw_double_135_hook,
    "draw_double_180_hook":           _draw_double_180_hook,
    "draw_chair":                     _draw_chair,
    "draw_multi_leg_chair":           _draw_chair,        # fallback to chair
    "draw_s_bar":                     _draw_s_bar,
    "draw_z_bar":                     _draw_z_bar,
    "draw_double_cranked_bar":        _draw_s_bar,        # similar rendering
    "draw_zigzag_bar":                _draw_s_bar,        # similar rendering
    "draw_closed_stirrup_90":         _draw_closed_stirrup_90,
    "draw_u_bar_with_hooks":          _draw_u_bar_with_hooks,
    "draw_s_bar_link":                _draw_s_bar_link,
    "draw_multi_leg_stirrup":         _draw_u_bar,        # fallback to U shape
    "draw_spacer_bar":                _draw_l_bar,        # fallback
    "draw_circular_tie":              _draw_circular_tie,
    "draw_helical":                   _draw_helical,
    "draw_radius_bar":                _draw_radius_bar,
    "draw_polygonal_hoop":            _draw_polygonal_hoop,
    "draw_truss_bar":                 _draw_truss_bar,
    "draw_t_headed_bar":              _draw_t_headed_bar,
    "draw_custom":                    _draw_generic,
}