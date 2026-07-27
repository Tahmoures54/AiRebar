# ui/license_dialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from config import THEMES, AppTheme
from utils.license import get_license_info, get_machine_id, activate_license, format_license_status


class LicenseDialog(tk.Toplevel):
    def __init__(self, master, db, callback=None):
        super().__init__(master)
        self.master_app = master
        self.db = db
        self.callback = callback

        # --- theme colours (fallback to Turquoise if state not available) ---
        if hasattr(master, 'state'):
            theme = master.state.theme
        else:
            theme = AppTheme.TURQUOISE
        colors = THEMES.get(theme, THEMES[AppTheme.TURQUOISE])
        self.bg = colors["bg"]
        self.fg = colors["fg"]
        self.accent = colors["accent"]
        self.button_style = f"{theme.value}.TButton"

        self.title("🔓 AiRebar Pro - License")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(bg=self.bg)
        self.geometry("580x680")
        self._center_on_screen(580, 680)

        # License info
        self.lic_info = get_license_info(self.db)
        self.lic_type = self.lic_info.get('type', 'trial')
        self._build_ui()

    def _center_on_screen(self, w, h):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # ----- header -----
        header = tk.Frame(self, bg=self.accent, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🔓  Unlock AiRebar Pro",
                 font=("Segoe UI", 16, "bold"), fg="white", bg=self.accent).pack(pady=12)

        main = tk.Frame(self, bg=self.bg, padx=30, pady=20)
        main.pack(fill="both", expand=True)

        # ----- status -----
        status_text = format_license_status(self.db)
        trial_days = self.lic_info.get('remaining_days', None)
        # FIXED: removed pady from Frame, now applied in pack
        status_frame = tk.Frame(main, bg=self.bg)
        status_frame.pack(fill="x", pady=5)
        tk.Label(status_frame, text="📊 Status:", font=("Arial", 10, "bold"),
                 fg=self.fg, bg=self.bg).pack(side="left")
        status_value = tk.Label(status_frame, text=f" {status_text}",
                                font=("Arial", 10), fg=self.fg, bg=self.bg)
        status_value.pack(side="left", padx=5)
        if trial_days is not None and self.lic_type != 'unlimited':
            try:
                trial_days = int(trial_days)
            except (ValueError, TypeError):
                trial_days = 0
            if trial_days > 0:
                days_color = "red" if trial_days <= 3 else "orange"
                tk.Label(status_frame, text=f"({trial_days} days left)",
                         font=("Arial", 10, "bold"), fg=days_color, bg=self.bg).pack(side="left")

        # If fully licensed
        if self.lic_type == 'unlimited':
            tk.Label(main, text="✅ You are using the full version.\nThank you for your support!",
                     font=("Arial", 11), fg="green", bg=self.bg, justify="center").pack(pady=20)
            ttk.Button(main, text="Close", command=self.destroy, style=self.button_style).pack(pady=10)
            return

        # ----- benefits (Why upgrade) -----
        benefits_frame = tk.Frame(main, bg="#f0f4fa" if self.bg == "white" else "#2a2d34",
                                  relief="ridge", bd=0, padx=15, pady=12)
        benefits_frame.pack(fill="x", pady=(10,5))
        tk.Label(benefits_frame, text="⭐ Why Upgrade to Pro?",
                 font=("Arial", 12, "bold"), fg=self.accent,
                 bg=benefits_frame["bg"]).pack(anchor="w")
        benefits = [
            "✅ Unlimited projects & exports",
            "✅ Remove all trial limitations",
            "✅ Priority technical support",
            "✅ Free updates for 1 year",
            "✅ Access to custom shape designer",
        ]
        for b in benefits:
            tk.Label(benefits_frame, text=b, font=("Arial", 10),
                     fg=self.fg, bg=benefits_frame["bg"], anchor="w", justify="left").pack(anchor="w", pady=1)

        # ----- heartfelt support message -----
        # FIXED: removed pady from Frame, now applied in pack
        support_msg = tk.Frame(main, bg=self.bg)
        support_msg.pack(fill="x", pady=5)
        tk.Label(support_msg, text="💛 Your license is our only source of income to cover heavy development "
                                   "costs and team salaries. Every purchase directly supports the future of AiRebar.",
                 font=("Arial", 9, "italic"), fg="gray", bg=self.bg, wraplength=500, justify="left").pack(anchor="w")

        # ----- machine ID (needed for activation) -----
        # FIXED: removed pady from Frame, now applied in pack
        mid_label = tk.Frame(main, bg=self.bg)
        mid_label.pack(fill="x", pady=(15,2))
        tk.Label(mid_label, text="📋 Your Machine ID:",
                 font=("Arial", 10, "bold"), fg=self.fg, bg=self.bg).pack(anchor="w")

        mid_frame = tk.Frame(main, bg=self.bg)
        mid_frame.pack(fill="x")
        mid = get_machine_id()
        mid_entry = ttk.Entry(mid_frame, width=38, state="readonly")
        mid_entry.pack(side="left", padx=(0,5))
        mid_entry.configure(state="normal")
        mid_entry.insert(0, mid)
        mid_entry.configure(state="readonly")

        def copy_mid():
            self.clipboard_clear()
            self.clipboard_append(mid)
            messagebox.showinfo("Copied", "Machine ID copied to clipboard.", parent=self)
        ttk.Button(mid_frame, text="📋 Copy", command=copy_mid, style=self.button_style).pack(side="left")

        # ----- purchase options (two ways) -----
        # FIXED: removed pady from Frame, now applied in pack
        purchase_header = tk.Frame(main, bg=self.bg)
        purchase_header.pack(fill="x", pady=(15,5))
        tk.Label(purchase_header, text="🛍️  Choose how to purchase:",
                 font=("Arial", 11, "bold"), fg=self.fg, bg=self.bg).pack(anchor="w")

        btn_frame = tk.Frame(main, bg=self.bg)
        btn_frame.pack(fill="x", pady=5)

        buy_website = tk.Button(
            btn_frame,
            text="🌐  Buy Online (Website)",
            font=("Arial", 11, "bold"),
            bg="#FFA500", fg="white",
            activebackground="#e59400", activeforeground="white",
            relief="flat", bd=0, padx=18, pady=10,
            cursor="hand2",
            command=lambda: webbrowser.open("https://airebar.io/license")
        )
        buy_website.pack(side="left", padx=(0, 15))

        whatsapp_btn = tk.Button(
            btn_frame,
            text="💬  Order via WhatsApp",
            font=("Arial", 11, "bold"),
            bg="#25D366", fg="white",
            activebackground="#1ebe57", activeforeground="white",
            relief="flat", bd=0, padx=18, pady=10,
            cursor="hand2",
            command=lambda: webbrowser.open("https://wa.me/989160684552")
        )
        whatsapp_btn.pack(side="left")

        guide_frame = tk.Frame(main, bg=self.bg)
        guide_frame.pack(fill="x", pady=5)
        tk.Label(guide_frame, text="📌 After payment, send your Machine ID (above) via WhatsApp or enter it on the "
                                   "website. You will receive your activation key instantly.",
                 font=("Arial", 9), fg="gray", bg=self.bg, wraplength=500, justify="left").pack(anchor="w")

        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=15)

        activate_header = tk.Frame(main, bg=self.bg)
        activate_header.pack(fill="x", pady=(0,10))
        tk.Label(activate_header, text="🔑 Already purchased? Activate here:",
                 font=("Arial", 10, "bold"), fg=self.fg, bg=self.bg).pack(anchor="w")

        key_frame = tk.Frame(main, bg=self.bg)
        key_frame.pack(fill="x", pady=(0,5))
        tk.Label(key_frame, text="Activation Key:", font=("Arial", 9),
                 fg=self.fg, bg=self.bg).pack(side="left")
        self.key_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.key_var, width=32).pack(side="left", padx=5)
        ttk.Button(key_frame, text="📋 Paste", command=self._paste_code,
                   style=self.button_style).pack(side="left")

        btn_row = tk.Frame(main, bg=self.bg)
        btn_row.pack(fill="x", pady=(10,5))
        ttk.Button(btn_row, text="✅ Activate Now", command=self._activate,
                   style=self.button_style).pack(side="left", padx=(0,15))
        ttk.Button(btn_row, text="Close", command=self.destroy,
                   style=self.button_style).pack(side="left")

        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=15)
        tk.Label(main, text="Need help? Contact us:",
                 font=("Arial", 9, "bold"), fg=self.fg, bg=self.bg, anchor="w").pack(anchor="w")
        tk.Label(main, text="🌐 www.airebar.io   |   💬 WhatsApp: +98 916 068 4552",
                 font=("Arial", 9), fg="gray", bg=self.bg, anchor="w").pack(anchor="w")

    def _paste_code(self):
        try:
            clipboard_text = self.clipboard_get()
            self.key_var.set(clipboard_text.strip())
        except tk.TclError:
            messagebox.showwarning("Clipboard Empty", "No text found on clipboard.", parent=self)

    def _activate(self):
        code = self.key_var.get().strip()
        if not code:
            messagebox.showwarning("Missing Code", "Please paste your activation code first.", parent=self)
            return
        try:
            success, message = activate_license(code, self.db)
        except ImportError:
            messagebox.showinfo("Info", "Direct activation not available.\nPlease use the advanced method.", parent=self)
            return
        if success:
            messagebox.showinfo("Success", "License activated successfully! Restart may be required.", parent=self)
            if self.callback:
                self.callback()
            self.destroy()
        else:
            messagebox.showerror("Activation Failed", message, parent=self)