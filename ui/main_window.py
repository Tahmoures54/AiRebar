# ui/main_window.py
"""Main application window – premium shell via MainWindowShellMixin."""

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
from ui.main_window_shell import MainWindowShellMixin

if TYPE_CHECKING:
    from main import RebarBBSApp

logger = setup_logger("RebarAgent.MainWindow")


class MainWindow(MainWindowShellMixin, ttk.Frame):
    def __init__(self, master: tk.Tk, app: "RebarBBSApp") -> None:
        self.app = app
        self.master = master
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

    def quit(self):
        self.app.destroy()

    def new_project(self):
        messagebox.showinfo("New Project", "Use Project Manager / File menu.")

    def open_project(self):
        messagebox.showinfo("Open Project", "Use Project Manager / File menu.")

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
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="System Doctor Report", font=("Arial", 12, "bold")).pack(anchor="w")
        txt = tk.Text(frm, wrap="word")
        txt.pack(fill="both", expand=True, pady=8)
        txt.insert("1.0", report)
        txt.config(state="disabled")
        ttk.Button(frm, text="Close", command=win.destroy).pack(anchor="e")

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
            except Exception as e:
                logger.error(f"Auto-create project failed: {e}")
            return
        messagebox.showinfo("Multiple Projects", "Please select a project from the File menu.")

    def _load_project_details(self, project_id: int):
        try:
            project = ProjectModel.get_by_id(project_id)
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

    def _run_in_background(self, task, on_success, on_error) -> None:
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

    def _setup_bindings(self) -> None:
        self.app.bind("<Control-n>", lambda e: self.open_input_dialog())
        self.app.bind("<Control-e>", lambda e: self.edit_selected_bar())

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
                        dims = json.loads(dims_json) if isinstance(dims_json, str) else (dims_json or {})
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

    def open_license_dialog(self) -> None:
        LicenseDialog(self.app, self.app.db, callback=self.refresh_license_display)

    def load_project_data(self) -> None:
        if not self.app.state.current_project_id:
            return
        self._load_project_details(self.app.state.current_project_id)
        ProjectModel.update_access(self.app.state.current_project_id)
        if hasattr(self.bbs_treeview, "filter_combo"):
            numbers = ListoferModel.get_numbers(self.app.state.current_project_id)
            self.bbs_treeview.update_filter_list(numbers)
        self.bbs_treeview.load_data()
        self.refresh_listofer_summary()
        self._refresh_summary()
        try:
            self.update_project_display()
        except Exception:
            pass

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

    def clear_project(self) -> None:
        if getattr(self.app.state, "is_modified", False):
            if not messagebox.askyesno("Unsaved Changes", "There are unsaved changes. Clear project anyway?"):
                return
        self.app.state.reset_project()
        self.app.title("RebarAgent")
        self.status_bar.update_project_info()
        if hasattr(self.bbs_treeview, "clear_tree"):
            self.bbs_treeview.clear_tree()
        self.refresh_listofer_summary()
        self.status_bar.update_summary(0, 0)

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
            return
        try:
            new_ref = data.get("pos", "") + " (copy)"
            lid = ListoferModel.get_or_create(
                self.app.state.current_project_id,
                data["listofer_number"],
                data.get("listofer_desc", ""),
            )
            RebarModel.add(
                listofer_id=lid, pos=new_ref, diameter=data["diameter"],
                shape_name=data["shape_name"], dimensions=data["dimensions"],
                quantity=data["quantity"], location=data.get("location", ""),
                element_type=data.get("element_type", ""), user=getpass.getuser(),
                date=datetime.datetime.now().isoformat(),
                grade=data.get("grade", DEFAULT_REBAR_GRADE),
            )
            self._on_bar_added()
        except Exception as e:
            messagebox.showerror("Duplicate Failed", str(e))

    def copy_to_clipboard(self) -> None:
        selected = self.bbs_treeview.tree.selection()
        if not selected:
            return
        rows = ["\t".join(str(v) for v in self.bbs_treeview.tree.item(item, "values")) for item in selected]
        self.clipboard_clear()
        self.clipboard_append("\n".join(rows))

    def _on_tree_right_click(self, event: tk.Event) -> None:
        iid = self.bbs_treeview.tree.identify_row(event.y)
        if iid:
            self.bbs_treeview.tree.selection_set(iid)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="✏️ Edit", command=self.edit_selected_bar)
            menu.add_command(label="📋 Duplicate", command=self.duplicate_rebar)
            menu.add_command(label="🗑️ Delete", command=self.delete_selected_bar)
            menu.add_separator()
            menu.add_command(label="📄 Copy", command=self.copy_to_clipboard)
            menu.post(event.x_root, event.y_root)

    def _on_listofer_filter_changed(self, event=None):
        self.bbs_treeview.load_data()
        self._refresh_summary()

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
            defaultextension=ext, filetypes=[(file_type, f"*{ext}")],
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
        self._run_in_background(task, lambda _: messagebox.showinfo("Success", f"Exported to {path}"),
                                lambda e: messagebox.showerror("Export Error", str(e)))

    def export_pdf(self):
        path = self._get_export_path(".pdf", "PDF files")
        if not path:
            return
        def task():
            export_pdf(path, self.app.state.current_project_id,
                       self.app.state.current_project_name,
                       self.app.state.current_client_name,
                       summary_data=self._get_summary_list())
        self._run_in_background(task, lambda _: messagebox.showinfo("Success", f"Exported to {path}"),
                                lambda e: messagebox.showerror("Export Error", str(e)))

    def export_html_report(self):
        if not self._ensure_project():
            return
        if not ListoferModel.get_numbers(self.app.state.current_project_id):
            messagebox.showinfo("Info", "No listofers to print.")
            return
        ListoferSelectorWindow(self.app, self.app.state.current_project_id, callback=self._generate_report)

    def _generate_report(self, lf_filter):
        path = self._get_export_path(".html", "HTML files")
        if not path:
            return
        def task():
            export_html(self.app.state.current_project_id, self.app.state.current_project_name,
                        self.app.state.current_client_name, path, listofer_number=lf_filter)
        self._run_in_background(task, lambda _: messagebox.showinfo("Success", "Report saved."),
                                lambda e: messagebox.showerror("Export Error", str(e)))

    def export_bvbs(self):
        path = self._get_export_path(".bvbs", "BVBS files")
        if not path:
            return
        def task():
            return export_bvbs(self.app.state.current_project_id, self.app.state.current_project_name,
                               self.app.state.current_client_name, path)
        self._run_in_background(task, lambda ok: messagebox.showinfo("Success", path) if ok else messagebox.showwarning("Warning", "No data"),
                                lambda e: messagebox.showerror("Export Error", str(e)))

    def import_bvbs(self):
        if not self._ensure_project():
            return
        path = filedialog.askopenfilename(filetypes=[("BVBS", "*.bvbs"), ("All", "*.*")])
        if not path:
            return
        try:
            preview, total_count = import_bvbs_preview(self.app.state.current_project_id, path)
            if not preview:
                messagebox.showinfo("Import", "No valid data.")
                return
            if not messagebox.askyesno("Import BVBS", f"Found {total_count} bars. Proceed?"):
                return
            def task():
                return import_bvbs(self.app.state.current_project_id, path)
            def on_success(result):
                n, errors = result
                messagebox.showinfo("Import", f"Imported {n}. Errors: {errors}")
                self.load_project_data()
            self._run_in_background(task, on_success, lambda e: messagebox.showerror("Import", str(e)))
        except Exception as e:
            messagebox.showerror("Import", str(e))

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
            messagebox.showwarning("Warning", "Select items first.")
            return
        stock_len = float(self.bbs_treeview.stock_length.get())
        lf_filter = self.bbs_treeview.filter_combo.get() if hasattr(self.bbs_treeview, "filter_combo") else ""
        lf_filter = None if lf_filter == FILTER_SHOW_ALL else lf_filter
        data_by_key = self.bbs_treeview.get_lengths_by_diameter_for_listofer(lf_filter)
        if not data_by_key:
            messagebox.showwarning("Warning", "No data.")
            return
        CuttingPlanWindow(self.app, self.app.state.current_project_id, data_by_key, stock_len, listofer_filter=lf_filter)

    def show_scrap_manager(self):
        if self._ensure_project():
            ScrapManagerWindow(self.app, self.app.state.current_project_id)

    def show_stock_manager(self):
        if self._ensure_project():
            StockManagerWindow(self.app, self.app.state.current_project_id)

    def open_custom_shape_designer(self):
        CustomShapeDesigner(self.app, on_shape_saved=lambda: default_shape_registry.refresh())

    def open_settings(self):
        SettingsWindow(self.app, self.app)
        self.after(100, self._auto_activate_project)

    def show_project_manager(self):
        messagebox.showinfo("Project Manager", "Use File menu to manage projects.")

    def show_welcome_dialog(self):
        WelcomeDialog(self.app, on_close=self._auto_activate_project, on_create_project=self._auto_activate_project)

    def show_user_guide(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        en_path = os.path.join(base_dir, "..", "User_Guide.html")
        if os.path.exists(en_path):
            webbrowser.open("file:///" + os.path.abspath(en_path).replace("\\", "/"))
        else:
            messagebox.showinfo("Guide", "User guide not found.")

    def show_about(self):
        messagebox.showinfo("About", "RebarAgent 1.6.0\n\nIntelligent BBS & Cutting Optimization\n© 2026")

    def contact_developer(self):
        if messagebox.askyesno("Contact Support", "Open WhatsApp?"):
            webbrowser.open("https://wa.me/989160684552")
