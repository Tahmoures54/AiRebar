# ui/coach_strip.py
"""Friendly guidance strip – reduces first-session anxiety."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class CoachStrip(ttk.Frame):
    def __init__(
        self,
        parent,
        on_add: Optional[Callable] = None,
        on_cut: Optional[Callable] = None,
        on_stock: Optional[Callable] = None,
        on_sample: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.on_add = on_add
        self.on_cut = on_cut
        self.on_stock = on_stock
        self.on_sample = on_sample
        self._tip = tk.StringVar(value="")
        self._build()

    def _build(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=4, pady=2)
        ttk.Label(bar, text="Quick path:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 8))
        for text, cmd in (
            ("1) Add position", self._go_add),
            ("2) Stock / scraps", self._go_stock),
            ("3) Cutting plan", self._go_cut),
            ("Sample project", self._go_sample),
        ):
            ttk.Button(bar, text=text, command=cmd, width=16).pack(side="left", padx=3)
        self.tip_label = ttk.Label(bar, textvariable=self._tip, foreground="#475569")
        self.tip_label.pack(side="left", padx=12)
        self.dismiss_btn = ttk.Button(bar, text="Hide tips", width=10, command=self._hide)
        self.dismiss_btn.pack(side="right", padx=4)

    def set_tip(self, text: str):
        self._tip.set(text or "")

    def set_context(self, has_project: bool, has_rebars: bool, has_stock: bool = False):
        if not has_project:
            self.set_tip("Start by opening or creating a project — takes under a minute.")
        elif not has_rebars:
            self.set_tip("Add your first position (New Pos). Shape + diameter + quantity is enough to begin.")
        elif not has_stock:
            self.set_tip("Optional: add stock bars, then run Cutting Plan for less waste.")
        else:
            self.set_tip("Ready. Run Cutting Plan, review waste %, then Confirm to update inventory.")

    def _go_add(self):
        if self.on_add:
            self.on_add()

    def _go_cut(self):
        if self.on_cut:
            self.on_cut()

    def _go_stock(self):
        if self.on_stock:
            self.on_stock()

    def _go_sample(self):
        if self.on_sample:
            self.on_sample()

    def _hide(self):
        self.pack_forget()
