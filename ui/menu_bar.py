# ui/menu_bar.py
"""
Modern MenuBar Implementation
- Dynamic handler lookup (MainWindow then App)
- Safer ttk.Menubutton usage
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import sys

from config import MENU_LABELS
from utils.logger import setup_logger

logger = setup_logger("AI_Rebar.MenuBar")


class MenuBar(tk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.main_window = parent  # MainWindow instance
        self.menus = {}

        self.structure = {
            "File": [
                ("new_project", "🆕 New Project", "N"),
                ("open_project", "📂 Open Project", "O"),
                ("show_project_manager", "🗂️ Project Manager", None),
                "sep",
                ("export_excel", "📊 Export Excel", None),
                ("export_pdf", "📄 Export PDF", None),
                ("export_html_report", "🖨️ Print Listofer", None),
                ("export_bvbs", "📤 Export BVBS", None),
                ("import_bvbs", "📥 Import BVBS", None),
                "sep",
                ("open_settings", "⚙️ Settings", None),
                "sep",
                ("quit", "🚪 Exit", "Q"),
            ],
            "Tools": [
                ("show_lap_splice", "📏 Lap Splice Calculator", None),
                ("show_cutting_plan_all", "✂️ Cutting Plan (All)", None),
                ("show_cutting_plan_selected", "✂️ Cutting Plan (Selected)", None),
                "sep",
                ("show_scrap_manager", "♻️ Scrap Manager", None),
                ("show_stock_manager", "📦 Stock Manager", None),
                "sep",
                ("open_custom_shape_designer", "✏️ Custom Shape Designer", None),
                "sep",
                ("open_system_doctor", "🩺 System Doctor", None),
            ],
            "Help": [
                ("show_welcome_dialog", "👋 Welcome", None),
                "sep",
                ("show_user_guide", "📖 User Guide", "F1"),
                ("show_about", "ℹ️ About", None),
                ("open_license_dialog", "🔑 License Management", None),
                ("contact_developer", "💬 Contact Developer", None),
            ],
        }

        self._setup_ui()

    def _setup_ui(self):
        for name, items in self.structure.items():
            menu = tk.Menu(self, tearoff=False)
            self.menus[name] = menu

            for item in items:
                if item == "sep":
                    menu.add_separator()
                else:
                    cmd, label, accel = item
                    menu.add_command(
                        label=MENU_LABELS.get(cmd, label),
                        command=self._get_handler(cmd),
                        accelerator=f"{self._get_accel()}+{accel}" if accel and len(accel) == 1 else (accel or ""),
                    )

            btn = ttk.Menubutton(self, text=f"  {name}  ")
            btn["menu"] = menu
            btn.pack(side="left", padx=1, pady=1)

    def _get_handler(self, method_name: str):
        def handler():
            # special case
            if method_name == "quit":
                try:
                    self.app.destroy()
                except Exception:
                    try:
                        self.app.quit()
                    except Exception:
                        pass
                return

            func = getattr(self.main_window, method_name, None)
            if callable(func):
                func()
                return

            func = getattr(self.app, method_name, None)
            if callable(func):
                func()
                return

            logger.warning(f"Menu action '{method_name}' not found (MainWindow/App).")
        return handler

    def _get_accel(self):
        return "Cmd" if sys.platform == "darwin" else "Ctrl"

    def update_state(self, project_is_open: bool):
        # optional: enable/disable menu items based on project state
        pass