# ui/cutting_plan_window.py
"""Cutting plan window: optimize, confirm, export."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Any, Dict

from logic.optimizer import (
    optimize_with_scraps_and_stock,
    OptimizerOptions,
    compute_plan_metrics,
    PULP_AVAILABLE,
)
from logic.inventory import apply_cutting_plan_inventory, revert_cutting_plan_inventory
from ui.cutting_plan_db import _compute_data_hash, _load_plan, _save_plan, _confirm_plan
from utils.logger import setup_logger
from utils.i18n import t

logger = setup_logger("RebarAgent.CuttingPlan")


class CuttingPlanWindow(tk.Toplevel):
    """Optimized cutting plan UI with draft/confirm lifecycle."""

    def __init__(self, parent, project_id, data_by_key, stock_length, listofer_filter=None):
        super().__init__(parent)
        self.title("Cutting Plan")
        self.geometry("960x640")
        self.transient(parent)
        self.project_id = project_id
        self.data_by_key = data_by_key or {}
        self.stock_len = float(stock_length)
        self.listofer_filter = listofer_filter
        self.plans_per_group: Dict[Any, Any] = {}
        self.plan_status = "draft"
        self._inventory_ledger = None
        self._optimizing = False
        self._bypass_cache = False
        self._cancel_event = threading.Event()
        self.summary_var = tk.StringVar(value="")
        self.create_widgets()
        self.after(100, self.generate_plan)

    def create_widgets(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Generate / Optimize", command=self.generate_plan).pack(side=tk.LEFT, padx=4)
        self.btn_confirm = ttk.Button(top, text="Confirm Plan", command=self.confirm_plan)
        self.btn_confirm.pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Re-optimize", command=self.re_optimize).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Export HTML", command=self.export_html).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Label(top, textvariable=self.summary_var).pack(side=tk.LEFT, padx=12)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill=tk.X, padx=8, pady=(0, 8))

    def _enable_buttons(self):
        for w in self.winfo_children():
            try:
                for c in w.winfo_children():
                    if isinstance(c, ttk.Button):
                        c.state(["!disabled"])
            except Exception:
                pass
        if self.plan_status == "confirmed":
            self.btn_confirm.state(["disabled"])

    def _disable_buttons(self):
        for w in self.winfo_children():
            try:
                for c in w.winfo_children():
                    if isinstance(c, ttk.Button):
                        c.state(["disabled"])
            except Exception:
                pass

    def generate_plan(self):
        if self._optimizing:
            return
        self._optimizing = True
        self._cancel_event.clear()
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        if not PULP_AVAILABLE:
            messagebox.showerror("Error", "PuLP not installed. pip install pulp", parent=self)
            self._optimizing = False
            return
        if not self._bypass_cache:
            data_hash = _compute_data_hash(self.project_id, self.listofer_filter, self.stock_len)
            cached, status = _load_plan(self.project_id, self.listofer_filter, self.stock_len, data_hash)
            if cached is not None:
                self.plans_per_group = cached
                self.plan_status = status or "draft"
                self._inventory_ledger = cached.get("_inventory_ledger") if isinstance(cached, dict) else None
                self._display_plan()
                self._optimizing = False
                self._enable_buttons()
                return
        self._disable_buttons()
        keys = sorted(self.data_by_key.keys(), key=lambda x: (x[0], x[1]))
        self.progress["maximum"] = max(1, len(keys))
        self.progress["value"] = 0

        def task():
            temp: Dict[Any, Any] = {}
            err = None
            try:
                opts = OptimizerOptions()
                for i, (dia, grade) in enumerate(keys, start=1):
                    if self._cancel_event.is_set():
                        break
                    items = self.data_by_key[(dia, grade)]
                    plans, new_scraps, usage = optimize_with_scraps_and_stock(
                        self.project_id, float(dia), str(grade), items, self.stock_len,
                        opts=opts, cancel_event=self._cancel_event,
                    )
                    metrics = compute_plan_metrics(plans, self.stock_len) if plans else {}
                    temp[(dia, grade)] = {
                        "plans": plans, "new_scraps": new_scraps,
                        "stock_usage": usage, "metrics": metrics,
                    }
                    self.after(0, lambda v=i: self.progress.configure(value=v))
            except Exception as e:
                logger.exception("optimize failed")
                err = str(e)

            def done():
                self._optimizing = False
                if err:
                    messagebox.showerror("Optimization", err, parent=self)
                else:
                    self.plans_per_group = temp
                    self.plan_status = "draft"
                    data_hash = _compute_data_hash(self.project_id, self.listofer_filter, self.stock_len)
                    _save_plan(self.project_id, self.listofer_filter, self.stock_len, data_hash, temp, status="draft")
                    self._display_plan()
                self._enable_buttons()

            self.after(0, done)

        threading.Thread(target=task, daemon=True).start()

    def _display_plan(self):
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        n_bars = 0
        total_waste = 0.0
        for key in sorted([k for k in self.plans_per_group if isinstance(k, tuple)], key=lambda x: (x[0], x[1])):
            dia, grade = key
            data = self.plans_per_group[key]
            plans = data.get("plans") or []
            new_scraps = data.get("new_scraps") or []
            if not plans:
                continue
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=f"Ø{dia:g} {grade}")
            cols = ("bar", "pieces", "used_m", "waste_m", "source")
            tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)
            for c, w in zip(cols, (60, 280, 80, 80, 100)):
                tree.heading(c, text=c)
                tree.column(c, width=w, anchor="center")
            tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
            sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=sb.set)
            for i, plan in enumerate(plans, start=1):
                bin_items = plan.get("bin") or []
                lengths = [f"{L:.3f}" for L, _ in bin_items]
                used = sum(L for L, _ in bin_items)
                bar_len = float(plan.get("bar_length") or self.stock_len)
                waste = max(0.0, bar_len - used)
                src = f"scrap#{plan['scrap_id']}" if plan.get("scrap_id") is not None else "stock"
                tree.insert("", tk.END, values=(i, ", ".join(lengths), f"{used:.3f}", f"{waste:.3f}", src))
                n_bars += 1
                total_waste += waste
            if new_scraps:
                tree.insert("", tk.END, values=("-", f"offcuts: {new_scraps}", "", "", ""))
        self.summary_var.set(f"Status: {self.plan_status}  |  bars: {n_bars}  |  waste: {total_waste:.2f} m")

    def confirm_plan(self):
        if self.plan_status == "confirmed":
            return
        if not self.plans_per_group:
            messagebox.showinfo("Info", "No plan to confirm.", parent=self)
            return
        if not messagebox.askyesno("Confirm", "Apply this plan to inventory (scrap/stock)?", parent=self):
            return
        try:
            ledger = apply_cutting_plan_inventory(self.project_id, self.plans_per_group, self.stock_len)
            self._inventory_ledger = ledger
            self.plans_per_group["_inventory_ledger"] = ledger
            self.plan_status = "confirmed"
            data_hash = _compute_data_hash(self.project_id, self.listofer_filter, self.stock_len)
            _save_plan(self.project_id, self.listofer_filter, self.stock_len, data_hash, self.plans_per_group, status="confirmed")
            _confirm_plan(self.project_id, self.listofer_filter, self.stock_len, data_hash)
            try:
                from utils.events import bus
                bus.emit("cut.confirmed", {"project_id": self.project_id})
                bus.emit("ui.refresh_request", {"reason": "cut_confirmed", "project_id": self.project_id})
            except Exception:
                pass
            self._enable_buttons()
            self.summary_var.set(f"Confirmed. Stock bars used: {ledger.get('stock_bars_consumed', 0)}")
            messagebox.showinfo("Confirmed", "Inventory updated.", parent=self)
        except Exception as e:
            logger.exception("confirm failed")
            messagebox.showerror("Confirm", str(e), parent=self)

    def re_optimize(self):
        if self.plan_status == "confirmed" and self._inventory_ledger:
            if not messagebox.askyesno("Re-optimize", "Revert inventory and re-run optimizer?", parent=self):
                return
            try:
                revert_cutting_plan_inventory(self.project_id, self._inventory_ledger)
                try:
                    from utils.events import bus
                    bus.emit("cut.rolled_back", {"project_id": self.project_id})
                    bus.emit("ui.refresh_request", {"reason": "cut_rolled_back", "project_id": self.project_id})
                except Exception:
                    pass
            except Exception as e:
                messagebox.showerror("Revert", str(e), parent=self)
                return
            self._inventory_ledger = None
            self.plan_status = "draft"
        self._bypass_cache = True
        self.generate_plan()
        self._bypass_cache = False

    def export_html(self):
        if not self.plans_per_group:
            messagebox.showinfo("Info", "No plan to export.", parent=self)
            return
        path = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
        if not path:
            return
        try:
            rows = ["<html><head><meta charset='utf-8'><title>Cutting Plan</title></head><body>"]
            rows.append(f"<h1>Cutting Plan — project {self.project_id}</h1>")
            rows.append(f"<p>Status: {self.plan_status} · stock {self.stock_len} m</p>")
            for key in sorted([k for k in self.plans_per_group if isinstance(k, tuple)], key=lambda x: (x[0], x[1])):
                dia, grade = key
                data = self.plans_per_group[key]
                rows.append(f"<h2>Ø{dia:g} mm — {grade}</h2><table border='1' cellpadding='4'>")
                rows.append("<tr><th>#</th><th>Pieces (m)</th><th>Used</th><th>Waste</th><th>Source</th></tr>")
                for i, plan in enumerate(data.get("plans") or [], start=1):
                    bin_items = plan.get("bin") or []
                    lengths = ", ".join(f"{L:.3f}" for L, _ in bin_items)
                    used = sum(L for L, _ in bin_items)
                    bar_len = float(plan.get("bar_length") or self.stock_len)
                    waste = max(0.0, bar_len - used)
                    src = f"scrap#{plan['scrap_id']}" if plan.get("scrap_id") is not None else "stock"
                    rows.append(f"<tr><td>{i}</td><td>{lengths}</td><td>{used:.3f}</td><td>{waste:.3f}</td><td>{src}</td></tr>")
                rows.append("</table>")
            rows.append("</body></html>")
            Path(path).write_text("\n".join(rows), encoding="utf-8")
            messagebox.showinfo("Export", f"Saved:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export", str(e), parent=self)
