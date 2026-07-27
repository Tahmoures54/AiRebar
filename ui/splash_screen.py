# ui/splash_screen.py
"""
Professional startup splash screen that stays until the app signals readiness.
Uses the application's turquoise colour palette and displays the correct version.
"""

import tkinter as tk
from tkinter import ttk
try:
    from config import VERSION
except ImportError:
    VERSION = "7.4"   # fallback if config doesn't export VERSION

_TITLE_FONT = ("Segoe UI", 28, "bold")
_SUBTITLE_FONT = ("Segoe UI", 10)
_VERSION_FONT = ("Segoe UI", 8)
_LOADING_FONT = ("Segoe UI", 10)
_FOOTER_FONT = ("Segoe UI", 7)


class SplashScreen(tk.Toplevel):
    """Splash window shown during application startup."""

    def __init__(self, master, max_wait_ms: int = 10000):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#E0F7FA")   # turquoise background

        # Flag to avoid double close
        self._closed = False

        # ── Dimensions & centring ────────────────────────────────
        w, h = 420, 240
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Subtle border for depth
        border_frame = tk.Frame(self, bg="#B2EBF2", bd=0)
        border_frame.pack(fill="both", expand=True, padx=3, pady=3)
        inner = tk.Frame(border_frame, bg="#E0F7FA")
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # ── Logo (simplified stirrup) ────────────────────────────
        logo_canvas = tk.Canvas(inner, width=80, height=50,
                                bg="#E0F7FA", highlightthickness=0)
        logo_canvas.pack(pady=(25, 0))
        logo_canvas.create_line(15, 35, 65, 35, fill="#006064", width=3)
        logo_canvas.create_line(15, 35, 15, 5, fill="#006064", width=3)
        logo_canvas.create_line(65, 35, 65, 5, fill="#006064", width=3)
        logo_canvas.create_line(15, 5, 27, 5, fill="#006064", width=3)
        logo_canvas.create_line(65, 5, 53, 5, fill="#006064", width=3)

        # ── App name & tagline ───────────────────────────────────
        tk.Label(inner, text="AI Rebar", font=_TITLE_FONT,
                 fg="#006064", bg="#E0F7FA").pack(pady=(2, 0))
        tk.Label(inner, text="Intelligent Bar Bending Schedule",
                 font=_SUBTITLE_FONT, fg="#004D40", bg="#E0F7FA").pack()

        # ── Version ─────────────────────────────────────────────
        tk.Label(inner, text=f"Version {VERSION}",
                 font=_VERSION_FONT, fg="#0097A7", bg="#E0F7FA").pack(pady=(2, 0))

        # ── Animated loading text ────────────────────────────────
        self.loading_text = tk.Label(
            inner, text="Loading   ",
            font=_LOADING_FONT, fg="#004D40", bg="#E0F7FA"
        )
        self.loading_text.pack(pady=(8, 0))
        self._dots = 0
        self._animate_loading()

        # ── Progress bar ─────────────────────────────────────────
        self.progress = ttk.Progressbar(inner, mode='indeterminate', length=320,
                                        style="turquoise.Horizontal.TProgressbar")
        self.progress.pack(pady=10)
        self.progress.start(12)

        # ── Footer ───────────────────────────────────────────────
        tk.Label(inner, text="© 2026 AI Rebar. All rights reserved.",
                 font=_FOOTER_FONT, fg="#0097A7", bg="#E0F7FA").pack(side="bottom", pady=5)

        # ── Auto‑close fallback ─────────────────────────────────
        self._max_wait = max_wait_ms
        self._auto_close_id = self.after(max_wait_ms, self.close)

    def _animate_loading(self):
        if self._closed:
            return
        self._dots = (self._dots + 1) % 4
        dots_str = "." * self._dots
        self.loading_text.config(text=f"Loading{dots_str}")
        self.after(500, self._animate_loading)

    def close(self):
        """Call this from the main app when initialisation is complete."""
        if self._closed:
            return
        self._closed = True
        if self._auto_close_id is not None:
            self.after_cancel(self._auto_close_id)
        self.progress.stop()
        self.destroy()