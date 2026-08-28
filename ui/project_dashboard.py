# ui/project_dashboard.py
"""Project Dashboard – KPI overview for the active project."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from logic.project_kpi import compute_project_kpi, format_kpi_report
from utils.i18n import t
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.Dashboard")


class ProjectDashboardDialog(tk.Toplevel):
    def __init__(self, master, project_id: int):
        super().__init__(master)
        self.project_id = project_id
        self.title(f"Dashboard – RebarAgent")
        self.geometry("640x520")
        self.transient(master)
        self.minsize(480, 360)

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x")
        ttk.Label(header, text="Project Dashboard", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(header, text="Refresh", command=self._refresh).pack(side="right")

        self.text = tk.Text(main, wrap="word", font=("Consolas", 10))
        self.text.pack(fill="both", expand=True, pady=8)
        self.text.configure(state="disabled")

        ttk.Button(main, text=t("btn.close") if False else "Close", command=self.destroy).pack(anchor="e")
        self.after(50, self._refresh)

    def _refresh(self):
        try:
            kpi = compute_project_kpi(self.project_id)
            report = format_kpi_report(kpi)
        except Exception as e:
            logger.error("dashboard: %s", e, exc_info=True)
            report = f"Could not compute KPI:\n{e}"
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", report)
        self.text.configure(state="disabled")
