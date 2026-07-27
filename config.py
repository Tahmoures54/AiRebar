# config.py
# Global configuration constants for the AI Rebar application.

import os
import json
from enum import Enum

# ---------- Enums ----------
class RebarGrade(str, Enum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    S240 = "S240"
    S400 = "S400"
    B500B = "B500B"

class AppTheme(str, Enum):
    TURQUOISE = "turquoise"

# ---------- Paths ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "rebar_database.db")
DB_PATH = DATABASE_FILE
APP_CONFIG_FILE = os.path.join(BASE_DIR, "app_config.json")
LOG_FILE = os.path.join(BASE_DIR, "logs", "app.log")

HIDDEN_LICENSE_DIR = (
    os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "AI Rebar")
    if os.name == "nt" else
    os.path.join(os.path.expanduser("~"), ".config", "airebar")
)
HIDDEN_LICENSE_FILE = os.path.join(HIDDEN_LICENSE_DIR, "license.dat")

# ---------- Database ----------
BACKUP_SUFFIX = ".backup"
AUTO_SAVE_INTERVAL_MS = 60_000

# ---------- Trial ----------
TRIAL_PERIOD_DAYS = 7
MAX_TRIAL_RECORDS = 50

# ---------- Material defaults ----------
STANDARD_STOCK_LENGTHS_M = [6, 12]
STANDARD_BRANCH_LENGTHS = STANDARD_STOCK_LENGTHS_M
MM_TO_M_FACTOR = 1000.0

WEIGHT_COEFFICIENT = 0.006165
STANDARD_DIAMETERS = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 32, 36, 40]

REBAR_GRADES = [g.value for g in RebarGrade]
DEFAULT_REBAR_GRADE = RebarGrade.A3.value

ELEMENT_TYPES = [
    "Foundation", "Footing", "Column", "Beam", "Slab",
    "Wall", "Stairs", "Stirrup", "Tie", "Link", "Other"
]

MAX_STOCK_LENGTH_MM = 18_000
LOW_STOCK_THRESHOLD = 5

QUICK_ADD_DEFAULTS = {
    "diameter": 12,
    "length": 6000,
    "quantity": 10,
    "shape_code": "00",
    "grade": DEFAULT_REBAR_GRADE
}
QUICK_ADD_SHAPE_CODES = ["00", "11", "12", "13", "21", "22", "23", "31", "32", "33"]
SUPPORTED_SHAPE_CODES = QUICK_ADD_SHAPE_CODES

SPLASH_DURATION_MS = 2500

# ---------- UI Theme ----------
# IMPORTANT: use string keys because UI calls apply_theme("turquoise")
THEMES = {
    AppTheme.TURQUOISE.value: {
        "bg": "#E0F7FA",
        "fg": "#006064",
        "tree_bg": "#FFFFFF",
        "tree_fg": "#006064",
        "entry_bg": "#FFFFFF",
        "button_bg": "#B2EBF2",
        "button_fg": "#004D40",
        "label_frame_bg": "#E0F7FA",
        "canvas_line": "#006064",
        "accent": "#00BCD4",
        "highlight": "#0097A7",
        "menu_bg": "#00BCD4",
        "menu_fg": "#FFFFFF",
    }
}

DEFAULT_THEME = AppTheme.TURQUOISE.value

# ---------- Logging ----------
LOG_LEVEL = "INFO"

# ---------- Export settings ----------
EXPORT_DATE_FORMAT = "%Y-%m-%d"
EXPORT_FILE_PREFIX = "BBS_Report"

# ---------- Company info ----------
COMPANY_INFO = {
    "name": "Sample Construction Co.",
    "logo": "",
    "engineer": "Engineering Department",
    "website": "www.sample-construction.com",
    "phone": "+1 (555) 123-4567",
}

# ---------- UI String Constants ----------
FILTER_SHOW_ALL = "-- Show All --"

MENU_LABELS = {
    "file": "File",
    "new_project": "New Project...",
    "open_project": "Open Project...",
    "project_manager": "Project Manager...",
    "export_excel": "Export Excel...",
    "export_pdf": "Export PDF...",
    "print_listofer": "📋 Print Listofer...",
    "export_bvbs": "🗂️ Export BVBS (BIM)...",
    "import_bvbs": "📥 Import BVBS (BIM)...",
    "settings": "Settings...",
    "exit": "Exit",
    "tools": "Tools",
    "lap_splice": "🔧 Lap Splice Calculator...",
    "cutting_plan_all": "🧠 Cutting Plan (All)",
    "cutting_plan_selected": "🧠 Cutting Plan (Selected)",
    "scrap_manager": "🧩 Smart Scrap Bank...",
    "stock_manager": "🧱 Stock Manager...",
    "custom_shape_designer": "✏️ Custom Shape Designer...",
    "help": "Help",
    "welcome": "📖 Welcome...",
    "user_guide": "📖 User Guide",
    "about": "About",
    "license_management": "🔑 License Management...",
    "contact_developer": "Contact Developer",
}

TOOLBAR_BUTTONS = {
    "new_rebar": "➕ New Rebar",
    "edit": "✏️ Edit",
    "delete": "🗑️ Delete",
    "print_listofer": "📋 Print Listofer",
    "cutting_plan": "🧠 Cutting Plan",
    "lap_splice": "🔧 Lap Splice Calc",
    "scrap_manager": "🧩 Smart Scrap Bank",
    "stock_manager": "🧱 Stock",
    "projects": "📁 Projects",
}

ERROR_MSGS = {
    "no_project": "No active project. Create a new one?",
    "wrong_password": "Incorrect. {attempts} attempt(s) left.",
    "access_denied": "The application will close.",
    "delete_confirm": "Delete selected rebar(s)?",
    "no_selection": "No row selected.",
}

FONT_DEFAULTS = {
    "tagline": ("Arial", 11, "italic"),
    "status": ("Arial", 10, "italic"),
    "summary": ("Arial", 10),
    "db_path": ("Arial", 9),
}

def should_show_welcome():
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return True
    return not cfg.get("hide_welcome", False)

def get_default_project_info():
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("project_info", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}