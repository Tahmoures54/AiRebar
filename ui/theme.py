"""
ThemeManager – Enterprise-grade theme orchestrator.
Handles dynamic style updates and persistence.
"""

import json
import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, Optional

from config import THEMES, AppTheme, APP_CONFIG_FILE

class ThemeManager:
    """Manages global application theming and style persistence."""

    _PREF_FILE = os.path.join(os.path.dirname(APP_CONFIG_FILE), "theme_config.json")

    def __init__(self, app: Any) -> None:
        self.app = app
        self.style = ttk.Style()
        self._current_theme = "turquoise"
        self._colors = THEMES.get(self._current_theme, {}).copy()
        
        self._load_saved_theme()

    def _load_saved_theme(self) -> None:
        """Loads theme preference from disk if available."""
        if os.path.exists(self._PREF_FILE):
            try:
                with open(self._PREF_FILE, 'r') as f:
                    pref = json.load(f)
                    self.apply_theme(pref.get("theme", "turquoise"), save=False)
            except Exception as e:
                print(f"Failed to load theme config: {e}")

    def apply_theme(self, theme_name: str, save: bool = True) -> None:
        """Applies a theme and updates the application state."""
        if theme_name not in THEMES:
            return

        self._current_theme = theme_name
        self._colors = THEMES[theme_name].copy()
        
        # Update App State
        if hasattr(self.app, 'state'):
            self.app.state.theme = AppTheme(theme_name)

        # Persist if requested
        if save:
            with open(self._PREF_FILE, 'w') as f:
                json.dump({"theme": theme_name}, f)

        # Trigger global style updates
        self._update_global_styles(theme_name)
        self._apply_menu_style()

    def _update_global_styles(self, theme_name: str) -> None:
        """Configures the ttk.Style engine (The standard way)."""
        colors = self._colors
        
        # Map class-specific configurations here
        # This replaces the recursive widget loop with a centralized engine
        self.style.configure(".", background=colors.get("bg", "#ffffff"), foreground=colors.get("fg", "#000000"))
        self.style.configure(f"{theme_name}.TFrame", background=colors.get("bg", "#ffffff"))
        self.style.configure(f"{theme_name}.TButton", font=("Segoe UI", 10))

    def _apply_menu_style(self) -> None:
        """Applies styling to non-ttk widgets (Menus/Frames)."""
        menu_bar = getattr(self.app, 'menu_bar', None)
        if not menu_bar:
            return

        bg = self._colors.get('menu_bg', self._colors.get('accent', '#009688'))
        fg = self._colors.get('menu_fg', '#ffffff')
        active_bg = self._colors.get('highlight', '#00796b')

        # Configure menu bar container
        menu_bar.configure(bg=bg)

        # Style standard tk.Menu objects
        for attr in ('_file_menu', '_tools_menu', '_help_menu'):
            menu = getattr(menu_bar, attr, None)
            if isinstance(menu, tk.Menu):
                menu.configure(
                    bg=bg, fg=fg,
                    activebackground=active_bg,
                    activeforeground='#ffffff',
                    relief='flat',
                    borderwidth=0
                )

    def get_color(self, key: str, default: Any = None) -> Any:
        """Safe access to current theme colors."""
        return self._colors.get(key, default)