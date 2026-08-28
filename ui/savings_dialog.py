# ui/savings_dialog.py
"""One-page savings report after confirming a cutting plan."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Dict, Optional


class SavingsReportDialog(tk.Toplevel):
    def __init__(self, master, metrics: Dict[str, Any], naive_bars: Optional[int] = None, stock_length_m: float = 12.0):
        super().__init__(master)
        self.title("Savings report – RebarAgent")
        self.geometry("480x420")
        self.transient(master)
        self.resizable(False, False)

        bars = int(metrics.get("bars") or 0)
        stock_bars = int(metrics.get("stock_bars") or 0)
        scrap_bars = int(metrics.get("scrap_bars") or 0)
        total_bar_m = float(metrics.get("total_bar_m") or 0)
        total_cut_m = float(metrics.get("total_cut_m") or 0)
        waste_m = float(metrics.get("waste_m") or 0)
        util = float(metrics.get("utilization_pct") or 0)
        demand_m = float(metrics.get("demand_m") or total_cut_m)

        if naive_bars is None:
            if stock_length_m > 0 and demand_m > 0:
                import math
                naive_bars = int(math.ceil(demand_m / stock_length_m))
            else:
                naive_bars = max(stock_bars, bars)
        bars_saved = max(0, naive_bars - stock_bars)
        naive_material_m = naive_bars * float(stock_length_m)
        material_saved_m = max(0.0, naive_material_m - total_bar_m)

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Cutting confirmed", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(main, text="Share this snapshot with your project manager.", foreground="#64748b").pack(anchor="w", pady=(0, 12))

        card = ttk.LabelFrame(main, text="Results", padding=12)
        card.pack(fill="x")
        for label, val in [
            ("Demand length", f"{demand_m:.2f} m"),
            ("Bars used (stock + scrap)", f"{bars}  (stock {stock_bars} · scrap {scrap_bars})"),
            ("Material used", f"{total_bar_m:.2f} m"),
            ("Cut length", f"{total_cut_m:.2f} m"),
            ("Waste", f"{waste_m:.2f} m"),
            ("Utilization", f"{util:.1f} %"),
        ]:
            r = ttk.Frame(card)
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=label, width=28).pack(side="left")
            ttk.Label(r, text=val, font=("Segoe UI", 10, "bold")).pack(side="left")

        save_fr = ttk.LabelFrame(main, text="Estimated savings vs naive one-bar-per-need", padding=12)
        save_fr.pack(fill="x", pady=12)
        ttk.Label(save_fr, text=f"Naive stock bars (ceil demand ÷ {stock_length_m:g} m): {naive_bars}").pack(anchor="w")
        ttk.Label(save_fr, text=f"Stock bars actually used: {stock_bars}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(save_fr, text=f"≈ {bars_saved} fewer stock bars · ≈ {material_saved_m:.1f} m less material drawn", foreground="#15803d", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6, 0))

        self._report_text = (
            f"RebarAgent savings report\nDemand: {demand_m:.2f} m\nBars used: {bars} (stock {stock_bars}, scrap {scrap_bars})\n"
            f"Material used: {total_bar_m:.2f} m · Cut: {total_cut_m:.2f} m · Waste: {waste_m:.2f} m\nUtilization: {util:.1f}%\n"
            f"Naive baseline bars (@{stock_length_m:g} m): {naive_bars}\nEstimated fewer stock bars: {bars_saved}\nEstimated material not drawn: {material_saved_m:.1f} m\n"
        )
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Copy report", command=self._copy).pack(side="left", padx=4)
        ttk.Button(btns, text="Save .txt…", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right", padx=4)
        self.grab_set()

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._report_text)
        messagebox.showinfo("Copied", "Report copied to clipboard.", parent=self)

    def _save(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], initialfile="rebaragent_savings.txt", parent=self)
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._report_text)
        messagebox.showinfo("Saved", path, parent=self)
