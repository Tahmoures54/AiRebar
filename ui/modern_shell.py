# ui/modern_shell.py
"""Premium main-shell chrome: hero header, KPI strip, action rail, workspace."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple


C = {
    "bg": "#0b1220",
    "bg_elev": "#111827",
    "bg_card": "#1a2332",
    "bg_soft": "#f1f5f9",
    "fg": "#e2e8f0",
    "fg_muted": "#94a3b8",
    "fg_dark": "#0f172a",
    "accent": "#06b6d4",
    "accent2": "#8b5cf6",
    "accent3": "#10b981",
    "warn": "#f59e0b",
    "danger": "#ef4444",
    "border": "#1e293b",
    "glow": "#22d3ee",
}


def configure_premium_styles(style: ttk.Style, theme_key: str = "premium") -> None:
    style.configure(f"{theme_key}.Hero.TFrame", background=C["bg"])
    style.configure(f"{theme_key}.Elev.TFrame", background=C["bg_elev"])
    style.configure(f"{theme_key}.Card.TFrame", background=C["bg_card"])
    style.configure(f"{theme_key}.Soft.TFrame", background=C["bg_soft"])
    style.configure(f"{theme_key}.HeroTitle.TLabel", background=C["bg"], foreground="#f8fafc", font=("Segoe UI Semibold", 16))
    style.configure(f"{theme_key}.HeroSub.TLabel", background=C["bg"], foreground=C["fg_muted"], font=("Segoe UI", 10))
    style.configure(f"{theme_key}.KPIValue.TLabel", background=C["bg_card"], foreground=C["glow"], font=("Segoe UI Semibold", 18))
    style.configure(f"{theme_key}.KPILabel.TLabel", background=C["bg_card"], foreground=C["fg_muted"], font=("Segoe UI", 9))
    style.configure(f"{theme_key}.Rail.TButton", font=("Segoe UI", 10), padding=(12, 8))
    style.configure(f"{theme_key}.Chip.TButton", font=("Segoe UI", 9), padding=(10, 6))
    style.configure(f"{theme_key}.Section.TLabelframe", background=C["bg_soft"], foreground=C["fg_dark"], font=("Segoe UI Semibold", 10))
    style.configure(f"{theme_key}.Section.TLabelframe.Label", background=C["bg_soft"], foreground=C["fg_dark"], font=("Segoe UI Semibold", 10))


class HeroHeader(ttk.Frame):
    def __init__(self, parent, theme_key: str, app_name: str = "RebarAgent",
                 tagline: str = "Intelligent BBS · Cutting Optimization · Smart Inventory",
                 on_license: Optional[Callable] = None, on_dashboard: Optional[Callable] = None,
                 on_insights: Optional[Callable] = None, **kwargs):
        super().__init__(parent, style=f"{theme_key}.Hero.TFrame", **kwargs)
        self.theme_key = theme_key
        self._project_var = tk.StringVar(value="No project selected")
        self._license_var = tk.StringVar(value="")
        self._build(app_name, tagline, on_license, on_dashboard, on_insights)

    def _build(self, app_name, tagline, on_license, on_dashboard, on_insights):
        tk_key = self.theme_key
        left = ttk.Frame(self, style=f"{tk_key}.Hero.TFrame")
        left.pack(side="left", fill="y", padx=16, pady=12)
        brand_row = ttk.Frame(left, style=f"{tk_key}.Hero.TFrame")
        brand_row.pack(anchor="w")
        accent = tk.Frame(brand_row, bg=C["accent"], width=4, height=36)
        accent.pack(side="left", padx=(0, 10))
        titles = ttk.Frame(brand_row, style=f"{tk_key}.Hero.TFrame")
        titles.pack(side="left")
        ttk.Label(titles, text=app_name, style=f"{tk_key}.HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(titles, text=tagline, style=f"{tk_key}.HeroSub.TLabel").pack(anchor="w")
        center = ttk.Frame(self, style=f"{tk_key}.Hero.TFrame")
        center.pack(side="left", expand=True, fill="x", padx=20)
        chip = tk.Frame(center, bg=C["bg_elev"], padx=14, pady=8)
        chip.pack(anchor="center")
        tk.Label(chip, textvariable=self._project_var, bg=C["bg_elev"], fg=C["fg"], font=("Segoe UI", 11, "bold")).pack()
        right = ttk.Frame(self, style=f"{tk_key}.Hero.TFrame")
        right.pack(side="right", padx=12, pady=10)
        if on_dashboard:
            ttk.Button(right, text="📊 Dashboard", command=on_dashboard, style=f"{tk_key}.Chip.TButton").pack(side="left", padx=3)
        if on_insights:
            ttk.Button(right, text="🧠 Insights", command=on_insights, style=f"{tk_key}.Chip.TButton").pack(side="left", padx=3)
        tk.Label(right, textvariable=self._license_var, bg=C["bg"], fg=C["accent3"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)
        if on_license:
            ttk.Button(right, text="🔑 License", command=on_license, style=f"{tk_key}.Chip.TButton").pack(side="left", padx=3)

    def set_project(self, name: str, client: str = ""):
        if not name:
            self._project_var.set("No project selected")
        elif client:
            self._project_var.set(f"📁  {name}  ·  {client}")
        else:
            self._project_var.set(f"📁  {name}")

    def set_license(self, text: str):
        self._license_var.set(text or "")


class KPIStrip(ttk.Frame):
    def __init__(self, parent, theme_key: str = "premium", **kwargs):
        super().__init__(parent, style=f"{theme_key}.Soft.TFrame", **kwargs)
        self.theme_key = theme_key
        self._vars: Dict[str, tk.StringVar] = {}
        self._cards_host = ttk.Frame(self, style=f"{theme_key}.Soft.TFrame")
        self._cards_host.pack(fill="x", padx=10, pady=8)
        for key, label in (("positions", "Positions"), ("weight", "Total weight"),
                           ("listofers", "Listofers"), ("stock", "Stock bars"), ("health", "Agent health")):
            self._add_card(key, label)

    def _add_card(self, key: str, label: str):
        var = tk.StringVar(value="—")
        self._vars[key] = var
        card = tk.Frame(self._cards_host, bg=C["bg_card"], padx=16, pady=10)
        card.pack(side="left", padx=6, fill="x", expand=True)
        tk.Frame(card, bg=C["accent"], height=2).pack(fill="x", pady=(0, 6))
        tk.Label(card, textvariable=var, bg=C["bg_card"], fg=C["glow"], font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(card, text=label, bg=C["bg_card"], fg=C["fg_muted"], font=("Segoe UI", 9)).pack(anchor="w")

    def update_metrics(self, positions: Any = "—", weight: Any = "—", listofers: Any = "—",
                       stock: Any = "—", health: Any = "—"):
        self._vars["positions"].set(str(positions))
        self._vars["weight"].set(str(weight))
        self._vars["listofers"].set(str(listofers))
        self._vars["stock"].set(str(stock))
        self._vars["health"].set(str(health))


class ActionRail(ttk.Frame):
    def __init__(self, parent, theme_key: str, actions: List[Tuple[str, Callable]], **kwargs):
        super().__init__(parent, style=f"{theme_key}.Elev.TFrame", **kwargs)
        self.theme_key = theme_key
        tk.Label(self, text="COMMANDS", bg=C["bg_elev"], fg=C["fg_muted"], font=("Segoe UI", 8, "bold")).pack(
            anchor="w", padx=12, pady=(12, 6))
        for text, cmd in actions:
            ttk.Button(self, text=text, command=cmd, style=f"{theme_key}.Rail.TButton").pack(fill="x", padx=10, pady=3)
        ttk.Frame(self, style=f"{theme_key}.Elev.TFrame").pack(fill="both", expand=True)


class CommandStrip(ttk.Frame):
    def __init__(self, parent, theme_key: str, actions: List[Tuple[str, Callable]], **kwargs):
        super().__init__(parent, style=f"{theme_key}.Soft.TFrame", **kwargs)
        host = ttk.Frame(self, style=f"{theme_key}.Soft.TFrame")
        host.pack(fill="x", padx=8, pady=6)
        for i, (text, cmd) in enumerate(actions):
            ttk.Button(host, text=text, command=cmd, style=f"{theme_key}.Chip.TButton").pack(side="left", padx=3)
            if i in (2, 5):
                ttk.Separator(host, orient="vertical").pack(side="left", fill="y", padx=6)
