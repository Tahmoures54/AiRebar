# ui/input_dialog.py
"""
Rebar input dialog – improved and stable:
- Larger window and preview canvas (resized to keep buttons visible)
- Minimizable (acts as a normal window)
- Fast standard -> shape refresh
- Robust standard filtering for ALL standards
- Preview works for:
  - draw functions in shapes.drawing (draw_l_bar, draw_u_bar, ...)
  - standard-module custom draw functions (e.g. mabhas9.draw_mabhas9_shape)
  - svg/custom segmented shapes handled by shapes.drawing
- Saves grade + standard into DB
"""

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
from config import ELEMENT_TYPES, STANDARD_DIAMETERS, REBAR_GRADES, DEFAULT_REBAR_GRADE

try:
    from shapes.drawing import draw_shape_on_canvas, DRAW_FUNCTIONS
    DRAW_AVAILABLE = True
except Exception:
    DRAW_AVAILABLE = False
    DRAW_FUNCTIONS = {}

logger = setup_logger("AI_Rebar.InputDialog")


STANDARD_DISPLAY_MAP = {
    "bs": "BS 8666 (UK)",
    "ir": "Iran – Mabhas 9",
    "aci": "ACI 318 – USA",
    "ec": "Eurocode 2",
    "is": "IS 2502 – India",
    "gb": "GB 50010 – China",
    "jis": "JIS G 3112 – Japan",
    "as": "AS 3600 – Australia",
    "nbr": "NBR 6118 – Brazil",
}

STANDARD_ALIASES = {
    "bs": ("bs", "bs8666"),
    "ir": ("ir", "mabhas9", "mabhas"),
    "aci": ("aci", "aci318"),
    "ec": ("ec", "ec2", "ec2-", "eurocode", "eurocode2"),
    "is": ("is", "is2502"),
    "gb": ("gb", "gb50010"),
    "jis": ("jis",),
    "as": ("as", "as3600"),
    "nbr": ("nbr", "nbr6118"),
}

STD_CODE_TO_MODULE = {
    "ir": "mabhas9",
    "bs": "bs8666",
    "aci": "aci318",
    "ec": "eurocode2",
    "is": "is2502",
    "gb": "gb50010",
    "jis": "jis",
    "as": "as3600",
    "nbr": "nbr6118",
}


