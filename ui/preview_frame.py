# ui/preview_frame.py
"""
Shape preview frame embedded in the main window.
Reads the currently selected shape, its parameters, and diameter
from the input frame and renders the shape on a canvas.
"""
import tkinter as tk
from tkinter import ttk

from shapes.drawing import draw_shape_on_canvas
from shapes.definitions import default_shape_registry


class PreviewFrame(ttk.LabelFrame):
    """Real‑time shape preview widget."""

    def __init__(self, parent, controller, style):
        super().__init__(parent, text="Shape Preview", width=350, height=300,
                         style=f"{style}.TLabelframe")
        self.controller = controller
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=1,
                                highlightbackground="gray")
        self.canvas.pack(padx=15, pady=15, expand=True, fill="both")
        self.pack_propagate(False)

    def update_preview(self):
        """Redraw the preview using the current shape and dimensions."""
        self.canvas.delete("all")

        # Obtain data from the dedicated input frame (if it exists)
        if not hasattr(self.controller, 'input_frame'):
            self._show_message("No input frame available")
            return

        input_frame = self.controller.input_frame
        shape_name = input_frame.shape_name.get()

        # Validate shape existence via the unified registry
        if not shape_name or shape_name not in default_shape_registry.flat_shapes:
            self._show_message("Select a shape")
            return

        # Gather parameter values
        params = {}
        for pname, entry in input_frame.param_entries.items():
            try:
                params[pname] = float(entry.get().strip())
            except ValueError:
                params[pname] = 0.0

        # Diameter
        try:
            diameter = float(input_frame.dia.get())
        except (ValueError, AttributeError):
            diameter = 16.0   # sensible default

        # Draw the shape using the centralized drawing function
        try:
            draw_shape_on_canvas(self.canvas, shape_name, params, diameter)
        except Exception as e:
            # Fallback error message on canvas
            self._show_message(f"Preview error:\n{e}", fill="red")

    def _show_message(self, text: str, fill: str = "gray"):
        """Display a centred text message on the canvas."""
        w = self.canvas.winfo_width() or 350
        h = self.canvas.winfo_height() or 300
        self.canvas.delete("all")
        self.canvas.create_text(w // 2, h // 2, text=text, fill=fill,
                                font=("Arial", 10))