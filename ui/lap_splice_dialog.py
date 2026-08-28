# ui/lap_splice_dialog.py
"""Lap / splice length calculator dialog."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.LapSplice")


class LapSpliceDialog(tk.Toplevel):
    """Simple lap / splice length calculator."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Lap / Splice Calculator")
        self.geometry("420x320")
        self.transient(parent)
        self.grab_set()

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Bar diameter (mm)").grid(row=0, column=0, sticky="w", pady=4)
        self.dia_var = tk.StringVar(value="16")
        ttk.Entry(frm, textvariable=self.dia_var, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="fy (MPa)").grid(row=1, column=0, sticky="w", pady=4)
        self.fy_var = tk.StringVar(value="400")
        ttk.Entry(frm, textvariable=self.fy_var, width=12).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="fc (MPa)").grid(row=2, column=0, sticky="w", pady=4)
        self.fc_var = tk.StringVar(value="25")
        ttk.Entry(frm, textvariable=self.fc_var, width=12).grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Multiplier (×db)").grid(row=3, column=0, sticky="w", pady=4)
        self.mult_var = tk.StringVar(value="40")
        ttk.Entry(frm, textvariable=self.mult_var, width=12).grid(row=3, column=1, sticky="w")

        ttk.Button(frm, text="Calculate", command=self._calc).grid(row=4, column=0, columnspan=2, pady=12)

        self.result = tk.StringVar(value="—")
        ttk.Label(frm, textvariable=self.result, font=("Segoe UI", 11, "bold")).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        ttk.Button(frm, text="Close", command=self.destroy).grid(row=6, column=0, columnspan=2, pady=8)

        try:
            self.geometry("+%d+%d" % (parent.winfo_rootx() + 80, parent.winfo_rooty() + 80))
        except Exception:
            pass

    def _calc(self):
        try:
            db = float(self.dia_var.get())
            mult = float(self.mult_var.get())
            lap_mm = db * mult
            self.result.set(f"Suggested lap ≈ {lap_mm:.0f} mm  ({lap_mm/10:.1f} cm)")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
