# ui/dialogs.py
# General-purpose dialogs: Lap Splice Calculator, Cutting Plan Window.
# Cutting plan now uses ttk.Treeview for scalable output and handles PuLP errors gracefully.
# Confirmed plans are locked – re‑optimization requires a deliberate forced action.
# Database writes are executed on a background thread to keep the UI responsive.
# ** Fix: data_hash now includes BBS contents so that confirmed plans remain locked **

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import threading
import sqlite3
import os
import json
import hashlib

from logic.calculator import calculate_lap_splice
from logic.optimizer import (
    PULP_AVAILABLE, optimize_labeled_cuts,
    optimize_with_scraps_and_stock, get_available_stock_bars,
    OptimizerOptions
)
from db.models import ScrapModel, StockModel   # only these are used from models
from config import WEIGHT_COEFFICIENT, DEFAULT_REBAR_GRADE, DB_PATH
from utils.logger import setup_logger

logger = setup_logger('AI_Rebar.Dialogs')

# Tolerance for matching scrap length to a plan bar (in mm)
CUTTING_TOLERANCE_MM = 1.0

# ----------------------------------------------------------------------
# Local caching helpers (replaces CuttingPlanModel dependency)
# ----------------------------------------------------------------------
def _ensure_cutting_plans_table():
    """Create the cutting_plans table if it does not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cutting_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                listofer_filter TEXT,
                stock_len REAL NOT NULL,
                data_hash TEXT NOT NULL,
                plans_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

def _compute_data_hash(project_id, listofer_filter, stock_len):
    """
    Create a unique hash based on the optimisation parameters AND the
    actual BBS data.  This ensures that when the rebar list changes
    the old (confirmed) plan is not reused.
    """
    # Collect rebar data for this project / filter
    from db.models import RebarModel
    rebars = RebarModel.get_for_project(project_id, listofer_filter)
    scraps = ScrapModel.get_all_scraps(project_id)

    data_dict = {
        "project_id": project_id,
        "listofer_filter": listofer_filter,
        "stock_len": stock_len,
        "rebars": [
            {"id": r[0], "lf": r[1], "pos": r[3], "dia": r[4],
             "shape": r[5], "dims": r[6], "qty": r[7], "grade": r[12]}
            for r in rebars
        ],
        "scraps": [
            {"id": s[0], "dia": s[1], "len": s[2], "grade": s[3], "used": s[5], "lf": s[6]}
            for s in scraps
        ],
    }
    raw = json.dumps(data_dict, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def _load_plan(project_id, listofer_filter, stock_len, data_hash):
    """Try to load a cached plan; returns (plans_dict, status) or (None, None)."""
    _ensure_cutting_plans_table()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """SELECT plans_json, status FROM cutting_plans
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (project_id, listofer_filter, stock_len, data_hash)
            )
            row = cur.fetchone()
            if row:
                plans_json, status = row
                plans = json.loads(plans_json)
                # Convert JSON keys back to tuples (they were stored as strings)
                restored = {}
                for key_str, value in plans.items():
                    parts = key_str.strip("()").split(",", 1)
                    dia = float(parts[0].strip())
                    grade = parts[1].strip().strip("'")
                    restored[(dia, grade)] = value
                return restored, status
    except Exception as e:
        logger.warning(f"Failed to load cached plan: {e}")
    return None, None

