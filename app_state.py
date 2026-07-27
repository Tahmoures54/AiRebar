# app_state.py
"""
Central application state container.
Keeps track of the current project, theme, database path, etc.
"""

from dataclasses import dataclass, field
from typing import Optional
import getpass
import datetime

from config import DEFAULT_THEME, DATABASE_FILE, get_default_project_info


@dataclass
class AppState:
    current_project_id: Optional[int] = None
    current_project_name: str = ""
    current_client_name: str = ""

    # store theme as string key (matches config.THEMES keys)
    theme: str = DEFAULT_THEME

    db_path: str = DATABASE_FILE

    current_user: str = field(default_factory=lambda: getpass.getuser())
    is_modified: bool = False
    last_modified: Optional[str] = None

    def mark_modified(self):
        self.is_modified = True
        self.last_modified = datetime.datetime.now().isoformat()

    def mark_saved(self):
        self.is_modified = False

    def reset_project(self):
        self.current_project_id = None
        self.current_project_name = ""
        self.current_client_name = ""
        self.is_modified = False
        self.last_modified = None

    def get_effective_project_name(self) -> str:
        if self.current_project_id is not None and self.current_project_name:
            return self.current_project_name
        default_info = get_default_project_info()
        return default_info.get("project_name", "")

    def get_effective_client_name(self) -> str:
        if self.current_project_id is not None and self.current_client_name:
            return self.current_client_name
        default_info = get_default_project_info()
        return default_info.get("client", "")

    def get_effective_company_name(self) -> str:
        default_info = get_default_project_info()
        return default_info.get("company_name", "")