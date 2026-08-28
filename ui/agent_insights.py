# ui/agent_insights.py
"""Agent Insights – intelligent analysis and recommendations for the current project."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from collections import defaultdict

from db.models import ListoferModel, RebarModel, ScrapModel, StockModel
from logic.calculator import calculate_weight
from shapes.definitions import default_shape_registry
from logic.inventory import analyze_stock_intelligence
from logic.agent_brain import analyze_project, format_agent_report
from utils.logger import setup_logger
from utils.i18n import t

if TYPE_CHECKING:
    from main import RebarAgentApp

logger = setup_logger("RebarAgent.AgentInsights")


class AgentInsightsDialog(tk.Toplevel):
    def __init__(self, master: tk.Tk, project_id: int):
        super().__init__(master)
        self.master_app = master
        self.project_id = project_id
        self.title(f"🤖 {t('insights.title')} – RebarAgent")
        self.geometry("780x620")
        self.minsize(640, 500)
        self.transient(master)
        self.grab_set()
        self._build_ui()
        self.after(50, self._run_analysis)
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="🤖 Agent Insights", font=("Segoe UI", 14, "bold")).pack(side="left")
        self.status_var = tk.StringVar(value=t("insights.analyzing"))
        ttk.Label(header, textvariable=self.status_var, foreground="#64748b").pack(side="left", padx=12)
        self.health_var = tk.StringVar(value="")
        self.health_label = ttk.Label(main, textvariable=self.health_var, font=("Segoe UI", 11, "bold"))
        self.health_label.pack(anchor="w", pady=(0, 4))
        self.headline_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.headline_var, wraplength=720).pack(anchor="w", pady=(0, 6))
        self.action_bar = ttk.Frame(main)
        self.action_bar.pack(fill="x", pady=(0, 8))
        self.nb = ttk.Notebook(main)
        self.nb.pack(fill="both", expand=True)
        self.summary_frame = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.summary_frame, text="  📊 Summary  ")
        self.summary_text = tk.Text(self.summary_frame, wrap="word", font=("Consolas", 10), height=18)
        self.summary_text.pack(fill="both", expand=True)
        self.summary_text.configure(state="disabled")
        self.rec_frame = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.rec_frame, text="  💡 Recommendations  ")
        self.rec_text = tk.Text(self.rec_frame, wrap="word", font=("Segoe UI", 10), height=18)
        self.rec_text.pack(fill="both", expand=True)
        self.rec_text.configure(state="disabled")
        self.dia_frame = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.dia_frame, text="  📏 By Diameter  ")
        cols = ("diameter", "pieces", "total_length_m", "weight_kg", "scraps")
        self.dia_tree = ttk.Treeview(self.dia_frame, columns=cols, show="headings", height=14)
        for c, tlabel, w in [("diameter", "Ø (mm)", 80), ("pieces", "Pieces", 80), ("total_length_m", "Total Length (m)", 130), ("weight_kg", "Weight (kg)", 110), ("scraps", "Available Scraps", 120)]:
            self.dia_tree.heading(c, text=tlabel)
            self.dia_tree.column(c, width=w, anchor="center")
        self.dia_tree.pack(fill="both", expand=True)
        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Button(footer, text="Refresh Analysis", command=self._run_analysis).pack(side="left")
        ttk.Button(footer, text=t("btn.close"), command=self.destroy).pack(side="right")

    def _set_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _run_analysis(self):
        self._agent_report = None
        self.status_var.set(t("insights.analyzing"))
        self.update_idletasks()
        try:
            self._agent_report = analyze_project(self.project_id)
            report, recommendations, dia_rows = self._analyze()
            brain = format_agent_report(self._agent_report)
            report = brain + "\n\n" + ("─" * 40) + "\n\n" + report
            self._set_text(self.summary_text, report)
            self._set_text(self.rec_text, recommendations)
            for item in self.dia_tree.get_children():
                self.dia_tree.delete(item)
            for row in dia_rows:
                self.dia_tree.insert("", "end", values=row)
            self._apply_agent_banner(self._agent_report)
            self.status_var.set(t("insights.done"))
        except Exception as e:
            logger.error(f"Agent analysis failed: {e}", exp_info=True)
            self.status_var.set("Analysis failed")
            messagebox.showerror("Agent Error", f"Could not analyze project:\n{e}", parent=self)

    def _analyze(self) -> Tuple[str, str, List[tuple]]:
        project_id = self.project_id
        rebars = RebarModel.get_for_project(project_id)
        listofers = ListoferModel.get_numbers(project_id)
        scraps = ScrapModel.get_all_scraps(project_id)
        stocks = StockModel.get_all(project_id)
        by_dia: Dict[float, dict] = defaultdict(lambda: {"pieces": 0, "length_mm": 0.0, "weight": 0.0, "grades": set()})
        total_weight = 0.0
        total_pieces = 0
        shape_counts: Dict[str, int] = defaultdict(int)
        for row in rebars:
            if len(row) < 8:
                continue
            dia = float(row[4])
            shape_name = row[5] or "00"
            dims_raw = row[6]
            qty = int(row[7] or 1)
            grade = row[12] if len(row) > 12 else "A3"
            dims = {}
            if isinstance(dims_raw, str):
                try:
                    dims = json.loads(dims_raw)
                except Exception:
                    dims = {}
            elif isinstance(dims_raw, dict):
                dims = dims_raw
            try:
                length_mm = float(default_shape_registry.calc_shape_length(shape_name, dims, dia))
            except Exception:
                length_mm = 0.0
            _, piece_wt = calculate_weight(dia, length_mm)
            total_len = length_mm * qty
            total_wt = piece_wt * qty
            by_dia[dia]["pieces"] += qty
            by_dia[dia]["length_mm"] += total_len
            by_dia[dia]["weight"] += total_wt
            by_dia[dia]["grades"].add(grade)
            total_weight += total_wt
            total_pieces += qty
            shape_counts[shape_name] += qty
        scrap_by_dia: Dict[float, int] = defaultdict(int)
        scrap_total_m = 0.0
        for s in scraps:
            if len(s) < 3:
                continue
            used = s[5] if len(s) > 5 else 0
            if used:
                continue
            dia = float(s[1])
            length_mm = float(s[2])
            scrap_by_dia[dia] += 1
            scrap_total_m += length_mm / 1000.0
        stock_lines = []
        for s in stocks or []:
            try:
                if len(s) >= 6:
                    dia, length, qty, grade = s[2], s[3], s[4], s[5]
                elif len(s) >= 5:
                    dia, length, qty, grade = s[1], s[2], s[3], s[4]
                else:
                    continue
                stock_lines.append(f"  Ø{dia} mm × {length/1000:.1f} m → {qty} bars ({grade})")
            except Exception:
                continue
        lines = ["=" * 56, "  REBARAGENT – PROJECT ANALYSIS REPORT", "=" * 56, "",
                 f"Listofers          : {len(listofers)}", f"Total rebar entries: {len(rebars)}",
                 f"Total pieces       : {total_pieces}", f"Total weight       : {total_weight:,.1f} kg",
                 f"Usable scraps      : {sum(scrap_by_dia.values())} pcs  ({scrap_total_m:.1f} m)",
                 f"Stock records      : {len(stocks or [])}", "", "-" * 56, "TOP SHAPES", "-" * 56]
        for shape, cnt in sorted(shape_counts.items(), key=lambda x: -x[1])[:8]:
            lines.append(f"  {shape:<12}  {cnt:>6} pieces")
        if not shape_counts:
            lines.append("  (no data)")
        lines.extend(["", "-" * 56, "STOCK INVENTORY", "-" * 56])
        lines.extend(stock_lines if stock_lines else ["  No stock defined. Consider adding stock bars."])
        lines.extend(["", "=" * 56])
        recs = ["💡 SMART RECOMMENDATIONS FROM REBARAGENT\n", "─" * 48 + "\n"]
        if total_pieces == 0:
            recs.append(f"• {t('insights.empty')}\n")
        else:
            if scrap_total_m < 5 and total_pieces > 20:
                recs.append("• Low scrap inventory. After the next cutting plan, usable off-cuts will be saved automatically in Scrap Bank.\n")
            if not stocks:
                recs.append("• No stock bars defined. Open Stock Manager and add your available 12 m / 6 m bars so the optimizer can respect real inventory.\n")
            long_pieces = 0
            for dia, info in by_dia.items():
                avg = (info["length_mm"] / info["pieces"]) if info["pieces"] else 0
                if avg > 11000:
                    long_pieces += info["pieces"]
            if long_pieces > 0:
                recs.append(f"• {long_pieces} pieces have average length > 11 m. Check if stock length is set correctly (usually 12 m).\n")
            if len(by_dia) >= 6:
                recs.append("• High diameter diversity. Group cutting plans by diameter for better scrap reuse and less changeover.\n")
            recs.append("• Run «Cutting Plan (All)» after updating stock and scraps for the best waste reduction.\n")
            recs.append("• Use the Scrap Manager regularly – the optimizer prioritizes existing off-cuts before cutting new stock bars.\n")
        recs.append("\n" + "─" * 48)
        recs.append("\nThese suggestions are rule-based heuristics. Always verify against site conditions and design drawings.")
        dia_rows = []
        for dia in sorted(by_dia.keys()):
            info = by_dia[dia]
            length_m = info["length_mm"] / 1000.0
            dia_rows.append((f"{dia:g}", info["pieces"], f"{length_m:.1f}", f"{info['weight']:.1f}", scrap_by_dia.get(dia, 0)))
        try:
            sa = analyze_stock_intelligence(self.project_id)
            recs.append("\n\n— Stock / procurement —\n")
            if sa.get("order_suggestions"):
                for s in sa["order_suggestions"]:
                    recs.append(f"• {s}\n")
            elif sa.get("summary"):
                recs.append(sa["summary"] + "\n")
        except Exception:
            pass
        return "\n".join(lines), "".join(recs), dia_rows

    def _apply_agent_banner(self, report):
        if not report:
            return
        try:
            self.health_var.set(f"Health {report.health_score}/100 — {report.health_label}")
            self.headline_var.set(report.headline)
            color = "#15803d" if report.health_score >= 80 else ("#ca8a04" if report.health_score >= 55 else "#b91c1c")
            self.health_label.configure(foreground=color)
        except Exception:
            pass
        for w in self.action_bar.winfo_children():
            w.destroy()
        for act in (report.actions or [])[:4]:
            ttk.Button(self.action_bar, text=act.title[:40], command=lambda a=act: self._run_action(a)).pack(side="left", padx=3)

    def _run_action(self, act):
        app = self.master_app
        mw = getattr(app, "main_window", None) or getattr(app, "win", None)
        target = mw
        if target is None:
            try:
                from ui.main_window import MainWindow
                for c in app.winfo_children():
                    if isinstance(c, MainWindow):
                        target = c
                        break
            except Exception:
                target = None
        mapping = {"add_pos": "open_input_dialog", "stock": "show_stock_manager", "scrap": "show_scrap_manager", "cutting": "show_cutting_plan_all", "insights": None}
        method = mapping.get(getattr(act, "action", ""), None)
        if target and method and hasattr(target, method):
            try:
                self.destroy()
                getattr(target, method)()
                return
            except Exception as e:
                logger.error("action dispatch: %s", e)
        messagebox.showinfo(act.title, act.detail, parent=self)
