# main.py
"""
Main Entry Point – AI Rebar Pro
Startup sequence:
- configure logging
- init DB (singleton manager)
- show splash
- run security checks (stub)
- build main window
"""

import os
import logging
import tkinter as tk
from tkinter import messagebox

from config import LOG_FILE, LOG_LEVEL, should_show_welcome
from db.database import DatabaseManager
from ui.theme import ThemeManager
from ui.splash_screen import SplashScreen
from ui.main_window import MainWindow
from app_state import AppState


def _configure_logging():
    try:
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        level = getattr(logging, str(LOG_LEVEL).upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(LOG_FILE, encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
    except Exception:
        # اگر logging fail شد، برنامه نباید کرش کند
        logging.basicConfig(level=logging.INFO)


logger = logging.getLogger("AI_Rebar.App")


class RebarBBSApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.state = AppState()

        # Singleton DB manager (thread-safe)
        self.db = DatabaseManager()
        self.db.setup_database()

        self.theme_manager = ThemeManager(self)

        self._initialize_application()

    def _initialize_application(self):
        self.withdraw()

        self._apply_global_settings()

        splash = SplashScreen(self, max_wait_ms=2000)
        self.wait_window(splash)

        if not self._run_security_checks():
            self.destroy()
            return

        # Main UI
        self.main_window = MainWindow(self, self)
        self.main_window.pack(fill="both", expand=True)

        # Apply theme (use string key)
        try:
            self.theme_manager.apply_theme("turquoise", save=False)
        except Exception as e:
            logger.warning(f"Theme apply failed: {e}")

        self.deiconify()
        self._show_welcome_if_needed()

    def _apply_global_settings(self):
        self.title("AI Rebar Pro")
        self.geometry("1280x800")
        self.report_callback_exception = self._global_error_handler

    def _run_security_checks(self) -> bool:
        # جای لایسنس/پسورد شما
        return True

    def _global_error_handler(self, exc_type, exc_value, exc_traceback):
        logger.critical("Uncaught Exception", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror("System Error", "A critical error occurred. Check logs.")

    def _show_welcome_if_needed(self):
        if should_show_welcome():
            from ui.welcome_dialog import WelcomeDialog
            WelcomeDialog(self, on_close=lambda: None)

    @property
    def menu_bar(self):
        return getattr(self.main_window, "menu_bar", None)


if __name__ == "__main__":
    _configure_logging()
    try:
        app = RebarBBSApp()
        app.mainloop()
    except Exception as e:
        logger.error(f"Failed to start app: {e}", exc_info=True)
        raise