def _save_plan(project_id, listofer_filter, stock_len, data_hash, plans_per_group, status='draft'):
    """Save (or update) a cutting plan to the database."""
    _ensure_cutting_plans_table()
    # Convert tuple keys to strings for JSON
    serializable = {}
    for (dia, grade), data in plans_per_group.items():
        key_str = f"({dia}, '{grade}')"
        serializable[key_str] = data
    plans_json = json.dumps(serializable)
    now = datetime.datetime.now().isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Upsert: delete any existing plan for this exact combination and insert new
            conn.execute(
                """DELETE FROM cutting_plans
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?""",
                (project_id, listofer_filter, stock_len, data_hash)
            )
            conn.execute(
                """INSERT INTO cutting_plans
                   (project_id, listofer_filter, stock_len, data_hash, plans_json, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, listofer_filter, stock_len, data_hash, plans_json, status, now)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save plan: {e}")

def _confirm_plan(project_id, listofer_filter, stock_len, data_hash):
    """Mark an existing draft plan as confirmed."""
    _ensure_cutting_plans_table()
    now = datetime.datetime.now().isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """UPDATE cutting_plans SET status = 'confirmed', updated_at = ?
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?""",
                (now, project_id, listofer_filter, stock_len, data_hash)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to confirm plan: {e}")


# ----------------------------------------------------------------------
# Lap Splice Calculator Dialog
# ----------------------------------------------------------------------
class LapSpliceDialog(tk.Toplevel):
    """Dialog for calculating lap splice length based on bar diameter and concrete grade."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("🔧 Lap Splice Calculator")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Bar Diameter (mm):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.dia_var = tk.StringVar(value="16")
        ttk.Entry(self, textvariable=self.dia_var, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(self, text="Concrete Grade (MPa):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.fc_var = tk.StringVar(value="25")
        ttk.Entry(self, textvariable=self.fc_var, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(self, text="Steel Yield Strength (MPa):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.fy_var = tk.StringVar(value="500")
        ttk.Entry(self, textvariable=self.fy_var, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(self, text="Condition:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.cond_var = tk.StringVar(value="Tension")
        cond_combo = ttk.Combobox(
            self, textvariable=self.cond_var,
            values=["Tension", "Compression"],
            state="readonly", width=12
        )
        cond_combo.grid(row=3, column=1, sticky="w")

        self.result_label = ttk.Label(
            self, text="Lap Length: - mm", font=("Arial", 12, "bold")
        )
        self.result_label.grid(row=4, column=0, columnspan=2, pady=15)

        ttk.Button(self, text="Calculate", command=self.calculate).grid(
            row=5, column=0, padx=10, pady=10
        )
        ttk.Button(self, text="Close", command=self.destroy).grid(
            row=5, column=1, padx=10, pady=10
        )

        self._center_on_parent()

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self.master
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def calculate(self):
        try:
            dia = float(self.dia_var.get())
            fc = float(self.fc_var.get())
            fy = float(self.fy_var.get())
            condition = self.cond_var.get()
            top = condition == "Tension"
            lap = calculate_lap_splice(dia, fy=fy, fc=fc, top_bar=top)
            self.result_label.config(text=f"Lap Length: {lap:.0f} mm")
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values.")
        except Exception as e:
            messagebox.showerror("Calculation Error", str(e))


# ----------------------------------------------------------------------
# Cutting Plan Window (Treeview-based)
# ----------------------------------------------------------------------
class CuttingPlanWindow(tk.Toplevel):
    """
    Window to display optimized cutting plan in a sortable Treeview.
    Supports draft/confirmed lifecycle with automatic scrap management.
    Once confirmed, the plan is locked – re‑optimization requires explicit force.
    """

    PROMO_MESSAGES = [
        "♻️  Minimizing material waste with MILP optimization...",
        "💡  Finding the smartest bar arrangement for you...",
        "💰  Saving you money on every stock bar...",
        "🧠  AI‑powered cutting – up to 30% less scrap",
        "📐  Tailoring the plan to your exact BBS...",
        "🚀  Using industry‑leading algorithms...",
        "🔧  Crunching numbers for the perfect cut...",
        "🌍  Helping the planet by reducing waste...",
        "🏗️  Building efficiency, one bar at a time...",
        "✨  Almost ready – your optimized plan is coming!"
    ]

    _TREE_COLS = {
        "bar": "Bar #",
        "used_mm": "Used (mm)",
        "waste_mm": "Waste (mm)",
        "bar_len_mm": "Bar Length (mm)",
        "cuts": "Pieces (pos, LF, length)",
    }

    def __init__(self, parent, project_id, data_by_key, stock_length, listofer_filter=None):
        super().__init__(parent)
        self.parent = parent
        self.title("🧠 AI-Optimized Cutting Plan")
        self.geometry("1050x800")
        self.project_id = project_id
        self.data_by_key = data_by_key
        self.stock_len = stock_length
        self.listofer_filter = listofer_filter
        self.plans_per_group = {}
        self.use_stock_limit_var = tk.BooleanVar(value=False)
        self._bypass_cache = False
        self.plan_status = None             # 'draft' or 'confirmed'
        self._cancel_event = threading.Event()
        self._opt_thread = None
        self._temp_results = None
        self._splash_after_id = None
        self._optimizing = False
        self._optimization_done = False

        self._tree_data = []
        self._sort_col = None
        self._sort_reverse = False

        self.create_widgets()
        self.transient(parent)
        self.grab_set()
        self._center_on_parent()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def create_widgets(self):
        if not PULP_AVAILABLE:
            messagebox.showerror("Error", "PuLP not installed.", parent=self)
            self.destroy()
            return

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=(0, 5))
        ttk.Checkbutton(
            top_frame,
            text="🧮 Respect actual stock limits (from Stock Manager)",
            variable=self.use_stock_limit_var
        ).pack(side="left", padx=(0, 20))

        self.summary_var = tk.StringVar(value="Click a diameter tab to see the plan")
        ttk.Label(top_frame, textvariable=self.summary_var, font=("Arial", 10, "bold")).pack(
            side="left", padx=10)

        self.locked_label = ttk.Label(top_frame, text="", foreground="red",
                                      font=("Arial", 9, "bold"))
        self.locked_label.pack(side="left", padx=10)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, pady=(5, 10))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        self.export_html_btn = ttk.Button(btn_frame, text="🌐 Export HTML", command=self.export_html)
        self.export_html_btn.pack(side="left", padx=5)
        self.reoptimize_btn = ttk.Button(btn_frame, text="🔄 Re-optimize", command=self.re_optimize)
        self.reoptimize_btn.pack(side="left", padx=5)
        self.confirm_plan_btn = ttk.Button(
            btn_frame, text="✅ Confirm Plan", command=self.confirm_plan, state="disabled"
        )
        self.confirm_plan_btn.pack(side="left", padx=5)
        self.force_reopt_btn = ttk.Button(
            btn_frame, text="⚠️ Force Re‑optimize", command=self._force_re_optimize
        )
        self.force_reopt_btn.pack(side="left", padx=5)
        self.force_reopt_btn.pack_forget()

        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right", padx=5)

        self.generate_plan()

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self.master
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _is_window_alive(self, window):
        try:
            return window is not None and window.winfo_exists()
        except tk.TclError:
            return False

    # ------------------------------------------------------------------
    # Treeview tab creation
    # ------------------------------------------------------------------
    def _create_diameter_tab(self, dia, grade, plans, new_scraps_m):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=f"Ø{dia} {grade}")

        tree = ttk.Treeview(frame, columns=list(self._TREE_COLS.keys()), show="headings",
                            selectmode="extended")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        for col_id, col_text in self._TREE_COLS.items():
            tree.heading(col_id, text=col_text,
                         command=lambda c=col_id, t=tree: self._sort_treeview(t, c))
            if col_id == "cuts":
                tree.column(col_id, width=500, anchor="w")
            elif col_id == "bar":
                tree.column(col_id, width=70, anchor="center")
            else:
                tree.column(col_id, width=120, anchor="center")

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        total_used = 0.0
        total_waste = 0.0
        total_provided = 0.0
        rows = []
        for i, plan in enumerate(plans):
            bar_len_m = plan['bar_length']
            pieces = plan['bin']
            used = sum(cut[0] for cut in pieces)
            waste = bar_len_m - used

            cut_descs = []
            for cut_len_m, lbl in pieces:
                pos = lbl.get('pos', '?')
                lf = lbl.get('listofer_no', '?')
                length_mm = cut_len_m * 1000.0
                cut_descs.append(f"{length_mm:.0f}mm (pos {pos}, LF{lf})")

            row_data = {
                "bar": f"#{i+1:03d}",
                "used_mm": f"{used*1000:.0f}",
                "waste_mm": f"{waste*1000:.0f}",
                "bar_len_mm": f"{bar_len_m*1000:.0f}",
                "cuts": ", ".join(cut_descs)
            }
            rows.append(row_data)

            total_used += used
            total_waste += waste
            total_provided += bar_len_m

        for row in rows:
            tree.insert("", "end", values=tuple(row[col] for col in self._TREE_COLS))

        waste_pct = (total_waste / total_provided * 100) if total_provided > 0 else 0
        summary = (f"Ø{dia} ({grade}): {len(plans)} bars, "
                   f"waste {total_waste*1000:.0f} mm ({waste_pct:.1f}%)")
        ttk.Label(frame, text=summary, font=("Arial", 9, "italic")).grid(
            row=2, column=0, pady=2, sticky="w")

    def _sort_treeview(self, tree, col):
        items = [(tree.item(iid, "values"), iid) for iid in tree.get_children('')]
        idx = list(self._TREE_COLS.keys()).index(col)

        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        def sort_key(row):
            val = row[0][idx]
            try:
                return float(val)
            except (ValueError, TypeError):
                return str(val).lower()

        items.sort(key=sort_key, reverse=self._sort_reverse)
        for index, (vals, iid) in enumerate(items):
            tree.move(iid, '', index)

        arrow = " ▼" if self._sort_reverse else " ▲"
        for cid in self._TREE_COLS:
            text = self._TREE_COLS[cid]
            if cid == col:
                text += arrow
            tree.heading(cid, text=text)

    # ------------------------------------------------------------------
    # Splash screen helpers
    # ------------------------------------------------------------------
    def _show_splash(self):
        self.splash = tk.Toplevel(self)
        self.splash.overrideredirect(True)
        self.splash.configure(bg="#2d3436")
        w, h = 400, 240
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        self.splash.geometry(f"{w}x{h}+{x}+{y}")
        self.splash.grab_set()

        logo_canvas = tk.Canvas(self.splash, width=60, height=40, bg="#2d3436", highlightthickness=0)
        logo_canvas.pack(pady=(15, 0))
        logo_canvas.create_line(5, 25, 55, 25, fill="#28a745", width=3)
        logo_canvas.create_line(5, 25, 5, 5, fill="#28a745", width=3)
        logo_canvas.create_line(55, 25, 55, 5, fill="#28a745", width=3)
        logo_canvas.create_line(5, 5, 15, 5, fill="#28a745", width=3)
        logo_canvas.create_line(55, 5, 45, 5, fill="#28a745", width=3)

        tk.Label(self.splash, text="AI Rebar", font=("Arial", 22, "bold"),
                 fg="#00b894", bg="#2d3436").pack(pady=(2, 0))
        tk.Label(self.splash, text="⏳ Please wait ...", font=("Arial", 11),
                 fg="#74b9ff", bg="#2d3436", wraplength=360).pack(pady=(5, 2))

        self._promo_index = 0
        self.splash_status = tk.Label(
            self.splash, text=self.PROMO_MESSAGES[0], font=("Arial", 10),
            fg="#dfe6e9", bg="#2d3436", wraplength=360)
        self.splash_status.pack(pady=(0, 5))

        self.splash_pb = ttk.Progressbar(self.splash, mode='indeterminate', length=250)
        self.splash_pb.pack(pady=5)
        self.splash_pb.start(10)

        tk.Button(self.splash, text="Cancel", command=self._cancel_optimization,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold")).pack(pady=10)

        self._rotate_splash_message()
        self.update()

    def _rotate_splash_message(self):
        if not self._is_window_alive(self.splash):
            return
        self._promo_index = (self._promo_index + 1) % len(self.PROMO_MESSAGES)
        try:
            self.splash_status.config(text=self.PROMO_MESSAGES[self._promo_index])
        except tk.TclError:
            return
        self._splash_after_id = self.splash.after(3000, self._rotate_splash_message)

    def _hide_splash(self):
        if self._splash_after_id is not None:
            try:
                self.after_cancel(self._splash_after_id)
            except Exception:
                pass
            self._splash_after_id = None
        if hasattr(self, 'splash') and self.splash is not None:
            try:
                if self._is_window_alive(self.splash):
                    self.splash_pb.stop()
                    self.splash.destroy()
            except tk.TclError:
                pass
            finally:
                self.splash = None

    def _cancel_optimization(self):
        self._cancel_event.set()
        if hasattr(self, 'splash') and self._is_window_alive(self.splash):
            try:
                self.splash_status.config(text="⚠️  Cancelling... Please wait.")
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------
    def _disable_buttons(self):
        self.export_html_btn.config(state="disabled")
        self.reoptimize_btn.config(state="disabled")
        self.confirm_plan_btn.config(state="disabled")
        self.force_reopt_btn.config(state="disabled")

    def _enable_buttons(self):
        self.export_html_btn.config(state="normal")
        self.reoptimize_btn.config(state="normal")
        self._update_buttons()

    def _update_buttons(self):
        if self.plan_status == 'confirmed':
            self.confirm_plan_btn.config(state="disabled")
            self.reoptimize_btn.config(state="disabled")
            self.force_reopt_btn.pack(side="left", padx=5)
            self.force_reopt_btn.config(state="normal")
            self.locked_label.config(text="🔒 Plan confirmed – locked")
        elif self.plan_status == 'draft':
            self.confirm_plan_btn.config(state="normal")
            self.reoptimize_btn.config(state="normal")
            self.force_reopt_btn.pack_forget()
            self.locked_label.config(text="")
        else:
            self.confirm_plan_btn.config(state="disabled")
            self.reoptimize_btn.config(state="normal")
            self.force_reopt_btn.pack_forget()
            self.locked_label.config(text="")

    # ------------------------------------------------------------------
    # Optimization entry point
    # ------------------------------------------------------------------
    def generate_plan(self):
        if self._optimizing:
            messagebox.showinfo("Busy", "Optimization is already in progress.", parent=self)
            return
        self._optimizing = True
        self._optimization_done = False

        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        if not PULP_AVAILABLE:
            messagebox.showerror("Error", "PuLP not installed.", parent=self)
            self._optimizing = False
            self._enable_buttons()
            return

        self._disable_buttons()

        data_hash = None
        if not self._bypass_cache:
            data_hash = _compute_data_hash(
                self.project_id, self.listofer_filter, self.stock_len
            )
            cached, status = _load_plan(
                self.project_id, self.listofer_filter, self.stock_len, data_hash
            )
            if cached is not None:
                self.plans_per_group = cached
                self.plan_status = status
                self._display_plan()
                self._optimizing = False
                self._enable_buttons()
                return

        self._cancel_event.clear()
        self._show_splash()

        def optimization_task():
            # Open a dedicated DB connection for this thread
            db_conn = sqlite3.connect(DB_PATH)
            db_conn.execute("PRAGMA journal_mode=WAL")
            temp_plans_per_group = {}
            error_msg = None
            scrap_updates = []      # list of scrap IDs to mark used
            scrap_additions = []    # new scraps to insert

            try:
                sorted_keys = sorted(self.data_by_key.keys(), key=lambda x: (x[0], x[1]))
                for dia, grade in sorted_keys:
                    if self._cancel_event.is_set():
                        break
                    items = self.data_by_key[(dia, grade)]
                    lengths = [it[0] for it in items]

                    available_raw = ScrapModel.get_available_scraps(self.project_id, dia, grade)
                    scrap_map = {row[0]: row[1] for row in available_raw}
                    available_scraps_m = [row[1] / 1000.0 for row in available_raw]

                    try:
                        if self.use_stock_limit_var.get():
                            plans, new_scraps_m, stock_usage = optimize_with_scraps_and_stock(
                                self.project_id, dia, grade, items, self.stock_len,
                                cancel_event=self._cancel_event
                            )
                        else:
                            plans, new_scraps_m = optimize_labeled_cuts(
                                items, self.stock_len, available_scraps_m,
                                cancel_event=self._cancel_event
                            )
                            stock_usage = {self.stock_len: 0}
                    except Exception as e:
                        msg = f"Optimization failed for Ø{dia} ({grade}): {e}"
                        logger.error(msg)
                        error_msg = msg
                        plans, new_scraps_m, stock_usage = [], [], {self.stock_len: 0}

                    if self._cancel_event.is_set():
                        break

                    temp_plans_per_group[(dia, grade)] = {
                        'plans': plans,
                        'new_scraps': new_scraps_m,
                        'stock_usage': stock_usage,
                        'scrap_map': scrap_map,
                        'items': items
                    }

                    # Process scrap updates
                    used_scrap_ids = set()
                    for plan in plans:
                        bar_len = plan['bar_length']
                        if bar_len < self.stock_len - 1e-6:
                            target_mm = bar_len * 1000.0
                            for sid, slen_mm in scrap_map.items():
                                if abs(slen_mm - target_mm) <= CUTTING_TOLERANCE_MM and sid not in used_scrap_ids:
                                    scrap_updates.append(sid)
                                    used_scrap_ids.add(sid)
                                    break

                    listofer_no = items[0][1].get('listofer_no', None) if items else None
                    for waste_m in new_scraps_m:
                        waste_mm = int(waste_m * 1000)
                        if waste_mm > 0:
                            scrap_additions.append((self.project_id, dia, waste_mm, grade, listofer_no))

                # DB writes on this thread
                cursor = db_conn.cursor()
                try:
                    for sid in scrap_updates:
                        cursor.execute("UPDATE scraps SET used = 1 WHERE id = ?", (sid,))
                    for (pid, dia, length, grade, lf) in scrap_additions:
                        cursor.execute(
                            "INSERT INTO scraps (project_id, diameter, length_mm, grade, date_created, used, listofer_number) "
                            "VALUES (?, ?, ?, ?, ?, 0, ?)",
                            (pid, dia, length, grade, datetime.datetime.now().isoformat(), lf)
                        )
                    db_conn.commit()
                except Exception as e:
                    logger.error(f"Database update failed: {e}", exc_info=True)
                    error_msg = f"Database update error: {e}"
                finally:
                    db_conn.close()

                self._temp_results = {
                    'plans_per_group': temp_plans_per_group,
                    'data_hash': data_hash,
                    'error_msg': error_msg,
                    'scrap_updates_count': len(scrap_updates),
                    'scrap_additions_count': len(scrap_additions),
                    'was_cancelled': self._cancel_event.is_set()
                }
            except Exception as e:
                logger.error(f"Optimization thread error: {e}", exc_info=True)
            finally:
                self.after(0, self._on_optimization_done)

        self._opt_thread = threading.Thread(target=optimization_task, daemon=True)
        self._opt_thread.start()

    def _on_optimization_done(self):
        if self._optimization_done:
            return
        self._optimization_done = True

        self._hide_splash()
        temp = self._temp_results or {}
        plans_per_group = temp.get('plans_per_group', {})
        error_msg = temp.get('error_msg')
        was_cancelled = temp.get('was_cancelled', False)
        new_saved = temp.get('scrap_additions_count', 0)
        used_marked = temp.get('scrap_updates_count', 0)

        if was_cancelled and not plans_per_group:
            self.summary_var.set("⚠️ Optimization cancelled by user.")
            self._optimizing = False
            self._enable_buttons()
            return

        if error_msg:
            messagebox.showwarning("Partial Failure", error_msg, parent=self)

        try:
            self.plans_per_group.clear()
            for (dia, grade), data in plans_per_group.items():
                plans = data['plans']
                new_scraps_m = data['new_scraps']
                self.plans_per_group[(dia, grade)] = {
                    'plans': plans,
                    'new_scraps': new_scraps_m
                }
                if plans:
                    self._create_diameter_tab(dia, grade, plans, new_scraps_m)

            if not was_cancelled:
                data_hash = temp.get('data_hash')
                if data_hash is None:
                    data_hash = _compute_data_hash(
                        self.project_id, self.listofer_filter, self.stock_len
                    )
                _save_plan(
                    self.project_id, self.listofer_filter, self.stock_len,
                    data_hash, self.plans_per_group, status='draft'
                )
                self.plan_status = 'draft'

            if new_saved or used_marked:
                self.summary_var.set(
                    f"✅ Scraps: {new_saved} new saved, {used_marked} reused."
                )
            else:
                self.summary_var.set("Optimization complete. Select a diameter tab to view details.")

        except Exception as e:
            logger.error(f"Error processing optimization results: {e}", exc_info=True)
            messagebox.showerror("Error", f"Error building plan view: {e}", parent=self)
        finally:
            self._optimizing = False
            self._bypass_cache = False
            self._enable_buttons()

    def _display_plan(self):
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        sorted_keys = sorted(self.plans_per_group.keys(), key=lambda x: (x[0], x[1]))
        for dia, grade in sorted_keys:
            data = self.plans_per_group[(dia, grade)]
            plans = data['plans']
            new_scraps = data.get('new_scraps', [])
            if plans:
                self._create_diameter_tab(dia, grade, plans, new_scraps)
        self.summary_var.set(f"📋 Plan loaded ({self.plan_status}). Click a tab to view.")

    def confirm_plan(self):
        if self.plan_status != 'draft':
            return
        if not messagebox.askyesno("Confirm Plan",
                                   "Are you sure you want to confirm this cutting plan?\n\n"
                                   "Once confirmed, it will be locked and cannot be re‑optimized "
                                   "without a forced override."):
            return
        data_hash = _compute_data_hash(
            self.project_id, self.listofer_filter, self.stock_len
        )
        _confirm_plan(
            self.project_id, self.listofer_filter, self.stock_len, data_hash
        )
        self.plan_status = 'confirmed'
        self._update_buttons()
        self.summary_var.set("📋 Plan confirmed and locked.")
        messagebox.showinfo("Confirmed",
                            "This cutting plan is now confirmed and locked.\n"
                            "Use 'Force Re‑optimize' only if you need to replace it.")

    def re_optimize(self):
        if self.plan_status == 'confirmed':
            messagebox.showwarning("Locked Plan",
                                   "This plan is already confirmed and locked.\n\n"
                                   "Use the 'Force Re‑optimize' button if you really need "
                                   "to overwrite it.")
            return
        self._bypass_cache = True
        self.generate_plan()

    def _force_re_optimize(self):
        if not messagebox.askyesno(
            "⚠️ Force Re‑optimize",
            "WARNING: This will permanently discard the current confirmed plan "
            "and all associated scrap assignments.\n\n"
            "This action cannot be undone. Proceed?",
            icon="warning"
        ):
            return
        if not messagebox.askyesno(
            "Final Confirmation",
            "Are you absolutely sure you want to replace the confirmed cutting plan?",
            icon="warning"
        ):
            return
        self._bypass_cache = True
        self.plan_status = None
        self.generate_plan()

    def export_html(self):
        if not self.plans_per_group:
            messagebox.showwarning("Warning", "No plan data available.")
            return

        try:
            from utils.cutting_plan_export import export_cutting_plan_html
        except ImportError:
            messagebox.showerror("Export Error",
                                 "HTML export module not available.\n"
                                 "Please check the installation or contact support.")
            return

        proj_name = "Current Project"
        client_name = ""
        if hasattr(self.parent, 'state'):
            proj_name = self.parent.state.current_project_name
            client_name = self.parent.state.current_client_name or ""
        else:
            proj_name = getattr(self.parent, 'current_project_name', proj_name)
            client_name = getattr(self.parent, 'current_client_name', "")

        default_name = f"Cutting_Plan_{datetime.date.today()}.html"
        path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")],
            initialfile=default_name
        )
        if path:
            # Extract the plan list from the stored structure
            plans_dict = {k: v['plans'] for k, v in self.plans_per_group.items()}
            try:
                export_cutting_plan_html(
                    filepath=path,
                    data_by_key=self.data_by_key,
                    stock_length=self.stock_len,
                    project_name=proj_name,
                    client_name=client_name,
                    project_id=self.project_id,
                    plans_by_key=plans_dict,          # <-- pass current plans
                    listofer_filter=self.listofer_filter,
                )
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {e}")