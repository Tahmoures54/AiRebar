# ui/main_window_shell.py
"""Premium shell layout mixin for MainWindow."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from config import APP_NAME, APP_VERSION, TOOLBAR_BUTTONS
from db.models import ListoferModel, RebarModel
from logic.calculator import calculate_weight
from shapes.definitions import default_shape_registry
from utils.logger import setup_logger

from ui.bbs_treeview import BBSTreeview
from ui.menu_bar import MenuBar
from ui.status_bar import StatusBar
from ui.coach_strip import CoachStrip
from ui.modern_shell import (
    HeroHeader, KPIStrip, ActionRail, CommandStrip, configure_premium_styles,
)

logger = setup_logger("RebarAgent.MainShell")


class MainWindowShellMixin:
    def _build_ui(self) -> None:
        theme_key = "premium"
        try:
            style = ttk.Style(self)
            configure_premium_styles(style, theme_key)
        except Exception:
            pass

        self.menu_bar = MenuBar(self, self.app)
        self.menu_bar.pack(fill="x")

        self.hero = HeroHeader(
            self,
            theme_key=theme_key,
            app_name=f"{APP_NAME}  v{APP_VERSION}",
            tagline="Intelligent BBS · Cutting Optimization · Smart Inventory",
            on_license=self.open_license_dialog,
            on_dashboard=self._open_dashboard_safe,
            on_insights=self._open_insights_safe,
        )
        self.hero.pack(fill="x")
        self.license_status_label = None

        self.kpi_strip = KPIStrip(self, theme_key=theme_key)
        self.kpi_strip.pack(fill="x")

        self.coach = CoachStrip(
            self,
            on_add=self.open_input_dialog,
            on_cut=self.show_cutting_plan_all,
            on_stock=self.show_stock_manager,
            on_sample=getattr(self, "load_sample_project", None),
        )
        self.coach.pack(fill="x", padx=4, pady=(0, 2))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=6, pady=4)

        rail_actions = [
            ("📌  New position", self.open_input_dialog),
            ("✂️  Cutting plan", self.show_cutting_plan_all),
            ("📦  Stock", self.show_stock_manager),
            ("♻️  Scrap bank", self.show_scrap_manager),
            ("📐  Lap / splice", self.show_lap_splice),
            ("📊  Dashboard", self._open_dashboard_safe),
            ("🧠  Agent insights", self._open_insights_safe),
        ]
        self.action_rail = ActionRail(body, theme_key=theme_key, actions=rail_actions)
        self.action_rail.pack(side="left", fill="y", padx=(0, 8))

        workspace = ttk.Frame(body)
        workspace.pack(side="left", fill="both", expand=True)

        chip_actions = [
            ("✏️ Edit", self.edit_selected_bar),
            ("🗑️ Delete", self.delete_selected_bar),
            ("📄 HTML report", self.export_html_report),
            ("📗 Excel", self.export_excel),
            ("📕 PDF", self.export_pdf),
            ("BVBS ↕", self.export_bvbs),
        ]
        self.cmd_strip = CommandStrip(workspace, theme_key=theme_key, actions=chip_actions)
        self.cmd_strip.pack(fill="x")

        lf_frame = ttk.LabelFrame(workspace, text="  Listofer summary", padding=6)
        lf_frame.pack(fill="x", pady=(4, 6))
        columns = ("lf_number", "lf_desc", "rebar_count", "total_weight")
        self.listofer_tree = ttk.Treeview(lf_frame, columns=columns, show="headings", height=3)
        self.listofer_tree.heading("lf_number", text="No.")
        self.listofer_tree.heading("lf_desc", text="Description")
        self.listofer_tree.heading("rebar_count", text="Bars")
        self.listofer_tree.heading("total_weight", text="Weight (kg)")
        for col, w in zip(columns, (80, 280, 80, 100)):
            self.listofer_tree.column(col, width=w, anchor="center")
        self.listofer_tree.pack(fill="x")
        self.listofer_tree.bind("<Double-1>", lambda e: self._on_listofer_double_click())

        bbs_frame = ttk.LabelFrame(workspace, text="  Bar bending schedule", padding=4)
        bbs_frame.pack(fill="both", expand=True)
        self.bbs_treeview = BBSTreeview(bbs_frame, self.app)
        self.bbs_treeview.pack(fill="both", expand=True)

        self.status_bar = StatusBar(self, self.app)
        self.status_bar.pack(side="bottom", fill="x")

    def _open_dashboard_safe(self) -> None:
        if not self._ensure_project():
            return
        try:
            from ui.project_dashboard import ProjectDashboard
            ProjectDashboard(
                self,
                self.app.state.current_project_id,
                getattr(self.app.state, "current_project_name", "") or "",
            )
        except Exception as e:
            messagebox.showerror("Dashboard", str(e))

    def _open_insights_safe(self) -> None:
        if not self._ensure_project():
            return
        try:
            from ui.agent_insights import AgentInsightsDialog
            AgentInsightsDialog(self, self.app.state.current_project_id)
        except Exception:
            try:
                from logic.agent_brain import AgentBrain
                brain = AgentBrain(self.app.state.current_project_id)
                report = brain.analyze() if hasattr(brain, "analyze") else str(brain)
                messagebox.showinfo("Agent insights", str(report)[:2000])
            except Exception as e:
                messagebox.showinfo("Agent insights", f"Insights unavailable:\n{e}")

    def _refresh_kpi_strip(self) -> None:
        if not getattr(self, "kpi_strip", None):
            return
        pid = getattr(self.app.state, "current_project_id", None)
        if not pid:
            self.kpi_strip.update_metrics()
            if getattr(self, "coach", None):
                self.coach.set_context(False, False, False)
            return
        try:
            rebars = RebarModel.get_for_project(pid) or []
            n_pos = len(rebars)
            weight = 0.0
            for bar in rebars:
                try:
                    if len(bar) >= 8:
                        dia, shape_name, dims_json, qty = bar[4], bar[5], bar[6], bar[7]
                        dims = json.loads(dims_json) if isinstance(dims_json, str) else (dims_json or {})
                        length_mm = default_shape_registry.calc_shape_length(shape_name, dims, dia) or 0
                        _, piece_wt = calculate_weight(dia, length_mm)
                        weight += piece_wt * (qty or 0)
                except Exception:
                    pass
            lfs = ListoferModel.get_numbers(pid) or []
            stock_n = "—"
            try:
                from db.models import StockModel
                rows = StockModel.get_all(project_id=pid) or []
                stock_n = sum(int(r[4] or 0) for r in rows)
            except Exception:
                pass
            health = "—"
            try:
                from logic.agent_brain import AgentBrain
                brain = AgentBrain(pid)
                if hasattr(brain, "health_score"):
                    health = f"{brain.health_score():.0f}%"
                elif hasattr(brain, "score"):
                    health = str(brain.score)
            except Exception:
                pass
            self.kpi_strip.update_metrics(
                positions=n_pos,
                weight=f"{weight:.1f} kg",
                listofers=len(lfs),
                stock=stock_n,
                health=health,
            )
            if getattr(self, "coach", None):
                self.coach.set_context(True, n_pos > 0, stock_n not in (0, "—"))
        except Exception as e:
            logger.debug("KPI refresh: %s", e)

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar_actions = {
            "new_rebar": self.open_input_dialog,
            "edit": self.edit_selected_bar,
            "delete": self.delete_selected_bar,
            "print_listofer": self.export_html_report,
            "cutting_plan": self.show_cutting_plan_all,
            "lap_splice": self.show_lap_splice,
            "scrap_manager": self.show_scrap_manager,
            "stock_manager": self.show_stock_manager,
        }
        toolbar_labels = dict(TOOLBAR_BUTTONS)
        toolbar_labels["new_rebar"] = "📌 New Pos"
        for key, cmd in toolbar_actions.items():
            ttk.Button(parent, text=toolbar_labels.get(key, key), command=cmd).pack(side="left", padx=5)

    def update_project_display(self) -> None:
        name = getattr(self.app.state, "current_project_name", "") or ""
        client = getattr(self.app.state, "current_client_name", "") or ""
        if getattr(self, "hero", None):
            self.hero.set_project(name, client)
        self._refresh_kpi_strip()
        try:
            self.refresh_listofer_summary()
        except Exception:
            pass

    def refresh_license_display(self) -> None:
        try:
            from utils.license import format_license_status
            text = format_license_status(self.app.db)
        except Exception:
            text = ""
        if getattr(self, "hero", None):
            self.hero.set_license(text)
        elif getattr(self, "license_status_label", None) is not None:
            self.license_status_label.config(text=text)
