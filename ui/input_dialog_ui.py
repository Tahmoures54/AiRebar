# ui/input_dialog_ui.py
"""Premium layout for InputDialog (add / edit position)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from utils.i18n import t
from config import ELEMENT_TYPES, STANDARD_DIAMETERS, REBAR_GRADES, DEFAULT_REBAR_GRADE


def build_premium_input_ui(self) -> None:
    """Premium add-position workspace: header · cards · live preview · sticky CTA."""
    BG = "#0b1220"
    SOFT = "#f1f5f9"
    ACCENT = "#06b6d4"
    MUTED = "#94a3b8"

    self.configure(bg=SOFT)
    try:
        style = ttk.Style(self)
        style.configure("Input.Header.TFrame", background=BG)
        style.configure("Input.Soft.TFrame", background=SOFT)
        style.configure("Input.Card.TLabelframe", background=SOFT, font=("Segoe UI Semibold", 10))
        style.configure("Input.Card.TLabelframe.Label", background=SOFT, foreground="#0f172a", font=("Segoe UI Semibold", 10))
        style.configure("Input.Primary.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8))
        style.configure("Input.Ghost.TButton", font=("Segoe UI", 9), padding=(10, 6))
    except Exception:
        pass

    header = tk.Frame(self, bg=BG, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")
    titles = tk.Frame(header, bg=BG)
    titles.pack(side="left", padx=14, pady=10)
    title_txt = t("input.edit_title") if self.editing else t("input.add_title")
    tk.Label(titles, text=title_txt, bg=BG, fg="#f8fafc", font=("Segoe UI Semibold", 14)).pack(anchor="w")
    tk.Label(
        titles,
        text="Shape · diameter · dimensions · live length & preview",
        bg=BG, fg=MUTED, font=("Segoe UI", 9),
    ).pack(anchor="w")
    chips = tk.Frame(header, bg=BG)
    chips.pack(side="right", padx=12)
    tk.Label(chips, text="Ctrl+Enter save  ·  Esc close", bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(side="right", padx=6)

    main = ttk.Frame(self, padding=12, style="Input.Soft.TFrame")
    main.pack(fill="both", expand=True)

    body = ttk.Frame(main, style="Input.Soft.TFrame")
    body.pack(fill="both", expand=True)
    body.columnconfigure(0, weight=3)
    body.columnconfigure(1, weight=2)
    body.rowconfigure(0, weight=1)

    left = ttk.Frame(body, style="Input.Soft.TFrame")
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    right = ttk.Frame(body, style="Input.Soft.TFrame")
    right.grid(row=0, column=1, sticky="nsew")

    gen = ttk.LabelFrame(left, text="  Project & listofer", padding=10, style="Input.Card.TLabelframe")
    gen.pack(fill="x", pady=(0, 8))
    gen.columnconfigure(1, weight=1)
    gen.columnconfigure(3, weight=1)

    lf = ttk.Frame(gen)
    lf.grid(row=0, column=0, columnspan=4, sticky="ew", pady=2)
    ttk.Label(lf, text=t("input.listofer_no"), width=12, anchor="e").pack(side="left", padx=(0, 5))
    self.listofer_combo = ttk.Combobox(lf, textvariable=self.listofer_var, values=self.listofer_numbers, width=16)
    self.listofer_combo.pack(side="left", padx=2)
    self.listofer_combo.set("")
    self.new_listofer_check = tk.BooleanVar(value=True)
    ttk.Checkbutton(lf, text=t("input.new"), variable=self.new_listofer_check, command=self._toggle_listofer).pack(side="left", padx=6)
    self.listofer_new_entry = ttk.Entry(lf, textvariable=self.listofer_new_var, width=16)
    self.listofer_new_entry.pack(side="left", padx=2)
    ttk.Button(lf, text=t("input.auto"), command=lambda: self.listofer_new_var.set(self._generate_next_listofer_number()), width=6).pack(side="left", padx=2)

    ttk.Label(gen, text=t("input.listofer_desc"), anchor="e").grid(row=1, column=0, padx=5, pady=3, sticky="e")
    ttk.Entry(gen, textvariable=self.listofer_desc_var).grid(row=1, column=1, columnspan=3, padx=5, pady=3, sticky="ew")

    id_card = ttk.LabelFrame(left, text="  Bar identity", padding=10, style="Input.Card.TLabelframe")
    id_card.pack(fill="x", pady=(0, 8))
    id_card.columnconfigure(1, weight=1)
    id_card.columnconfigure(3, weight=1)

    ttk.Label(id_card, text=t("input.position"), anchor="e").grid(row=0, column=0, padx=5, pady=3, sticky="e")
    self.pos_var = tk.StringVar(value="1")
    ttk.Entry(id_card, textvariable=self.pos_var, width=16).grid(row=0, column=1, padx=5, pady=3, sticky="w")

    ttk.Label(id_card, text=t("input.diameter"), anchor="e").grid(row=0, column=2, padx=5, pady=3, sticky="e")
    self.dia_var = tk.StringVar(value="10")
    self.dia_var.trace_add("write", lambda *a: self._schedule_preview())
    self.dia_combo = ttk.Combobox(
        id_card, textvariable=self.dia_var, values=STANDARD_DIAMETERS, width=10,
        validate="key", validatecommand=self.vcmd_numeric,
    )
    self.dia_combo.grid(row=0, column=3, padx=5, pady=3, sticky="w")
    self.dia_combo.set("10")

    ttk.Label(id_card, text=t("input.element_type"), anchor="e").grid(row=1, column=0, padx=5, pady=3, sticky="e")
    self.element_var = tk.StringVar(value="Column")
    ttk.Combobox(id_card, textvariable=self.element_var, values=ELEMENT_TYPES, width=16).grid(row=1, column=1, padx=5, pady=3, sticky="w")

    ttk.Label(id_card, text=t("input.location"), anchor="e").grid(row=1, column=2, padx=5, pady=3, sticky="e")
    self.location_var = tk.StringVar(value="")
    ttk.Entry(id_card, textvariable=self.location_var, width=20).grid(row=1, column=3, padx=5, pady=3, sticky="w")

    ttk.Label(id_card, text=t("input.standard"), anchor="e").grid(row=2, column=0, padx=5, pady=3, sticky="e")
    self.standard_var = tk.StringVar()
    self.standard_combo = ttk.Combobox(id_card, textvariable=self.standard_var, values=[], state="readonly", width=28)
    self.standard_combo.grid(row=2, column=1, columnspan=2, padx=5, pady=3, sticky="w")
    self.standard_combo.bind("<<ComboboxSelected>>", self._on_standard_changed)

    ttk.Label(id_card, text=t("input.grade"), anchor="e").grid(row=3, column=0, padx=5, pady=3, sticky="e")
    self.grade_var = tk.StringVar(value=DEFAULT_REBAR_GRADE)
    self.grade_combo = ttk.Combobox(id_card, textvariable=self.grade_var, values=REBAR_GRADES, width=14)
    self.grade_combo.grid(row=3, column=1, padx=5, pady=3, sticky="w")
    self.grade_combo.set(DEFAULT_REBAR_GRADE)

    shape_card = ttk.LabelFrame(left, text="  Shape & dimensions", padding=10, style="Input.Card.TLabelframe")
    shape_card.pack(fill="both", expand=True)

    shape_row = ttk.Frame(shape_card)
    shape_row.pack(fill="x", pady=(0, 6))
    ttk.Label(shape_row, text=t("input.shape")).pack(side="left")
    self.shape_combo = ttk.Combobox(shape_row, textvariable=self.shape_var, width=40)
    self.shape_combo.pack(side="left", fill="x", expand=True, padx=8)
    self.shape_combo.bind("<<ComboboxSelected>>", lambda e: self._on_shape_changed())
    self.shape_combo.bind("<KeyRelease>", self._filter_shapes)
    ttk.Button(shape_row, text="Designer", command=self._open_designer, style="Input.Ghost.TButton").pack(side="left")

    ttk.Label(shape_card, textvariable=self.shape_hint_var, foreground="#64748b", font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(0, 6))

    self.param_frame = ttk.LabelFrame(shape_card, text=t("input.dimensions_mm"), padding=8)
    self.param_frame.pack(fill="both", expand=True)

    self.error_label = ttk.Label(shape_card, text="", foreground="#ef4444", font=("Segoe UI", 9, "italic") )
    self.error_label.pack(anchor="w", pady=(4, 0))

    metrics = tk.Frame(shape_card, bg="#e2e8f0", padx=10, pady=6)
    metrics.pack(fill="x", pady=(8, 0))
    tk.Label(metrics, textvariable=self.length_label_var, bg="#e2e8f0", fg="#0e7490", font=("Segoe UI Semibold", 10)).pack(anchor="w")

    prev_card = ttk.LabelFrame(right, text="  Live preview", padding=8, style="Input.Card.TLabelframe")
    prev_card.pack(fill="both", expand=True)
    canvas_host = tk.Frame(prev_card, bg="#0f172a", padx=2, pady=2)
    canvas_host.pack(fill="both", expand=True)
    self.canvas = tk.Canvas(canvas_host, bg="#0f172a", width=self.CANVAS_W, height=self.CANVAS_H, highlightthickness=0)
    self.canvas.pack(fill="both", expand=True)
    self.canvas.bind("<Configure>", lambda e: self._schedule_preview())
    tk.Label(prev_card, text="Updates as you type dimensions", foreground="#64748b", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

    footer = tk.Frame(self, bg="#e2e8f0", padx=12, pady=10)
    footer.pack(side="bottom", fill="x")

    ttk.Label(footer, text=t("input.quantity")).pack(side="left", padx=(4, 4))
    self.quantity_var = tk.StringVar(value="1")
    ttk.Entry(footer, textvariable=self.quantity_var, width=8, validate="key", validatecommand=self.vcmd_int).pack(side="left", padx=4)
    ttk.Checkbutton(footer, text=t("input.add_another"), variable=self.keep_open_var).pack(side="left", padx=16)

    self.status_label = ttk.Label(footer, text="", foreground="#059669", font=("Segoe UI", 9, "bold"))
    self.status_label.pack(side="left", padx=8)

    ttk.Button(footer, text=t("btn.cancel"), command=self.destroy, style="Input.Ghost.TButton").pack(side="right", padx=4)
    save_text = "Update position" if self.editing else "Add to project"
    ttk.Button(footer, text=save_text, command=self._save_bar, style="Input.Primary.TButton").pack(side="right", padx=4)

    self.bind("<Control-Return>", lambda e: self._save_bar())
    self.bind("<Escape>", lambda e: self.destroy())
    self._toggle_listofer()
