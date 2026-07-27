# ui/main_window.py
"""
Main application window – contains all UI elements.
Includes a dedicated Listofer Summary treeview in the workspace.
Auto-selects or creates a project if none is active.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
import tkinter as tk
import webbrowser
import getpass
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, TYPE_CHECKING

from config import (
    DEFAULT_REBAR_GRADE, ERROR_MSGS, FILTER_SHOW_ALL, FONT_DEFAULTS,
    TOOLBAR_BUTTONS
)
from db.models import ListoferModel, ProjectModel, RebarModel
from logic.calculator import calculate_weight
from shapes.definitions import default_shape_registry

from utils.bvbs_export import export_bvbs
from utils.bvbs_import import import_bvbs, import_bvbs_preview
from utils.excel_export import export_excel
from utils.html_report import export_html
from utils.license import format_license_status, increment_usage
from utils.logger import setup_logger
from utils.pdf_export import export_pdf

from ui.bbs_treeview import BBSTreeview
from ui.custom_shape_designer import CustomShapeDesigner
from ui.dialogs import CuttingPlanWindow, LapSpliceDialog
from ui.input_dialog import InputDialog
from ui.license_dialog import LicenseDialog
from ui.listofer_selector_window import ListoferSelectorWindow
from ui.logo_widget import LogoWidget
from ui.menu_bar import MenuBar
from ui.scrap_manager import ScrapManagerWindow
from ui.settings_window import SettingsWindow
from ui.status_bar import StatusBar
from ui.stock_manager import StockManagerWindow
from ui.welcome_dialog import WelcomeDialog

if TYPE_CHECKING:
    from main import RebarBBSApp

logger = setup_logger("AI_Rebar.MainWindow")


class MainWindow(ttk.Frame):
    def __init__(self, master: tk.Tk, app: "RebarBBSApp") -> None:
        self.app = app
        self.master = master

        # Robust theme (Enum or str)
        self._theme = getattr(self.app.state.theme, "value", self.app.state.theme)

        super().__init__(master, style=f"{self._theme}.TFrame")

        self.menu_bar: MenuBar | None = None
        self.license_status_label: ttk.Label | None = None
        self.bbs_treeview: BBSTreeview | None = None
        self.listofer_tree: ttk.Treeview | None = None
        self.status_bar: StatusBar | None = None

        self._build_ui()
        self._setup_bindings()

        self.after(100, self._auto_activate_project)

    # ------------------------------------------------------------------
    # Menu handlers
    # ------------------------------------------------------------------
    def quit(self):
        self.app.destroy()

    def new_project(self):
        messagebox.showinfo("New Project", "Implement New Project workflow in Project Manager window.")

    def open_project(self):
        messagebox.showinfo("Open Project", "Implement Open Project workflow in Project Manager window.")

    def open_system_doctor(self):
        try:
            from utils.doctor import generate_system_report
            report = generate_system_report()
        except Exception as e:
            report = f"Doctor failed:\n{e}"

        win = tk.Toplevel(self)
        win.title("System Doctor")
        win.geometry("900x650")
        win.transient(self)
        win.resizable(True, True)

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="System Doctor Report", font=("Arial", 12, "bold")).pack(anchor="w")

        txt = tk.Text(frm, wrap="word")
        txt.pack(fill="both", expand=True, pady=8)
        txt.insert("1.0", report)
        txt.config(state="disabled")

        btns = ttk.Frame(frm)
        btns.pack(fill="x")
        ttk.Button(btns, text="Close", command=win.destroy).pack(side="right")

        # center
        win.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (win.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    # ------------------------------------------------------------------
    # Auto-activate project from settings/database
    # ------------------------------------------------------------------
    def _auto_activate_project(self):
        if self.app.state.current_project_id:
            self._load_project_details(self.app.state.current_project_id)
            self.load_project_data()
            return

        projects = ProjectModel.get_all()
        if len(projects) == 1:
            pid, pname = projects[0]
            self.app.state.current_project_id = pid
            self._load_project_details(pid)
            self.update_project_display()
            return

        if len(projects) == 0:
            from config import get_default_project_info
            info = get_default_project_info()
            proj_name = info.get("project_name", "").strip() or "Default Project"
            client = info.get("client", "").strip() or ""
            try:
                pid = ProjectModel.create(proj_name, client)
                self.app.state.current_project_id = pid
                self.app.state.current_project_name = proj_name
                self.app.state.current_client_name = client
                self.update_project_display()
                return
            except Exception as e:
                logger.error(f"Auto-create project failed: {e}")
                return

        messagebox.showinfo("Multiple Projects", "Please select a project from the File menu.")

    def _load_project_details(self, project_id: int):
        """Fetch project name and client from the database and store in app state."""
        try:
            project = ProjectModel.get_by_id(project_id)   # returns (id, name, client)
            if project:
                self.app.state.current_project_name = project[1] if project[1] else "Unknown Project"
                self.app.state.current_client_name = project[2] or ""
        except Exception as e:
            logger.error(f"Failed to load project details: {e}")

    def _ensure_project(self) -> bool:
        if self.app.state.current_project_id:
            return True
        self._auto_activate_project()
        return self.app.state.current_project_id is not None

    # ------------------------------------------------------------------
    # Background task runner
    # ------------------------------------------------------------------
    def _run_in_background(
        self,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        self.master.config(cursor="watch")

        def worker():
            try:
                result = task()
                self.after(0, lambda: on_success(result))
            except Exception as e:
                logger.error(f"Background task failed: {e}", exc_info=True)
                self.after(0, lambda: on_error(e))
            finally:
                self.after(0, lambda: self.master.config(cursor=""))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # UI Initialization
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        theme_style = f"{self._theme}.TFrame"

        self.menu_bar = MenuBar(self, self.app)
        self.menu_bar.pack(fill="x", pady=(0, 2))

        header = ttk.Frame(self, style=theme_style)
        header.pack(fill="x", pady=(0, 5))
        LogoWidget(header).pack(side="left", padx=(5, 10))
        ttk.Label(
            header,
            text="Intelligent Bar Bending Schedule & Cutting Optimization",
            font=FONT_DEFAULTS["tagline"],
            foreground="#64748b",
        ).pack(side="left", padx=10)

        license_frame = ttk.Frame(header, style=theme_style)
        license_frame.pack(side="right", padx=10)
        self.license_status_label = ttk.Label(license_frame, text="", font=("Arial", 10, "bold"))
        self.license_status_label.pack(side="left", padx=5)
        ttk.Button(license_frame, text="🔑 License", command=self.open_license_dialog).pack(side="left", padx=5)
        self.refresh_license_display()

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=5)

        toolbar = ttk.Frame(self, style=theme_style)
        toolbar.pack(fill="x", pady=(0, 10))
        self._build_toolbar(toolbar)

        main_area = ttk.Frame(self, style=theme_style)
        main_area.pack(fill="both", expand=True, padx=10, pady=5)

        lf_frame = ttk.LabelFrame(main_area, text="📋 Listofer Summary")
        lf_frame.pack(fill="x", pady=(0, 5))
        columns = ("lf_number", "lf_desc", "rebar_count", "total_weight")
        self.listofer_tree = ttk.Treeview(lf_frame, columns=columns, show="headings", height=4)
        self.listofer_tree.heading("lf_number", text="Listofer No")
        self.listofer_tree.heading("lf_desc", text="Description")
        self.listofer_tree.heading("rebar_count", text="Rebars")
        self.listofer_tree.heading("total_weight", text="Total Weight (kg)")
        self.listofer_tree.column("lf_number", width=120, anchor="w")
        self.listofer_tree.column("lf_desc", width=250, anchor="w")
        self.listofer_tree.column("rebar_count", width=80, anchor="center")
        self.listofer_tree.column("total_weight", width=120, anchor="center")
        self.listofer_tree.pack(fill="x", padx=5, pady=5)
        self.listofer_tree.bind("<Double-1>", lambda e: self._on_listofer_double_click())

        self.bbs_treeview = BBSTreeview(main_area, self.app, style=self._theme)
        self.bbs_treeview.pack(fill="both", expand=True, pady=(10, 0))
        self.bbs_treeview.tree.bind("<Button-3>", self._on_tree_right_click)
        if hasattr(self.bbs_treeview, "filter_combo"):
            self.bbs_treeview.filter_combo.bind("<<ComboboxSelected>>", self._on_listofer_filter_changed)

        self.status_bar = StatusBar(main_area, self.app)
        self.status_bar.pack(side="bottom", fill="x", pady=(5, 0))

    def _build_toolbar(self, parent: ttk.Frame) -> None:
        toolbar_actions: dict[str, Callable[[], None]] = {
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
            label = toolbar_labels.get(key, key)
            ttk.Button(parent, text=label, command=cmd, style=f"{self._theme}.TButton").pack(side="left", padx=5)
            if key in ("delete", "print_listofer", "lap_splice"):
                ttk.Separator(parent, orient="vertical").pack(side="left", fill="y", padx=5)

    def _setup_bindings(self) -> None:
        self.app.bind("<Control-n>", lambda e: self.open_input_dialog())
        self.app.bind("<Control-e>", lambda e: self.edit_selected_bar())

    # ------------------------------------------------------------------
    # Listofer Summary
    # ------------------------------------------------------------------
    def refresh_listofer_summary(self) -> None:
        if not self.listofer_tree or not self.app.state.current_project_id:
            return
        for row in self.listofer_tree.get_children():
            self.listofer_tree.delete(row)
        try:
            numbers = ListoferModel.get_numbers(self.app.state.current_project_id)
            for lf_num in numbers:
                lf_desc = ListoferModel.get_description_by_number(self.app.state.current_project_id, lf_num) or ""
                rebars = RebarModel.get_for_project(self.app.state.current_project_id, listofer_number=lf_num)
                count = len(rebars)
                weight = 0.0
                for bar in rebars:
                    if len(bar) >= 8:
                        dia, shape_name, dims_json, qty = bar[4], bar[5], bar[6], bar[7]
                        if isinstance(dims_json, str):
                            try:
                                dims = json.loads(dims_json)
                            except Exception:
                                dims = {}
                        else:
                            dims = dims_json or {}
                        try:
                            length_mm = default_shape_registry.calc_shape_length(shape_name, dims, dia)
                        except Exception:
                            length_mm = 0.0
                        _, piece_wt = calculate_weight(dia, length_mm)
                        weight += piece_wt * qty
                self.listofer_tree.insert("", "end", values=(lf_num, lf_desc, count, f"{weight:.2f}"))
        except Exception as e:
            logger.error(f"Failed to refresh listofer summary: {e}", exc_info=True)

    def _on_listofer_double_click(self) -> None:
        selected = self.listofer_tree.selection()
        if not selected:
            return
        lf_num = self.listofer_tree.item(selected[0], "values")[0]
        if hasattr(self.bbs_treeview, "filter_combo"):
            self.bbs_treeview.filter_combo.set(str(lf_num))
            self.bbs_treeview.load_data()
            self._refresh_summary()

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------
    def refresh_license_display(self) -> None:
        self.license_status_label.config(text=format_license_status(self.app.db))

    def open_license_dialog(self) -> None:
        LicenseDialog(self.app, self.app.db, callback=self.refresh_license_display)

    # ------------------------------------------------------------------
    # Project State Management
    # ------------------------------------------------------------------
    def load_project_data(self) -> None:
        if not self.app.state.current_project_id:
            return
        # Ensure project details (especially client name) are fresh
        self._load_project_details(self.app.state.current_project_id)
        ProjectModel.update_access(self.app.state.current_project_id)
        if hasattr(self.bbs_treeview, "filter_combo"):
            numbers = ListoferModel.get_numbers(self.app.state.current_project_id)
            self.bbs_treeview.update_filter_list(numbers)
        self.bbs_treeview.load_data()
        self.refresh_listofer_summary()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        if not self.app.state.current_project_id:
            return
        try:
            rebars = RebarModel.get_for_project(self.app.state.current_project_id)
            total_weight = 0.0
            for row in rebars:
                if len(row) < 8:
                    continue
                dia, shape_name, dims_str, qty = row[4], row[5], row[6], row[7]
                dims = json.loads(dims_str) if isinstance(dims_str, str) else (dims_str or {})
                try:
                    length_mm = default_shape_registry.calc_shape_length(shape_name, dims, dia)
                except Exception:
                    length_mm = 0.0
                _, piece_weight = calculate_weight(dia, length_mm)
                total_weight += piece_weight * qty
            self.status_bar.update_summary(len(rebars), total_weight)
        except Exception as e:
            logger.error(f"Error refreshing summary: {e}", exc_info=True)
            self.status_bar.update_summary(0, 0)

    def update_project_display(self) -> None:
        self.app.title(f"AI Rebar – {self.app.state.current_project_name}")
        self.status_bar.update_project_info()
        self._refresh_summary()
        self.load_project_data()

    def clear_project(self) -> None:
        if getattr(self.app.state, "is_modified", False):
            if not messagebox.askyesno("Unsaved Changes", "There are unsaved changes. Clear project anyway?"):
                return
        self.app.state.reset_project()
        self.app.title("AI Rebar")
        self.status_bar.update_project_info()
        if hasattr(self.bbs_treeview, "clear_tree"):
            self.bbs_treeview.clear_tree()
        self.refresh_listofer_summary()
        self.status_bar.update_summary(0, 0)

    # ------------------------------------------------------------------
    # Rebar CRUD Operations
    # ------------------------------------------------------------------
    def open_input_dialog(self) -> None:
        if not self._ensure_project():
            return
        InputDialog(self, self.app.state.current_project_id, self._on_bar_added)

    def _on_bar_added(self) -> None:
        self.load_project_data()
        if not increment_usage(self.app.db):
            self.open_license_dialog()
            self.refresh_license_display()

    def edit_selected_bar(self) -> None:
        if not self._ensure_project():
            return
        selected = self.bbs_treeview.tree.selection()
        if not selected:
            messagebox.showinfo("Info", ERROR_MSGS["no_selection"])
            return
        rebar_id = self.bbs_treeview.tree.item(selected[0], "values")[0]
        data = RebarModel.get_by_id(rebar_id)
        if data:
            InputDialog(self, self.app.state.current_project_id, self._on_bar_added, edit_data=data)
        else:
            messagebox.showerror("Error", "Could not retrieve rebar data.")

    def delete_selected_bar(self) -> None:
        if not self._ensure_project():
            return
        selected = self.bbs_treeview.tree.selection()
        if not selected:
            messagebox.showinfo("Info", ERROR_MSGS["no_selection"])
            return
        if not messagebox.askyesno("Confirm Deletion", ERROR_MSGS["delete_confirm"]):
            return
        for item in selected:
            rebar_id = self.bbs_treeview.tree.item(item, "values")[0]
            try:
                RebarModel.delete(rebar_id)
            except Exception as e:
                logger.error(f"Delete failed: {e}")
                messagebox.showerror("Database Error", f"Delete failed: {e}")
        self._on_bar_added()

    def duplicate_rebar(self) -> None:
        if not self._ensure_project():
            return
        selected = self.bbs_treeview.tree.selection()
        if not selected:
            messagebox.showinfo("Info", ERROR_MSGS["no_selection"])
            return
        rebar_id = self.bbs_treeview.tree.item(selected[0], "values")[0]
        data = RebarModel.get_by_id(rebar_id)
        if not data:
            messagebox.showerror("Error", "Could not read rebar data.")
            return
        try:
            new_ref = data.get("pos", "") + " (copy)"
            lid = ListoferModel.get_or_create(
                self.app.state.current_project_id,
                data["listofer_number"],
                data.get("listofer_desc", ""),
            )
            RebarModel.add(
                listofer_id=lid,
                pos=new_ref,
                diameter=data["diameter"],
                shape_name=data["shape_name"],
                dimensions=data["dimensions"],
                quantity=data["quantity"],
                location=data.get("location", ""),
                element_type=data.get("element_type", ""),
                user=getpass.getuser(),
                date=datetime.datetime.now().isoformat(),
                grade=data.get("grade", DEFAULT_REBAR_GRADE),
            )
            self._on_bar_added()
        except Exception as e:
            logger.error(f"Duplication failed: {e}")
            messagebox.showerror("Duplicate Failed", str(e))

    def copy_to_clipboard(self) -> None:
        selected = self.bbs_treeview.tree.selection()
        if not selected:
            return
        rows = ["\t".join(str(v) for v in self.bbs_treeview.tree.item(item, "values")) for item in selected]
        self.clipboard_clear()
        self.clipboard_append("\n".join(rows))
        messagebox.showinfo("Copied", f"{len(rows)} row(s) copied to clipboard.")

    def _on_tree_right_click(self, event: tk.Event) -> None:
        iid = self.bbs_treeview.tree.identify_row(event.y)
        if iid:
            self.bbs_treeview.tree.selection_set(iid)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="✏️ Edit", command=self.edit_selected_bar)
            menu.add_command(label="📋 Duplicate", command=self.duplicate_rebar)
            menu.add_command(label="🗑️ Delete", command=self.delete_selected_bar)
            menu.add_separator()
            menu.add_command(label="📄 Copy to Clipboard", command=self.copy_to_clipboard)
            menu.post(event.x_root, event.y_root)

    def _on_listofer_filter_changed(self, event=None):
        self.bbs_treeview.load_data()
        self._refresh_summary()

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------
    def _get_summary_list(self):
        if hasattr(self.bbs_treeview, "summary_tree"):
            return [list(self.bbs_treeview.summary_tree.item(item, "values"))
                    for item in self.bbs_treeview.summary_tree.get_children()]
        return []

    def _get_export_path(self, ext, file_type):
        if not self._ensure_project():
            return None
        proj_name = self.app.state.current_project_name.replace(" ", "_")
        return filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(file_type, f"*{ext}")],
            initialfile=f"{proj_name}_{datetime.date.today()}{ext}",
        )

    def export_excel(self):
        path = self._get_export_path(".xlsx", "Excel files")
        if not path:
            return

        def task():
            export_excel(path, self.app.state.current_project_id,
                         self.app.state.current_project_name,
                         self.app.state.current_client_name,
                         summary_data=self._get_summary_list())

        self._run_in_background(task,
                                lambda _: messagebox.showinfo("Success", f"Exported to {path}"),
                                lambda e: messagebox.showerror("Export Error", f"Excel Export Failed:\n{e}"))

    def export_pdf(self):
        path = self._get_export_path(".pdf", "PDF files")
        if not path:
            return

        def task():
            export_pdf(path, self.app.state.current_project_id,
                       self.app.state.current_project_name,
                       self.app.state.current_client_name,
                       summary_data=self._get_summary_list())

        self._run_in_background(task,
                                lambda _: messagebox.showinfo("Success", f"Exported to {path}"),
                                lambda e: messagebox.showerror("Export Error", f"PDF Export Failed:\n{e}"))

    def export_html_report(self):
        if not self._ensure_project():
            return
        if not ListoferModel.get_numbers(self.app.state.current_project_id):
            messagebox.showinfo("Info", "No listofers exist in this project to print.")
            return
        ListoferSelectorWindow(self.app, self.app.state.current_project_id, callback=self._generate_report)

    def _generate_report(self, lf_filter):
        path = self._get_export_path(".html", "HTML files")
        if not path:
            return

        def task():
            export_html(self.app.state.current_project_id,
                        self.app.state.current_project_name,
                        self.app.state.current_client_name,
                        path,
                        listofer_number=lf_filter)

        self._run_in_background(task,
                                lambda _: messagebox.showinfo("Success", "Report saved and opened."),
                                lambda e: messagebox.showerror("Export Error", f"HTML Export Failed:\n{e}"))

    def export_bvbs(self):
        path = self._get_export_path(".bvbs", "BVBS files")
        if not path:
            return

        def task():
            return export_bvbs(self.app.state.current_project_id,
                               self.app.state.current_project_name,
                               self.app.state.current_client_name,
                               path)

        def on_success(success):
            if success:
                messagebox.showinfo("Success", f"BVBS exported to {path}")
            else:
                messagebox.showwarning("Warning", "No data available to export.")

        self._run_in_background(task, on_success,
                                lambda e: messagebox.showerror("Export Error", f"BVBS Export Failed:\n{e}"))

    def import_bvbs(self):
        if not self._ensure_project():
            return
        path = filedialog.askopenfilename(
            title="Select BVBS File",
            filetypes=[("BVBS files", "*.bvbs"), ("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            preview, total_count = import_bvbs_preview(self.app.state.current_project_id, path)
            if not preview:
                messagebox.showinfo("Import Result", "No valid rebar data found.")
                return
            preview_text = f"Found {total_count} bars.\n\nPreview (first {min(len(preview),10)}):\n"
            for bar in preview[:10]:
                grade_str = f", Grade:{bar['grade']}" if bar.get("grade") else ""
                preview_text += (
                    f"  ID: {bar['id']}, Ø{bar['diameter']}mm, Qty:{bar['quantity']}, "
                    f"LF:{bar['listofer']}, Pos:{bar['position']}{grade_str}\n"
                )
            if not messagebox.askyesno("Import BVBS", f"{preview_text}\n\nProceed with import?"):
                return

            def task():
                return import_bvbs(self.app.state.current_project_id, path)

            def on_success(result):
                success_count, errors = result
                if success_count > 0:
                    messagebox.showinfo("Import Complete", f"Imported {success_count} bars.\nErrors: {errors}")
                    self.load_project_data()
                else:
                    messagebox.showerror("Import Failed", f"No bars imported.\nErrors: {errors}")

            self._run_in_background(task, on_success,
                                    lambda e: messagebox.showerror("Import Error", f"BVBS processing failed:\n{e}"))
        except Exception as e:
            logger.error(f"BVBS preview error: {e}", exc_info=True)
            messagebox.showerror("Import Error", f"Failed to parse BVBS file:\n{e}")

    # ------------------------------------------------------------------
    # Dialog launchers
    # ------------------------------------------------------------------
    def show_lap_splice(self):
        LapSpliceDialog(self.app)

    def show_cutting_plan_all(self):
        if not self._ensure_project():
            return
        if not self.bbs_treeview.tree.get_children():
            messagebox.showwarning("Warning", "No data available to optimize.")
            return
        current_filter = self.bbs_treeview.filter_combo.get() if hasattr(self.bbs_treeview, "filter_combo") else ""
        if current_filter not in (FILTER_SHOW_ALL, ""):
            self._show_cutting_plan_for_lf(current_filter)
            return
        numbers = ListoferModel.get_numbers(self.app.state.current_project_id)
        if not numbers:
            messagebox.showinfo("Info", "No listofers defined.")
            return
        ListoferSelectorWindow(self.app, self.app.state.current_project_id, callback=self._show_cutting_plan_for_lf)

    def _show_cutting_plan_for_lf(self, lf_filter):
        stock_len = float(self.bbs_treeview.stock_length.get())
        data_by_key = self.bbs_treeview.get_lengths_by_diameter_for_listofer(lf_filter)
        if not data_by_key:
            messagebox.showwarning("Warning", "No matching data found.")
            return
        CuttingPlanWindow(self.app, self.app.state.current_project_id, data_by_key, stock_len, listofer_filter=lf_filter)

    def show_cutting_plan_selected(self):
        if not self.bbs_treeview.tree.selection():
            messagebox.showwarning("Warning", "Please select items first.")
            return
        stock_len = float(self.bbs_treeview.stock_length.get())
        lf_filter = self.bbs_treeview.filter_combo.get() if hasattr(self.bbs_treeview, "filter_combo") else ""
        lf_filter = None if lf_filter == FILTER_SHOW_ALL else lf_filter
        data_by_key = self.bbs_treeview.get_lengths_by_diameter_for_listofer(lf_filter)
        if not data_by_key:
            messagebox.showwarning("Warning", "No data matches the current selection criteria.")
            return
        CuttingPlanWindow(self.app, self.app.state.current_project_id, data_by_key, stock_len, listofer_filter=lf_filter)

    def show_scrap_manager(self):
        if not self._ensure_project():
            return
        ScrapManagerWindow(self.app, self.app.state.current_project_id)

    def show_stock_manager(self):
        if not self._ensure_project():
            return
        StockManagerWindow(self.app, self.app.state.current_project_id)

    def open_custom_shape_designer(self):
        CustomShapeDesigner(self.app, on_shape_saved=lambda: default_shape_registry.refresh())

    def open_settings(self):
        SettingsWindow(self.app, self.app)
        self.after(100, self._auto_activate_project)

    def show_project_manager(self):
        messagebox.showinfo("Project Manager", "Use File > Open Project to manage projects.")

    def show_welcome_dialog(self):
        WelcomeDialog(self.app, on_close=self._auto_activate_project, on_create_project=self._auto_activate_project)

    def show_user_guide(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        en_path = os.path.join(base_dir, "..", "User_Guide.html")
        fa_path = os.path.join(base_dir, "..", "راهنمای_کاربر.html")

        has_en = os.path.exists(en_path)
        has_fa = os.path.exists(fa_path)

        if not has_en and not has_fa:
            messagebox.showinfo("Guide not found", "User guide files are missing.")
            return

        dlg = tk.Toplevel(self)
        dlg.title("Open User Guide")
        dlg.geometry("300x150")
        dlg.transient(self)
        dlg.resizable(False, False)
        dlg.configure(bg="#f8fafc")

        ttk.Label(
            dlg, text="Which language would you like to open?",
            font=("Arial", 11, "bold"), background="#f8fafc"
        ).pack(pady=15)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=5)

        def open_and_close(path):
            webbrowser.open("file:///" + os.path.abspath(path).replace("\\", "/"))
            dlg.destroy()

        if has_en and has_fa:
            ttk.Button(btn_frame, text="English", command=lambda: open_and_close(en_path)).pack(side="left", padx=5)
            ttk.Button(btn_frame, text="فارسی", command=lambda: open_and_close(fa_path)).pack(side="left", padx=5)
        elif has_en:
            ttk.Button(btn_frame, text="Open English Guide", command=lambda: open_and_close(en_path)).pack(pady=10)
        elif has_fa:
            ttk.Button(btn_frame, text="باز کردن راهنمای فارسی", command=lambda: open_and_close(fa_path)).pack(pady=10)

        ttk.Button(dlg, text="Cancel", command=dlg.destroy).pack(pady=5)

        dlg.update_idletasks()
        pw, ph = self.winfo_width(), self.winfo_height()
        px, py = self.winfo_x(), self.winfo_y()
        w, h = dlg.winfo_width(), dlg.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        dlg.geometry(f"+{x}+{y}")

    def show_about(self):
        messagebox.showinfo("About", "AI Rebar v7.4\n\nIntelligent Bar Bending Schedule & Cutting Optimization\n© 2026")

    def contact_developer(self):
        if messagebox.askyesno("Contact Support", "Open WhatsApp to contact developer?"):
            webbrowser.open("https://wa.me/989160684552")