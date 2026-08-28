# ui/lap_splice_dialog.py
"""Lap splice length calculator dialog."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from logic.calculator import calculate_lap_splice
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.LapSplice")


class LapSpliceDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🔧 Lap Splice Calculator")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        ttk.Label(self, text="Bar Diameter (mm):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.dia_var = tk.StringVar(value="16")
        ttk.Entry(self, textvariable=self.dia_var, width=12).grid(row=0, column=1, padx=10, pady=10, sticky="w")
        ttk.Label(self, text="Concrete fc (MPa):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.fc_var = tk.StringVar(value="25")
        ttk.Entry(self, textvariable=self.fc_var, width=12).grid(row=1, column=1, padx=10, pady=10, sticky="w")
        ttk.Label(self, text="fy (MPa):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.fy_var = tk.StringVar(value="400")
        ttk.Entry(self, textvariable=self.fy_var, width=12).grid(row=2, column=1, padx=10, pady=10, sticky="w")
        ttk.Button(self, text="Calculate", command=self._calc).grid(row=3, column=0, columnspan=2, pady=12)
        self.result_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.result_var, font=("Segoe UI", 11, "bold")).grid(row=4, column=0, columnspan=2)
        ttk.Button(self, text="Close", command=self.destroy).grid(row=5, column=0, columnspan=2, pady=8)

    def _calc(self):
        try:
            dia = float(self.dia_var.get())
            fc = float(self.fc_var.get())
            fy = float(self.fy_var.get())
            lap = calculate_lap_splice(dia, fc, fy)
            self.result_var.set(f"Lap length ≈ {lap:.0f} mm")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
