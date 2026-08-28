# ui/stock_manager.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import logging

from db.models import StockModel
from config import REBAR_GRADES, DEFAULT_REBAR_GRADE

logger = logging.getLogger(__name__)

MAX_STOCK_LENGTH_MM = 18000
LOW_STOCK_THRESHOLD = 5


def _emit_stock_changed(project_id=None, reason="stock"):
    try:
        from utils.events import bus
        bus.emit("stock.changed", {"project_id": project_id, "reason": reason})
        bus.emit("ui.refresh_request", {"reason": reason, "project_id": project_id})
    except Exception:
        pass


class StockDialog(tk.Toplevel):
    def __init__(self, parent, title="Add Stock", dia=12.0, length=12000.0,
                 qty=10, grade=DEFAULT_REBAR_GRADE, show_project_option=False,
                 project_id=None):
        super().__init__(parent)
        self.result = None
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
        ttk.Combobox(self, textvariable=self.grade_var, values=REBAR_GRADES, width=12).grid(row=3, column=1, sticky="w")
        self.assign_var = None
        if show_project_option and project_id is not None:
            self.assign_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(self, text="Assign to current project", variable=self.assign_var).grid(row=4, column=0, columnspan=2, pady=5)
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        self._center_on_parent()

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self.master
        pw, ph, px, py = parent.winfo_width(), parent.winfo_height(), parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    def on_ok(self):
        try:
            dia = float(self.dia_var.get())
            length = float(self.len_var.get())
            qty = int(self.qty_var.get())
            if dia <= 0 or length <= 0 or qty <= 0:
                raise ValueError("All values must be positive.")
            if length > MAX_STOCK_LENGTH_MM:
                raise ValueError(f"Length cannot exceed {MAX_STOCK_LENGTH_MM} mm.")
            grade = self.grade_var.get().strip() or DEFAULT_REBAR_GRADE
            assign = self.assign_var.get() if self.assign_var is not None else False
            self.result = (dia, length, qty, grade, assign)
            self.destroy()
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e), parent=self)


class StockManagerWindow(tk.Toplevel):
    def __init__(self, parent, project_id):
        super().__init__(parent)
        self.parent_app = parent
        self.project_id = project_id
        self.title("Stock Manager - Manage Rebar Stock")
        self.geometry("780x480")
        self.transient(parent)
        self.grab_set()
        self._create_widgets()
        self._center_on_parent()
        self.refresh_list()

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self.master
        pw, ph, px, py = parent.winfo_width(), parent.winfo_height(), parent.winfo_x(), parent.winfo_y()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

    def _create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        ttk.Button(toolbar, text="Add Stock", command=self.add_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Edit", command=self.edit_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Delete", command=self.delete_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_list).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Export Excel", command=self.export_stock).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Scrap Manager", command=self._open_scrap_manager).pack(side="left", padx=2)
        ttk.Label(toolbar, text="Project Filter:").pack(side="left", padx=(12, 0))
        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.filter_var, values=["All", "Current Project"], state="readonly", width=18).pack(side="left", padx=5)
        self.filter_var.trace("w", lambda *a: self.refresh_list())
        columns = ("id", "project", "diameter", "grade", "length", "quantity")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        for col, text, w in (("id", "ID", 40), ("project", "Project", 100), ("diameter", "Diameter (mm)", 100), ("grade", "Grade", 60), ("length", "Length (mm)", 110), ("quantity", "Quantity", 80)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.tag_configure("low_stock", foreground="red")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=5)

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
        items.sort(key=lambda x: (x[2], x[3]))
        for item in items:
            pid_display = item[1] if item[1] is not None else "Global"
            qty = item[4]
            tags = ("low_stock",) if qty < LOW_STOCK_THRESHOLD else ()
            self.tree.insert("", "end", values=(item[0], pid_display, item[2], item[5], item[3], qty), tags=tags)

    def add_stock(self):
        dlg = StockDialog(self, title="Add Stock", dia=12.0, length=12000.0, qty=10, grade=DEFAULT_REBAR_GRADE,
                          show_project_option=self.project_id is not None, project_id=self.project_id)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, qty, grade, assign = dlg.result
        project = self.project_id if assign else None
        try:
            StockModel.add(project, dia, length, qty, grade=grade)
            self.refresh_list()
            _emit_stock_changed(self.project_id, "stock_add")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add stock: {e}")

    def edit_stock(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a stock item first.")
            return
        vals = self.tree.item(selected[0])['values']
        stock_id, _, old_dia, old_grade, old_len, old_qty = vals
        dlg = StockDialog(self, title="Edit Stock", dia=old_dia, length=old_len, qty=old_qty, grade=old_grade, show_project_option=False)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, qty, grade, _ = dlg.result
        try:
            StockModel.update(stock_id, dia, length, qty, grade=grade)
            self.refresh_list()
            _emit_stock_changed(self.project_id, "stock_edit")
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
            _emit_stock_changed(self.project_id, "stock_delete")
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")

    def export_stock(self):
        try:
            from utils.stock_export import export_stock_excel
        except ImportError:
            messagebox.showerror("Missing Module", "Stock export module is not available.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")],
                                                 initialfile=f"Stock_Inventory_{datetime.date.today()}.xlsx")
        if not filepath:
            return
        try:
            export_stock_excel(filepath, project_id=self._get_filtered_project_id())
            messagebox.showinfo("Success", f"Stock report saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def _open_scrap_manager(self):
        try:
            from ui.scrap_manager import ScrapManagerWindow
        except ImportError:
            messagebox.showerror("Missing Module", "Scrap Manager module is not available.")
            return
        if hasattr(self.parent_app, 'db'):
            ScrapManagerWindow(self.parent_app, self.project_id)
        else:
            messagebox.showerror("Error", "Cannot open Scrap Manager – parent app not found.")
