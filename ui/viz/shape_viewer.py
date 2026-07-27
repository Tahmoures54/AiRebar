# ui/viz/shape_viewer.py
"""
Enhanced shape viewer widget for displaying a single rebar shape.
Supports full drawing via shapes.drawing if available,
otherwise provides a detailed fallback for all common shape codes.
Displays parameters, cut length, grade, and shape code.
"""

import tkinter as tk
import math
from typing import Dict, Optional

# Attempt to import the advanced drawing function
try:
    from shapes.drawing import draw_shape_on_canvas
    HAS_DRAW_FUNC = True
except ImportError:
    HAS_DRAW_FUNC = False

from shapes.definitions import default_shape_registry


class ShapeViewer(tk.Canvas):
    """
    A canvas widget that draws a single rebar shape with its dimensions,
    cut length, and optional grade. Can be used in forms, reports, or previews.
    """

    def __init__(self, parent, width=350, height=250, bg=None,
                 line_color="#1a73e8", text_color="#333333", **kwargs):
        if bg is None:
            bg = "white"
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=1, highlightbackground="#cccccc", **kwargs)
        self.line_color = line_color
        self.text_color = text_color
        self.shape_code = None
        self.dimensions = {}
        self.diameter = 10.0
        self.grade = ""
        self.bind("<Configure>", lambda e: self._redraw())

    def set_theme_colors(self, line_color=None, text_color=None):
        """Apply external theme colours (e.g., from ThemeManager)."""
        if line_color is not None:
            self.line_color = line_color
        if text_color is not None:
            self.text_color = text_color
        self._redraw()

    def draw_shape(self, shape_code: str, dimensions: dict,
                   diameter: float = 10.0, grade: str = ""):
        """
        Store parameters and redraw.
        dimensions : dict {param_name: value_mm}
        """
        self.shape_code = shape_code
        self.dimensions = dimensions.copy()
        self.diameter = diameter
        self.grade = grade
        self._redraw()

    def _redraw(self, event=None):
        """Redraw only the shape layer to avoid flickering."""
        self.delete("shape_layer")          # remove previous shape items
        self.delete("info_overlay")         # remove previous info text
        if not self.shape_code or self.shape_code not in default_shape_registry.flat_shapes:
            self.create_text(self.winfo_width() // 2, self.winfo_height() // 2,
                             text="No shape selected", fill=self.text_color,
                             tags="shape_layer")
            return

        w, h = self.winfo_width(), self.winfo_height()
        if w < 10:
            w = 350
        if h < 10:
            h = 250

        # Show shape code in top‑left corner
        self.create_text(8, 8, text=self.shape_code, anchor="nw",
                         font=("Arial", 7, "italic"), fill="gray", tags="shape_layer")

        if HAS_DRAW_FUNC:
            try:
                draw_shape_on_canvas(self, self.shape_code, self.dimensions, self.diameter)
                self._add_info_overlay(w, h)
                return
            except Exception:
                pass

        # Fallback – proportional drawing based on actual dimensions
        self._fallback_proportional_draw()

    def _add_info_overlay(self, w, h):
        """Add text information after successful shape drawing."""
        # cut length using registry
        try:
            length_mm = default_shape_registry.calc_shape_length(
                self.shape_code, self.dimensions, self.diameter
            )
            cut_text = f"Cut length: {length_mm:.0f} mm"
        except Exception:
            cut_text = "Cut length: N/A"

        grade_text = f" | Grade: {self.grade}" if self.grade else ""
        dim_str = ", ".join(f"{k}={v:.0f}" for k, v in self.dimensions.items())

        self.create_text(w // 2, h - 30,
                         text=f"{cut_text}{grade_text}    ({dim_str})",
                         font=("Arial", 8, "italic"),
                         fill=self.text_color,
                         tags="info_overlay")

    # ------------------------------------------------------------------
    # Helper: coordinate transformation from real dimensions
    # ------------------------------------------------------------------
    def _calc_transform(self, max_x, max_y, margin=50):
        w = self.winfo_width()
        h = self.winfo_height()
        if max_x == 0:
            max_x = 100.0
        if max_y == 0:
            max_y = 100.0
        scale = min((w - 2 * margin) / max_x, (h - 2 * margin) / max_y)
        offset_x = margin + (w - 2 * margin - max_x * scale) / 2
        offset_y = margin + (h - 2 * margin - max_y * scale) / 2

        def transform(x, y):
            return offset_x + x * scale, offset_y + y * scale
        return transform

    # ------------------------------------------------------------------
    # Fallback: draw with real dimensions (proportional)
    # ------------------------------------------------------------------
    def _fallback_proportional_draw(self):
        """Draw a simple but proportional representation using given dimensions."""
        shape = self.shape_code
        p = self.dimensions
        d = self.diameter
        w = self.winfo_width()
        h = self.winfo_height()
        lw = max(2, int(d * 0.4))
        tag = "shape_layer"

        # Each shape returns a list of (x,y) points in mm, starting at (0,0)
        # We'll scale them to fit the canvas.
        points = []

        if shape == "00 - Straight Bar":
            A = p.get("A", 100)
            points = [(0, 0), (A, 0)]

        elif shape == "11 - L-Bar":
            A = p.get("A", 100)
            B = p.get("B", 100)
            points = [(0, 0), (A, 0), (A, B)]

        elif shape == "12 - L-Bar with 90° Hook":
            A = p.get("A", 100)
            B = p.get("B", 100)
            hook = d * 6   # approximate hook length
            points = [(0, 0), (A, 0), (A, B), (A + hook, B)]

        elif shape == "13 - L-Bar with 135° Hook":
            A = p.get("A", 100)
            B = p.get("B", 100)
            hook = d * 6
            dx = hook * 0.7
            dy = -hook * 0.7
            points = [(0, 0), (A, 0), (A, B), (A + dx, B + dy)]

        elif shape in ("21 - Straight with Two 90° Hooks",):
            A = p.get("A", 100)
            hook = d * 6
            points = [(hook, 0), (0, 0), (A, 0), (A + hook, 0)]

        elif shape == "22 - Straight with Two 135° Hooks":
            A = p.get("A", 100)
            hook = d * 6
            dx = hook * 0.7
            points = [(0 + dx, -dx), (0, 0), (A, 0), (A + dx, -dx)]

        elif shape == "31 - Z-Bar":
            A = p.get("A", 100)
            H = p.get("H", 100)
            B = p.get("B", 100)
            # simplified: two horizontal segments with diagonal in between
            points = [(0, 0), (A, 0), (A + H, H), (A + H + B, H)]

        elif shape == "32 - U-Bar with 90° Hooks":
            A = p.get("A", 100)
            B = p.get("B", 100)
            C = p.get("C", 100)
            hook = d * 6
            points = [(0, 0), (0, B), (C, B), (C, 0), (C + hook, 0)]

        elif shape == "33 - U-Bar with 135° Hooks":
            A = p.get("A", 100)
            B = p.get("B", 100)
            C = p.get("C", 100)
            hook = d * 6
            dx = hook * 0.7
            dy = -hook * 0.7
            points = [(0, 0), (0, B), (C, B), (C, 0), (C + dx, dy)]

        elif shape == "51 - Closed Stirrup (135° Hooks)":
            A = p.get("A", 100)
            B = p.get("B", 100)
            # rectangle plus hook stubs
            points = [(0, B), (0, 0), (A, 0), (A, B), (A - d*3, B + d*3),
                      (d*3, B + d*3), (0, B)]

        elif shape == "52 - Closed Stirrup (90° Hooks)":
            A = p.get("A", 100)
            B = p.get("B", 100)
            points = [(0, B), (0, 0), (A, 0), (A, B), (A + d*3, B),
                      (A + d*3, 0 - d*3), (0 - d*3, 0 - d*3), (0 - d*3, B)]

        elif shape == "71 - Circular Hoop (Lapped)":
            # circle – not drawn with points, special
            D = p.get("D", 100)
            cx, cy = D/2, D/2
            # scale D to fit canvas
            margin = 40
            scale = min((w - 2*margin) / D, (h - 2*margin) / D)
            r = D/2 * scale
            cx_sc = margin + (w - 2*margin)/2
            cy_sc = margin + (h - 2*margin)/2
            self.create_oval(cx_sc - r, cy_sc - r, cx_sc + r, cy_sc + r,
                             outline=self.line_color, width=lw, tags=tag)
            self._add_info_overlay(w, h)
            return

        elif shape == "72 - Circular Tie (135° Hooks)":
            D = p.get("D", 100)
            # draw a circle with hook stubs
            self._fallback_proportional_draw()  # fallback to generic
            return

        elif shape == "74 - Radius Bar":
            A = p.get("A", 100)
            B = p.get("B", 100)
            R = p.get("R", 100)
            # simplified: vertical line, arc, horizontal line
            points = [(0, 0), (0, B)]
            # We'll draw arc separately using create_arc; for polyline just draw the two lines
            trans = self._calc_transform(A + R, B + R, margin=50)
            x0, y0 = trans(0, 0)
            x1, y1 = trans(0, B)
            x2, y2 = trans(R, B)
            x3, y3 = trans(R + A, B)
            self.create_line(x0, y0, x1, y1, fill=self.line_color, width=lw, tags=tag)
            self.create_arc(x1 - R, y1 - R, x1 + R, y1 + R,
                            start=90, extent=90, style="arc",
                            outline=self.line_color, width=lw, tags=tag)
            self.create_line(x2, y2, x3, y3, fill=self.line_color, width=lw, tags=tag)
            self._add_info_overlay(w, h)
            return

        else:
            # Generic fallback: show a simple line
            self.create_text(w // 2, h // 2,
                             text=f"Shape: {shape}\n(use main drawing)",
                             fill=self.text_color, tags=tag)
            self._add_info_overlay(w, h)
            return

        # If we have a polyline, draw it
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            max_x = max(xs) - min(xs)
            max_y = max(ys) - min(ys)
            trans = self._calc_transform(max_x, max_y, margin=40)
            coords = []
            for x, y in points:
                tx, ty = trans(x - min(xs), y - min(ys))  # shift so min corner is at (0,0)
                coords.extend([tx, ty])
            self.create_line(*coords, fill=self.line_color, width=lw,
                             capstyle=tk.ROUND, joinstyle=tk.ROUND, tags=tag)

        self._add_info_overlay(w, h)