# ui/listofer_selector_window.py
"""
Optimized listofer selector with search, status, and single DB query.
Now centres itself on the parent window.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from collections import defaultdict

from db.models import ListoferModel, RebarModel
from shapes.definitions import default_shape_registry
from logic.calculator import calculate_weight

logger = logging.getLogger(__name__)


class ListoferSelectorWindow(tk.Toplevel):
    """
    Optimized listofer selector with search, status, and single DB query.
    """

    def __init__(self, parent, project_id, callback):
        super().__init__(parent)
        self.callback = callback
        self.project_id = project_id
        self.title("📋 Select Listofer for AI-Generated Report")
        self.geometry("650x450")
        self.transient(parent)
        self.grab_set()

        # Data containers
        self._all_items = []          # list of (listofer_no, desc, item_count, weight, status)
        self._filtered_rows = []      # filtered iids for tree

        ttk.Label(self, text="Select a Listofer to generate an intelligent BBS report:",
                  font=("Arial", 11, "bold")).pack(pady=10)

        # Search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left")
        search_entry.bind("<KeyRelease>", self._on_search)

        # Treeview frame
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("num", "desc", "items", "weight", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        self.tree.heading("num", text="Listofer No.")
        self.tree.column("num", width=100, anchor="center")
        self.tree.heading("desc", text="Description")
        self.tree.column("desc", width=220)
        self.tree.heading("items", text="Rebar Items")
        self.tree.column("items", width=90, anchor="center")
        self.tree.heading("weight", text="Total Weight (kg)")
        self.tree.column("weight", width=120, anchor="center")
        self.tree.heading("status", text="Status")
        self.tree.column("status", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_data()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="✨ Generate AI Report",
                   command=self.on_print).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        # Center on parent
        self._center_on_parent()

    def _center_on_parent(self):
        """Position this window at the centre of its parent."""
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

    # ------------------------------------------------------------------
    # Data loading – single DB query, grouping in memory
    # ------------------------------------------------------------------
    def load_data(self):
        # Fetch all rebars for the project in one query
        all_rebars = RebarModel.get_for_project(self.project_id)  # returns list of tuples

        # Group by listofer number
        grouped = defaultdict(list)
        for row in all_rebars:
            # row: (id, lnumber, ldesc, pos, dia, shape_name, dims_str, qty,
            #        location, element_type, added_by, date_added, grade)
            lf_no = row[1]          # listofer number
            grouped[lf_no].append(row)

        self._all_items.clear()
        # Sort by listofer number (natural sort)
        numbers = sorted(grouped.keys(), key=lambda n: (n != "-- All Listofers --", n))

        for num in numbers:
            rebars = grouped[num]
            desc = ""
            if rebars:
                # Description is column index 2 of the first rebar
                desc = rebars[0][2] if len(rebars[0]) > 2 and rebars[0][2] else ""

            # Calculate weight and detect errors
            total_weight, has_error = self._process_rebars(rebars)
            status = "⚠️ Error" if has_error else "✅ OK"
            if not rebars:
                status = "❌ Empty"

            self._all_items.append((num, desc, len(rebars), total_weight, status))

        # Add "All" special entry at the end (not from DB)
        self._all_items.append(("-- All Listofers --", "Complete project summary", "", "", ""))

        self._filter_treeview()

    def _process_rebars(self, rebars) -> tuple:
        """Calculate total weight and check for errors."""
        total = 0.0
        error_flag = False
        for row in rebars:
            try:
                dia = float(row[4])
                shape_name = row[5]
                dims_str = row[6]
                qty = int(row[7])

                # Parse dimensions
                if isinstance(dims_str, str):
                    try:
                        dims = json.loads(dims_str)
                    except (json.JSONDecodeError, TypeError):
                        dims = {}
                else:
                    dims = dims_str or {}

                # Check if shape exists in registry
                if shape_name not in default_shape_registry.flat_shapes:
                    error_flag = True
                    continue

                length_mm = default_shape_registry.calc_shape_length(shape_name, dims, dia)
                _, piece_wt = calculate_weight(dia, length_mm)
                total += piece_wt * qty
            except Exception as e:
                logger.warning(f"Error processing rebar {row[0]}: {e}")
                error_flag = True
        return total, error_flag

    # ------------------------------------------------------------------
    # Search / filtering
    # ------------------------------------------------------------------
    def _on_search(self, event=None):
        self._filter_treeview()

    def _filter_treeview(self):
        """Clear and repopulate tree based on search text."""
        query = self.search_var.get().strip().lower()
        # Remove previous rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._filtered_rows.clear()
        for item in self._all_items:
            lf_no = item[0]
            if query and query not in lf_no.lower():
                continue
            # Insert into tree
            iid = self.tree.insert("", "end", values=item)
            self._filtered_rows.append(iid)
            # Highlight the "All" row
            if lf_no == "-- All Listofers --":
                self.tree.tag_configure("all", background="#e6eff9")
                self.tree.item(iid, tags=("all",))

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------
    def on_print(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a listofer.")
            return
        values = self.tree.item(selected[0], "values")
        lf_number = values[0]
        if lf_number == "-- All Listofers --":
            lf_number = None
        self.destroy()
        self.callback(lf_number)