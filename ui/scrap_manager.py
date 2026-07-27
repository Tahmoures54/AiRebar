# ui/scrap_manager.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from db.models import ScrapModel, RebarModel, ListoferModel
from config import REBAR_GRADES, DEFAULT_REBAR_GRADE

logger = logging.getLogger(__name__)


class ScrapEditDialog(tk.Toplevel):
    """Dialog for adding or editing a scrap piece."""

    def __init__(self, parent, title="Add Scrap", scrap_data=None):
        super().__init__(parent)
        self.result = None  # (diameter, length, grade, listofer_number)
        self.title(title)
        self.geometry("300x250")
        self.transient(parent)
        self.grab_set()

        self.dia_var = tk.StringVar(value=str(scrap_data[1]) if scrap_data else "12")
        self.len_var = tk.StringVar(value=str(scrap_data[2]) if scrap_data else "500")
        self.grade_var = tk.StringVar(value=scrap_data[3] if scrap_data else DEFAULT_REBAR_GRADE)
        self.lf_var = tk.StringVar(value=scrap_data[4] if scrap_data and len(scrap_data) > 4 else "")

        ttk.Label(self, text="Diameter (mm):").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        ttk.Entry(self, textvariable=self.dia_var, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(self, text="Length (mm):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        ttk.Entry(self, textvariable=self.len_var, width=12).grid(row=1, column=1, sticky="w")

        ttk.Label(self, text="Grade:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        ttk.Combobox(self, textvariable=self.grade_var, values=REBAR_GRADES, width=12).grid(row=2, column=1, sticky="w")

        ttk.Label(self, text="Listofer No (opt):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        ttk.Entry(self, textvariable=self.lf_var, width=12).grid(row=3, column=1, sticky="w")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        # Center dialog on parent
        self._center_on_parent()

    def _center_on_parent(self):
        """Position this dialog at the center of its parent."""
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

    def _on_ok(self):
        try:
            dia = float(self.dia_var.get())
            length = float(self.len_var.get())
            if dia <= 0 or length <= 0:
                raise ValueError("Diameter and length must be positive.")
            grade = self.grade_var.get().strip() or DEFAULT_REBAR_GRADE
            lf_no = self.lf_var.get().strip() or None
            self.result = (dia, length, grade, lf_no)
            self.destroy()
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e), parent=self)


class RebarAssignmentDialog(tk.Toplevel):
    """Dialog to select a rebar item from the project for scrap assignment."""

    def __init__(self, parent, project_id, scrap_dia, scrap_grade):
        super().__init__(parent)
        self.result_rebar_id = None
        self.title("Assign Scrap to Rebar")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Select a rebar item to assign this scrap to:",
                  font=("Arial", 10, "bold")).pack(pady=10)

        # Treeview to list rebars
        columns = ("ID", "Pos", "Listofer", "Shape", "Dia", "Grade", "Length (mm)")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80, anchor="center")
        self.tree.column("Shape", width=120)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Assign", command=self._on_assign).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        # Load rebars matching the scrap's diameter and grade (if available)
        self._load_rebars(project_id, scrap_dia, scrap_grade)

        # Center dialog on parent
        self._center_on_parent()

    def _center_on_parent(self):
        """Position this dialog at the center of its parent."""
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

    def _load_rebars(self, project_id, dia, grade):
        all_rebars = RebarModel.get_for_project(project_id)   # returns list of tuples
        for r in all_rebars:
            r_dia = float(r[4])
            r_grade = r[12] if len(r) > 12 else DEFAULT_REBAR_GRADE
            # Filter by matching diameter and grade, or show all if no exact match
            if dia and grade and (r_dia != dia or r_grade != grade):
                continue
            # Calculate length from shape and dimensions
            from shapes.definitions import default_shape_registry
            import json
            shape_name = r[5]
            dims_str = r[6]
            try:
                dims = json.loads(dims_str) if isinstance(dims_str, str) else dims_str or {}
            except Exception:
                dims = {}
            try:
                length_mm = default_shape_registry.calc_shape_length(shape_name, dims, r_dia)
            except Exception:
                length_mm = 0
            values = (r[0], r[3], r[1], shape_name, f"{r_dia:.0f}", r_grade, f"{length_mm:.0f}")
            self.tree.insert("", "end", values=values)

    def _on_assign(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a rebar item.")
            return
        self.result_rebar_id = int(self.tree.item(selected[0], "values")[0])
        self.destroy()


class ScrapManagerWindow(tk.Toplevel):
    """Window for managing scrap pieces with SQL filtering/sorting, color tags,
    and assignment to BBS items."""

    _DB_COLUMN_MAP = {
        "id": "id",
        "diameter": "diameter",
        "grade": "grade",
        "length_mm": "length_mm",
        "date": "date_created",
        "status": "used",
        "listofer": "listofer_number",
    }

    def __init__(self, parent, project_id):
        super().__init__(parent)
        self.parent = parent
        self.project_id = project_id
        self.title("🧩 Smart Scrap Bank Manager")
        self.geometry("950x550")
        self.transient(parent)
        self.grab_set()

        self._sort_col = "date"
        self._sort_reverse = True

        self.dia_filter = tk.StringVar(value="All")
        self.grade_filter = tk.StringVar(value="All")

        self._create_widgets()
        self._center_on_parent()          # position the window at the center of the parent
        self.load_data()

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
        filter_frame = ttk.Frame(self, padding=5)
        filter_frame.pack(fill="x", pady=5)

        ttk.Label(filter_frame, text="Diameter:").pack(side="left", padx=(0, 2))
        self.dia_combo = ttk.Combobox(filter_frame, textvariable=self.dia_filter,
                                      state="readonly", width=8)
        self.dia_combo.pack(side="left", padx=5)
        self.dia_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        ttk.Label(filter_frame, text="Grade:").pack(side="left", padx=(15, 2))
        self.grade_combo = ttk.Combobox(filter_frame, textvariable=self.grade_filter,
                                        state="readonly", width=8)
        self.grade_combo.pack(side="left", padx=5)
        self.grade_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        ttk.Button(filter_frame, text="➕ Add Scrap", command=self._add_scrap).pack(side="right", padx=2)
        ttk.Button(filter_frame, text="✏️ Edit", command=self._edit_selected).pack(side="right", padx=2)
        ttk.Button(filter_frame, text="🔗 Assign to BBS", command=self._assign_to_bbs).pack(side="right", padx=2)
        ttk.Button(filter_frame, text="♻️ Mark as Used", command=self._mark_as_used).pack(side="right", padx=2)
        ttk.Button(filter_frame, text="🗑️ Delete", command=self._delete_selected).pack(side="right", padx=2)

        columns = ("id", "diameter", "grade", "listofer", "length_mm", "date", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(
                col, text=col.capitalize() if col != "listofer" else "Listofer",
                command=lambda c=col: self._sort_by_column(c)
            )
            width = {"id": 40, "diameter": 70, "grade": 60, "listofer": 80,
                     "length_mm": 100, "date": 140, "status": 80}.get(col, 80)
            self.tree.column(col, width=width, anchor="center")
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        # Color tags for status
        self.tree.tag_configure("available", foreground="#2e7d32")  # green
        self.tree.tag_configure("used", foreground="#c62828")       # red

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        summary_frame = ttk.Frame(self, padding=5)
        summary_frame.pack(fill="x", side="bottom", pady=5)
        self.summary_label = ttk.Label(summary_frame, text="Total Available: -- mm",
                                       font=("Arial", 10, "bold"))
        self.summary_label.pack(side="right", padx=10)

    # ------------------------------------------------------------------
    # Data loading (SQL‑side filtering & sorting)
    # ------------------------------------------------------------------
    def load_data(self):
        try:
            distinct_diams = self._fetch_distinct("diameter")
            distinct_grades = self._fetch_distinct("grade")
            self.dia_combo['values'] = ["All"] + [str(d) for d in distinct_diams]
            self.grade_combo['values'] = ["All"] + [g for g in distinct_grades if g]
            if self.dia_filter.get() not in self.dia_combo['values']:
                self.dia_filter.set("All")
            if self.grade_filter.get() not in self.grade_combo['values']:
                self.grade_filter.set("All")
        except Exception as e:
            logger.error(f"Failed to load filter values: {e}")

        dia_val = self.dia_filter.get()
        grade_val = self.grade_filter.get()
        where_clauses = ["project_id = ?"]
        params = [self.project_id]

        if dia_val != "All":
            where_clauses.append("diameter = ?")
            params.append(float(dia_val))
        if grade_val != "All":
            where_clauses.append("grade = ?")
            params.append(grade_val)

        where = " AND ".join(where_clauses)
        sort_db_col = self._DB_COLUMN_MAP.get(self._sort_col, "date_created")
        direction = "DESC" if self._sort_reverse else "ASC"
        query = f"""
            SELECT id, diameter, length_mm, grade, date_created, used, listofer_number
            FROM scraps
            WHERE {where}
            ORDER BY {sort_db_col} {direction}
        """

        try:
            scraps = self.parent.db.fetchall(query, tuple(params))
        except Exception as e:
            logger.error(f"Failed to load scraps: {e}")
            messagebox.showerror("Error", f"Could not load scraps: {e}")
            return

        self.tree.delete(*self.tree.get_children())
        total_available = 0.0
        for s in scraps:
            sid, diam, length, grade, date, used, lf = s
            status_text = "Available" if used == 0 else "Used"
            tag = "available" if used == 0 else "used"
            values = (sid, diam, grade, lf or "—", f"{length:.1f}", date[:10] if date else "", status_text)
            self.tree.insert("", "end", values=values, tags=(tag,))
            if used == 0:
                total_available += length

        self.summary_label.config(text=f"Total Available Length: {total_available:.1f} mm")

    def _fetch_distinct(self, column):
        rows = self.parent.db.fetchall(
            f"SELECT DISTINCT {column} FROM scraps WHERE project_id = ? AND {column} IS NOT NULL",
            (self.project_id,)
        )
        return [r[0] for r in rows]

    def _sort_by_column(self, col_name):
        if self._sort_col == col_name:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col_name
            self._sort_reverse = False
        for c in self._DB_COLUMN_MAP.keys():
            text = c.capitalize()
            if c == self._sort_col:
                text += " ▼" if self._sort_reverse else " ▲"
            self.tree.heading(c, text=text)
        self.load_data()

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def _add_scrap(self):
        dlg = ScrapEditDialog(self, title="Add Scrap")
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, grade, lf_no = dlg.result
        try:
            ScrapModel.add_scrap(self.project_id, dia, length, grade=grade, listofer_number=lf_no)
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add scrap: {e}")

    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a scrap to edit.")
            return
        item = selected[0]
        scrap_id = int(self.tree.item(item, "values")[0])
        row = self.parent.db.fetchone(
            "SELECT id, diameter, length_mm, grade, listofer_number FROM scraps WHERE id = ?",
            (scrap_id,)
        )
        if not row:
            messagebox.showerror("Error", "Record not found.")
            return
        scrap_data = row  # (id, dia, length, grade, lf)
        dlg = ScrapEditDialog(self, title="Edit Scrap", scrap_data=scrap_data)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        dia, length, grade, lf_no = dlg.result
        try:
            self.parent.db.execute(
                "UPDATE scraps SET diameter=?, length_mm=?, grade=?, listofer_number=? WHERE id=?",
                (dia, length, grade, lf_no, scrap_id), commit=True
            )
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Could not update scrap: {e}")

    def _mark_as_used(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "No scrap selected.")
            return
        if not messagebox.askyesno("Confirm", "Mark selected scrap(s) as used?"):
            return
        for item in selected:
            scrap_id = int(self.tree.item(item, "values")[0])
            try:
                ScrapModel.mark_as_used(scrap_id)
            except Exception as e:
                messagebox.showerror("Error", f"Could not update scrap {scrap_id}: {e}")
                return
        self.load_data()

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "No scrap selected.")
            return
        if messagebox.askyesno("Confirm", "Delete selected scrap(s) permanently?"):
            for item in selected:
                scrap_id = int(self.tree.item(item, "values")[0])
                try:
                    ScrapModel.delete_scrap(scrap_id)
                except Exception as e:
                    messagebox.showerror("Error", f"Delete failed: {e}")
            self.load_data()

    # ------------------------------------------------------------------
    # NEW: Assign scrap to a BBS rebar item
    # ------------------------------------------------------------------
    def _assign_to_bbs(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a scrap to assign.")
            return
        if len(selected) > 1:
            messagebox.showinfo("Info", "Please select only one scrap for assignment.")
            return
        item = selected[0]
        scrap_id = int(self.tree.item(item, "values")[0])
        # Ensure scrap is available
        status = self.tree.item(item, "values")[6]  # "Available" or "Used"
        if status != "Available":
            if not messagebox.askyesno("Already Used", "This scrap is already marked as used. Assign anyway?"):
                return

        # Get scrap details
        scrap_row = self.parent.db.fetchone(
            "SELECT id, diameter, length_mm, grade FROM scraps WHERE id = ?", (scrap_id,)
        )
        if not scrap_row:
            messagebox.showerror("Error", "Scrap not found.")
            return
        scrap_dia, scrap_grade = scrap_row[1], scrap_row[3]

        # Open rebar selection dialog
        dlg = RebarAssignmentDialog(self, self.project_id, scrap_dia, scrap_grade)
        self.wait_window(dlg)
        if dlg.result_rebar_id is None:
            return  # user cancelled

        rebar_id = dlg.result_rebar_id

        # Mark scrap as used and create assignment record in one transaction
        try:
            # Get listofer number for the rebar (to fill assignment)
            rebar_info = self.parent.db.fetchone(
                "SELECT r.listofer_id, l.number FROM rebars r "
                "JOIN listofers l ON r.listofer_id = l.id WHERE r.id = ?",
                (rebar_id,)
            )
            listofer_number = rebar_info[1] if rebar_info else ""

            # Mark scrap as used
            ScrapModel.mark_as_used(scrap_id)

            # Insert into cutting_assignments (project_id, listofer_number, rebar_id, source_type='scrap', source_id=scrap_id)
            self.parent.db.execute(
                "INSERT INTO cutting_assignments (project_id, listofer_number, rebar_id, source_type, source_id) "
                "VALUES (?, ?, ?, 'scrap', ?)",
                (self.project_id, listofer_number, rebar_id, scrap_id),
                commit=True
            )
            messagebox.showinfo("Success", f"Scrap #{scrap_id} assigned to Rebar #{rebar_id}.")
            self.load_data()
        except Exception as e:
            logger.error(f"Assignment failed: {e}")
            messagebox.showerror("Error", f"Could not assign scrap: {e}")