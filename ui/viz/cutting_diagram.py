"""
Cutting Diagram Visualisation Module – MVC Refactored
- CuttingPlanModel: data + color mapping logic (no UI dependency)
- CuttingDiagram: view for a single bar, zoomable & HiDPI‑aware
- CuttingPlanFrame: composite view with toolbar, legend, export & scroll
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Tuple, Dict, Optional
import math

# ----------------------------------------------------------------------
# Optional Pillow for PNG export
# ----------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ----------------------------------------------------------------------
# Default colours
# ----------------------------------------------------------------------
DEFAULT_COLORS = [
    '#4CAF50', '#2196F3', '#FFC107', '#9C27B0', '#FF5722', '#607D8B',
    '#E91E63', '#00BCD4', '#795548', '#3F51B5'
]

DEFAULT_BG = "#ffffff"
DEFAULT_FG = "#333333"
DEFAULT_SCRAP_COLOR = "#f0f0f0"
DEFAULT_SCRAP_TEXT_COLOR = "#e53e3e"
LEGEND_FONT_SIZE = 8
TOOLTIP_BG = "#fffbe6"

# ----------------------------------------------------------------------
# Model – pure data + logic
# ----------------------------------------------------------------------
class CuttingPlanModel:
    """Stores plan data and provides colour mapping and statistics."""

    def __init__(self, plans: List[Dict], stock_length_m: float,
                 dia: float = 0, grade: str = ""):
        self.plans = plans
        self.stock_length_m = stock_length_m
        self.dia = dia
        self.grade = grade
        self._color_map: Dict[tuple, str] = {}
        self._rebuild_color_map()

    def _rebuild_color_map(self):
        """Assign a unique colour for every (listofer_no, grade) pair."""
        self._color_map.clear()
        for plan in self.plans:
            for _, lbl in plan['bin']:
                key = (lbl.get('listofer_no', '?'), lbl.get('grade', self.grade))
                if key not in self._color_map:
                    self._color_map[key] = DEFAULT_COLORS[
                        len(self._color_map) % len(DEFAULT_COLORS)
                    ]

    def get_color(self, listofer_no: str, grade: str) -> str:
        return self._color_map.get((listofer_no, grade), '#888888')

    def get_all_colors(self) -> Dict[tuple, str]:
        return dict(self._color_map)

    # ------------------------------------------------------------------
    # Static helper for weight (used by both model and view)
    # ------------------------------------------------------------------
    @staticmethod
    def piece_weight(length_mm: float, dia_mm: float) -> float:
        if dia_mm <= 0:
            return 0.0
        return (length_mm / 1000.0) * (dia_mm ** 2) * 0.006165

    @staticmethod
    def usage_percent(used_mm: float, stock_mm: float) -> float:
        return (used_mm / stock_mm * 100.0) if stock_mm > 0 else 0.0


# ----------------------------------------------------------------------
# View – CuttingDiagram (Canvas)
# ----------------------------------------------------------------------
class CuttingDiagram(tk.Canvas):
    """
    Displays a single bar with pieces, tooltips, selection, zoom.
    Uses the CuttingPlanModel for colour lookup.
    """

    def __init__(self, parent, model: CuttingPlanModel,
                 stock_length_mm: float = 12000.0,
                 on_select_callback=None, zoom: float = 1.0,
                 **kwargs):
        super().__init__(parent, height=80, bg=kwargs.pop('bg', DEFAULT_BG),
                         highlightthickness=1, highlightbackground='#ccc', **kwargs)
        self._model = model
        self.stock_length_mm = stock_length_mm           # original (not zoomed)
        self.pieces: List[Tuple[float, dict]] = []       # original (length_mm, label)
        self._on_select = on_select_callback
        self.zoom = zoom

        # HiDPI scaling factor
        self._dpi_scale = max(1.0, self.tk.call('tk', 'scaling'))
        self._base_font_size = max(6, int(7 * self._dpi_scale))

        # Tooltip state
        self._tooltip_items = []
        self._current_hover = None
        self._piece_bboxes: List[Tuple[float, float, float, float]] = []
        self._selected_idx: Optional[int] = None

        # Binding
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def set_plan(self, pieces: List[Tuple[float, dict]],
                 bar_length_mm: Optional[float] = None):
        if bar_length_mm is not None:
            self.stock_length_mm = bar_length_mm
        self.pieces = pieces[:]
        self.redraw()

    def set_zoom(self, zoom: float):
        self.zoom = max(0.1, min(zoom, 5.0))
        self.redraw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def redraw(self, event=None):
        """Full redraw (optimised by clearing only relevant items)."""
        self.delete("piece", "text", "tooltip", "tooltip_bg", "scrap")
        self._piece_bboxes.clear()
        self._tooltip_items.clear()

        w = self.winfo_width()
        if w < 10 or not self.pieces:
            return

        margin = 20
        logical_width = self.stock_length_mm * self.zoom
        if logical_width <= 0:
            return
        scale = (w - 2 * margin) / logical_width

        bar_h = max(12, 16 * self._dpi_scale)
        y_center = 35 * self._dpi_scale
        font_size = max(5, int(self._base_font_size * self.zoom))

        # Base bar
        self.create_line(margin, y_center, margin + logical_width * scale, y_center,
                         fill='#bbb', width=max(4, 8 * self._dpi_scale),
                         capstyle="round", tags="piece")

        x = margin
        for i, (length_mm, lbl) in enumerate(self.pieces):
            pw = max(length_mm * scale, 1.0)
            color = self._model.get_color(lbl.get('listofer_no', '?'),
                                          lbl.get('grade', ''))

            tag = f"piece_{i}"
            self.create_rectangle(
                x, y_center - bar_h/2, x + pw, y_center + bar_h/2,
                fill=color, outline='white', width=1,
                tags=(tag, "piece"),
                activeoutline='black', activewidth=2
            )
            if pw > 35 * self._dpi_scale:
                pos = lbl.get('pos', '')
                lf_id = lbl.get('listofer_no', '')
                txt = f"{pos}/LF{lf_id}"
                self.create_text(x + pw/2, y_center, text=txt,
                                 anchor='center',
                                 font=('Arial', font_size, 'bold'),
                                 fill='white', tags=(tag, "text"))

            self._piece_bboxes.append((x, y_center - bar_h/2,
                                       x + pw, y_center + bar_h/2))
            x += pw

        # Scrap
        total_used = sum(p[0] for p in self.pieces)
        remaining = self.stock_length_mm - total_used
        if remaining > 1:
            waste_x = margin + total_used * scale
            self.create_line(waste_x, y_center - 6, margin + logical_width * scale, y_center - 6,
                             fill='red', dash=(2, 2), tags="scrap")
            self.create_text(margin + logical_width * scale, y_center - 14,
                             text=f"Scrap: {remaining:.0f} mm",
                             anchor='ne',
                             font=('Arial', max(6, font_size - 1)),
                             fill=DEFAULT_SCRAP_TEXT_COLOR, tags="scrap")

        # Usage percent
        usage = CuttingPlanModel.usage_percent(total_used, self.stock_length_mm)
        self.create_text(margin, y_center - 18,
                         text=f"Usage: {usage:.0f}%",
                         anchor='sw',
                         font=('Arial', max(6, font_size - 1), 'italic'),
                         fill=DEFAULT_FG, tags="scrap")

        # Adjust scrollregion
        self.configure(scrollregion=(0, 0, margin + logical_width * scale + margin,
                                     int(80 * self._dpi_scale)))

    # ------------------------------------------------------------------
    # Hit testing & interactions
    # ------------------------------------------------------------------
    def _hit_test(self, x, y):
        for idx, (x0, y0, x1, y1) in enumerate(self._piece_bboxes):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return idx
        return None

    def _on_motion(self, event):
        idx = self._hit_test(event.x, event.y)
        if idx != self._current_hover:
            self._hide_tooltip()
            self._current_hover = idx
            if idx is not None:
                self._show_tooltip(event, idx)

    def _on_leave(self, event):
        self._hide_tooltip()

    def _on_click(self, event):
        idx = self._hit_test(event.x, event.y)
        if idx is not None and idx < len(self.pieces):
            self._selected_idx = idx
            if self._on_select:
                _, lbl = self.pieces[idx]
                lbl_with_len = lbl.copy()
                lbl_with_len['cut_len_mm'] = self.pieces[idx][0]
                self._on_select(idx, lbl_with_len)

    def _show_tooltip(self, event, idx):
        _, lbl = self.pieces[idx]
        pos = lbl.get('pos', '?')
        lf = lbl.get('listofer_no', '?')
        dia = lbl.get('dia', self._model.dia)
        grade = lbl.get('grade', self._model.grade)
        length_mm = self.pieces[idx][0]
        wgt = CuttingPlanModel.piece_weight(length_mm, float(dia) if dia != '?' else 0)
        text = (
            f"Pos: {pos}\n"
            f"Listofer: {lf}\n"
            f"Dia: Ø{dia}\n"
            f"Grade: {grade}\n"
            f"Length: {length_mm:.0f} mm\n"
            f"Weight: {wgt:.3f} kg"
        )
        x = event.x + 15
        y = event.y + 15
        txt_obj = self.create_text(x, y, text=text, anchor='nw',
                                   font=('Arial', self._base_font_size),
                                   fill='black', tags='tooltip')
        bbox = self.bbox(txt_obj)
        if bbox:
            self.create_rectangle(bbox[0]-3, bbox[1]-3, bbox[2]+3, bbox[3]+3,
                                  fill=TOOLTIP_BG, outline='#aaa', tags='tooltip_bg')
            self.tag_raise(txt_obj)
        else:
            self.create_rectangle(x-5, y-5, x+200, y+80,
                                  fill=TOOLTIP_BG, outline='#aaa', tags='tooltip_bg')
        self._tooltip_items = ['tooltip', 'tooltip_bg']

    def _hide_tooltip(self):
        self.delete('tooltip', 'tooltip_bg')
        self._tooltip_items.clear()
        self._current_hover = None


# ----------------------------------------------------------------------
# Composite View – CuttingPlanFrame
# ----------------------------------------------------------------------
class CuttingPlanFrame(ttk.Frame):
    """
    A frame containing multiple CuttingDiagram instances, legend,
    info panel, zoom controls, and export buttons.
    """

    def __init__(self, parent, plans: List[Dict], stock_length_m: float = 12.0,
                 dia: float = 0, grade: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.model = CuttingPlanModel(plans, stock_length_m, dia, grade)
        self.zoom_level = 1.0
        self.canvases: List[CuttingDiagram] = []
        self.info_var = tk.StringVar(value="Click a piece to see details")
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()
        self.canvases.clear()

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 5))
        ttk.Button(toolbar, text="🔍 Zoom In", command=self.zoom_in).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔍 Zoom Out", command=self.zoom_out).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📷 Export All as PNG", command=self.export_png).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📋 Export All as SVG", command=self.export_svg).pack(side="left", padx=2)

        # Legend
        self.legend_frame = ttk.Frame(self)
        self.legend_frame.pack(fill="x", pady=2)
        self._build_legend()

        # Info panel
        ttk.Label(self, textvariable=self.info_var,
                  foreground='#0b2b4f', font=('Arial', 9, 'italic')).pack(fill="x", pady=(2, 5))

        # Scrollable canvas area
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        self.scroll_canvas = tk.Canvas(outer, highlightthickness=0)
        h_scroll = ttk.Scrollbar(outer, orient="horizontal", command=self.scroll_canvas.xview)
        v_scroll = ttk.Scrollbar(outer, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        self.scrollable_frame = ttk.Frame(self.scroll_canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        )
        self.scroll_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scroll_canvas.grid(row=0, column=0, sticky="nsew")
        h_scroll.grid(row=1, column=0, sticky="ew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        # Create diagrams
        for i, plan in enumerate(self.model.plans):
            bar_len_m = plan.get('bar_length', self.model.stock_length_m)
            bar_len_mm = bar_len_m * 1000

            pieces_raw = []
            for length_m, lbl in plan['bin']:
                lbl_full = {
                    'pos': lbl.get('pos', '?'),
                    'listofer_no': lbl.get('listofer_no', '?'),
                    'dia': lbl.get('dia', self.model.dia),
                    'grade': lbl.get('grade', self.model.grade),
                    **{k: v for k, v in lbl.items()
                       if k not in ('pos', 'listofer_no', 'dia', 'grade')}
                }
                length_mm = length_m * 1000
                pieces_raw.append((length_mm, lbl_full))

            header = ttk.Label(self.scrollable_frame,
                               text=f"Bar #{i+1}  (length: {bar_len_m:.2f} m)",
                               font=("Arial", 9, "bold"))
            header.pack(anchor="w", padx=5, pady=(5, 0))

            diagram = CuttingDiagram(
                self.scrollable_frame,
                model=self.model,
                stock_length_mm=bar_len_mm,
                on_select_callback=self._on_piece_select,
                zoom=self.zoom_level,
                width=600, height=int(70 * diagram._dpi_scale) if i == 0 else 80
            )
            diagram.pack(fill='x', padx=5, pady=2)
            diagram.set_plan(pieces_raw, bar_length_mm=bar_len_mm)
            self.canvases.append(diagram)

    def _build_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()
        color_map = self.model.get_all_colors()
        if not color_map:
            return
        for (lf, gd), color in sorted(color_map.items()):
            frm = ttk.Frame(self.legend_frame)
            frm.pack(side="left", padx=4, pady=2)
            swatch = tk.Canvas(frm, width=14, height=14, bg=color, highlightthickness=0)
            swatch.pack(side="left")
            ttk.Label(frm, text=f"LF{lf} {gd}",
                      font=('Arial', LEGEND_FONT_SIZE)).pack(side="left")

    def _on_piece_select(self, idx, lbl):
        pos = lbl.get('pos', '?')
        lf = lbl.get('listofer_no', '?')
        dia = lbl.get('dia', '?')
        grade = lbl.get('grade', '')
        length_mm = lbl.get('cut_len_mm', 0)
        try:
            d = float(dia)
            wgt = CuttingPlanModel.piece_weight(length_mm, d)
        except:
            wgt = 0.0
        self.info_var.set(
            f"Selected: Pos {pos}, LF {lf}, Dia Ø{dia}, Grade {grade}  |  "
            f"Length: {length_mm:.0f} mm, Weight: {wgt:.3f} kg"
        )

    # ---------- Zoom ----------
    def zoom_in(self):
        self.zoom_level = min(3.0, self.zoom_level * 1.2)
        for c in self.canvases:
            c.set_zoom(self.zoom_level)

    def zoom_out(self):
        self.zoom_level = max(0.5, self.zoom_level / 1.2)
        for c in self.canvases:
            c.set_zoom(self.zoom_level)

    # ---------- PNG Export ----------
    def export_png(self):
        if not PILLOW_AVAILABLE:
            messagebox.showerror("Missing Library",
                                 "Pillow is required for PNG export.\n"
                                 "Install it with: pip install Pillow")
            return
        if not self.model.plans:
            messagebox.showwarning("No Data", "No cutting plan to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile="cutting_plan.png"
        )
        if not filepath:
            return

        try:
            bar_height = 80
            bar_spacing = 40
            canvas_width = 800
            total_height = len(self.model.plans) * (bar_height + bar_spacing) + 60
            img = Image.new("RGB", (canvas_width, total_height), "white")
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 12)
                small_font = ImageFont.truetype("arial.ttf", 9)
            except:
                font = ImageFont.load_default()
                small_font = font

            y_offset = 20
            for i, plan in enumerate(self.model.plans):
                bar_len_m = plan.get('bar_length', self.model.stock_length_m)
                pieces = plan['bin']
                total_used = sum(p[0] for p in pieces)
                waste = bar_len_m - total_used if bar_len_m > total_used else 0.0
                scale = (canvas_width - 40) / bar_len_m

                draw.text((20, y_offset), f"Bar #{i+1}  Length: {bar_len_m:.2f} m",
                          fill="black", font=font)
                y_offset += 20

                x0 = 20
                y0 = y_offset + 10
                x1 = 20 + (bar_len_m * scale)
                y1 = y0 + 20
                draw.rectangle([x0, y0, x1, y1], outline="gray", width=2)

                x_cursor = x0
                for length_m, lbl in pieces:
                    width = length_m * scale
                    color = self.model.get_color(lbl.get('listofer_no', '?'),
                                                lbl.get('grade', ''))
                    draw.rectangle([x_cursor, y0, x_cursor + width, y1],
                                   fill=color, outline="white")
                    if width > 50:
                        pos = lbl.get('pos', '')
                        lf = lbl.get('listofer_no', '?')
                        text = f"{pos}/LF{lf}"
                        draw.text((x_cursor + width/2 - 15, y0 + 2), text,
                                  fill="white", font=small_font)
                    x_cursor += width

                if waste > 0.001:
                    waste_x = x_cursor
                    waste_w = waste * scale
                    draw.rectangle([waste_x, y0, waste_x + waste_w, y1],
                                   fill=DEFAULT_SCRAP_COLOR, outline="#ccc")
                    if waste_w > 30:
                        draw.text((waste_x + 2, y0 + 2), f"Waste {waste*1000:.0f} mm",
                                  fill=DEFAULT_SCRAP_TEXT_COLOR, font=small_font)

                y_offset += bar_height + bar_spacing

            draw.text((20, total_height - 25), "Generated by AI Rebar", fill="gray", font=small_font)
            img.save(filepath)
            messagebox.showinfo("Exported", f"PNG saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ---------- SVG Export ----------
    def export_svg(self):
        if not self.model.plans:
            messagebox.showwarning("No Data", "No cutting plan to export.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg")],
            initialfile="cutting_plan.svg"
        )
        if not filepath:
            return

        try:
            svg_width = 800
            margin = 20
            bar_h = 20
            gap = 60
            total_height = len(self.model.plans) * gap + 40
            svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{total_height}" '
                   f'viewBox="0 0 {svg_width} {total_height}" font-family="Arial, sans-serif">']
            y = 30
            for i, plan in enumerate(self.model.plans):
                bar_len_m = plan.get('bar_length', self.model.stock_length_m)
                scale = (svg_width - 2 * margin) / bar_len_m
                svg.append(f'  <text x="{margin}" y="{y-10}" font-size="12" font-weight="bold">'
                           f'Bar #{i+1} – {bar_len_m:.2f} m</text>')
                y += 5
                svg.append(f'  <line x1="{margin}" y1="{y+bar_h/2}" x2="{svg_width-margin}" '
                           f'y2="{y+bar_h/2}" stroke="#ccc" stroke-width="6"/>')

                x = margin
                for length_m, lbl in plan['bin']:
                    w = length_m * scale
                    color = self.model.get_color(lbl.get('listofer_no', '?'),
                                                lbl.get('grade', ''))
                    svg.append(f'  <rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" '
                               f'fill="{color}" stroke="white" stroke-width="1" rx="2">'
                               f'<title>Pos {lbl.get("pos","?")} LF{lbl.get("listofer_no","?")} Grade {lbl.get("grade","")}</title></rect>')
                    if w > 40:
                        label = f'{lbl.get("pos","?")}/LF{lbl.get("listofer_no","?")}'
                        svg.append(f'  <text x="{x + w/2:.1f}" y="{y + bar_h/2 + 4}" '
                                   f'text-anchor="middle" fill="white" font-size="8" font-weight="bold">'
                                   f'{label}</text>')
                    x += w
                waste = bar_len_m - sum(p[0] for p in plan['bin'])
                if waste > 0.001:
                    w = waste * scale
                    svg.append(f'  <rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" '
                               f'fill="#f0f0f0" stroke="#ccc" stroke-dasharray="4"/>')
                    if w > 30:
                        svg.append(f'  <text x="{x + w/2:.1f}" y="{y + bar_h/2 + 4}" '
                                   f'text-anchor="middle" fill="#e53e3e" font-size="8">'
                                   f'Waste</text>')
                y += gap
            svg.append('</svg>')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(svg))
            messagebox.showinfo("Exported", f"SVG saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))