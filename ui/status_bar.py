# ui/status_bar.py
"""
Status bar widget – shows database path (with blinking LED), project info,
weight summary (with warning colours), temporary messages,
and a context menu for the DB path.
"""

import os
import subprocess
import platform
import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """Bottom bar displaying DB path (blinking LED), project name, weight summary,
    and temporary messages."""

    def __init__(self, parent, app, **kwargs):
        self.app = app
        # اصلاح: theme یک رشته است و .value نیاز ندارد
        super().__init__(parent, style=f"{app.state.theme}.TFrame", **kwargs)

        # Theme colours
        try:
            colors = app.theme_manager.current_colors
            self._bg = colors.get("bg", "white")
            self._fg = colors.get("fg", "black")
            self._accent = colors.get("accent", "#28a745")
        except AttributeError:
            self._bg = app._get_theme_bg() if hasattr(app, "_get_theme_bg") else "white"
            self._fg = "black"
            self._accent = "#28a745"

        self._blink_job_id = None
        self._blink_on = True
        self._led_color = self._accent
        self._msg_after_id = None

        # Weight warning limits (set via set_weight_limit)
        self._weight_warning = None   # kg, if total > this -> orange
        self._weight_critical = None  # kg, if total > this -> red

        self._build()
        self._update_led()
        self.start_blinking()

    def set_weight_limit(self, warning_kg: float = None, critical_kg: float = None):
        """Set thresholds that cause the summary text to change colour.
        If total_weight > warning_kg -> orange, > critical_kg -> red.
        Pass None to disable that level.
        """
        self._weight_warning = warning_kg
        self._weight_critical = critical_kg
        # Refresh summary if currently shown
        if self.app.state.current_project_id:
            self.update_summary()

    def _build(self):
        # ---- Left: DB LED + path ----
        left_frame = tk.Frame(self, bg=self._bg)
        left_frame.pack(side="left", padx=(10, 0), fill="y")

        # LED canvas
        self._led_canvas = tk.Canvas(
            left_frame, width=14, height=14,
            bg=self._bg, highlightthickness=0
        )
        self._led_canvas.pack(side="left", padx=(0, 5))
        self._led = self._led_canvas.create_oval(2, 2, 12, 12,
                                                 fill=self._led_color, outline="")

        # DB path label (with right‑click menu)
        self.db_label = tk.Label(
            left_frame,
            text=self.app.state.db_path if hasattr(self.app, 'state') else "",
            font=("Arial", 8),
            fg="#636e72", bg=self._bg,
            cursor="hand2"   # indicate interactivity
        )
        self.db_label.pack(side="left")
        self._attach_db_context_menu()

        # ---- Right section ----
        # Temporary message label (far right)
        self.msg_label = tk.Label(
            self,
            text="",
            font=("Arial", 10, "bold"),
            fg=self._fg, bg=self._bg
        )
        self.msg_label.pack(side="right", padx=(0, 20))

        # Project info label
        self.project_label = tk.Label(
            self,
            text="No project loaded",
            font=("Arial", 9),
            fg=self._fg, bg=self._bg
        )
        self.project_label.pack(side="right", padx=(0, 10))

        # Weight summary label
        self.summary_label = tk.Label(
            self,
            text="",
            font=("Arial", 9, "bold"),
            fg=self._fg, bg=self._bg
        )
        self.summary_label.pack(side="right", padx=(0, 10))

    # ------------------------------------------------------------------
    # Context menu for the DB path
    # ------------------------------------------------------------------
    def _attach_db_context_menu(self):
        menu = tk.Menu(self.db_label, tearoff=0)
        menu.add_command(label="📂 Open File Location", command=self._open_db_location)
        menu.add_command(label="📋 Copy Path", command=self._copy_db_path)
        self.db_label.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        # Also allow right‑click on the label's parent frame area (optional)

    def _open_db_location(self):
        path = self.app.state.db_path
        if not path or not os.path.exists(path):
            return
        folder = os.path.dirname(path)
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder])
            else:  # Linux
                subprocess.run(["xdg-open", folder])
        except Exception:
            pass

    def _copy_db_path(self):
        path = self.app.state.db_path
        if path:
            self.clipboard_clear()
            self.clipboard_append(path)
            self.update_message("📋 Database path copied to clipboard", 2000)

    # ------------------------------------------------------------------
    # Public update methods
    # ------------------------------------------------------------------
    def update_db_path(self, path=None):
        if path:
            self.app.state.db_path = path
        self.db_label.config(text=self.app.state.db_path)
        self.stop_blinking()
        self._update_led()
        self.start_blinking()

    def _update_led(self):
        db_path = self.app.state.db_path if hasattr(self.app, 'state') else ""
        exists = os.path.exists(db_path) if db_path else False
        self._led_color = self._accent if exists else "red"
        self._led_canvas.itemconfig(self._led, fill=self._led_color)

    def update_project_info(self):
        if self.app.state.current_project_id:
            text = (
                f"Project: {self.app.state.current_project_name}"
                f" | Client: {self.app.state.current_client_name or 'N/A'}"
            )
        else:
            text = "No project loaded. Create or open a project to begin."
        self.project_label.config(text=text)

    def update_summary(self, item_count=0, total_weight=0.0):
        if not self.app.state.current_project_id:
            self.summary_label.config(text="")
            return

        text = f"Total items: {item_count}  |  Total weight: {total_weight:.2f} kg"

        # Determine colour based on weight thresholds
        color = self._fg   # default
        if self._weight_critical is not None and total_weight > self._weight_critical:
            color = "#c0392b"   # red
        elif self._weight_warning is not None and total_weight > self._weight_warning:
            color = "#e67e22"   # orange

        self.summary_label.config(text=text, fg=color)

    def update_message(self, text, duration=3000):
        """Display a temporary message (e.g., 'Record saved') and clear it after a delay."""
        self.msg_label.config(text=text)
        if self._msg_after_id is not None:
            self.after_cancel(self._msg_after_id)
        self._msg_after_id = self.after(duration, lambda: self.msg_label.config(text=""))

    # ------------------------------------------------------------------
    # Blinking logic
    # ------------------------------------------------------------------
    def start_blinking(self):
        if self._blink_job_id is not None:
            self.stop_blinking()
        self._blink_on = True
        self._do_blink()

    def stop_blinking(self):
        if self._blink_job_id is not None:
            self.after_cancel(self._blink_job_id)
            self._blink_job_id = None
        self._led_canvas.itemconfig(self._led, fill=self._led_color)

    def _do_blink(self):
        if self._blink_on:
            fill = self._led_color
        else:
            fill = self._bg
        self._led_canvas.itemconfig(self._led, fill=fill)
        self._blink_on = not self._blink_on
        self._blink_job_id = self.after(800, self._do_blink)

    def destroy(self):
        self.stop_blinking()
        if self._msg_after_id is not None:
            self.after_cancel(self._msg_after_id)
        super().destroy()