class InputDialog(tk.Toplevel):
    # Larger overall size, canvas proportionally increased but still leaves room for buttons
    WINDOW_W = 1250
    WINDOW_H = 820
    MIN_W = 1050
    MIN_H = 800

    CANVAS_W = 700
    CANVAS_H = 420

    PREVIEW_DELAY_MS = 80

    def __init__(self, parent, project_id, callback, edit_data=None):
        super().__init__(parent)
        self.parent = parent
        self.project_id = project_id
        self.callback = callback
        self.current_user = getpass.getuser()
        self.edit_data = edit_data or {}
        self.editing = edit_data is not None

        self.title("Edit Rebar" if self.editing else "Add Rebar")
        self.resizable(True, True)
        # Allow minimize – do NOT make transient (transient removes minimize button)
        # We'll just lift and focus without transient to keep minimize/maximize
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # Validation
        self.vcmd_numeric = (self.register(self._validate_numeric_input), "%P")
        self.vcmd_int = (self.register(self._validate_int_input), "%P")

        # Shape data
        self.all_shape_keys = list(default_shape_registry.flat_shapes.keys())
        logger.debug(f"InputDialog shapes loaded: {len(self.all_shape_keys)}")
        if not self.all_shape_keys:
            messagebox.showwarning(
                "Shape Error",
                "No shape definitions loaded.\nPlease check shapes/definitions.py",
                parent=self,
            )

        self.filtered_shape_keys: list[str] = []
        self.shape_var = tk.StringVar()

        # Listofer
        self.listofer_numbers = ListoferModel.get_numbers(project_id)
        self.listofer_var = tk.StringVar()
        self.listofer_new_var = tk.StringVar()
        self.listofer_desc_var = tk.StringVar()

        self.auto_listofer_number = self._generate_next_listofer_number()
        self.listofer_new_var.set(self.auto_listofer_number)

        # UI state
        self.param_entries: dict[str, tk.StringVar] = {}
        self.length_label_var = tk.StringVar(value="Total cut length: -- mm")
        self.shape_hint_var = tk.StringVar(value="")
        self.keep_open_var = tk.BooleanVar(value=True)
        self._preview_after_id = None
        self._suspend_standard_callback = False

        # Build UI
        self._build_ui()
        self._populate_standard_combo()

        # Default standard
        initial_code = "bs"
        self._set_standard_display(initial_code)
        self._filter_by_standard(initial_code, show_hint=True)

        if self.filtered_shape_keys:
            self.shape_var.set(self.filtered_shape_keys[0])

        # Edit load
        if self.editing:
            self._load_edit_data()
        else:
            self._on_shape_changed()

        self._apply_geometry()

        # Lift and focus without transient
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

        self.after(120, self._update_preview)
        logger.debug(f"InputDialog opened (edit={self.editing})")

    # -----------------------------------------------------------------
    # Window geometry – ensures dialog fits on screen
    # -----------------------------------------------------------------
    def _apply_geometry(self):
        self.minsize(self.MIN_W, self.MIN_H)

        W, H = self.WINDOW_W, self.WINDOW_H
        self.withdraw()
        self.update_idletasks()

        try:
            self.parent.update_idletasks()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            pw = max(1, self.parent.winfo_width())
            ph = max(1, self.parent.winfo_height())
            x = px + (pw // 2) - (W // 2)
            y = py + (ph // 2) - (H // 2)
        except Exception:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw // 2) - (W // 2)
            y = (sh // 2) - (H // 2)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, min(x, screen_width - W))
        y = max(0, min(y, screen_height - H - 40))

        self.geometry(f"{W}x{H}+{x}+{y}")
        self.deiconify()

    # -----------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------
    def _validate_numeric_input(self, P):
        if P in ("", "."):
            return True
        try:
            return float(P) >= 0
        except ValueError:
            return False

    def _validate_int_input(self, P):
        if P == "":
            return True
        return P.isdigit()

    # -----------------------------------------------------------------
    # Standard/shape matching helpers
    # -----------------------------------------------------------------
    def _normalize_text(self, value):
        return str(value or "").strip().lower()

    def _extract_lead_token(self, text):
        txt = self._normalize_text(text)
        if " - " in txt:
            txt = txt.split(" - ", 1)[0].strip()
        return txt

    def _text_matches_standard(self, text, standard_code):
        token = self._extract_lead_token(text)
        aliases = STANDARD_ALIASES.get(standard_code, (standard_code,))
        for alias in aliases:
            a = alias.lower()
            if token == a or token.startswith(a):
                return True
        return False

    def _shape_belongs_to_standard(self, shape_key, standard_code):
        if self._text_matches_standard(shape_key, standard_code):
            return True

        shape_def = default_shape_registry.flat_shapes.get(shape_key, {}) or {}
        candidates = [
            shape_def.get("code"),
            shape_def.get("standard_code"),
            shape_def.get("standard"),
            shape_def.get("source_standard"),
            shape_def.get("prefix"),
        ]
        for item in candidates:
            if item and self._text_matches_standard(item, standard_code):
                return True
        return False

    def _get_shape_keys_for_standard(self, standard_code):
        standard_code = (standard_code or "bs").strip().lower()

        registry_keys = []
        try:
            registry_keys = default_shape_registry.get_shape_keys_by_standard(standard_code) or []
        except Exception as e:
            logger.debug(f"Registry standard mapping failed for '{standard_code}': {e}")

        if registry_keys:
            logger.debug(f"Standard '{standard_code}': registry={len(registry_keys)}")
            return list(registry_keys)

        prefix_keys = [k for k in self.all_shape_keys if self._shape_belongs_to_standard(k, standard_code)]
        logger.debug(f"Standard '{standard_code}': registry=0 prefix_inferred={len(prefix_keys)}")
        return prefix_keys

    # -----------------------------------------------------------------
    # Listofer helpers
    # -----------------------------------------------------------------
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
        elif listofer_no:
            self.new_listofer_check.set(True)
            self._toggle_listofer()
            self.listofer_new_var.set(listofer_no)
        else:
            self.new_listofer_check.set(True)
            self._toggle_listofer()

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
            if shape not in self.filtered_shape_keys:
                self._filter_by_standard(std_code, show_hint=True)
            self.shape_var.set(shape)
            self._on_shape_changed()

            try:
                dims = json.loads(data.get("dimensions", "{}"))
            except Exception:
                dims = {}
            for k, var in self.param_entries.items():
                var.set(str(dims.get(k, 10)))

        self.quantity_var.set(str(data.get("quantity", "1") or "1"))

    # -----------------------------------------------------------------
    # UI construction (canvas size enlarged but balanced)
    # -----------------------------------------------------------------
    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        gen = ttk.LabelFrame(main, text="General Information", padding=10)
        gen.pack(fill="x", pady=(0, 10))
        gen.columnconfigure(0, weight=0)
        gen.columnconfigure(1, weight=1)
        gen.columnconfigure(2, weight=0)
        gen.columnconfigure(3, weight=1)

        # Listofer row
        lf = ttk.Frame(gen)
        lf.grid(row=0, column=0, columnspan=4, sticky="ew", pady=2)

        ttk.Label(lf, text="Listofer No:", width=12, anchor="e").pack(side="left", padx=(0, 5))

        self.listofer_combo = ttk.Combobox(lf, textvariable=self.listofer_var, values=self.listofer_numbers, width=18)
        self.listofer_combo.pack(side="left", padx=2)
        self.listofer_combo.set("")

        self.new_listofer_check = tk.BooleanVar(value=True)
        ttk.Checkbutton(lf, text="New", variable=self.new_listofer_check, command=self._toggle_listofer).pack(
            side="left", padx=6
        )

        self.listofer_new_entry = ttk.Entry(lf, textvariable=self.listofer_new_var, width=18)
        self.listofer_new_entry.pack(side="left", padx=2)

        ttk.Button(
            lf, text="Auto", command=lambda: self.listofer_new_var.set(self._generate_next_listofer_number()), width=6
        ).pack(side="left", padx=2)

        ttk.Label(gen, text="Listofer Description:", anchor="e").grid(row=1, column=0, padx=5, pady=3, sticky="e")
        ttk.Entry(gen, textvariable=self.listofer_desc_var, width=60).grid(
            row=1, column=1, columnspan=3, padx=5, pady=3, sticky="ew"
        )

        # Position & Diameter
        ttk.Label(gen, text="Position (Mark):", anchor="e").grid(row=2, column=0, padx=5, pady=3, sticky="e")
        self.pos_var = tk.StringVar(value="1")
        ttk.Entry(gen, textvariable=self.pos_var, width=18).grid(row=2, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(gen, text="Diameter (mm):", anchor="e").grid(row=2, column=2, padx=5, pady=3, sticky="e")
        self.dia_var = tk.StringVar(value="10")
        self.dia_var.trace_add("write", lambda *a: self._schedule_preview())

        self.dia_combo = ttk.Combobox(
            gen,
            textvariable=self.dia_var,
            values=STANDARD_DIAMETERS,
            width=10,
            validate="key",
            validatecommand=self.vcmd_numeric,
        )
        self.dia_combo.grid(row=2, column=3, padx=5, pady=3, sticky="w")
        self.dia_combo.set("10")

        # Element Type & Location
        ttk.Label(gen, text="Element Type:", anchor="e").grid(row=3, column=0, padx=5, pady=3, sticky="e")
        self.element_var = tk.StringVar(value="Column")
        ttk.Combobox(gen, textvariable=self.element_var, values=ELEMENT_TYPES, width=18).grid(
            row=3, column=1, padx=5, pady=3, sticky="w"
        )

        ttk.Label(gen, text="Location/Zone:", anchor="e").grid(row=3, column=2, padx=5, pady=3, sticky="e")
        self.location_var = tk.StringVar(value="")
        ttk.Entry(gen, textvariable=self.location_var, width=22).grid(row=3, column=3, padx=5, pady=3, sticky="w")

        # Standard
        ttk.Label(gen, text="Standard:", anchor="e").grid(row=4, column=0, padx=5, pady=3, sticky="e")
        self.standard_var = tk.StringVar()
        self.standard_combo = ttk.Combobox(gen, textvariable=self.standard_var, values=[], state="readonly", width=32)
        self.standard_combo.grid(row=4, column=1, padx=5, pady=3, sticky="w")
        self.standard_combo.bind("<<ComboboxSelected>>", self._on_standard_changed)

        # Grade
        ttk.Label(gen, text="Grade (Type):", anchor="e").grid(row=5, column=0, padx=5, pady=3, sticky="e")
        self.grade_var = tk.StringVar(value=DEFAULT_REBAR_GRADE)
        self.grade_combo = ttk.Combobox(gen, textvariable=self.grade_var, values=REBAR_GRADES, width=16)
        self.grade_combo.grid(row=5, column=1, padx=5, pady=3, sticky="w")
        self.grade_combo.set(DEFAULT_REBAR_GRADE)

        # --- Shape & Dimensions ---
        shape_frame = ttk.LabelFrame(main, text="Shape & Dimensions", padding=10)
        shape_frame.pack(fill="both", expand=True, pady=(0, 10))

        paned = ttk.Panedwindow(shape_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        shape_label_frame = ttk.Frame(left)
        shape_label_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(shape_label_frame, text="Shape Type:", font=("Arial", 10, "bold")).pack(side="left")
        ttk.Button(shape_label_frame, text="✏️ Custom Designer", command=self._open_designer).pack(side="right", padx=5)

        self.shape_combo = ttk.Combobox(left, textvariable=self.shape_var, values=[], state="normal", width=52)
        self.shape_combo.pack(fill="x", pady=(0, 4))
        self.shape_combo.bind("<<ComboboxSelected>>", lambda e: self._on_shape_changed())
        self.shape_combo.bind("<KeyRelease>", self._filter_shapes)

        ttk.Label(left, textvariable=self.shape_hint_var, foreground="#555", font=("Arial", 8, "italic")).pack(
            anchor="w", pady=(0, 8)
        )

        self.param_frame = ttk.LabelFrame(left, text="Dimensions (mm)", padding=8)
        self.param_frame.pack(fill="both", expand=True)

        self.error_label = ttk.Label(left, text="", foreground="red", font=("Arial", 9, "italic"))
        self.error_label.pack(anchor="w", pady=(4, 0))

        ttk.Label(left, textvariable=self.length_label_var, foreground="blue", font=("Arial", 9, "italic")).pack(
            anchor="w", pady=(6, 0)
        )

        # Preview canvas – larger but still leaves room for bottom buttons
        self.canvas = tk.Canvas(
            right,
            bg="white",
            width=self.CANVAS_W,
            height=self.CANVAS_H,
            highlightthickness=1,
            highlightbackground="gray",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._schedule_preview())

        # Bottom controls
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(6, 0))

        ttk.Label(bottom, text="Quantity:").pack(side="left", padx=5)
        self.quantity_var = tk.StringVar(value="1")
        ttk.Entry(bottom, textvariable=self.quantity_var, width=10, validate="key", validatecommand=self.vcmd_int).pack(
            side="left", padx=5
        )

        ttk.Checkbutton(bottom, text="Add Another", variable=self.keep_open_var).pack(side="left", padx=20)

        self.status_label = ttk.Label(bottom, text="", foreground="green", font=("Arial", 9, "bold"))
        self.status_label.pack(side="left", padx=10)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=5)
        save_text = "Update" if self.editing else "Add to Project"
        ttk.Button(btn_frame, text=save_text, command=self._save_bar).pack(side="right", padx=5)

        self._toggle_listofer()

    # -----------------------------------------------------------------
    # Standard combo
    # -----------------------------------------------------------------
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
        display = self.standard_var.get()
        return self._display_to_code.get(display, "bs")

    # -----------------------------------------------------------------
    # Filtering
    # -----------------------------------------------------------------
    def _filter_by_standard(self, standard_code, show_hint=False):
        standard_code = (standard_code or "bs").strip().lower()

        keys = self._get_shape_keys_for_standard(standard_code)
        if keys:
            self.filtered_shape_keys = keys
            if show_hint:
                self.shape_hint_var.set(f"{len(keys)} shape(s) for {STANDARD_DISPLAY_MAP.get(standard_code, standard_code)}")
        else:
            self.filtered_shape_keys = []
            if show_hint:
                self.shape_hint_var.set(f"No shapes for {STANDARD_DISPLAY_MAP.get(standard_code, standard_code)}")

        self.shape_combo["values"] = self.filtered_shape_keys

        if self.filtered_shape_keys:
            if self.shape_var.get() not in self.filtered_shape_keys:
                self.shape_var.set(self.filtered_shape_keys[0])
        else:
            self.shape_var.set("")

        self._on_shape_changed()

    # -----------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------
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

        filtered = [k for k in self.filtered_shape_keys if text in k.lower()]
        self.shape_combo["values"] = filtered
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
        logger.debug(f"Selected standard display='{selected_display}' -> code='{new_std}'")

        try:
            set_standard(new_std)
        except Exception as e:
            logger.debug(f"set_standard('{new_std}') failed: {e}")

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
        param_names = shape_def.get("params", [])
        defaults = default_shape_registry.get_default_params(shape_name)

        for i, param in enumerate(param_names):
            ttk.Label(self.param_frame, text=f"{param} (mm):").grid(row=i, column=0, padx=6, pady=4, sticky="w")
            var = tk.StringVar(value=str(defaults.get(param, 10)))
            ent = ttk.Entry(self.param_frame, textvariable=var, width=12, validate="key", validatecommand=self.vcmd_numeric)
            ent.grid(row=i, column=1, padx=6, pady=4, sticky="w")
            self.param_entries[param] = var

        for var in self.param_entries.values():
            var.trace_add("write", lambda *a: self._schedule_preview())

        self._schedule_preview()

    # -----------------------------------------------------------------
    # Preview
    # -----------------------------------------------------------------
    def _schedule_preview(self):
        if self._preview_after_id is not None:
            try:
                self.after_cancel(self._preview_after_id)
            except Exception:
                pass
        self._preview_after_id = self.after(self.PREVIEW_DELAY_MS, self._update_preview)

    def _get_standard_code_for_shape(self, shape_key: str) -> str:
        try:
            shape_def = default_shape_registry.flat_shapes.get(shape_key) or {}
            sc = (shape_def.get("standard_code") or "").strip().lower()
            if sc:
                return sc
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
                logger.warning(f"Preview draw (drawing.py) failed: {e}")

        if not drawn and draw_func_name not in ("draw_generic", "draw_svg_template", "draw_custom_segmented"):
            std_code = self._get_standard_code_for_shape(shape_name)
            module_name = STD_CODE_TO_MODULE.get(std_code)
            if module_name:
                try:
                    mod = importlib.import_module(f"shapes.standards.{module_name}")
                    draw_func = getattr(mod, draw_func_name, None)
                    if callable(draw_func):
                        draw_func(self.canvas, shape_name, params, diameter)
                        drawn = True
                except Exception as e:
                    logger.warning(f"Custom drawing failed ({module_name}.{draw_func_name}): {e}")

        if not drawn:
            if DRAW_AVAILABLE:
                try:
                    draw_shape_on_canvas(self.canvas, shape_name, params, diameter)
                    drawn = True
                except Exception as e:
                    logger.warning(f"Preview draw error: {e}")
                    self._draw_fallback(shape_name, params, diameter)
            else:
                self._draw_fallback(shape_name, params, diameter)

        try:
            length_mm = default_shape_registry.calc_shape_length(shape_name, params, diameter)
            self.length_label_var.set(f"Total cut length: {length_mm:.1f} mm")
            self.error_label.config(text="")
        except Exception as e:
            logger.warning(f"Length calculation failed for {shape_name}: {e}")
            self.length_label_var.set("Total cut length: --")
            self.error_label.config(text="Invalid dimensions for this shape")

    def _draw_fallback(self, shape_name, params, diameter):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        try:
            total_length = default_shape_registry.calc_shape_length(shape_name, params, diameter)
        except Exception:
            total_length = 500.0

        margin = 50
        max_len_px = max(10, cw - 2 * margin)
        scale = max_len_px / total_length if total_length > 0 else 1.0

        x1 = margin
        y = ch // 2
        x2 = x1 + total_length * scale

        self.canvas.create_line(x1, y, x2, y, fill="#006064", width=3)
        self.canvas.create_text(cw // 2, y - 20, text=shape_name, fill="#006064", font=("Arial", 10, "bold"))
        dim_text = ", ".join(f"{k}={v:.0f}" for k, v in params.items())
        self.canvas.create_text(cw // 2, y + 15, text=dim_text, fill="#333", font=("Arial", 8))
        self.canvas.create_text(cw // 2, y + 35, text=f"Ø {diameter} mm", fill="#666", font=("Arial", 8))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _save_bar(self):
        logger.info(f"Saving rebar (edit={self.editing})")

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

        listofer_id = ListoferModel.get_or_create(
            self.project_id,
            listofer_number,
            description=self.listofer_desc_var.get().strip()
        )

        pos = self.pos_var.get().strip()
        if not pos:
            messagebox.showerror("Error", "Position is required.", parent=self)
            return

        dia_val = self.dia_var.get().strip()
        if not dia_val:
            messagebox.showerror("Error", "Diameter is required.", parent=self)
            return
        try:
            diameter = float(dia_val)
            if diameter <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Diameter must be a positive number.", parent=self)
            return

        element_type = self.element_var.get().strip() or None
        location = self.location_var.get().strip() or None
        shape_name = self.shape_var.get()

        if shape_name not in default_shape_registry.flat_shapes:
            messagebox.showerror("Invalid Shape", f"'{shape_name}' is not a valid shape.", parent=self)
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

        dimensions_json = json.dumps(dimensions)

        qty_val = self.quantity_var.get().strip()
        if not qty_val:
            messagebox.showerror("Error", "Quantity is required.", parent=self)
            return
        try:
            quantity = int(qty_val)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer.", parent=self)
            return

        grade = self.grade_var.get().strip() or DEFAULT_REBAR_GRADE
        user = self.current_user
        date = datetime.datetime.now().isoformat()
        standard_code = self._get_standard_code()

        try:
            if self.editing:
                RebarModel.update(
                    rebar_id=self.edit_data["id"],
                    listofer_id=listofer_id,
                    pos=pos,
                    diameter=diameter,
                    shape_name=shape_name,
                    dimensions=dimensions_json,
                    quantity=quantity,
                    location=location,
                    element_type=element_type,
                    user=user,
                    date=date,
                    grade=grade,
                    standard=standard_code
                )
            else:
                RebarModel.add(
                    listofer_id=listofer_id,
                    pos=pos,
                    diameter=diameter,
                    shape_name=shape_name,
                    dimensions=dimensions_json,
                    quantity=quantity,
                    location=location,
                    element_type=element_type,
                    user=user,
                    date=date,
                    grade=grade,
                    standard=standard_code
                )

            self._show_success_message()

            try:
                self.parent.status_bar.update_message("✅ Record saved successfully!")
            except AttributeError:
                pass

            self.callback()

            if self.keep_open_var.get() and not self.editing:
                try:
                    next_pos = int(pos) + 1
                    self.pos_var.set(str(next_pos))
                except ValueError:
                    self.pos_var.set("")
                self.quantity_var.set("1")
                self.element_var.set("Column")
                if self.filtered_shape_keys:
                    self.shape_var.set(self.filtered_shape_keys[0])
                else:
                    self.shape_var.set("")
                self._on_shape_changed()
                self.shape_combo.focus_set()
            else:
                self.after(500, self.destroy)

        except Exception as e:
            logger.error(f"Save failed: {e}", exc_info=True)
            messagebox.showerror("Database Error", f"Could not save rebar: {e}", parent=self)

    def _show_success_message(self):
        self.status_label.config(text="✓ Record saved", foreground="green")
        self.after(1800, lambda: self.status_label.config(text=""))