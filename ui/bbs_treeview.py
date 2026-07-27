# ui/bbs_treeview.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from typing import Optional, Callable

from config import STANDARD_STOCK_LENGTHS_M, DEFAULT_REBAR_GRADE
from shapes.definitions import default_shape_registry
from logic.calculator import calculate_weight
from logic.optimizer import PULP_AVAILABLE
from db.models import RebarModel, ListoferModel

logger = logging.getLogger(__name__)


class BBSTreeview(ttk.LabelFrame):
    """Enhanced BBS table with caching, sorting, and cleaner architecture.
    Already fills the parent container and uses centred column alignment for clarity."""

    def __init__(self, parent, controller, style):
        super().__init__(parent, text="Bar Bending Schedule (BBS)",
                         style=f"{style}.TLabelframe")
        self.controller = controller
        self.style_prefix = style

        # Cache for summary calculations: iid -> (dia, grade, cut_len_m, qty)
        self._summary_cache = {}
        # Optional extra data, populated only if needed externally
        self.item_data = {}

        # Filter controls
        filter_frame = ttk.Frame(self, style=f"{style}.TFrame")
        filter_frame.pack(fill="x", pady=5, padx=5)

        ttk.Label(filter_frame, text="Filter by Listofer:",
                  style=f"{style}.TLabel").pack(side="left", padx=10)

        self.filter_combo = ttk.Combobox(filter_frame, state="readonly", width=40)
        self.filter_combo.pack(side="left", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        ttk.Label(filter_frame, text="Stock Len (m):",
                  style=f"{style}.TLabel").pack(side="left", padx=(20, 5))

        self.stock_length = ttk.Combobox(filter_frame,
                                         values=STANDARD_STOCK_LENGTHS_M,
                                         width=10, state="readonly")
        self.stock_length.pack(side="left", padx=5)
        self.stock_length.set(12)
        self.stock_length.bind("<<ComboboxSelected>>", lambda e: self.update_summary())

        # Tree container
        tree_container = ttk.Frame(self, style=f"{style}.TFrame")
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("ID", "Listofer No.", "Listofer Desc.", "Pos.", "Dia", "Grade",
                   "Shape Code", "Shape", "Dimensions (mm)", "Cut Len (mm)", "Qty",
                   "Unit Wt (kg/m)", "Total Wt (kg)", "Location", "Element",
                   "Added By", "Date Added")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings",
                                 style=f"{style}.Treeview")
        for col in columns:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_column(c))  # click to sort
            # Default width – overridden for certain columns
            width = 80
            if col in ("Dimensions (mm)", "Shape"):
                width = 160
            elif col == "Cut Len (mm)":
                width = 100
            elif col == "Grade":
                width = 60
            # All columns are centred for a clean look
            self.tree.column(col, width=width, anchor="center")
        # Override specific anchors for readability
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Listofer No.", width=100, anchor="center")
        self.tree.column("Listofer Desc.", width=150, anchor="w")   # description left-aligned

        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # Summary frame
        self.summary_frame = ttk.LabelFrame(self, text="Summary & Analysis",
                                            style=f"{style}.TLabelframe")
        self.summary_frame.pack(fill="x", padx=5, pady=5)

        self.total_weight_label = ttk.Label(self.summary_frame,
                                            text="Total Weight: 0.00 kg",
                                            font=("Arial", 14, "bold"),
                                            style=f"{style}.TLabel")
        self.total_weight_label.pack(side="right", padx=20, pady=5)

        summary_columns = ("Diameter", "Grade", "Total Wt (kg)", "Total Len (m)",
                           "# Stock Bars", "Waste (m)", "Waste (%)")
        self.summary_tree = ttk.Treeview(self.summary_frame, columns=summary_columns,
                                         show="headings", height=5,
                                         style=f"{style}.Treeview")
        for col in summary_columns:
            self.summary_tree.heading(col, text=col)
            width = 100 if col == "# Stock Bars" else 90
            self.summary_tree.column(col, width=width, anchor="center")
        self.summary_tree.pack(side="left", fill="x", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._summary_cache.clear()
        self.item_data.clear()
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        self.total_weight_label.config(text="Total Weight: 0.00 kg")

    def update_filter_list(self, numbers):
        self.filter_combo['values'] = ["-- Show All --"] + numbers
        self.filter_combo.set("-- Show All --")

    def load_data(self):
        project_id = self.controller.state.current_project_id
        if not project_id:
            self.clear_tree()
            return

        if not self.filter_combo['values']:
            numbers = ListoferModel.get_numbers(project_id)
            self.update_filter_list(numbers)

        filter_val = self.filter_combo.get()
        number = None if filter_val in ("-- Show All --", "") else filter_val

        self.clear_tree()

        rows = RebarModel.get_for_project(project_id, number)
        for row in rows:
            # Now handle rows with 14 columns (standard included) or 13 (older DBs)
            if len(row) >= 14:
                (rebar_id, lnum, ldesc, pos, dia, shape_name, dims_str, qty,
                 loc, elem, added_by, date_added, grade, standard) = row
            elif len(row) >= 13:
                (rebar_id, lnum, ldesc, pos, dia, shape_name, dims_str, qty,
                 loc, elem, added_by, date_added, grade) = row
                standard = ""
            else:
                # Legacy fallback (should rarely happen)
                (rebar_id, lnum, ldesc, pos, dia, shape_name, dims_str, qty,
                 loc, elem, added_by, date_added) = row
                grade = DEFAULT_REBAR_GRADE
                standard = ""

            shape_info = default_shape_registry.get_shape_def(shape_name)
            if not shape_info:
                continue

            try:
                if dims_str and dims_str.startswith('{'):
                    param_values = json.loads(dims_str)
                    param_values = {k: float(v) for k, v in param_values.items()}
                else:
                    param_values = {}
                    if dims_str:
                        for part in dims_str.split(','):
                            if '=' in part:
                                key, val = part.split('=')
                                param_values[key.strip()] = float(val.strip())

                cut_len = shape_info["calc_length"](param_values, float(dia))
                unit_wt, total_wt = calculate_weight(float(dia), cut_len)
                total_wt *= qty

                iid = str(rebar_id)
                values = (
                    rebar_id, lnum, ldesc, pos, dia, grade,
                    shape_info["code"], shape_name, dims_str, f"{cut_len:.0f}", qty,
                    f"{unit_wt:.3f}", f"{total_wt:.2f}", loc, elem,
                    added_by, date_added
                )
                self.tree.insert("", "end", values=values, iid=iid)

                # Update cache for summary (only essential fields)
                self._summary_cache[iid] = (dia, grade, cut_len / 1000.0, qty, total_wt)

                # Store full item data only if needed (optional)
                self.item_data[iid] = {
                    "rebar_id": rebar_id,
                    "listofer_no": lnum,
                    "listofer_desc": ldesc,
                    "pos": pos,
                    "diameter": float(dia),
                    "grade": grade,
                    "shape": shape_name,
                    "dimensions": dims_str,
                    "quantity": qty,
                    "cut_len_mm": cut_len,
                    "cut_len_m": cut_len / 1000,
                    "location": loc,
                    "element": elem,
                    "added_by": added_by,
                    "date_added": date_added,
                }
            except Exception as e:
                logger.error(f"Error loading row {rebar_id}: {e}")
                continue

        self.update_summary()

    # ------------------------------------------------------------------
    # Summary with caching
    # ------------------------------------------------------------------
    def update_summary(self):
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        stock_len = float(self.stock_length.get())
        summary = {}   # (dia, grade) -> [total_wt, total_len_m, lengths_list]
        total_weight = 0.0

        for iid, (dia, grade, cut_len_m, qty, total_wt) in self._summary_cache.items():
            total_weight += total_wt
            key = (dia, grade)
            if key not in summary:
                summary[key] = [0.0, 0.0, []]
            summary[key][0] += total_wt
            summary[key][1] += cut_len_m * qty
            summary[key][2].extend([cut_len_m] * qty)

        self.total_weight_label.config(text=f"Total Weight: {total_weight:,.2f} kg")

        for (dia, grade) in sorted(summary.keys()):
            total_wt_dia, total_l, lengths = summary[(dia, grade)]
            if total_l == 0:
                continue
            num_bars = int(total_l / stock_len) + (1 if total_l % stock_len > 0 else 0)
            total_provided = num_bars * stock_len
            waste = total_provided - total_l
            waste_pct = (waste / total_provided * 100) if total_provided > 0 else 0
            self.summary_tree.insert("", "end", values=(
                f"Ø {dia}", grade, f"{total_wt_dia:,.2f}",
                f"{total_l:,.2f}", num_bars, f"{waste:.2f}",
                f"{waste_pct:.2f} %"
            ))

    # ------------------------------------------------------------------
    # Column sorting
    # ------------------------------------------------------------------
    def _sort_column(self, col_name):
        """Sort tree rows by the given column name."""
        cols = self.tree["columns"]
        if col_name not in cols:
            return
        idx = cols.index(col_name)

        # Determine current sorting order (toggle)
        if hasattr(self, '_sort_col') and self._sort_col == col_name:
            self._sort_reverse = not getattr(self, '_sort_reverse', False)
        else:
            self._sort_col = col_name
            self._sort_reverse = False

        # Get all items with their values
        rows = [(self.tree.item(iid, "values"), iid) for iid in self.tree.get_children('')]
        # Define key for sorting: try numeric if possible, else string
        def sort_key(row):
            val = row[0][idx]
            try:
                return float(val)
            except (ValueError, TypeError):
                return str(val).lower()
        rows.sort(key=sort_key, reverse=self._sort_reverse)

        # Rearrange items in tree
        for index, (vals, iid) in enumerate(rows):
            self.tree.move(iid, '', index)

        # Update header to indicate sort direction
        arrow = " ▼" if self._sort_reverse else " ▲"
        for c in cols:
            text = c
            if c == col_name:
                text = c + arrow
            self.tree.heading(c, text=text,
                              command=lambda col=c: self._sort_column(col))

    # ------------------------------------------------------------------
    # Cutting plan helpers
    # ------------------------------------------------------------------
    def get_all_lengths_by_diameter(self):
        """Return data for all items in tree (for external use)."""
        data = {}
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, 'values')
            dia = float(vals[4])
            grade = vals[5] if len(vals) > 5 else DEFAULT_REBAR_GRADE
            cut_len_m = float(vals[9]) / 1000
            qty = int(vals[10])
            for _ in range(qty):
                lbl = {
                    "rebar_id": vals[0],
                    "pos": vals[3],
                    "listofer_no": vals[1],
                    "listofer_desc": vals[2],
                    "dia": dia,
                    "grade": grade,
                    "cut_len_m": cut_len_m,
                }
                key = (dia, grade)
                if key not in data:
                    data[key] = []
                data[key].append((cut_len_m, lbl))
        return data

    def get_lengths_by_diameter_for_listofer(self, listofer_number=None):
        data = {}
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, 'values')
            lf = vals[1]
            if listofer_number is not None and lf != listofer_number:
                continue
            dia = float(vals[4])
            grade = vals[5] if len(vals) > 5 else DEFAULT_REBAR_GRADE
            cut_len_m = float(vals[9]) / 1000
            qty = int(vals[10])
            for _ in range(qty):
                lbl = {
                    "rebar_id": vals[0],
                    "pos": vals[3],
                    "listofer_no": vals[1],
                    "listofer_desc": vals[2],
                    "dia": dia,
                    "grade": grade,
                    "cut_len_m": cut_len_m,
                }
                key = (dia, grade)
                if key not in data:
                    data[key] = []
                data[key].append((cut_len_m, lbl))
        return data

    def cutting_plan_selected(self):
        selected_iids = self.tree.selection()
        if not selected_iids:
            messagebox.showwarning("Warning", "No items selected.")
            return
        stock_len = float(self.stock_length.get())
        if not PULP_AVAILABLE:
            messagebox.showerror("Error", "PuLP not installed.")
            return
        data_by_key = {}
        for iid in selected_iids:
            vals = self.tree.item(iid, 'values')
            dia = float(vals[4])
            grade = vals[5] if len(vals) > 5 else DEFAULT_REBAR_GRADE
            cut_len_m = float(vals[9]) / 1000
            qty = int(vals[10])
            for _ in range(qty):
                lbl = {
                    "rebar_id": vals[0],
                    "pos": vals[3],
                    "listofer_no": vals[1],
                    "listofer_desc": vals[2],
                    "dia": dia,
                    "grade": grade,
                    "cut_len_m": cut_len_m,
                }
                key = (dia, grade)
                if key not in data_by_key:
                    data_by_key[key] = []
                data_by_key[key].append((cut_len_m, lbl))
        self._open_cutting_plan(data_by_key, stock_len)

    def cutting_plan_all(self):
        if not self.tree.get_children():
            messagebox.showwarning("Warning", "No data to optimize.")
            return
        filter_val = self.filter_combo.get()
        listofer_filter = None if filter_val in ("-- Show All --", "") else filter_val
        stock_len = float(self.stock_length.get())
        data_by_key = self.get_lengths_by_diameter_for_listofer(listofer_filter)
        if not data_by_key:
            messagebox.showwarning("Warning", "No data for the selected filter.")
            return
        self._open_cutting_plan(data_by_key, stock_len)

    def _open_cutting_plan(self, data, stock_len):
        """Bridge to controller to open the cutting plan window."""
        if hasattr(self.controller, 'open_cutting_plan'):
            self.controller.open_cutting_plan(data, stock_len)
        else:
            # Fallback (legacy)
            from ui.dialogs import CuttingPlanWindow
            CuttingPlanWindow(self.controller, data, stock_len)