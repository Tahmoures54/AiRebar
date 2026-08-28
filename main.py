# main.py
"""
Main Entry Point – RebarAgent
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

from config import LOG_FILE, LOG_LEVEL, should_show_welcome, APP_VERSION, APP_NAME
from utils.i18n import load_language_from_config, apply_to_config_globals, t
from db.database import DatabaseManager
from ui.theme import ThemeManager
from ui.splash_screen import SplashScreen
from ui.main_window import MainWindow
from app_state import AppState


def _configure_logging():
    try:
        load_language_from_config()
        apply_to_config_globals()
    except Exception:
        pass

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
        logging.basicConfig(level=logging.INFO)


logger = logging.getLogger("RebarAgent.App")


class RebarAgentApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.state = AppState()

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

        self.main_window = MainWindow(self, self)
        self.main_window.pack(fill="both", expand=True)

        try:
            self.theme_manager.apply_theme("turquoise", save=False)
        except Exception as e:
            logger.warning(f"Theme apply failed: {e}")

        self.deiconify()
        self._show_welcome_if_needed()

    def _apply_global_settings(self):
        self.title(t("app_title"))
        self.geometry("1280x800")
        self.minsize(1024, 700)
        self.report_callback_exception = self._global_error_handler

    def _run_security_checks(self) -> bool:
        return True

    def _global_error_handler(self, exc_type, exc_value, exc_traceback):
        logger.critical("Uncaught Exception", exc_info=(exc_type, exp_value, exp_traceback))
        messagebox.showerror("System Error", "A critical error occurred. Check logs.")

    def _show_welcome_if_needed(self):
        if should_show_welcome():
            from ui.welcome_dialog import WelcomeDialog
            WelcomeDialog(self, on_close=lambda: None)

    @property
    def menu_bar(self):
        return getattr(self.main_window, "menu_bar", None)


def main():
    _configure_logging()
    try:
        app = RebarAgentApp()
        app.mainloop()
    except Exception as e:
        logger.error(f"Failed to start app: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
