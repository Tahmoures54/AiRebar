# ui/settings_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import shutil
import os
import sqlite3

from config import APP_CONFIG_FILE
from utils.password_manager import (
    is_password_set, set_password, remove_password,
    change_password, check_password
)
from utils.license import get_license_info, format_license_status


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app                     # This is the RebarBBSApp instance
        self.title("⚙️ Settings")
        self.geometry("580x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Only save initial values for welcome and db path (theme is fixed)
        self._initial_welcome = None
        self._initial_db_path = app.state.db_path
        self._pending_welcome = None
        self._pending_db_path = None

        # Project info defaults
        self._initial_project_info = {}
        self._pending_project_info = {}

        self._create_widgets()
        self._load_values()

    def _create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ----- General tab (no theme selection) -----
        self.gen_frame = ttk.Frame(notebook)
        notebook.add(self.gen_frame, text="📋 General")

        # Welcome checkbox
        self.welcome_var = tk.BooleanVar()
        ttk.Checkbutton(self.gen_frame, text="Show Welcome dialog on startup",
                        variable=self.welcome_var).grid(
            row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # Database path
        ttk.Label(self.gen_frame, text="Database Path:").grid(row=1, column=0, padx=10, pady=(10,5), sticky="w")
        self.db_path_var = tk.StringVar()
        db_entry = ttk.Entry(self.gen_frame, textvariable=self.db_path_var, width=40, state="readonly")
        db_entry.grid(row=1, column=1, padx=10, pady=(10,5), sticky="we")
        ttk.Button(self.gen_frame, text="Browse...", command=self._browse_db).grid(
            row=1, column=2, padx=5, pady=(10,5))

        # ----- Project Info tab (NEW) -----
        self.proj_frame = ttk.Frame(notebook)
        notebook.add(self.proj_frame, text="🏗️ Project Info")

        ttk.Label(self.proj_frame, text="Default Project Details",
                  font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(15,5), sticky="w")

        ttk.Label(self.proj_frame, text="Project Name:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.project_name_var = tk.StringVar()
        ttk.Entry(self.proj_frame, textvariable=self.project_name_var, width=35).grid(
            row=1, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(self.proj_frame, text="Company Name:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.company_name_var = tk.StringVar()
        ttk.Entry(self.proj_frame, textvariable=self.company_name_var, width=35).grid(
            row=2, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(self.proj_frame, text="Client:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.client_var = tk.StringVar()
        ttk.Entry(self.proj_frame, textvariable=self.client_var, width=35).grid(
            row=3, column=1, padx=10, pady=5, sticky="w")

        ttk.Label(self.proj_frame, text="These values are used as defaults when no specific project is selected.",
                  wraplength=350, foreground="gray").grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # ----- Security tab -----
        self.sec_frame = ttk.Frame(notebook)
        notebook.add(self.sec_frame, text="🔐 Security")

        self.pwd_status_label = ttk.Label(self.sec_frame, text="")
        self.pwd_status_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(15,10), sticky="w")

        self.pwd_action_frame = ttk.LabelFrame(self.sec_frame, text="Set / Change Password")
        self.pwd_action_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(self.pwd_action_frame, text="Old Password:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.old_pwd_var = tk.StringVar()
        self.old_pwd_entry = ttk.Entry(self.pwd_action_frame, textvariable=self.old_pwd_var, show="*", width=20)
        self.old_pwd_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.pwd_action_frame, text="New Password:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.new_pwd_var = tk.StringVar()
        ttk.Entry(self.pwd_action_frame, textvariable=self.new_pwd_var, show="*", width=20).grid(
            row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(self.pwd_action_frame, text="Confirm New:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.confirm_pwd_var = tk.StringVar()
        ttk.Entry(self.pwd_action_frame, textvariable=self.confirm_pwd_var, show="*", width=20).grid(
            row=2, column=1, padx=5, pady=5, sticky="w")

        btn_frame = ttk.Frame(self.pwd_action_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Set / Change", command=self._set_password).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Remove Password", command=self._remove_password).pack(side="left", padx=5)

        # ----- Backup/Restore tab -----
        self.bkp_frame = ttk.Frame(notebook)
        notebook.add(self.bkp_frame, text="💾 Backup/Restore")

        ttk.Label(self.bkp_frame, text="Backup your database to a safe location or restore a previous backup.",
                  wraplength=400).pack(padx=10, pady=10)

        ttk.Button(self.bkp_frame, text="📤 Create Backup", command=self._create_backup).pack(pady=5)
        ttk.Button(self.bkp_frame, text="📥 Restore Backup", command=self._restore_backup).pack(pady=5)

        # ----- License tab -----
        self.lic_frame = ttk.Frame(notebook)
        notebook.add(self.lic_frame, text="🔑 License")

        self.license_info_label = ttk.Label(self.lic_frame, text="", font=("Arial", 10),
                                            wraplength=450, justify="left")
        self.license_info_label.pack(padx=10, pady=10, fill="both", expand=True)
        ttk.Button(self.lic_frame, text="🔑 Manage License", command=self._open_license_dialog).pack(pady=(0,10))

        # ---- Bottom buttons: Apply / Cancel / Close ----
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=(0,10))
        ttk.Button(bottom_frame, text="Apply", command=self._apply_changes).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=self._cancel_changes).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="Close", command=self.destroy).pack(side="right", padx=5)

    # ------------------------------------------------------------------
    # Load initial values
    # ------------------------------------------------------------------
    def _load_values(self):
        try:
            with open(APP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            show = not config.get('hide_welcome', False)
        except Exception:
            show = True
        self._initial_welcome = show
        self.welcome_var.set(show)
        self._pending_welcome = show

        self.db_path_var.set(self._initial_db_path)
        self._pending_db_path = self._initial_db_path

        # Load project info defaults
        try:
            with open(APP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            proj_info = config.get('project_info', {})
        except Exception:
            proj_info = {}
        self._initial_project_info = proj_info
        self._pending_project_info = proj_info.copy()
        self.project_name_var.set(proj_info.get('project_name', ''))
        self.company_name_var.set(proj_info.get('company_name', ''))
        self.client_var.set(proj_info.get('client', ''))

        self._update_password_status()
        self._update_license_display()

    # ------------------------------------------------------------------
    # Apply / Cancel
    # ------------------------------------------------------------------
    def _apply_changes(self):
        # Apply welcome preference
        if self._pending_welcome != self._initial_welcome:
            config = {}
            try:
                with open(APP_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            config['hide_welcome'] = not self._pending_welcome
            try:
                with open(APP_CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                self._initial_welcome = self._pending_welcome
            except Exception as e:
                messagebox.showerror("Error", f"Could not save preference: {e}")

        # Apply database path change
        if self._pending_db_path != self._initial_db_path:
            if not self._test_db_connection(self._pending_db_path):
                return
            config = {}
            try:
                with open(APP_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            config['database_path'] = self._pending_db_path
            try:
                with open(APP_CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                messagebox.showerror("Error", f"Could not save config: {e}")
                return
            self.app.state.db_path = self._pending_db_path
            self._initial_db_path = self._pending_db_path
            self.db_path_var.set(self._pending_db_path)
            if hasattr(self.app, 'status_bar'):
                self.app.status_bar.update_db_path(self._pending_db_path)
            try:
                self.app.reconnect_database()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reconnect database: {e}")

        # Apply project info
        new_proj_info = {
            'project_name': self.project_name_var.get().strip(),
            'company_name': self.company_name_var.get().strip(),
            'client': self.client_var.get().strip(),
        }
        if new_proj_info != self._initial_project_info:
            config = {}
            try:
                with open(APP_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            config['project_info'] = new_proj_info
            try:
                with open(APP_CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                self._initial_project_info = new_proj_info
                self._pending_project_info = new_proj_info
            except Exception as e:
                messagebox.showerror("Error", f"Could not save project info: {e}")
                return

        messagebox.showinfo("Settings", "Settings applied successfully.")

    def _cancel_changes(self):
        self.welcome_var.set(self._initial_welcome)
        self._pending_welcome = self._initial_welcome
        self.db_path_var.set(self._initial_db_path)
        self._pending_db_path = self._initial_db_path

        # Revert project info
        self.project_name_var.set(self._initial_project_info.get('project_name', ''))
        self.company_name_var.set(self._initial_project_info.get('company_name', ''))
        self.client_var.set(self._initial_project_info.get('client', ''))
        self._pending_project_info = self._initial_project_info.copy()

        messagebox.showinfo("Cancelled", "Changes have been reverted.")

    # ------------------------------------------------------------------
    # Database browsing with connection test
    # ------------------------------------------------------------------
    def _browse_db(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Database File",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not path:
            return
        if not self._test_db_connection(path):
            return
        self.db_path_var.set(path)
        self._pending_db_path = path

    def _test_db_connection(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Error", "Selected file does not exist.")
            return False
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
            if not cursor.fetchone():
                messagebox.showerror("Invalid Database", "The file is not a valid AiRebar database.")
                conn.close()
                return False
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not open database:\n{e}")
            return False
        return True

    # ------------------------------------------------------------------
    # Backup / Restore
    # ------------------------------------------------------------------
    def _create_backup(self):
        src = self.app.state.db_path
        if not os.path.exists(src):
            messagebox.showerror("Error", "Current database file not found.")
            return
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Save Backup As",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")]
        )
        if not dest:
            return
        try:
            shutil.copy2(src, dest)
            messagebox.showinfo("Backup", f"Backup saved to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {e}")

    def _restore_backup(self):
        src = filedialog.askopenfilename(
            parent=self,
            title="Select Backup File",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not src:
            return
        if not self._test_db_connection(src):
            return
        if not messagebox.askyesno("Confirm Restore",
                                   "This will replace the current database with the backup. "
                                   "All unsaved changes will be lost. Continue?"):
            return
        try:
            dest = self.app.state.db_path
            self.app.db.close()
            shutil.copy2(src, dest)
            self.app.reconnect_database()
            messagebox.showinfo("Restore", "Database restored successfully.")
            if hasattr(self.app, 'main_window'):
                self.app.main_window.update_project_display()
        except Exception as e:
            messagebox.showerror("Error", f"Restore failed: {e}")

    # ------------------------------------------------------------------
    # Password management
    # ------------------------------------------------------------------
    def _update_password_status(self):
        if is_password_set():
            self.pwd_status_label.config(text="🔒 Password is set.", foreground="green")
            self.old_pwd_entry.config(state="normal")
        else:
            self.pwd_status_label.config(text="🔓 No password set.", foreground="red")
            self.old_pwd_entry.config(state="disabled")
        self.old_pwd_var.set("")
        self.new_pwd_var.set("")
        self.confirm_pwd_var.set("")

    def _set_password(self):
        old = self.old_pwd_var.get()
        new = self.new_pwd_var.get()
        confirm = self.confirm_pwd_var.get()
        if new != confirm:
            messagebox.showerror("Error", "New passwords do not match.")
            return
        if new and len(new) < 4:
            messagebox.showwarning("Weak Password", "Password should be at least 4 characters.")
            return
        if is_password_set():
            if not old:
                messagebox.showerror("Error", "Old password is required.")
                return
            if not check_password(old):
                messagebox.showerror("Error", "Old password is incorrect.")
                return
            success = change_password(old, new)
        else:
            set_password(new)
            success = True
        if success:
            messagebox.showinfo("Success", "Password updated.")
            self._update_password_status()
        else:
            messagebox.showerror("Error", "Failed to change password.")

    def _remove_password(self):
        if not is_password_set():
            messagebox.showinfo("Info", "No password is currently set.")
            return
        if not messagebox.askyesno("Confirm", "Remove password protection?"):
            return
        remove_password()
        messagebox.showinfo("Success", "Password removed.")
        self._update_password_status()

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------
    def _update_license_display(self):
        info = get_license_info(self.app.db)
        lic_type = info.get('type', 'unknown')
        rem_days = info.get('remaining_days', None)
        if lic_type == 'unlimited':
            text = "✅ Full License – permanent"
        elif lic_type in ('3month', '6month', '1year'):
            text = f"⏳ {lic_type.capitalize()} license"
            if rem_days is not None:
                text += f" – {rem_days} day(s) left"
        elif lic_type == 'trial':
            text = f"🆓 Trial license"
            if rem_days is not None:
                text += f" – {rem_days} day(s) left"
            records = info.get('records_used', 0)
            max_rec = info.get('max_records', 0)
            if max_rec:
                text += f" | {records}/{max_rec} records used"
        else:
            text = "❓ Unknown license type"
        self.license_info_label.config(text=text)

    def _open_license_dialog(self):
        if hasattr(self.app, 'main_window') and self.app.main_window:
            self.app.main_window.open_license_dialog()
            self._update_license_display()
        else:
            messagebox.showerror("Error", "Main window not available.")