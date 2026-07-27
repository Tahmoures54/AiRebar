# generate_license_gui.py
"""
AI Rebar – License Key Generator (GUI)
Admin tool to generate activation keys for customers.
Uses the same secret key as the main application (utils/license.py).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import hmac
import hashlib
import base64
import datetime

# ------------------------------------------------------------
# Must match SECRET_KEY in utils/license.py
# ------------------------------------------------------------
SECRET_KEY = b'AiRebar2025!SecretKeyForLicenseSigning'

# License types and their durations (days), unlimited is None
LICENSE_TYPES = {
    "3-Month (90 days)": 90,
    "6-Month (180 days)": 180,
    "1-Year (365 days)": 365,
    "Unlimited (permanent)": None,
}


def generate_key(machine_id: str, license_type: str, expiry_date: str, issued_date: str) -> str:
    """
    Create a signed activation key.
    """
    msg = f"{machine_id}|{license_type}|{expiry_date}|{issued_date}".encode()
    signature = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()
    raw = f"{machine_id}|{license_type}|{expiry_date}|{issued_date}|{signature}"
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    return encoded


class LicenseGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Rebar – License Key Generator")
        self.root.geometry("600x480")
        self.root.resizable(False, False)
        self.root.configure(padx=20, pady=20)

        # Styling
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Generate.TButton", font=("Segoe UI", 11, "bold"))

        self._build_ui()

    def _build_ui(self):
        # Title
        ttk.Label(self.root, text="AI Rebar License Key Generator",
                  style="Title.TLabel").pack(pady=(0, 20))

        # Machine ID
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", pady=5)
        ttk.Label(frame, text="Machine ID:", style="Heading.TLabel").pack(side="left", padx=(0, 10))
        self.machine_id_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.machine_id_var, width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(frame, text="Paste", command=self._paste_machine_id).pack(side="left", padx=5)

        # License type
        frame2 = ttk.Frame(self.root)
        frame2.pack(fill="x", pady=10)
        ttk.Label(frame2, text="License Type:", style="Heading.TLabel").pack(side="left", padx=(0, 10))
        self.license_type_var = tk.StringVar()
        self.license_combo = ttk.Combobox(frame2, textvariable=self.license_type_var,
                                          values=list(LICENSE_TYPES.keys()),
                                          state="readonly", width=35)
        self.license_combo.pack(side="left")
        self.license_combo.current(0)  # default to 3-Month
        self.license_combo.bind("<<ComboboxSelected>>", self._on_license_type_changed)

        # Expiry date
        frame3 = ttk.Frame(self.root)
        frame3.pack(fill="x", pady=5)
        ttk.Label(frame3, text="Expiry Date:", style="Heading.TLabel").pack(side="left", padx=(0, 10))
        self.expiry_var = tk.StringVar()
        self.expiry_entry = ttk.Entry(frame3, textvariable=self.expiry_var, width=20)
        self.expiry_entry.pack(side="left", padx=(0, 5))
        ttk.Label(frame3, text="(YYYY-MM-DD, empty = auto)").pack(side="left")
        # Auto-fill based on selected license type
        self._on_license_type_changed()

        # Generate button
        ttk.Button(self.root, text="Generate Activation Key",
                   style="Generate.TButton",
                   command=self._generate).pack(pady=15)

        # Output area
        ttk.Label(self.root, text="Activation Key:", style="Heading.TLabel").pack(anchor="w", pady=(10, 5))
        self.output_text = tk.Text(self.root, height=4, width=70, font=("Consolas", 11), wrap="word")
        self.output_text.pack(fill="x", pady=(0, 10))
        self.output_text.config(state="disabled")

        # Copy button
        ttk.Button(self.root, text="📋 Copy to Clipboard", command=self._copy_to_clipboard).pack()

        # Footer
        ttk.Label(self.root, text="Send this key to the customer. They must activate it in the License dialog.",
                  font=("Segoe UI", 8, "italic"), foreground="gray").pack(side="bottom", pady=(10, 0))

    def _paste_machine_id(self):
        try:
            clipboard = self.root.clipboard_get()
            self.machine_id_var.set(clipboard.strip())
        except tk.TclError:
            pass

    def _on_license_type_changed(self, event=None):
        # Auto-calculate expiry based on license type
        ltype = self.license_type_var.get()
        if ltype not in LICENSE_TYPES:
            return
        days = LICENSE_TYPES[ltype]
        if days:
            expiry = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        else:
            expiry = "2099-12-31"  # far future for unlimited
        self.expiry_var.set(expiry)

    def _generate(self):
        machine_id = self.machine_id_var.get().strip()
        if not machine_id:
            messagebox.showerror("Error", "Please enter a Machine ID.")
            return

        ltype_display = self.license_type_var.get()
        if ltype_display not in LICENSE_TYPES:
            messagebox.showerror("Error", "Please select a valid license type.")
            return

        # Extract short code for the license (e.g., "3month", "unlimited")
        ltype_short = ltype_display.lower()
        if "unlimited" in ltype_short:
            ltype_code = "unlimited"
        elif "3-month" in ltype_short or "90" in ltype_short:
            ltype_code = "3month"
        elif "6-month" in ltype_short or "180" in ltype_short:
            ltype_code = "6month"
        elif "1-year" in ltype_short or "365" in ltype_short:
            ltype_code = "1year"
        else:
            ltype_code = ltype_short.split()[0]

        expiry_str = self.expiry_var.get().strip()
        # Validate expiry date if provided
        if expiry_str:
            try:
                datetime.date.fromisoformat(expiry_str)
            except ValueError:
                messagebox.showerror("Error", "Invalid expiry date format. Use YYYY-MM-DD.")
                return
        else:
            # Fallback to auto
            self._on_license_type_changed()
            expiry_str = self.expiry_var.get()

        issued_str = datetime.date.today().isoformat()
        try:
            key = generate_key(machine_id, ltype_code, expiry_str, issued_str)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate key:\n{e}")
            return

        # Display key in text widget
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", key)
        self.output_text.config(state="disabled")

        # Success message
        messagebox.showinfo("Success", "Activation key generated successfully!")

    def _copy_to_clipboard(self):
        key = self.output_text.get("1.0", "end").strip()
        if key:
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            messagebox.showinfo("Copied", "Key copied to clipboard.")
        else:
            messagebox.showwarning("Warning", "No key to copy. Generate one first.")


def main():
    root = tk.Tk()
    app = LicenseGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()