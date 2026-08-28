# ui/project_manager.py
"""Project Manager Window for RebarAgent. Full CRUD for projects."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Callable, TYPE_CHECKING

from db.models import ProjectModel, ListoferModel, RebarModel
from utils.logger import setup_logger
from utils.i18n import t

if TYPE_CHECKING:
    from main import RebarAgentApp

logger = setup_logger("RebarAgent.ProjectManager")


class ProjectManagerWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, app: "RebarAgentApp", on_project_changed: Optional[Callable[[], None]] = None, mode: str = "manage"):
        super().__init__(master)
        self.app = app
        self.on_project_changed = on_project_changed
        self.mode = mode
        self.title(f"🗂️ {t('pm.title')} – RebarAgent")
        self.geometry("720x480")
        self.minsize(600, 400)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        self._selected_id: Optional[int] = None
        self._build_ui()
        self._refresh_list()
        self._center()
        if mode == "new":
            self.after(100, self._create_project)

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
        ttk.Label(header, text=t("pm.title"), font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(header, text=t("pm.subtitle"), font=("Segoe UI", 9), foreground="#64748b").pack(side="left", padx=12)
        tree_frame = ttk.Frame(main)
        tree_frame.pack(fill="both", expand=True)
        columns = ("id", "name", "client", "listofers", "rebars")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse", height=12)
        for col, text, w, anc in [("id", "ID", 50, "center"), ("name", "Project Name", 220, "w"), ("client", "Client", 160, "w"), ("listofers", "Listofers", 80, "center"), ("rebars", "Rebars", 80, "center")]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor=anc)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self._open_selected())
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_frame, text=f"🆕 {t('pm.new')}", command=self._create_project).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text=f"📂 {t('btn.open')}", command=self._open_selected).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=f"✏️ {t('btn.rename')}", command=self._rename_selected).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=f"🗑️ {t('btn.delete')}", command=self._delete_selected).pack(side="left", padx=6)
        ttk.Button(btn_frame, text=t("btn.close"), command=self.destroy).pack(side="right")
        self.status_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.status_var, foreground="#64748b").pack(anchor="w", pady=(8, 0))

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            projects = ProjectModel.get_all()
            for pid, name in projects:
                details = ProjectModel.get_by_id(pid)
                client = details[2] if details and len(details) > 2 else ""
                listofers = ListoferModel.get_numbers(pid)
                rebars = RebarModel.get_for_project(pid)
                self.tree.insert("", "end", iid=str(pid), values=(pid, name, client or "—", len(listofers), len(rebars)))
            count = len(projects)
            self.status_var.set(f"{count} project(s) found" if count else t("pm.empty"))
        except Exception as e:
            logger.error(f"Failed to load projects: {e}", exc_info=True)
            messagebox.showerror("Error", f"Could not load projects:\n{e}", parent=self)

    def _on_select(self, event=None):
        sel = self.tree.selection()
        self._selected_id = int(sel[0]) if sel else None

    def _create_project(self):
        dlg = _NewProjectDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            name, client = dlg.result
            try:
                pid = ProjectModel.create(name, client)
                self._activate_project(pid, name, client)
                self._refresh_list()
                if str(pid) in self.tree.get_children():
                    self.tree.selection_set(str(pid))
                    self.tree.see(str(pid))
                messagebox.showinfo(t("pm.title"), t("pm.created", name=name), parent=self)
                if self.mode == "new":
                    self.destroy()
            except Exception as e:
                logger.error(f"Create project failed: {e}", exp_info=True)
                messagebox.showerror("Error", f"Failed to create project:\n{e}", parent=self)

    def _open_selected(self):
        if self._selected_id is None:
            messagebox.showinfo("Info", "Please select a project first.", parent=self)
            return
        try:
            details = ProjectModel.get_by_id(self._selected_id)
            if not details:
                messagebox.showerror("Error", "Project not found.", parent=self)
                return
            pid, name, client = details[0], details[1], details[2] or ""
            self._activate_project(pid, name, client)
            messagebox.showinfo(t("pm.title"), t("pm.opened", name=name), parent=self)
            self.destroy()
        except Exception as e:
            logger.error(f"Open project failed: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to open project:\n{e}", parent=self)

    def _rename_selected(self):
        if self._selected_id is None:
            messagebox.showinfo("Info", "Please select a project first.", parent=self)
            return
        details = ProjectModel.get_by_id(self._selected_id)
        if not details:
            return
        old_name, old_client = details[1], details[2] or ""
        new_name = simpledialog.askstring("Rename Project", "New project name:", initialvalue=old_name, parent=self)
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()
        new_client = simpledialog.askstring("Client Name", "Client (optional):", initialvalue=old_client, parent=self)
        if new_client is None:
            new_client = old_client
        else:
            new_client = new_client.strip()
        try:
            ProjectModel.update(self._selected_id, new_name, new_client)
            if self.app.state.current_project_id == self._selected_id:
                self.app.state.current_project_name = new_name
                self.app.state.current_client_name = new_client
                if self.on_project_changed:
                    self.on_project_changed()
            self._refresh_list()
            messagebox.showinfo("Renamed", f"Project renamed to «{new_name}».", parent=self)
        except Exception as e:
            logger.error(f"Rename failed: {e}", exp_info=True)
            messagebox.showerror("Error", f"Rename failed:\n{e}", parent=self)

    def _delete_selected(self):
        if self._selected_id is None:
            messagebox.showinfo("Info", "Please select a project first.", parent=self)
            return
        details = ProjectModel.get_by_id(self._selected_id)
        if not details:
            return
        name = details[1]
        if not messagebox.askyesno(t("btn.delete"), t("pm.delete_confirm", name=name), parent=self, icon="warning"):
            return
        try:
            was_active = self.app.state.current_project_id == self._selected_id
            ProjectModel.delete(self._selected_id)
            if was_active:
                self.app.state.reset_project()
                if self.on_project_changed:
                    self.on_project_changed()
            self._selected_id = None
            self._refresh_list()
            messagebox.showinfo("Deleted", f"Project «{name}» has been deleted.", parent=self)
        except Exception as e:
            logger.error(f"Delete failed: {e}", exp_info=True)
            messagebox.showerror("Error", f"Delete failed:\n{e}", parent=self)

    def _activate_project(self, pid: int, name: str, client: str):
        self.app.state.current_project_id = pid
        self.app.state.current_project_name = name
        self.app.state.current_client_name = client or ""
        ProjectModel.update_access(pid)
        if self.on_project_changed:
            self.on_project_changed()


class _NewProjectDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("New Project")
        self.geometry("400x180")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Project Name *").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(frm, textvariable=self.name_var, width=40)
        name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        name_entry.focus_set()
        ttk.Label(frm, text="Client (optional)").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.client_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.client_var, width=40).grid(row=3, column=0, sticky="ew", pady=(0, 16))
        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, sticky="e")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Create", command=self._ok).pack(side="right")
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Required", "Project name cannot be empty.", parent=self)
            return
        self.result = (name, self.client_var.get().strip())
        self.destroy()
