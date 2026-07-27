# ui/stock_manager.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import logging

from db.models import StockModel
from config import REBAR_GRADES, DEFAULT_REBAR_GRADE

logger = logging.getLogger(__name__)

# Maximum allowed stock length in millimetres (configurable)
MAX_STOCK_LENGTH_MM = 18000
LOW_STOCK_THRESHOLD = 5          # quantity below which the row turns red


class StockDialog(tk.Toplevel):
    """Dialog for adding or editing stock items."""

    def __init__(self, parent, title="Add Stock", dia=12.0, length=12000.0,
                 qty=10, grade=DEFAULT_REBAR_GRADE, show_project_option=False,
                 project_id=None):
        super().__init__(parent)
        self.result = None  # (diameter, length, quantity, grade, assign_to_project)
        self.title(title)
        self.geometry("320x270")
        self.transient(parent)
        self.grab_set()
        self.project_id = project_id

        ttk.Label(self, text="Diameter (mm):").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.dia_var = tk.StringVar(value=str(dia))
        ttk.Entry(self, textvariable=self.dia_var, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(self, text="Length (mm):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.len_var = tk.StringVar(value=str(length))
        ttk.Entry(self, textvariable=self.len_var, width=12).grid(row=1, column=1, sticky="w")

        ttk.Label(self, text="Quantity:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.qty_var = tk.StringVar(value=str(qty))
        ttk.Entry(self, textvariable=self.qty_var, width=12).grid(row=2, column=1, sticky="w")

        ttk.Label(self, text="Grade:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.grade_var = tk.StringVar(value=grade)
        ttk.Combobox(self, textvariable=self.grade_var, values=REBAR_GRADES,
                     width=12).grid(row=3, column=1, sticky="w")

        self.assign_var = None
        if show_project_option and project_id is not None:
            self.assign_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(self, text="Assign to current project",
                            variable=self.assign_var).grid(row=4, column=0, columnspan=2, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        # Center dialog relative to parent
        self._center_on_parent()

    def _center_on_parent(self):
        """Center this dialog on its parent window."""
        self.update_idletasks()
        parent = self.master
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def on_ok(self):
        try:
            dia = float(self.dia_var.get())
            length = float(self.len_var.get())
            qty = int(self.qty_var.get())
            if dia <= 0 or length <= 0 or qty <= 0:
                raise ValueError("All values must be positive.")
            if length > MAX_STOCK_LENGTH_MM:
                raise ValueError(f"Length cannot exceed {MAX_STOCK_LENGTH_MM} mm "
                                 f"({MAX_STOCK_LENGTH_MM / 1000:.0f} m).")
            grade = self.grade_var.get().strip() or DEFAULT_REBAR_GRADE
            assign = self.assign_var.get() if self.assign_var is not None else False
            self.result = (dia, length, qty, grade, assign)
            self.destroy()
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e), parent=self)


class StockManagerWindow(tk.Toplevel):
    def __init__(self, parent, project_id):
        super().__init__(parent)
        self.parent_app = parent          # the main RebarBBSApp instance
        self.project_id = project_id
        self.title("🧱 Stock Manager - Manage Rebar Stock")
        self.geometry("780x480")
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._center_on_parent()          # position the window at the center of the parent
        self.refresh_list()

    def _center_on_parent(self):
        """Place the window exactly at the center of its parent."""
        self.update_idletasks()
        parent = self.master
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        ttk.Button(toolbar, text="➕ Add Stock", command=self.add_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="✏️ Edit", command=self.edit_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑️ Delete", command=self.delete_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh_list).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📊 Export Excel", command=self.export_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🧩 Scrap Manager", command=self._open_scrap_manager).pack(side="left", padx=2)

        ttk.Label(toolbar, text="│").pack(side="left", padx=5)

        ttk.Label(toolbar, text="Project Filter:").pack(side="left")
        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.filter_var,
                     values=["All", "Current Project"],
                     state="readonly", width=18).pack(side="left", padx=5)
        self.filter_var.trace("w", lambda *a: self.refresh_list())

        columns = ("id", "project", "diameter", "grade", "length", "quantity")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=40, anchor="center")
        self.tree.heading("project", text="Project")
        self.tree.column("project", width=100)
        self.tree.heading("diameter", text="Diameter (mm)")
        self.tree.column("diameter", width=100, anchor="center")
        self.tree.heading("grade", text="Grade")
        self.tree.column("grade", width=60, anchor="center")
        self.tree.heading("length", text="Length (mm)")
        self.tree.column("length", width=110, anchor="center")
        self.tree.heading("quantity", text="Quantity")
        self.tree.column("quantity", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Tag for low stock
        self.tree.tag_configure("low_stock", foreground="red")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=5)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _get_filtered_project_id(self):
        return self.project_id if self.filter_var.get() == "Current Project" else None

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        filter_pid = self._get_filtered_project_id()
        try:
            items = StockModel.get_all(project_id=filter_pid)
        except AttributeError:
            messagebox.showerror("Error", "StockModel.get_all is not implemented.")
            return
        items.sort(key=lambda x: (x[2], x[3]))   # diameter, then length
        for item in items:
            pid_display = item[1] if item[1] is not None else "Global"
            qty = item[4]
            tags = ("low_stock",) if qty < LOW_STOCK_THRESHOLD else ()
            self.tree.insert("", "end", values=(
                item[0], pid_display, item[2], item[5], item[3], qty
            ), tags=tags)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_stock(self):
        dlg = StockDialog(
            self, title="Add Stock", dia=12.0, length=12000.0, qty=10,
            grade=DEFAULT_REBAR_GRADE,
            show_project_option=self.project_id is not None,
            project_id=self.project_id
        )
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, qty, grade, assign = dlg.result
        project = self.project_id if assign else None
        try:
            StockModel.add(project, dia, length, qty, grade=grade)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add stock: {e}")

    def edit_stock(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a stock item first.")
            return
        vals = self.tree.item(selected[0])['values']
        stock_id, _, old_dia, old_grade, old_len, old_qty = vals
        dlg = StockDialog(self, title="Edit Stock", dia=old_dia, length=old_len,
                          qty=old_qty, grade=old_grade, show_project_option=False)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, qty, grade, _ = dlg.result
        try:
            StockModel.update(stock_id, dia, length, qty, grade=grade)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not update stock: {e}")

    def delete_stock(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a stock item first.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected stock item?"):
            return
        stock_id = self.tree.item(selected[0])['values'][0]
        try:
            StockModel.delete(stock_id)
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_stock(self):
        try:
            from utils.stock_export import export_stock_excel
        except ImportError:
            messagebox.showerror("Missing Module", "Stock export module is not available.")
            return
        default_name = f"Stock_Inventory_{datetime.date.today()}.xlsx"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=default_name
        )
        if not filepath:
            return
        try:
            filter_pid = self._get_filtered_project_id()
            export_stock_excel(filepath, project_id=filter_pid)
            messagebox.showinfo("Success", f"Stock report saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    # ------------------------------------------------------------------
    # Integration with Scrap Manager
    # ------------------------------------------------------------------
    def _open_scrap_manager(self):
        """Open the Scrap Manager window for the current project."""
        try:
            from ui.scrap_manager import ScrapManagerWindow
        except ImportError:
            messagebox.showerror("Missing Module", "Scrap Manager module is not available.")
            return
        # self.parent_app is the main RebarBBSApp instance (passed as parent to __init__)
        if hasattr(self.parent_app, 'db'):
            ScrapManagerWindow(self.parent_app, self.project_id)
        else:
            messagebox.showerror("Error", "Cannot open Scrap Manager – parent app not found.")