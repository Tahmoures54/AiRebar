# ui/input_dialog.py
"""Rebar input dialog – premium UI via input_dialog_ui."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import json
import datetime
import getpass
import re
import importlib

from shapes.definitions import default_shape_registry
from shapes.constants import set_standard, CURRENT_STANDARD
from db.models import RebarModel, ListoferModel
from utils.logger import setup_logger
from utils.i18n import t
from config import ELEMENT_TYPES, STANDARD_DIAMETERS, REBAR_GRADES, DEFAULT_REBAR_GRADE

try:
    from shapes.drawing import draw_shape_on_canvas, DRAW_FUNCTIONS
    DRAW_AVAILABLE = True
except Exception:
    DRAW_AVAILABLE = False
    DRAW_FUNCTIONS = {}

logger = setup_logger("RebarAgent.InputDialog")

STANDARD_DISPLAY_MAP = {
    "bs": "BS 8666 (UK)", "ir": "Iran – Mabhas 9", "aci": "ACI 318 – USA",
    "ec": "Eurocode 2", "is": "IS 2502 – India", "gb": "GB 50010 – China",
    "jis": "JIS G 3112 – Japan", "as": "AS 3600 – Australia", "nbr": "NBR 6118 – Brazil",
}
STANDARD_ALIASES = {
    "bs": ("bs", "bs8666"), "ir": ("ir", "mabhas9", "mabhas"),
    "aci": ("aci", "aci318"), "ec": ("ec", "ec2", "ec2-", "eurocode", "eurocode2"),
    "is": ("is", "is2502"), "gb": ("gb", "gb50010"), "jis": ("jis",),
    "as": ("as", "as3600"), "nbr": ("nbr", "nbr6118"),
}
STD_CODE_TO_MODULE = {
    "ir": "mabhas9", "bs": "bs8666", "aci": "aci318", "ec": "eurocode2",
    "is": "is2502", "gb": "gb50010", "jis": "jis", "as": "as3600", "nbr": "nbr6118",
}


class InputDialog(tk.Toplevel):
    WINDOW_W, WINDOW_H = 1250, 820
    MIN_W, MIN_H = 1050, 800
    CANVAS_W, CANVAS_H = 700, 420
    PREVIEW_DELAY_MS = 80

    def __init__(self, parent, project_id, callback, edit_data=None):
        super().__init__(parent)
        self.parent = parent
        self.project_id = project_id
        self.callback = callback
        self.current_user = getpass.getuser()
        self.edit_data = edit_data or {}
        self.editing = edit_data is not None
        self.title(t("input.edit_title") if self.editing else t("input.add_title"))
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.vcmd_numeric = (self.register(self._validate_numeric_input), "%P")
        self.vcmd_int = (self.register(self._validate_int_input), "%P")
        self.all_shape_keys = list(default_shape_registry.flat_shapes.keys())
        if not self.all_shape_keys:
            messagebox.showwarning("Shape Error", "No shape definitions loaded.", parent=self)
        self.filtered_shape_keys: list[str] = []
        self.shape_var = tk.StringVar()
        self.listofer_numbers = ListoferModel.get_numbers(project_id)
        self.listofer_var = tk.StringVar()
        self.listofer_new_var = tk.StringVar()
        self.listofer_desc_var = tk.StringVar()
        self.auto_listofer_number = self._generate_next_listofer_number()
        self.listofer_new_var.set(self.auto_listofer_number)
        self.param_entries: dict[str, tk.StringVar] = {}
        self.length_label_var = tk.StringVar(value="Total cut length: -- mm")
        self.shape_hint_var = tk.StringVar(value="")
        self.keep_open_var = tk.BooleanVar(value=True)
        self._preview_after_id = None
        self._suspend_standard_callback = False
        self._build_ui()
        self._populate_standard_combo()
        initial_code = "bs"
        self._set_standard_display(initial_code)
        self._filter_by_standard(initial_code, show_hint=True)
        if self.filtered_shape_keys:
            self.shape_var.set(self.filtered_shape_keys[0])
        if self.editing:
            self._load_edit_data()
        else:
            self._on_shape_changed()
        self._apply_geometry()
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass
        self.after(120, self._update_preview)

    def _build_ui(self):
        from ui.input_dialog_ui import build_premium_input_ui
        build_premium_input_ui(self)

    def _apply_geometry(self):
        self.minsize(self.MIN_W, self.MIN_H)
        W, H = self.WINDOW_W, self.WINDOW_H
        self.withdraw()
        self.update_idletasks()
        try:
            self.parent.update_idletasks()
            px, py = self.parent.winfo_rootx(), self.parent.winfo_rooty()
            pw, ph = max(1, self.parent.winfo_width()), max(1, self.parent.winfo_height())
            x, y = px + (pw // 2) - (W // 2), py + (ph // 2) - (H // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (W // 2)
            y = (self.winfo_screenheight() // 2) - (H // 2)
        x = max(0, min(x, self.winfo_screenwidth() - W))
        y = max(0, min(y, self.winfo_screenheight() - H - 40))
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.deiconify()

    def _validate_numeric_input(self, P):
        if P in ("", "."):
            return True
        try:
            return float(P) >= 0
        except ValueError:
            return False

    def _validate_int_input(self, P):
        return P == "" or P.isdigit()

    def _normalize_text(self, value):
        return str(value or "").strip().lower()

    def _extract_lead_token(self, text):
        txt = self._normalize_text(text)
        if " - " in txt:
            txt = txt.split(" - ", 1)[0].strip()
        return txt

    def _text_matches_standard(self, text, standard_code):
        token = self._extract_lead_token(text)
        for alias in STANDARD_ALIASES.get(standard_code, (standard_code,)):
            a = alias.lower()
            if token == a or token.startswith(a):
                return True
        return False

    def _shape_belongs_to_standard(self, shape_key, standard_code):
        if self._text_matches_standard(shape_key, standard_code):
            return True
        shape_def = default_shape_registry.flat_shapes.get(shape_key, {}) or {}
        for item in [shape_def.get(k) for k in ("code", "standard_code", "standard", "source_standard", "prefix")]:
            if item and self._text_matches_standard(item, standard_code):
                return True
        return False

    def _get_shape_keys_for_standard(self, standard_code):
        standard_code = (standard_code or "bs").strip().lower()
        try:
            registry_keys = default_shape_registry.get_shape_keys_by_standard(standard_code) or []
        except Exception:
            registry_keys = []
        if registry_keys:
            return list(registry_keys)
        return [k for k in self.all_shape_keys if self._shape_belongs_to_standard(k, standard_code)]

    def _generate_next_listofer_number(self):
        numbers = self.listofer_numbers
        if not numbers:
            return "L-001"
        pat = re.compile(r"^[A-Za-z]+-0*(\d+)$", re.IGNORECASE)
        max_num = 0
        for num in numbers:
            m = pat.match(num)
            if m:
                max_num = max(max_num, int(m.group(1)))
        return f"L-{max_num + 1:03d}"

    def _load_edit_data(self):
        data = self.edit_data
        listofer_no = data.get("listofer_number")
        if listofer_no and listofer_no in self.listofer_numbers:
            self.new_listofer_check.set(False)
            self._toggle_listofer()
            self.listofer_var.set(listofer_no)
        else:
            self.new_listofer_check.set(True)
            self._toggle_listofer()
            if listofer_no:
                self.listofer_new_var.set(listofer_no)
        self.listofer_desc_var.set(data.get("listofer_desc") or "")
        self.pos_var.set(str(data.get("pos", "") or ""))
        self.dia_var.set(str(data.get("diameter", "") or "10"))
        self.element_var.set(data.get("element_type") or "Column")
        self.location_var.set(data.get("location") or "")
        std_code = (data.get("standard") or CURRENT_STANDARD or "bs").strip().lower()
        if std_code not in STANDARD_DISPLAY_MAP:
            std_code = "bs"
        self._set_standard_display(std_code)
        self.grade_var.set(data.get("grade", DEFAULT_REBAR_GRADE) or DEFAULT_REBAR_GRADE)
        self._filter_by_standard(std_code, show_hint=True)
        shape = data.get("shape_name")
        if shape in default_shape_registry.flat_shapes:
            self.shape_var.set(shape)
            self._on_shape_changed()
            try:
                dims = json.loads(data.get("dimensions", "{}"))
            except Exception:
                dims = {}
            for k, var in self.param_entries.items():
                var.set(str(dims.get(k, 10)))
        self.quantity_var.set(str(data.get("quantity", "1") or "1"))

    def _populate_standard_combo(self):
        self._display_to_code = {}
        display_values = []
        for code, display in STANDARD_DISPLAY_MAP.items():
            self._display_to_code[display] = code
            display_values.append(display)
        self.standard_combo["values"] = display_values
        self.standard_var.set(STANDARD_DISPLAY_MAP["bs"])

    def _set_standard_display(self, code):
        display = STANDARD_DISPLAY_MAP.get(code, code)
        self._suspend_standard_callback = True
        try:
            self.standard_var.set(display)
        finally:
            self._suspend_standard_callback = False

    def _get_standard_code(self):
        return self._display_to_code.get(self.standard_var.get(), "bs")

    def _filter_by_standard(self, standard_code, show_hint=False):
        standard_code = (standard_code or "bs").strip().lower()
        keys = self._get_shape_keys_for_standard(standard_code)
        self.filtered_shape_keys = keys or []
        if show_hint:
            label = STANDARD_DISPLAY_MAP.get(standard_code, standard_code)
            self.shape_hint_var.set(f"{len(self.filtered_shape_keys)} shape(s) for {label}" if keys else f"No shapes for {label}")
        self.shape_combo["values"] = self.filtered_shape_keys
        if self.filtered_shape_keys:
            if self.shape_var.get() not in self.filtered_shape_keys:
                self.shape_var.set(self.filtered_shape_keys[0])
        else:
            self.shape_var.set("")
        self._on_shape_changed()

    def _open_designer(self):
        try:
            self.parent.open_custom_shape_designer()
        except AttributeError:
            messagebox.showerror("Error", "Custom shape designer not available", parent=self)
            return
        default_shape_registry.refresh()
        self.all_shape_keys = list(default_shape_registry.flat_shapes.keys())
        self._filter_by_standard(self._get_standard_code(), show_hint=True)

    def _filter_shapes(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        text = (self.shape_var.get() or "").lower().strip()
        if not text:
            self.shape_combo["values"] = self.filtered_shape_keys
            self._schedule_preview()
            return
        self.shape_combo["values"] = [k for k in self.filtered_shape_keys if text in k.lower()]
        self._schedule_preview()

    def _toggle_listofer(self):
        if self.new_listofer_check.get():
            self.listofer_combo.config(state="disabled")
            self.listofer_new_entry.config(state="normal")
            self.listofer_var.set("")
        else:
            self.listofer_combo.config(state="normal")
            self.listofer_new_entry.config(state="disabled")

    def _on_standard_changed(self, event=None):
        if self._suspend_standard_callback:
            return
        selected_display = self.standard_combo.get()
        self.after_idle(lambda d=selected_display: self._apply_standard_change_by_display(d))

    def _apply_standard_change_by_display(self, selected_display):
        new_std = self._display_to_code.get(selected_display, "bs")
        try:
            set_standard(new_std)
        except Exception:
            pass
        self._filter_by_standard(new_std, show_hint=True)
        self._schedule_preview()

    def _on_shape_changed(self):
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()
        shape_name = self.shape_var.get()
        if not shape_name or shape_name not in default_shape_registry.flat_shapes:
            self._schedule_preview()
            return
        shape_def = default_shape_registry.flat_shapes[shape_name]
        defaults = default_shape_registry.get_default_params(shape_name)
        for i, param in enumerate(shape_def.get("params", [])):
            ttk.Label(self.param_frame, text=f"{param} (mm):").grid(row=i, column=0, padx=6, pady=4, sticky="w")
            var = tk.StringVar(value=str(defaults.get(param, 10)))
            ttk.Entry(self.param_frame, textvariable=var, width=12, validate="key", validatecommand=self.vcmd_numeric).grid(row=i, column=1, padx=6, pady=4, sticky="w")
            self.param_entries[param] = var
            var.trace_add("write", lambda *a: self._schedule_preview())
        self._schedule_preview()

    def _schedule_preview(self):
        if self._preview_after_id is not None:
            try:
                self.after_cancel(self._preview_after_id)
            except Exception:
                pass
        self._preview_after_id = self.after(self.PREVIEW_DELAY_MS, self._update_preview)

    def _get_standard_code_for_shape(self, shape_key: str) -> str:
        try:
            sc = (default_shape_registry.flat_shapes.get(shape_key) or {}).get("standard_code") or ""
            if sc:
                return sc.strip().lower()
        except Exception:
            pass
        return self._get_standard_code()

    def _update_preview(self):
        self._preview_after_id = None
        shape_name = self.shape_var.get()
        if not shape_name or shape_name not in default_shape_registry.flat_shapes:
            self.canvas.delete("all")
            self.length_label_var.set("Total cut length: --")
            self.error_label.config(text="")
            return
        params = {}
        for k, var in self.param_entries.items():
            try:
                params[k] = float(var.get())
            except ValueError:
                params[k] = 0.0
        try:
            diameter = float(self.dia_var.get())
        except ValueError:
            diameter = 10.0
        self.canvas.delete("all")
        shape_def = default_shape_registry.flat_shapes.get(shape_name) or {}
        draw_func_name = (shape_def.get("draw_func") or "draw_generic").strip()
        drawn = False
        if DRAW_AVAILABLE and (draw_func_name in DRAW_FUNCTIONS or draw_func_name in ("draw_generic", "draw_svg_template", "draw_custom_segmented")):
            try:
                draw_shape_on_canvas(self.canvas, shape_name, params, diameter)
                drawn = True
            except Exception as e:
                logger.warning(f"Preview draw failed: {e}")
        if not drawn and draw_func_name not in ("draw_generic", "draw_svg_template", "draw_custom_segmented"):
            module_name = STD_CODE_TO_MODULE.get(self._get_standard_code_for_shape(shape_name))
            if module_name:
                try:
                    mod = importlib.import_module(f"shapes.standards.{module_name}")
                    draw_func = getattr(mod, draw_func_name, None)
                    if callable(draw_func):
                        draw_func(self.canvas, shape_name, params, diameter)
                        drawn = True
                except Exception:
                    pass
        if not drawn:
            try:
                if DRAW_AVAILABLE:
                    draw_shape_on_canvas(self.canvas, shape_name, params, diameter)
                else:
                    self._draw_fallback(shape_name, params, diameter)
            except Exception:
                self._draw_fallback(shape_name, params, diameter)
        try:
            length_mm = default_shape_registry.calc_shape_length(shape_name, params, diameter)
            self.length_label_var.set(f"✂  Cut length  {length_mm:.1f} mm   ·   {length_mm/1000:.3f} m")
            self.error_label.config(text="")
        except Exception:
            self.length_label_var.set("Total cut length: --")
            self.error_label.config(text="Invalid dimensions for this shape")

    def _draw_fallback(self, shape_name, params, diameter):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        try:
            total_length = default_shape_registry.calc_shape_length(shape_name, params, diameter)
        except Exception:
            total_length = 500.0
        margin = 50
        scale = max(10, cw - 2 * margin) / total_length if total_length > 0 else 1.0
        x1, y = margin, ch // 2
        x2 = x1 + total_length * scale
        self.canvas.create_line(x1, y, x2, y, fill="#22d3ee", width=3)
        self.canvas.create_text(cw // 2, y - 20, text=shape_name, fill="#e2e8f0", font=("Segoe UI", 10, "bold"))
        dim_text = ", ".join(f"{k}={v:.0f}" for k, v in params.items())
        self.canvas.create_text(cw // 2, y + 15, text=dim_text, fill="#94a3b8", font=("Segoe UI", 8))
        self.canvas.create_text(cw // 2, y + 35, text=f"Ø {diameter} mm", fill="#64748b", font=("Segoe UI", 8))

    def _save_bar(self):
        if self.new_listofer_check.get():
            listofer_number = self.listofer_new_var.get().strip()
            if not listofer_number:
                messagebox.showerror("Error", "Enter a Listofer number.", parent=self)
                return
        else:
            listofer_number = self.listofer_var.get().strip()
            if not listofer_number:
                messagebox.showerror("Error", "Select a Listofer number.", parent=self)
                return
        listofer_id = ListoferModel.get_or_create(self.project_id, listofer_number, description=self.listofer_desc_var.get().strip())
        pos = self.pos_var.get().strip()
        if not pos:
            messagebox.showerror("Error", "Position is required.", parent=self)
            return
        try:
            diameter = float(self.dia_var.get().strip())
            if diameter <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Diameter must be a positive number.", parent=self)
            return
        shape_name = self.shape_var.get()
        if shape_name not in default_shape_registry.flat_shapes:
            messagebox.showerror("Invalid Shape", f"'{shape_name}' is not valid.", parent=self)
            return
        dimensions = {}
        for k, var in self.param_entries.items():
            val_str = var.get().strip()
            if not val_str:
                messagebox.showerror("Dimension Error", f"Dimension '{k}' cannot be empty.", parent=self)
                return
            try:
                dimensions[k] = float(val_str)
            except ValueError:
                messagebox.showerror("Dimension Error", f"Invalid value for '{k}'.", parent=self)
                return
        try:
            quantity = int(self.quantity_var.get().strip())
            if quantity <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Quantity must be a positive integer.", parent=self)
            return
        grade = self.grade_var.get().strip() or DEFAULT_REBAR_GRADE
        standard_code = self._get_standard_code()
        payload = dict(
            listofer_id=listofer_id, pos=pos, diameter=diameter, shape_name=shape_name,
            dimensions=json.dumps(dimensions), quantity=quantity,
            location=self.location_var.get().strip() or None,
            element_type=self.element_var.get().strip() or None,
            user=self.current_user, date=datetime.datetime.now().isoformat(),
            grade=grade, standard=standard_code,
        )
        try:
            if self.editing:
                RebarModel.update(rebar_id=self.edit_data["id"], **payload)
            else:
                RebarModel.add(**payload)
            self._show_success_message()
            try:
                self.parent.status_bar.update_message("✅ Record saved successfully!")
            except Exception:
                pass
            self.callback()
            if self.keep_open_var.get() and not self.editing:
                try:
                    self.pos_var.set(str(int(pos) + 1))
                except ValueError:
                    self.pos_var.set("")
                self.quantity_var.set("1")
                if self.filtered_shape_keys:
                    self.shape_var.set(self.filtered_shape_keys[0])
                self._on_shape_changed()
                self.shape_combo.focus_set()
            else:
                self.after(500, self.destroy)
        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            messagebox.showerror("Database Error", f"Could not save rebar: {e}", parent=self)

    def _show_success_message(self):
        self.status_label.config(text="✓ Record saved", foreground="#059669")
        self.after(1800, lambda: self.status_label.config(text=""))
