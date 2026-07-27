# ui/custom_shape_designer.py
"""
Interactive designer for user‑defined rebar shapes.
Allows drawing of line and arc segments, assigning parameter names,
and saving the shape definition to the database.
Features: snap-to-grid, visual annotations, undo/redo,
proper arc drawing, and full geometry management.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math
import json
import re
from typing import List, Dict, Optional, Tuple

# Handle missing dependencies for standalone testing
try:
    from db.models import CustomShapeModel
    from shapes.definitions import default_shape_registry
except ImportError:
    CustomShapeModel = None
    default_shape_registry = None


class CustomShapeDesigner(tk.Toplevel):
    """Interactive designer for user-defined rebar shapes."""

    def __init__(self, parent, on_shape_saved=None):
        super().__init__(parent)
        self.parent = parent
        self.on_shape_saved = on_shape_saved
        self.title("Custom Shape Designer")
        self.geometry("1050x750")
        self.resizable(True, True)

        # Drawing state
        self.segments: List[Dict] = []
        self.points: List[Tuple[float, float]] = [(0.0, 0.0)]
        self.drawing = False
        self.start_node: Optional[Tuple[float, float]] = None
        self.current_temp: Optional[Dict] = None

        # Undo/Redo stacks
        self.undo_stack: List[Tuple[List[Dict], List[Tuple[float, float]]]] = []
        self.redo_stack: List[Tuple[List[Dict], List[Tuple[float, float]]]] = []

        # Grid & snap
        self.grid_size = 10.0
        self.snap_enabled = tk.BooleanVar(value=False)

        # Transform state (will be updated in _redraw)
        self._scale = 1.0
        self._offset_x = 50
        self._offset_y = 300

        self._build_ui()
        self._bind_events()
        # ★ رفع مشکل نقطه شروع: رسم اولیه را با تأخیر انجام بده تا ابعاد بوم واقعی شوند
        self.after(50, self._redraw)

    # ----------------------------------------------------------------------
    # UI construction
    # ----------------------------------------------------------------------
    def _build_ui(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        # Left: drawing canvas
        self.canvas = tk.Canvas(paned, bg="white", highlightthickness=1,
                                highlightbackground="gray")
        paned.add(self.canvas, weight=3)

        # Right: control panel
        ctrl_frame = ttk.Frame(paned, padding=5)
        paned.add(ctrl_frame, weight=1)

        # Shape code & name
        ttk.Label(ctrl_frame, text="Shape Code:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.code_var = tk.StringVar(value="CUST01")
        ttk.Entry(ctrl_frame, textvariable=self.code_var, width=12).pack(fill="x", pady=2)

        ttk.Label(ctrl_frame, text="Shape Name:").pack(anchor="w", pady=(8, 0))
        self.name_var = tk.StringVar(value="My Custom Shape")
        ttk.Entry(ctrl_frame, textvariable=self.name_var, width=25).pack(fill="x", pady=2)

        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill="x", pady=10)

        # Drawing tools
        ttk.Label(ctrl_frame, text="Drawing Tools", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.tool_mode = tk.StringVar(value="line")
        ttk.Radiobutton(ctrl_frame, text="➕ Line", variable=self.tool_mode, value="line").pack(anchor="w")
        ttk.Radiobutton(ctrl_frame, text="🔄 Arc (CW)", variable=self.tool_mode, value="arc_cw").pack(anchor="w")
        ttk.Radiobutton(ctrl_frame, text="🔄 Arc (CCW)", variable=self.tool_mode, value="arc_ccw").pack(anchor="w")

        ttk.Checkbutton(ctrl_frame, text="Snap to Grid (10 mm)", variable=self.snap_enabled).pack(anchor="w", pady=5)

        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill="x", pady=10)

        # Undo / Redo
        undo_redo_frame = ttk.Frame(ctrl_frame)
        undo_redo_frame.pack(fill="x", pady=2)
        self.undo_btn = ttk.Button(undo_redo_frame, text="↩ Undo", command=self.undo)
        self.undo_btn.pack(side="left", padx=2, expand=True, fill="x")
        self.redo_btn = ttk.Button(undo_redo_frame, text="↪ Redo", command=self.redo)
        self.redo_btn.pack(side="left", padx=2, expand=True, fill="x")
        self._update_undo_redo_buttons()

        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill="x", pady=10)

        # Segment list with scrollbar
        ttk.Label(ctrl_frame, text="Segments:", font=("Arial", 10, "bold")).pack(anchor="w")
        list_frame = ttk.Frame(ctrl_frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.segment_listbox = tk.Listbox(list_frame, height=10, width=30, yscrollcommand=scrollbar.set)
        self.segment_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.segment_listbox.yview)
        self.segment_listbox.bind("<Double-Button-1>", self._on_edit_segment)

        # Segment action buttons
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="✏️ Edit", command=self._edit_selected_segment).pack(side="left", padx=2, expand=True)
        ttk.Button(btn_frame, text="🗑️ Delete", command=self._delete_selected_segment).pack(side="left", padx=2, expand=True)
        ttk.Button(btn_frame, text="🧹 Clear All", command=self._clear_all).pack(side="left", padx=2, expand=True)

        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill="x", pady=10)

        # Save & Close
        ttk.Button(ctrl_frame, text="💾 Save Shape", command=self._save_shape).pack(fill="x", pady=5)
        ttk.Button(ctrl_frame, text="❌ Close", command=self.destroy).pack(fill="x", pady=2)

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-Z>", lambda e: self.redo())

    # ----------------------------------------------------------------------
    # Coordinate transforms (auto-scale and snap)
    # ----------------------------------------------------------------------
    def _update_transform(self):
        """Compute scale and offset so that all points fit nicely."""
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 400
        margin = 50

        # If only one point, center it
        if len(self.points) <= 1:
            self._scale = 1.0
            self._offset_x = w / 2
            self._offset_y = h / 2
            return

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y
        if width == 0:
            width = 100
        if height == 0:
            height = 100

        scale = min((w - 2 * margin) / width, (h - 2 * margin) / height)
        self._scale = scale
        self._offset_x = margin - min_x * scale + (w - 2 * margin - width * scale) / 2
        self._offset_y = margin - min_y * scale + (h - 2 * margin - height * scale) / 2

    def _to_canvas(self, x_mm, y_mm):
        self._update_transform()
        return (
            self._offset_x + x_mm * self._scale,
            self._offset_y - y_mm * self._scale   # flip y
        )

    def _from_canvas(self, canvas_x, canvas_y):
        return (
            (canvas_x - self._offset_x) / self._scale,
            (self._offset_y - canvas_y) / self._scale
        )

    def _snap(self, x_mm, y_mm):
        if self.snap_enabled.get():
            gs = self.grid_size
            x_mm = round(x_mm / gs) * gs
            y_mm = round(y_mm / gs) * gs
        return x_mm, y_mm

    # ----------------------------------------------------------------------
    # Drawing interaction
    # ----------------------------------------------------------------------
    def _on_click(self, event):
        if self.drawing:
            return
        last = self.points[-1]
        x_can, y_can = self._to_canvas(last[0], last[1])
        # Euclidean distance to start point
        if math.hypot(event.x - x_can, event.y - y_can) > 20:
            return

        self.drawing = True
        self.start_node = last
        mode = self.tool_mode.get()
        if mode == "line":
            self.current_temp = {'type': 'line', 'param': ''}
        elif mode in ("arc_cw", "arc_ccw"):
            self.current_temp = {
                'type': 'arc',
                'direction': 'cw' if mode == 'arc_cw' else 'ccw',
                'angle': 90,
                'radius_param': ''
            }

    def _on_drag(self, event):
        if not self.drawing or self.tool_mode.get() != "line":
            return
        self.canvas.delete("temp")
        x1, y1 = self._to_canvas(self.start_node[0], self.start_node[1])
        ex, ey = event.x, event.y
        if self.snap_enabled.get():
            ex_mm, ey_mm = self._from_canvas(ex, ey)
            ex_mm, ey_mm = self._snap(ex_mm, ey_mm)
            ex, ey = self._to_canvas(ex_mm, ey_mm)
        self.canvas.create_line(x1, y1, ex, ey, dash=(4, 2), tags="temp", fill="gray")

    def _on_release(self, event):
        if not self.drawing:
            return
        mode = self.tool_mode.get()
        last = self.start_node

        if mode == "line":
            ex_mm, ey_mm = self._from_canvas(event.x, event.y)
            ex_mm, ey_mm = self._snap(ex_mm, ey_mm)
            dx = ex_mm - last[0]
            dy = ey_mm - last[1]
            length = math.hypot(dx, dy)
            if length < 1:
                self.drawing = False
                self.canvas.delete("temp")
                return

            angle = math.atan2(dy, dx)
            param_name = simpledialog.askstring(
                "Parameter Name", "Enter parameter for this line (e.g., A, B, L1):", parent=self
            )
            if not param_name or not param_name.strip():
                self.drawing = False
                self.canvas.delete("temp")
                return

            self.current_temp['param'] = param_name.strip()
            self.current_temp['direction_ang'] = angle
            self.current_temp['_preview_length'] = length   # store drawn length for preview rebuild

            self._push_state()
            self.segments.append(self.current_temp)
            self.points.append((ex_mm, ey_mm))
            self._update_segment_list()
            self._clear_redo()
            self.drawing = False
            self._redraw()

        elif "arc" in mode:
            param_name_r = simpledialog.askstring(
                "Radius Parameter", "Enter parameter name for radius (e.g., R1):", parent=self
            )
            if not param_name_r or not param_name_r.strip():
                self.drawing = False
                return

            angle_str = simpledialog.askstring(
                "Arc Angle", "Enter angle in degrees (default 90):", parent=self, initialvalue="90"
            )
            # Handle Cancel
            if angle_str is None:
                self.drawing = False
                return
            try:
                angle = float(angle_str.strip())
                if angle <= 0 or angle > 360:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Angle", "Angle must be between 1 and 360 degrees.", parent=self)
                self.drawing = False
                return

            self.current_temp['radius_param'] = param_name_r.strip()
            self.current_temp['angle'] = angle

            default_radius = 100.0
            self._compute_arc_endpoint(self.current_temp, default_radius)

            self._push_state()
            self.segments.append(self.current_temp)
            self._update_segment_list()
            self._clear_redo()
            self.drawing = False
            self._redraw()

    def _compute_arc_endpoint(self, seg, radius):
        """Compute arc endpoint based on previous segment direction."""
        if len(self.segments) > 0:
            prev = self.segments[-1]
            ang = prev.get('direction_ang', 0.0) if prev['type'] == 'line' else prev.get('end_direction_ang', 0.0)
        else:
            ang = 0.0

        last = self.points[-1]
        angle_deg = seg['angle']
        direction = seg.get('direction', 'cw')

        if direction == 'cw':
            cx = last[0] - math.sin(ang) * radius
            cy = last[1] + math.cos(ang) * radius
            new_ang = ang - math.radians(angle_deg)
        else:
            cx = last[0] + math.sin(ang) * radius
            cy = last[1] - math.cos(ang) * radius
            new_ang = ang + math.radians(angle_deg)

        end_x = cx + radius * math.cos(new_ang)
        end_y = cy + radius * math.sin(new_ang)
        self.points.append((end_x, end_y))
        seg['end_direction_ang'] = new_ang
        seg['_preview_radius'] = radius

    # ----------------------------------------------------------------------
    # Undo / Redo
    # ----------------------------------------------------------------------
    def _push_state(self):
        self.undo_stack.append((
            [dict(s) for s in self.segments],
            list(self.points)
        ))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

    def _clear_redo(self):
        self.redo_stack.clear()
        self._update_undo_redo_buttons()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(([dict(s) for s in self.segments], list(self.points)))
        self.segments, self.points = self.undo_stack.pop()
        self._update_segment_list()
        self._redraw()
        self._update_undo_redo_buttons()

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(([dict(s) for s in self.segments], list(self.points)))
        self.segments, self.points = self.redo_stack.pop()
        self._update_segment_list()
        self._redraw()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self.undo_btn.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self.redo_btn.config(state=tk.NORMAL if self.redo_stack else tk.DISABLED)

    def _clear_all(self):
        if messagebox.askyesno("Clear All", "Are you sure you want to clear the canvas?", parent=self):
            self._push_state()
            self.segments.clear()
            self.points = [(0.0, 0.0)]
            self._update_segment_list()
            self._clear_redo()
            self._redraw()

    # ----------------------------------------------------------------------
    # Drawing helpers
    # ----------------------------------------------------------------------
    def _redraw(self):
        self.canvas.delete("all")
        if not self.points:
            return
        self._update_transform()

        if self.snap_enabled.get():
            self._draw_grid()

        # Draw each segment
        for i, seg in enumerate(self.segments):
            p1 = self.points[i]
            p2 = self.points[i+1] if i+1 < len(self.points) else p1
            x1, y1 = self._to_canvas(p1[0], p1[1])
            x2, y2 = self._to_canvas(p2[0], p2[1])

            if seg['type'] == 'line':
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
            else:
                self._draw_arc_segment(seg, i)

            # Annotate parameter
            param = seg.get('param') if seg['type'] == 'line' else seg.get('radius_param')
            if param:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                dx = x2 - x1
                dy = y2 - y1
                length = math.hypot(dx, dy)
                if length > 0:
                    nx = -dy / length * 15
                    ny = dx / length * 15
                else:
                    nx, ny = 0, -15
                self.canvas.create_text(mx + nx, my + ny, text=param,
                                        fill="darkgreen", font=("Arial", 10, "bold"))

        # Draw nodes
        for idx, (x, y) in enumerate(self.points):
            xc, yc = self._to_canvas(x, y)
            color = "blue" if idx == 0 else "red"   # highlight start node
            self.canvas.create_oval(xc-4, yc-4, xc+4, yc+4, fill=color, outline="")

    def _draw_arc_segment(self, seg, idx):
        """Draw arc as a series of short line segments (polar approximation)."""
        p1 = self.points[idx]
        radius = seg.get('_preview_radius', 100.0)
        angle_deg = seg['angle']
        direction = seg.get('direction', 'cw')

        if idx > 0:
            prev = self.segments[idx-1]
            ang = prev.get('direction_ang', 0.0) if prev['type'] == 'line' else prev.get('end_direction_ang', 0.0)
        else:
            ang = 0.0

        # Compute arc center and polar start angle
        if direction == 'cw':
            cx = p1[0] - math.sin(ang) * radius
            cy = p1[1] + math.cos(ang) * radius
            start_theta = ang - math.pi/2   # vector from center to p1
            total_rad = -math.radians(angle_deg)
        else:
            cx = p1[0] + math.sin(ang) * radius
            cy = p1[1] - math.cos(ang) * radius
            start_theta = ang + math.pi/2
            total_rad = math.radians(angle_deg)

        # Number of steps based on angle magnitude
        n_steps = max(10, int(angle_deg / 5))
        last_x, last_y = p1

        for step in range(1, n_steps + 1):
            fraction = step / n_steps
            theta = start_theta + total_rad * fraction
            px = cx + radius * math.cos(theta)
            py = cy + radius * math.sin(theta)

            xc1, yc1 = self._to_canvas(last_x, last_y)
            xc2, yc2 = self._to_canvas(px, py)
            self.canvas.create_line(xc1, yc1, xc2, yc2, fill="blue", width=2)
            last_x, last_y = px, py

    def _draw_grid(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        gs = self.grid_size * self._scale
        if gs < 5:
            return

        # Vertical lines
        x = 0.0
        while x < w:
            self.canvas.create_line(x, 0, x, h, fill="#e0e0e0", dash=(1, 3))
            x += gs
        # Horizontal lines
        y = 0.0
        while y < h:
            self.canvas.create_line(0, y, w, y, fill="#e0e0e0", dash=(1, 3))
            y += gs

    def _update_segment_list(self):
        self.segment_listbox.delete(0, tk.END)
        for i, seg in enumerate(self.segments):
            if seg['type'] == 'line':
                desc = f"Line: {seg.get('param', '?')}"
            else:
                desc = f"Arc ({seg.get('direction', '?')}) angle={seg.get('angle', 90)}° rad={seg.get('radius_param', '?')}"
            self.segment_listbox.insert(tk.END, f"{i+1}: {desc}")

    # ----------------------------------------------------------------------
    # Segment editing
    # ----------------------------------------------------------------------
    def _edit_selected_segment(self):
        sel = self.segment_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.segments):
            return

        seg = self.segments[idx]
        if seg['type'] == 'line':
            new_param = simpledialog.askstring("Edit Parameter", "Parameter name:",
                                               initialvalue=seg.get('param', ''), parent=self)
            if new_param and new_param.strip():
                self._push_state()
                seg['param'] = new_param.strip()
                self._update_segment_list()
                self._clear_redo()
                self._redraw()
        else:
            new_rparam = simpledialog.askstring("Edit Radius Param", "Radius param name:",
                                                initialvalue=seg.get('radius_param', ''), parent=self)
            if new_rparam and new_rparam.strip():
                seg['radius_param'] = new_rparam.strip()
            new_angle_str = simpledialog.askstring("Edit Angle", "Angle (deg):",
                                                   initialvalue=str(seg.get('angle', 90)), parent=self)
            if new_angle_str is not None:
                try:
                    seg['angle'] = float(new_angle_str.strip())
                except ValueError:
                    pass

            self._push_state()
            # Recompute endpoints after editing
            self._rebuild_points_from(idx)
            self._update_segment_list()
            self._clear_redo()
            self._redraw()

    def _delete_selected_segment(self):
        sel = self.segment_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.segments):
            return

        self._push_state()
        del self.segments[idx]
        self._rebuild_points_from(idx)
        self._update_segment_list()
        self._clear_redo()
        self._redraw()

    def _rebuild_points_from(self, start_idx):
        """Recompute points from start_idx onward, keeping previous points intact."""
        if start_idx == 0:
            self.points = [(0.0, 0.0)]
        else:
            self.points = self.points[:start_idx+1]  # keep nodes up to the segment before the removed one

        # Determine current direction from the last kept segment
        curr_ang = 0.0
        if len(self.points) > 1 and start_idx > 0 and (start_idx - 1) < len(self.segments):
            prev = self.segments[start_idx - 1]
            if prev['type'] == 'line':
                curr_ang = prev.get('direction_ang', 0.0)
            else:
                curr_ang = prev.get('end_direction_ang', 0.0)

        # Rebuild remaining segments
        for i in range(start_idx, len(self.segments)):
            seg = self.segments[i]
            last = self.points[-1]
            if seg['type'] == 'line':
                L = seg.get('_preview_length', 100.0)   # Use stored preview length
                ang = seg.get('direction_ang', curr_ang)
                next_pt = (last[0] + L * math.cos(ang), last[1] + L * math.sin(ang))
                self.points.append(next_pt)
                curr_ang = ang
            else:  # arc
                R = seg.get('_preview_radius', 100.0)
                angle_deg = seg['angle']
                direction = seg.get('direction', 'cw')
                if direction == 'cw':
                    cx = last[0] - math.sin(curr_ang) * R
                    cy = last[1] + math.cos(curr_ang) * R
                    new_ang = curr_ang - math.radians(angle_deg)
                else:
                    cx = last[0] + math.sin(curr_ang) * R
                    cy = last[1] - math.cos(curr_ang) * R
                    new_ang = curr_ang + math.radians(angle_deg)
                end = (cx + R * math.cos(new_ang), cy + R * math.sin(new_ang))
                self.points.append(end)
                curr_ang = new_ang
                seg['end_direction_ang'] = new_ang
                seg['_preview_radius'] = R

    def _on_edit_segment(self, event=None):
        self._edit_selected_segment()

    # ----------------------------------------------------------------------
    # Save shape definition
    # ----------------------------------------------------------------------
    def _save_shape(self):
        code = self.code_var.get().strip()
        name = self.name_var.get().strip()
        if not code or not name:
            messagebox.showerror("Error", "Code and name are required.", parent=self)
            return
        if not self.segments:
            messagebox.showerror("Error", "No segments drawn.", parent=self)
            return
        # Allow alphanumeric, underscore, hyphen
        if not re.match(r'^[A-Za-z0-9_-]+$', code):
            messagebox.showwarning("Warning", "Shape code may contain letters, numbers, underscore or hyphen.", parent=self)
            return

        definition = {"segments": []}
        for seg in self.segments:
            if seg['type'] == 'line':
                definition["segments"].append({
                    "type": "line",
                    "param": seg['param']
                })
            else:
                angle = seg.get('angle', 90)
                if angle <= 0 or angle > 360:
                    messagebox.showerror("Error", "Arc angle must be between 1 and 360 degrees.", parent=self)
                    return
                definition["segments"].append({
                    "type": "arc",
                    "direction": seg['direction'],
                    "angle": angle,
                    "radius_param": seg['radius_param']
                })

        # Persist to database if available
        if CustomShapeModel:
            existing = CustomShapeModel.get_by_code(code)
            if existing:
                if not messagebox.askyesno("Overwrite", f"Shape code '{code}' already exists. Overwrite?", parent=self):
                    return
                CustomShapeModel.update(code, name, definition)
            else:
                CustomShapeModel.create(code, name, definition)
        else:
            # Standalone mode: just print JSON
            print(f"MOCK SAVE: {code} - {name}\n{json.dumps(definition, indent=2)}")

        if default_shape_registry:
            default_shape_registry.refresh()

        if self.on_shape_saved:
            self.on_shape_saved()

        messagebox.showinfo("Success", f"Shape '{code} – {name}' saved.", parent=self)
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = CustomShapeDesigner(root)
    root.mainloop()