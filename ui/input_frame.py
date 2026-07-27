"""
Alternative input frame for adding/editing rebars.
Uses the unified shape registry, real-time validation,
keyboard shortcuts, and live preview synchronization.
Now with automatic project selection when only one project exists.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import json
import getpass
import logging

from shapes.definitions import default_shape_registry
from config import ELEMENT_TYPES, STANDARD_DIAMETERS, DEFAULT_REBAR_GRADE
from db.models import ListoferModel, RebarModel, ProjectModel

logger = logging.getLogger('AI_Rebar.InputFrame')


class InputFrame(ttk.LabelFrame):
    def __init__(self, parent, controller, style):
        super().__init__(parent, text="Input Data", style=f"{style}.TLabelframe")
        self.controller = controller
        self.style_prefix = style
        self.param_entries = {}
        self.selected_item_for_edit = None
        self._validation_cmd = self.register(self._validate_numeric)

        self._create_widgets()
        self._bind_keys()

    # ------------------------------------------------------------------
    # Numeric validation for real‑time input filtering
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_numeric(action, value_if_allowed):
        if action == '0':          # deletion
            return True
        if value_if_allowed == '':
            return True
        if value_if_allowed.count('.') > 1:
            return False
        for ch in value_if_allowed:
            if not (ch.isdigit() or ch == '.'):
                return False
        return True

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _create_widgets(self):
        grid = ttk.Frame(self, style=f"{self.style_prefix}.TFrame")
        grid.pack(fill="x", padx=10, pady=5)

        # Row 0: Listofer
        ttk.Label(grid, text="Listofer No.:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.listofer_no = ttk.Combobox(grid, width=18)
        self.listofer_no.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(grid, text="Listofer Desc.:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.listofer_desc = ttk.Combobox(grid, width=28)
        self.listofer_desc.grid(row=0, column=3, columnspan=3, padx=5, pady=5, sticky="ew")

        # Row 1: Position, Diameter, Quantity
        ttk.Label(grid, text="Pos:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.pos = tk.Entry(grid, width=10,
                            validate="key",
                            validatecommand=(self._validation_cmd, '%d', '%S'))
        self.pos.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(grid, text="Dia (mm):", style=f"{self.style_prefix}.TLabel") \
            .grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.dia = ttk.Combobox(grid, values=STANDARD_DIAMETERS,
                                width=10, state="readonly")
        self.dia.grid(row=1, column=3, padx=5, pady=5)
        self.dia.set(16)

        ttk.Label(grid, text="Qty:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=1, column=4, sticky="w", padx=5, pady=5)
        self.qty = tk.Entry(grid, width=10,
                            validate="key",
                            validatecommand=(self._validation_cmd, '%d', '%S'))
        self.qty.grid(row=1, column=5, padx=5, pady=5)
        self.qty.insert(0, "1")

        # Row 2: Element type, Location
        ttk.Label(grid, text="Element Type:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.element_type = ttk.Combobox(grid, values=ELEMENT_TYPES, state="readonly", width=18)
        self.element_type.grid(row=2, column=1, padx=5, pady=5)
        self.element_type.set("Column")

        ttk.Label(grid, text="Location:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.location = tk.Entry(grid, width=28)
        self.location.grid(row=2, column=3, columnspan=3, padx=5, pady=5, sticky="ew")

        # Row 3: Shape type
        ttk.Label(grid, text="Shape Type:", style=f"{self.style_prefix}.TLabel") \
            .grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.shape_name = ttk.Combobox(grid, values=[], state="readonly", width=60)
        self.shape_name.grid(row=3, column=1, columnspan=5, padx=5, pady=5, sticky="ew")
        self.shape_name.bind("<<ComboboxSelected>>", self.on_shape_select)

        # Parameters frame
        self.params_frame = ttk.Frame(self, style=f"{self.style_prefix}.TFrame")
        self.params_frame.pack(fill="x", padx=10, pady=5, anchor='w')

        # Action buttons
        actions = ttk.Frame(self, style=f"{self.style_prefix}.TFrame")
        actions.pack(fill="x", padx=10, pady=10)
        self.btn_add = ttk.Button(actions, text="Add Rebar", command=self.add_rebar)
        self.btn_add.pack(side="left", padx=5)
        self.btn_edit = ttk.Button(actions, text="Edit Selected", command=self.edit_rebar)
        self.btn_edit.pack(side="left", padx=5)
        self.btn_save = ttk.Button(actions, text="Save Edit", command=self.update_edited_rebar,
                                   state="disabled")
        self.btn_save.pack(side="left", padx=5)
        self.btn_delete = ttk.Button(actions, text="Delete Selected", command=self.delete_rebar)
        self.btn_delete.pack(side="left", padx=5)
        self.btn_clear = ttk.Button(actions, text="Clear Inputs", command=self.clear_inputs)
        self.btn_clear.pack(side="right", padx=5)

        self.refresh_shape_list()
        self.on_shape_select()

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------
    def _bind_keys(self):
        self.bind_all("<Control-s>", lambda e: self._save_shortcut())
        self.bind("<Return>", lambda e: self._enter_shortcut())

    def _save_shortcut(self):
        if self.selected_item_for_edit is not None:
            self.update_edited_rebar()
        else:
            self.add_rebar()

    def _enter_shortcut(self):
        focused = self.focus_get()
        if focused in self.param_entries.values() or focused == self.qty:
            self._save_shortcut()

    # ------------------------------------------------------------------
    # Shape list & selection
    # ------------------------------------------------------------------
    def refresh_shape_list(self):
        default_shape_registry.refresh()
        shape_names = sorted(default_shape_registry.flat_shapes.keys())
        self.shape_name['values'] = shape_names
        if shape_names:
            current = self.shape_name.get()
            if current not in shape_names:
                self.shape_name.current(0)

    def on_shape_select(self, event=None):
        for w in self.params_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()

        shape_name = self.shape_name.get()
        shape = default_shape_registry.flat_shapes.get(shape_name)
        if not shape:
            return

        defaults = default_shape_registry.get_default_params(shape_name)
        col = 0
        for p in shape["params"]:
            ttk.Label(self.params_frame, text=f"{p} (mm):",
                      style=f"{self.style_prefix}.TLabel") \
                .grid(row=0, column=col, padx=5, pady=5, sticky="w")
            entry = tk.Entry(self.params_frame, width=10,
                             validate="key",
                             validatecommand=(self._validation_cmd, '%d', '%S'))
            entry.insert(0, str(defaults.get(p, "")))
            entry.grid(row=0, column=col + 1, padx=5, pady=5)
            self.param_entries[p] = entry
            col += 2

        self._update_preview()
        for pname, ent in self.param_entries.items():
            ent.bind("<KeyRelease>", lambda e: self._update_preview())
        self.dia.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

    def _update_preview(self):
        try:
            preview = self.controller.preview_frame
        except AttributeError:
            logger.warning("No preview_frame attribute in controller.")
            return
        try:
            preview.update_preview()
        except Exception as e:
            logger.error(f"Error updating preview: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Input clearing & JSON extraction
    # ------------------------------------------------------------------
    def clear_inputs(self):
        self.listofer_no.set('')
        self.listofer_desc.set('')
        self.pos.delete(0, tk.END)
        self.dia.set(16)
        self.qty.delete(0, tk.END)
        self.qty.insert(0, "1")
        self.location.delete(0, tk.END)
        self.element_type.set("Column")
        if default_shape_registry.flat_shapes:
            self.shape_name.current(0)
        self.on_shape_select()
        self.btn_add.config(state="normal")
        self.btn_save.config(state="disabled")
        self.btn_edit.config(state="normal")
        self.selected_item_for_edit = None

    def _get_dimensions_json(self):
        dims = {}
        for pname, ent in self.param_entries.items():
            try:
                val = float(ent.get().strip())
                if val <= 0:
                    raise ValueError(f"Dimension {pname} must be positive.")
                dims[pname] = val
            except ValueError:
                raise ValueError(f"Invalid value for {pname}.")
        return json.dumps(dims)

    # ------------------------------------------------------------------
    # Automatic project selection helper
    # ------------------------------------------------------------------
    def _get_active_project_id(self):
        """Return the current project_id or auto‑select the only project if available."""
        state = self.controller.state
        if state.current_project_id is not None:
            return state.current_project_id

        # Auto‑select if exactly one project exists in the database
        try:
            projects = ProjectModel.get_all()   # returns list of (id, name) tuples
            if len(projects) == 1:
                pid, pname = projects[0]
                state.current_project_id = pid
                state.current_project_name = pname
                # Also update listofer lists for the newly selected project
                self.update_listofer_lists()
                return pid
            elif len(projects) > 1:
                messagebox.showerror("Error",
                    "No active project. Please select or create one from the Project Manager.")
                return None
            else:
                messagebox.showerror("Error",
                    "No projects exist. Please create a new project first.")
                return None
        except Exception as e:
            messagebox.showerror("Error", f"Unable to access projects: {e}")
            return None

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def add_rebar(self):
        project_id = self._get_active_project_id()
        if not project_id:
            return

        try:
            lnum = self.listofer_no.get().strip()
            ldesc = self.listofer_desc.get().strip()
            if not lnum:
                raise ValueError("Listofer number required.")
            lid = ListoferModel.get_or_create(project_id, lnum, ldesc)

            pos = self.pos.get().strip()
            if not pos:
                raise ValueError("Position required.")
            dia = int(self.dia.get())
            qty = int(self.qty.get())
            if qty <= 0:
                raise ValueError("Quantity must be positive.")

            loc = self.location.get().strip() or None
            shape = self.shape_name.get()
            elem = self.element_type.get() or None

            dims_json = self._get_dimensions_json()

            user = getpass.getuser()
            now = datetime.datetime.now().isoformat()

            RebarModel.add(
                listofer_id=lid,
                pos=pos,
                diameter=dia,
                shape_name=shape,
                dimensions=dims_json,
                quantity=qty,
                location=loc,
                element_type=elem,
                user=user,
                date=now,
                grade=DEFAULT_REBAR_GRADE
            )

            self.controller.bbs_treeview.load_data()
            self.update_listofer_lists()
            self.clear_inputs()
            self.controller.state.mark_modified()
        except Exception as e:
            messagebox.showerror("Input Error", str(e))

    def edit_rebar(self):
        tree = self.controller.bbs_treeview.tree
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select an item to edit.")
            return

        item_id = selected[0]
        values = tree.item(item_id, 'values')
        rebar_id = int(values[0])

        self.clear_inputs()
        self.selected_item_for_edit = rebar_id

        self.listofer_no.set(values[1])
        self.listofer_desc.set(values[2])
        self.pos.insert(0, values[3])
        self.dia.set(values[4])
        self.shape_name.set(values[6])
        self.on_shape_select()

        dims_str = values[7]
        try:
            dims = json.loads(dims_str)
            for p, val in dims.items():
                if p in self.param_entries:
                    self.param_entries[p].delete(0, tk.END)
                    self.param_entries[p].insert(0, str(val))
        except Exception:
            pass

        self.qty.delete(0, tk.END)
        self.qty.insert(0, values[9])
        self.location.insert(0, values[12] if values[12] else "")
        self.element_type.set(values[13] if values[13] else "Column")

        self.btn_add.config(state="disabled")
        self.btn_save.config(state="normal")
        self.btn_edit.config(state="disabled")

    def update_edited_rebar(self):
        project_id = self._get_active_project_id()
        if not project_id:
            return
        if self.selected_item_for_edit is None:
            return

        try:
            lnum = self.listofer_no.get().strip()
            ldesc = self.listofer_desc.get().strip()
            if not lnum:
                raise ValueError("Listofer number required.")
            lid = ListoferModel.get_or_create(project_id, lnum, ldesc)

            pos = self.pos.get().strip()
            dia = int(self.dia.get())
            qty = int(self.qty.get())
            loc = self.location.get().strip() or None
            shape = self.shape_name.get()
            elem = self.element_type.get() or None
            dims_json = self._get_dimensions_json()

            user = getpass.getuser()
            now = datetime.datetime.now().isoformat()

            RebarModel.update(
                rebar_id=self.selected_item_for_edit,
                listofer_id=lid,
                pos=pos,
                diameter=dia,
                shape_name=shape,
                dimensions=dims_json,
                quantity=qty,
                location=loc,
                element_type=elem,
                user=user,
                date=now,
                grade=DEFAULT_REBAR_GRADE
            )

            self.controller.bbs_treeview.load_data()
            self.clear_inputs()
            self.controller.state.mark_modified()
        except Exception as e:
            messagebox.showerror("Update Error", str(e))

    def delete_rebar(self):
        tree = self.controller.bbs_treeview.tree
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "No selection.")
            return
        if messagebox.askyesno("Confirm", f"Delete {len(selected)} item(s)?"):
            for item_id in selected:
                rebar_id = int(tree.item(item_id, 'values')[0])
                RebarModel.delete(rebar_id)
            self.controller.bbs_treeview.load_data()
            self.update_listofer_lists()
            self.controller.state.mark_modified()

    def update_listofer_lists(self):
        project_id = self._get_active_project_id()
        if not project_id:
            return
        nums = ListoferModel.get_numbers(project_id)
        descs = ListoferModel.get_descriptions(project_id)
        self.listofer_no['values'] = nums
        self.listofer_desc['values'] = descs
        if hasattr(self.controller, 'bbs_treeview'):
            self.controller.bbs_treeview.update_filter_list(nums)