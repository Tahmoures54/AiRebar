# ui/welcome_dialog.py
import tkinter as tk
from tkinter import ttk
import webbrowser
import datetime
import json
import os
import sqlite3
from typing import Callable, Optional

class WelcomeDialog(tk.Toplevel):
    """
    Redesigned welcome dialog:
    - Fixed footer with main action button (changes text based on project state).
    - "Don't show again" checkbox (persisted to app_config.json).
    - No Cancel button – the footer button is the primary way to proceed.
    - If a project already exists in the database, the button shows "Continue"
      and simply closes the dialog instead of creating a new project.
    - The database is queried directly (rebar_database.db) to determine
      whether any project is present.
    - Scrolling content is only the upper part; footer always visible.
    """

    def __init__(self, master: tk.Tk, on_close: Optional[Callable] = None,
                 on_create_project: Optional[Callable] = None):
        super().__init__(master)
        self.master_app = master
        self.on_close = on_close
        self.on_create_project = on_create_project

        # Theme
        self.bg = "#ffffff"
        self.fg = "#1e293b"
        self.accent = "#2563eb"
        self.muted = "#94a3b8"

        # Window setup
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(bg=self.bg)
        self.attributes("-alpha", 0.0)

        self._drag_data = {"x": 0, "y": 0}
        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<ButtonRelease-1>", self._stop_drag)
        self.bind("<B1-Motion>", self._do_drag)
        self.bind("<Escape>", lambda e: self.close_dialog())

        # Detect if a project already exists by querying the database
        self._project_exists = self._project_exists_in_db()

        # --- Footer (fixed, always visible) ---
        self.show_again_var = tk.BooleanVar(value=True)   # True = show again (unchecked = hide)
        self.footer = tk.Frame(self, bg="#f8fafc", height=48)
        self.footer.pack(side="bottom", fill="x")
        self.footer.pack_propagate(False)

        # Left: links
        links_frame = tk.Frame(self.footer, bg="#f8fafc")
        links_frame.pack(side="left", padx=10)
        site = tk.Label(links_frame, text="www.airebar.io", font=("Segoe UI Variable", 8, "underline"),
                        fg=self.accent, bg="#f8fafc", cursor="hand2")
        site.pack(side="left", padx=(0,8))
        site.bind("<Button-1>", lambda e: webbrowser.open("https://airebar.io"))
        wa = tk.Label(links_frame, text="💬 WhatsApp", font=("Segoe UI Variable", 8, "underline"),
                      fg="#16a34a", bg="#f8fafc", cursor="hand2")
        wa.pack(side="left")
        wa.bind("<Button-1>", lambda e: webbrowser.open("https://wa.me/989160684552"))

        # Right: checkbox + action button
        actions_frame = tk.Frame(self.footer, bg="#f8fafc")
        actions_frame.pack(side="right", padx=10)

        cb = tk.Checkbutton(actions_frame, text="Don't show again",
                            variable=self.show_again_var,
                            onvalue=False, offvalue=True,   # False = checked → don't show
                            bg="#f8fafc", fg="#475569",
                            selectcolor="#f8fafc", activebackground="#f8fafc",
                            font=("Segoe UI Variable", 9))
        cb.pack(side="left", padx=(0, 12))

        # Button text changes depending on whether a project exists in DB
        btn_text = "Continue" if self._project_exists else "Let's Go →"
        btn_bg = "#16a34a" if self._project_exists else "#2563eb"
        self.go_btn = tk.Label(actions_frame, text=btn_text,
                               font=("Segoe UI Variable", 10, "bold"),
                               bg=btn_bg, fg="white", padx=20, pady=4,
                               cursor="hand2", relief="flat")
        self.go_btn.pack(side="left")
        self.go_btn.bind("<Button-1>", lambda e: self._go_action())
        # Hover effects
        hover_bg = "#15803d" if self._project_exists else "#1d4ed8"
        self.go_btn.bind("<Enter>", lambda e, b=self.go_btn, h=hover_bg: b.config(bg=h))
        self.go_btn.bind("<Leave>", lambda e, b=self.go_btn, o=btn_bg: b.config(bg=o))

        # --- Scrollable content area ---
        self.canvas = tk.Canvas(self, bg=self.bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((2, 2), window=self.scrollable_frame, anchor="nw",
                                  width=516)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=(2, 0))
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=(2, 0))

        # Mouse wheel
        self.canvas.bind("<Enter>", lambda e: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_mousewheel())

        self._build_content()
        self._center_on_parent()
        self.grab_set()
        self._closing = False
        self._fade_in()
        self.focus_set()

    # ------------------------------------------------------------------
    # Check if a project exists directly in the SQLite database
    # ------------------------------------------------------------------
    def _project_exists_in_db(self) -> bool:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'rebar_database.db')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except (sqlite3.Error, FileNotFoundError):
            return False

    def _get_main_window(self):
        if hasattr(self.master_app, 'main_window'):
            return self.master_app.main_window
        return None

    # ------------------------------------------------------------------
    # Mouse wheel scrolling
    # ------------------------------------------------------------------
    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ------------------------------------------------------------------
    # Animation & dragging
    # ------------------------------------------------------------------
    def _fade_in(self, alpha: float = 0.0):
        if self._closing or not self.winfo_exists():
            return
        if alpha < 1.0:
            alpha += 0.08
            self.attributes("-alpha", min(alpha, 1.0))
            self.after(15, lambda: self._fade_in(alpha))
        else:
            self.attributes('-topmost', False)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _stop_drag(self, event):
        self._drag_data["x"] = 0
        self._drag_data["y"] = 0

    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_data["x"]
        y = self.winfo_y() + event.y - self._drag_data["y"]
        self.geometry(f"+{x}+{y}")

    def _center_on_parent(self):
        self.update_idletasks()
        parent = self.master_app
        if parent and parent.winfo_exists():
            w = self.winfo_width()
            h = self.winfo_height()
            if w > 1 and h > 1:
                x = parent.winfo_x() + (parent.winfo_width() - w) // 2
                y = parent.winfo_y() + (parent.winfo_height() - h) // 2
                self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    # Scrollable content (top part)
    # ------------------------------------------------------------------
    def _build_content(self):
        card_w = 520
        window_h = 600

        body = self.scrollable_frame

        # Header
        header = tk.Frame(body, bg=self.bg)
        header.pack(fill="x", pady=(16, 0))

        tk.Label(header, text="AI Rebar", font=("Segoe UI Variable", 24, "bold"),
                 bg=self.bg, fg="#dc2626", anchor="center").pack()
        tk.Label(header, text="Intelligent Rebar Cutting & Inventory Management",
                 font=("Segoe UI Variable", 11), bg=self.bg, fg="#64748b", anchor="center").pack()

        ver_frame = tk.Frame(header, bg=self.bg)
        ver_frame.pack(pady=(2, 0))
        tk.Label(ver_frame, text="v7.4", font=("Segoe UI Variable", 8, "bold"),
                 bg="#E0F7FA", fg="#006064", padx=8, pady=2).pack()

        ttk.Separator(body, orient="horizontal").pack(fill="x", padx=30, pady=12)

        # Greeting
        content = tk.Frame(body, bg=self.bg)
        content.pack(fill="both", expand=True, padx=28, pady=(8, 4))

        greeting = self._get_greeting()
        tk.Label(content, text=greeting, font=("Segoe UI Variable", 13, "bold"),
                 bg=self.bg, fg=self.fg, anchor="w").pack(fill="x", pady=(0, 2))
        tk.Label(content, text="Let's set up your workspace and start saving material.",
                 font=("Segoe UI Variable", 10, "italic"),
                 bg=self.bg, fg=self.accent, anchor="w").pack(fill="x", pady=(0, 10))

        # Quick Start Steps
        tk.Label(content, text="⚡ Quick Start Guide", font=("Segoe UI Variable", 11, "bold"),
                 bg=self.bg, fg=self.fg, anchor="w").pack(fill="x", pady=(0, 8))

        steps = [
            {"step": "1", "title": "Create a Project", "desc": "Set up a project for your site or client.",
             "enabled": True},
            {"step": "2", "title": "Update Stock / Inventory", "desc": "Define available bars and lengths on site.",
             "enabled": False},
            {"step": "3", "title": "Add Rebar Positions", "desc": "Insert bars with shape codes & quantities.",
             "enabled": False},
        ]

        for s in steps:
            step_frame = tk.Frame(content, bg=self.bg)
            step_frame.pack(fill="x", pady=4)

            icon_frame = tk.Frame(step_frame, bg=self.bg, width=36, height=36)
            icon_frame.pack(side="left", padx=(0, 12))
            icon_frame.pack_propagate(False)
            if s["enabled"]:
                tk.Label(icon_frame, text=s["step"], font=("Arial", 14, "bold"),
                         bg=self.bg, fg=self.fg).place(relx=0.5, rely=0.5, anchor="center")
            else:
                tk.Label(icon_frame, text="🔒", font=("Arial", 12),
                         bg=self.bg).place(relx=0.5, rely=0.5, anchor="center")

            text_frame = tk.Frame(step_frame, bg=self.bg)
            text_frame.pack(side="left", fill="x", expand=True)
            tk.Label(text_frame, text=s["title"], font=("Segoe UI Variable", 11, "bold"),
                     bg=self.bg, fg=self.fg if s["enabled"] else self.muted, anchor="w").pack(anchor="w")
            tk.Label(text_frame, text=s["desc"], font=("Segoe UI Variable", 9),
                     bg=self.bg, fg="#64748b" if s["enabled"] else self.muted, anchor="w").pack(anchor="w")

        ttk.Separator(content, orient="horizontal").pack(fill="x", pady=12)

        # Why AI Rebar?
        tk.Label(content, text="🚀 Why AI Rebar?", font=("Segoe UI Variable", 11, "bold"),
                 bg=self.bg, fg="#0D7377", anchor="w").pack(fill="x", pady=(0, 6))

        benefits = [
            ("📉", "Reduce waste up to 30%", "Smart MILP algorithm finds the optimal cutting plan every time."),
            ("⏱️", "Save hours of work", "Generate a complete BBS report in seconds, not hours."),
            ("💰", "Lower material costs", "Reuse scraps automatically and never over‑order stock."),
        ]
        for icon, title, desc in benefits:
            row = tk.Frame(content, bg=self.bg)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=icon, font=("Segoe UI Variable", 14), bg=self.bg).pack(side="left", padx=(0, 8))
            detail = tk.Frame(row, bg=self.bg)
            detail.pack(side="left", fill="x", expand=True)
            tk.Label(detail, text=title, font=("Segoe UI Variable", 10, "bold"),
                     bg=self.bg, fg=self.fg, anchor="w").pack(anchor="w")
            tk.Label(detail, text=desc, font=("Segoe UI Variable", 8),
                     bg=self.bg, fg="#64748b", anchor="w", wraplength=350, justify="left").pack(anchor="w")

        ttk.Separator(content, orient="horizontal").pack(fill="x", pady=10)

        # Key Features
        tk.Label(content, text="♻️  Minimise Waste – Maximise Efficiency",
                 font=("Segoe UI Variable", 11, "bold"),
                 bg=self.bg, fg="#16a34a", anchor="w").pack(fill="x", pady=(0, 6))

        features = [
            "📉  MILP optimization – minimal waste",
            "🔁  Smart scrap reuse",
            "📦  Real‑time inventory",
            "📋  One‑click Listofer (BBS)",
            "📊  Reports: HTML, Excel, PDF, BVBS",
            "🌍  Multi‑standard shapes (BS, ACI, Eurocode…)",
        ]
        for feat in features:
            tk.Label(content, text=feat, font=("Segoe UI Variable", 10),
                     bg=self.bg, fg="#334155", anchor="w", padx=8).pack(fill="x", pady=1)

        self.geometry(f"{card_w}x{window_h}")
        self.resizable(False, False)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _go_action(self):
        """Called when the footer button is clicked."""
        self._save_show_preference()
        if self._project_exists:
            # Just close – user already has a project in the database
            self.close_dialog()
        else:
            # Close dialog first, then trigger project creation
            self.close_dialog()
            if self.on_create_project:
                self.on_create_project()

    def _save_show_preference(self):
        """Persist the 'show welcome dialog' flag in app_config.json."""
        show_welcome = self.show_again_var.get()  # True = show again, False = don't show
        config_path = os.path.join(os.path.dirname(__file__), '..', 'app_config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}
        config['show_welcome'] = show_welcome
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def close_dialog(self):
        self._closing = True
        self._save_show_preference()
        self._unbind_mousewheel()
        self.destroy()
        if self.on_close:
            self.on_close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_greeting(self) -> str:
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return "Good Morning! 🌅"
        elif 12 <= hour < 17:
            return "Good Afternoon! ☀️"
        elif 17 <= hour < 22:
            return "Good Evening! 🌆"
        else:
            return "Hello Night Owl! 🌙"