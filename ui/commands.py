# ui/commands.py
"""Command Pattern for AI Rebar – encapsulates every UI action.
Synchronised with the current MainWindow interface (v7.4)."""

from abc import ABC, abstractmethod


class Command(ABC):
    def __init__(self, app):
        self.app = app

    @abstractmethod
    def execute(self): ...


class NewProjectCommand(Command):
    """Trigger the creation of a new project (auto‑create if needed)."""
    def execute(self):
        self.app.new_project()


class OpenProjectCommand(Command):
    """Open the project manager (redirects to settings if needed)."""
    def execute(self):
        self.app.open_project()


class SettingsCommand(Command):
    """Open the Settings window."""
    def execute(self):
        self.app.open_settings()


class NewRebarCommand(Command):
    """Open the rebar input dialog."""
    def execute(self):
        self.app.open_input_dialog()


class EditRebarCommand(Command):
    """Edit the currently selected rebar."""
    def execute(self):
        self.app.edit_selected_bar()


class DeleteRebarCommand(Command):
    """Delete the currently selected rebar(s)."""
    def execute(self):
        self.app.delete_selected_bar()


class ExportExcelCommand(Command):
    """Export BBS to Excel."""
    def execute(self):
        self.app.export_excel()


class ExportPDFCommand(Command):
    """Export BBS to PDF."""
    def execute(self):
        self.app.export_pdf()


class ExportHTMLCommand(Command):
    """Generate and open an HTML report (BBS)."""
    def execute(self):
        self.app.export_html_report()


class BVBSExportCommand(Command):
    """Export project data to BVBS file."""
    def execute(self):
        self.app.export_bvbs()


class BVBSImportCommand(Command):
    """Import rebar data from a BVBS file."""
    def execute(self):
        self.app.import_bvbs()


class CuttingPlanAllCommand(Command):
    """Show cutting plan for all or filtered listofers."""
    def execute(self):
        self.app.show_cutting_plan_all()


class CuttingPlanSelectedCommand(Command):
    """Show cutting plan only for selected rows."""
    def execute(self):
        self.app.show_cutting_plan_selected()


class ScrapManagerCommand(Command):
    """Open the Smart Scrap Bank manager."""
    def execute(self):
        self.app.show_scrap_manager()


class StockManagerCommand(Command):
    """Open the Stock manager."""
    def execute(self):
        self.app.show_stock_manager()


class LapSpliceCommand(Command):
    """Open the lap splice calculator."""
    def execute(self):
        self.app.show_lap_splice()


class LicenseCommand(Command):
    """Open the license management dialog."""
    def execute(self):
        self.app.open_license_dialog()


class CustomShapeDesignerCommand(Command):
    """Open the custom shape designer."""
    def execute(self):
        self.app.open_custom_shape_designer()


class WelcomeDialogCommand(Command):
    """Show the welcome / splash dialog."""
    def execute(self):
        self.app.show_welcome_dialog()


class UserGuideCommand(Command):
    """Open the user guide window."""
    def execute(self):
        self.app.show_user_guide()


class AboutCommand(Command):
    """Show the About dialog."""
    def execute(self):
        self.app.show_about()


class ContactDeveloperCommand(Command):
    """Open WhatsApp contact link."""
    def execute(self):
        self.app.contact_developer()


def register_commands(app):
    """Return a dictionary mapping command names to Command instances."""
    return {
        "new_project":      NewProjectCommand(app),
        "open_project":     OpenProjectCommand(app),
        "settings":         SettingsCommand(app),
        "new_rebar":        NewRebarCommand(app),
        "edit_rebar":       EditRebarCommand(app),
        "delete_rebar":     DeleteRebarCommand(app),
        "export_excel":     ExportExcelCommand(app),
        "export_pdf":       ExportPDFCommand(app),
        "html_report":      ExportHTMLCommand(app),
        "export_bvbs":      BVBSExportCommand(app),
        "import_bvbs":      BVBSImportCommand(app),
        "cutting_all":      CuttingPlanAllCommand(app),
        "cutting_sel":      CuttingPlanSelectedCommand(app),
        "scrap":            ScrapManagerCommand(app),
        "stock":            StockManagerCommand(app),
        "lap_splice":       LapSpliceCommand(app),
        "license":          LicenseCommand(app),
        "custom_shape":     CustomShapeDesignerCommand(app),
        "welcome":          WelcomeDialogCommand(app),
        "user_guide":       UserGuideCommand(app),
        "about":            AboutCommand(app),
        "contact_dev":      ContactDeveloperCommand(app),
    }