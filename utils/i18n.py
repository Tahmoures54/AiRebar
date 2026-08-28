# utils/i18n.py
"""Lightweight i18n for RebarAgent. Default UI language English; Persian (fa) supported."""

from __future__ import annotations

import json
import os
from typing import Dict

from config import APP_CONFIG_FILE

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "app_title": "RebarAgent – Intelligent Rebar Assistant",
        "app_tagline": "Bar bending schedule & cutting optimization — clear, accurate, less waste",
        "menu.file": "File", "menu.tools": "Tools", "menu.help": "Help",
        "menu.new_project": "New Project...", "menu.open_project": "Open Project...",
        "menu.project_manager": "Project Manager...", "menu.export_excel": "Export Excel...",
        "menu.export_pdf": "Export PDF...", "menu.print_listofer": "Print Listofer...",
        "menu.export_bvbs": "Export BVBS (BIM)...", "menu.import_bvbs": "Import BVBS (BIM)...",
        "menu.settings": "Settings...", "menu.exit": "Exit",
        "menu.lap_splice": "Lap Splice Calculator...", "menu.cutting_plan_all": "Cutting Plan (All)",
        "menu.cutting_plan_selected": "Cutting Plan (Selected)", "menu.scrap_manager": "Scrap Bank...",
        "menu.stock_manager": "Stock Manager...", "menu.custom_shape_designer": "Custom Shape Designer...",
        "menu.agent_insights": "Agent Insights...", "menu.welcome": "Welcome...",
        "menu.user_guide": "User Guide", "menu.about": "About",
        "menu.license_management": "License Management...", "menu.contact_developer": "Contact Developer",
        "menu.system_doctor": "System Doctor...", "menu.project_dashboard": "Project Dashboard...",
        "menu.backup_project": "Backup Project...", "menu.import_backup": "Restore Backup...",
        "menu.import_excel": "Import from Excel...", "menu.load_sample_project": "Load Sample Project",
        "menu.download_excel_template": "Download Excel Template...", "menu.recent_projects": "Recent Projects",
        "tb.new_rebar": "New Pos", "tb.edit": "Edit", "tb.delete": "Delete",
        "tb.print_listofer": "Print Listofer", "tb.cutting_plan": "Cutting Plan",
        "tb.agent_insights": "Insights", "tb.lap_splice": "Lap Splice",
        "tb.scrap_manager": "Scrap Bank", "tb.stock_manager": "Stock", "tb.projects": "Projects",
        "filter.show_all": "-- Show All --", "btn.close": "Close", "btn.cancel": "Cancel",
        "btn.save": "Save", "btn.create": "Create", "btn.open": "Open",
        "btn.delete": "Delete", "btn.rename": "Rename", "btn.refresh": "Refresh",
        "err.no_project": "No active project. Create or open one to continue.",
        "err.no_selection": "Please select a row first.",
        "err.delete_confirm": "Delete the selected rebar(s)? This cannot be undone.",
        "err.wrong_password": "Incorrect password. {attempts} attempt(s) left.",
        "err.access_denied": "Access denied. The application will close.",
        "err.generic": "Something went wrong. Check the log for details.",
        "pm.title": "Project Manager",
        "pm.subtitle": "Open a project or create a new one — takes under a minute.",
        "pm.new": "New Project", "pm.empty": "No projects yet. Create your first project to get started.",
        "pm.created": "Project «{name}» created and activated.",
        "pm.opened": "Project «{name}» is now active.",
        "pm.delete_confirm": "Delete project «{name}» and ALL its data?\n\nListofers, rebars, scraps and stock will be removed.\nThis cannot be undone.",
        "welcome.title": "Welcome to RebarAgent",
        "welcome.headline": "From schedule to cutting plan — with less waste",
        "welcome.body": "Three simple steps:\n  1) Create or open a project\n  2) Add positions (New Pos)\n  3) Run Cutting Plan — review waste, then Confirm\n\nYou do not need every feature on day one. Start small; the rest waits when you need it.",
        "welcome.continue": "Continue", "welcome.create_project": "Create Project", "welcome.hide": "Don't show this again",
        "insights.title": "Agent Insights", "insights.analyzing": "Analyzing project…",
        "insights.done": "Analysis complete",
        "insights.empty": "Project is empty. Add rebars with «New Pos» to get recommendations.",
        "status.ready": "Ready", "status.no_project": "No project selected",
        "settings.language": "Language",
        "settings.language_hint": "UI language (restart may be needed for some windows)",
        "settings.theme": "Theme", "settings.general": "General",
        "about.body": "RebarAgent\n\nIntelligent Bar Bending Schedule & Cutting Optimization\nBuilt for detailers and site teams who need accuracy without complexity.",
        "input.add_title": "Add Rebar", "input.edit_title": "Edit Rebar", "input.general": "General Information",
        "input.listofer_no": "Listofer No:", "input.listofer_desc": "Listofer Description:",
        "input.position": "Position (Mark):", "input.diameter": "Diameter (mm):",
        "input.element_type": "Element Type:", "input.location": "Location/Zone:",
        "input.standard": "Standard:", "input.grade": "Grade (Type):",
        "input.shape_dims": "Shape & Dimensions", "input.shape_type": "Shape Type:",
        "input.custom_designer": "Custom Designer", "input.dimensions_mm": "Dimensions (mm)",
        "input.quantity": "Quantity:", "input.add_another": "Add Another",
        "input.new": "New", "input.auto": "Auto", "input.save": "Save",
        "input.no_project": "No active project. Open or create a project first.",
        "scrap.title": "Smart Scrap Bank", "scrap.diameter": "Diameter:", "scrap.grade": "Grade:",
        "scrap.add": "Add Scrap", "scrap.edit": "Edit", "scrap.assign_bbs": "Assign to BBS",
        "scrap.mark_used": "Mark as Used", "scrap.delete": "Delete",
        "scrap.total_available": "Total Available Length: {mm:.1f} mm",
        "scrap.select_edit": "Select a scrap to edit.", "scrap.none_selected": "No scrap selected.",
        "scrap.confirm_used": "Mark selected scrap(s) as used?",
        "scrap.confirm_delete": "Delete selected scrap(s) permanently?",
        "scrap.select_assign": "Select a scrap to assign.", "scrap.one_only": "Please select only one scrap for assignment.",
        "scrap.already_used": "This scrap is already marked as used. Assign anyway?",
        "scrap.not_found": "Scrap not found.", "scrap.assign_title": "Assign Scrap to Rebar",
        "scrap.assign_hint": "Select a rebar item to assign this scrap to:",
        "scrap.select_rebar": "Select a rebar item.", "scrap.assigned_ok": "Scrap #{sid} assigned to Rebar #{rid}.",
        "scrap.dia_mm": "Diameter (mm):", "scrap.len_mm": "Length (mm):",
        "scrap.listofer_opt": "Listofer No (opt):", "scrap.invalid": "Invalid Input",
        "stock.title": "Stock Manager", "stock.qty": "Quantity:", "stock.project_filter": "Project Filter:",
        "stock.no_selection": "Select a stock item first.", "stock.confirm_delete": "Delete selected stock item?",
        "stock.saved": "Stock report saved to {path}",
        "cut.title": "Optimized Cutting Plan", "cut.busy": "Optimization is already in progress.",
        "cut.cancelled": "Optimization cancelled by user.", "cut.export": "Export",
        "cut.reoptimize": "Re-optimize", "cut.confirm_plan": "Confirm Plan",
        "cut.force_reopt": "Force Re-optimize", "cut.locked": "Plan confirmed – locked",
        "cut.optimizing": "Optimizing cutting plan…", "cut.please_wait": "Please wait…", "cut.cancel": "Cancel",
        "common.error": "Error", "common.info": "Info", "common.confirm": "Confirm",
        "common.success": "Success", "common.warning": "Warning", "common.no_selection": "No Selection",
    },
    "fa": {
        "app_title": "RebarAgent – دستیار هوشمند آرماتور",
        "app_tagline": "لیستوفر و بهینه‌سازی برش — دقیق، شفاف، با پرت کمتر",
        "menu.file": "پرونده", "menu.tools": "ابزارها", "menu.help": "راهنما",
        "menu.new_project": "پروژه جدید...", "menu.open_project": "باز کردن پروژه...",
        "menu.project_manager": "مدیریت پروژه‌ها...", "menu.export_excel": "خروجی اکسل...",
        "menu.export_pdf": "خروجی PDF...", "menu.print_listofer": "چاپ لیستوفر...",
        "menu.export_bvbs": "خروجی BVBS (BIM)...", "menu.import_bvbs": "ورود BVBS (BIM)...",
        "menu.settings": "تنظیمات...", "menu.exit": "خروج",
        "menu.lap_splice": "محاسبه اورلب...", "menu.cutting_plan_all": "برنامه برش (همه)",
        "menu.cutting_plan_selected": "برنامه برش (انتخاب‌شده)", "menu.scrap_manager": "بانک ضایعات...",
        "menu.stock_manager": "مدیریت موجودی...", "menu.custom_shape_designer": "طراح شکل سفارشی...",
        "menu.agent_insights": "تحلیل هوشمند...", "menu.welcome": "خوش‌آمد...",
        "menu.user_guide": "راهنمای کاربر", "menu.about": "درباره",
        "menu.license_management": "مدیریت لایسنس...", "menu.contact_developer": "تماس با سازنده",
        "menu.system_doctor": "عیب‌یاب سیستم...", "menu.project_dashboard": "داشبورد پروژه...",
        "menu.backup_project": "پشتیبان پروژه...", "menu.import_backup": "بازیابی پشتیبان...",
        "menu.import_excel": "ورود از اکسل...", "menu.load_sample_project": "بارگذاری پروژه نمونه",
        "menu.download_excel_template": "دانلود قالب اکسل...", "menu.recent_projects": "پروژه‌های اخیر",
        "tb.new_rebar": "پوز جدید", "tb.edit": "ویرایش", "tb.delete": "حذف",
        "tb.print_listofer": "چاپ لیستوفر", "tb.cutting_plan": "برنامه برش",
        "tb.agent_insights": "تحلیل", "tb.lap_splice": "اورلب",
        "tb.scrap_manager": "ضایعات", "tb.stock_manager": "موجودی", "tb.projects": "پروژه‌ها",
        "filter.show_all": "-- نمایش همه --", "btn.close": "بستن", "btn.cancel": "انصراف",
        "btn.save": "ذخیره", "btn.create": "ایجاد", "btn.open": "باز کردن",
        "btn.delete": "حذف", "btn.rename": "تغییر نام", "btn.refresh": "بروزرسانی",
        "err.no_project": "پروژه‌ای فعال نیست. یک پروژه بسازید یا باز کنید.",
        "err.no_selection": "ابتدا یک ردیف را انتخاب کنید.",
        "err.delete_confirm": "ردیف(های) انتخاب‌شده حذف شوند؟ این کار قابل بازگشت نیست.",
        "err.wrong_password": "رمز نادرست است. {attempts} تلاش باقی مانده.",
        "err.access_denied": "دسترسی مجاز نیست. برنامه بسته می‌شود.",
        "err.generic": "خطایی رخ داد. جزئیات در فایل لاگ ثبت شده است.",
        "pm.title": "مدیریت پروژه‌ها",
        "pm.subtitle": "پروژه را باز کنید یا در کمتر از یک دقیقه پروژه جدید بسازید.",
        "pm.new": "پروژه جدید", "pm.empty": "هنوز پروژه‌ای نیست. اولین پروژه را بسازید تا شروع کنید.",
        "pm.created": "پروژه «{name}» ساخته و فعال شد.",
        "pm.opened": "پروژه «{name}» فعال است.",
        "pm.delete_confirm": "پروژه «{name}» و همه داده‌های آن حذف شود؟\n\nلیستوفر، میلگرد، ضایعات و موجودی پاک می‌شوند.\nاین کار قابل بازگشت نیست.",
        "welcome.title": "به RebarAgent خوش آمدید",
        "welcome.headline": "از لیستوفر تا برنامه برش — با پرت کمتر",
        "welcome.body": "سه قدم ساده:\n  ۱) پروژه بسازید یا باز کنید\n  ۲) پوز اضافه کنید (پوز جدید)\n  ۳) برنامه برش را بزنید — پرت را ببینید و تأیید کنید\n\nلازم نیست روز اول همه قابلیت‌ها را بلد باشید. کوچک شروع کنید.",
        "welcome.continue": "ادامه", "welcome.create_project": "ایجاد پروژه", "welcome.hide": "دیگر نشان داده نشود",
        "insights.title": "تحلیل هوشمند", "insights.analyzing": "در حال تحلیل پروژه…",
        "insights.done": "تحلیل انجام شد",
        "insights.empty": "پروژه خالی است. با «پوز جدید» میلگرد اضافه کنید تا پیشنهادها فعال شوند.",
        "status.ready": "آماده", "status.no_project": "پروژه‌ای انتخاب نشده",
        "settings.language": "زبان",
        "settings.language_hint": "زبان رابط (برای بعضی پنجره‌ها ممکن است نیاز به اجرای دوباره باشد)",
        "settings.theme": "پوسته", "settings.general": "عمومی",
        "about.body": "RebarAgent\n\nلیستوفر و بهینه‌سازی برش میلگرد\nبرای دفتر فنی و کارگاه — دقیق، بدون پیچیدگی اضافه.",
        "input.add_title": "افزودن میلگرد", "input.edit_title": "ویرایش میلگرد", "input.general": "اطلاعات کلی",
        "input.listofer_no": "شماره لیستوفر:", "input.listofer_desc": "شرح لیستوفر:",
        "input.position": "پوز (علامت):", "input.diameter": "قطر (میلی‌متر):",
        "input.element_type": "نوع عضو:", "input.location": "محل / ناحیه:",
        "input.standard": "استاندارد:", "input.grade": "رده (نوع):",
        "input.shape_dims": "شکل و ابعاد", "input.shape_type": "نوع شکل:",
        "input.custom_designer": "طراح سفارشی", "input.dimensions_mm": "ابعاد (میلی‌متر)",
        "input.quantity": "تعداد:", "input.add_another": "افزودن بعدی",
        "input.new": "جدید", "input.auto": "خودکار", "input.save": "ذخیره",
        "input.no_project": "پروژه‌ای فعال نیست. ابتدا پروژه بسازید یا باز کنید.",
        "scrap.title": "بانک ضایعات هوشمند", "scrap.diameter": "قطر:", "scrap.grade": "رده:",
        "scrap.add": "افزودن ضایعات", "scrap.edit": "ویرایش", "scrap.assign_bbs": "اختصاص به لیستوفر",
        "scrap.mark_used": "علامت استفاده‌شده", "scrap.delete": "حذف",
        "scrap.total_available": "جمع طول موجود: {mm:.1f} میلی‌متر",
        "scrap.select_edit": "یک ضایعات را برای ویرایش انتخاب کنید.", "scrap.none_selected": "ضایعاتی انتخاب نشده است.",
        "scrap.confirm_used": "ضایعات انتخاب‌شده به‌عنوان استفاده‌شده علامت بخورد؟",
        "scrap.confirm_delete": "ضایعات انتخاب‌شده برای همیشه حذف شود؟",
        "scrap.select_assign": "یک ضایعات برای اختصاص انتخاب کنید.", "scrap.one_only": "فقط یک ضایعات را برای اختصاص انتخاب کنید.",
        "scrap.already_used": "این ضایعات قبلاً استفاده‌شده است. باز هم اختصاص داده شود؟",
        "scrap.not_found": "ضایعات پیدا نشد.", "scrap.assign_title": "اختصاص ضایعات به میلگرد",
        "scrap.assign_hint": "یک ردیف میلگرد را برای اختصاص این ضایعات انتخاب کنید:",
        "scrap.select_rebar": "یک ردیف میلگرد انتخاب کنید.", "scrap.assigned_ok": "ضایعات #{sid} به میلگرد #{rid} اختصاص یافت.",
        "scrap.dia_mm": "قطر (میلی‌متر):", "scrap.len_mm": "طول (میلی‌متر):",
        "scrap.listofer_opt": "شماره لیستوفر (اختیاری):", "scrap.invalid": "ورودی نامعتبر",
        "stock.title": "مدیریت موجودی", "stock.qty": "تعداد:", "stock.project_filter": "فیلتر پروژه:",
        "stock.no_selection": "ابتدا یک ردیف موجودی را انتخاب کنید.", "stock.confirm_delete": "ردیف موجودی حذف شود؟",
        "stock.saved": "گزارش موجودی در {path} ذخیره شد",
        "cut.title": "برنامه برش بهینه‌شده", "cut.busy": "بهینه‌سازی در حال اجراست.",
        "cut.cancelled": "بهینه‌سازی توسط کاربر لغو شد.", "cut.export": "خروجی",
        "cut.reoptimize": "بهینه‌سازی مجدد", "cut.confirm_plan": "تأیید برنامه",
        "cut.force_reopt": "اجبار بهینه‌سازی مجدد", "cut.locked": "برنامه تأیید و قفل شده است",
        "cut.optimizing": "در حال بهینه‌سازی برنامه برش…", "cut.please_wait": "لطفاً صبر کنید…", "cut.cancel": "لغو",
        "common.error": "خطا", "common.info": "اطلاع", "common.confirm": "تأیید",
        "common.success": "موفق", "common.warning": "هشدار", "common.no_selection": "بدون انتخاب",
    },
}

_current_lang = "en"

def get_language() -> str:
    return _current_lang

def load_language_from_config() -> str:
    global _current_lang
    try:
        with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        lang = str(cfg.get("language", "en")).lower()
        if lang not in STRINGS:
            lang = "en"
        _current_lang = lang
    except Exception:
        _current_lang = "en"
    return _current_lang

def set_language(lang: str, persist: bool = True) -> None:
    global _current_lang
    lang = (lang or "en").lower()
    if lang not in STRINGS:
        lang = "en"
    _current_lang = lang
    if persist:
        cfg = {}
        try:
            if os.path.isfile(APP_CONFIG_FILE):
                with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg["language"] = lang
        try:
            os.makedirs(os.path.dirname(APP_CONFIG_FILE) or ".", exist_ok=True)
            with open(APP_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def t(key: str, **kwargs) -> str:
    lang = _current_lang if _current_lang in STRINGS else "en"
    text = STRINGS.get(lang, {}).get(key)
    if text is None:
        text = STRINGS.get("en", {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text

def apply_to_config_globals() -> None:
    import config as cfg
    cfg.FILTER_SHOW_ALL = t("filter.show_all")
    cfg.MENU_LABELS = {
        "file": t("menu.file"), "new_project": t("menu.new_project"), "open_project": t("menu.open_project"),
        "project_manager": t("menu.project_manager"), "export_excel": t("menu.export_excel"),
        "export_pdf": t("menu.export_pdf"), "print_listofer": t("menu.print_listofer"),
        "export_bvbs": t("menu.export_bvbs"), "import_bvbs": t("menu.import_bvbs"),
        "settings": t("menu.settings"), "exit": t("menu.exit"), "tools": t("menu.tools"),
        "lap_splice": t("menu.lap_splice"), "cutting_plan_all": t("menu.cutting_plan_all"),
        "cutting_plan_selected": t("menu.cutting_plan_selected"), "scrap_manager": t("menu.scrap_manager"),
        "stock_manager": t("menu.stock_manager"), "custom_shape_designer": t("menu.custom_shape_designer"),
        "help": t("menu.help"), "welcome": t("menu.welcome"), "user_guide": t("menu.user_guide"),
        "about": t("menu.about"), "license_management": t("menu.license_management"),
        "contact_developer": t("menu.contact_developer"), "agent_insights": t("menu.agent_insights"),
        "system_doctor": t("menu.system_doctor"), "project_dashboard": t("menu.project_dashboard"),
        "backup_project": t("menu.backup_project"), "import_backup": t("menu.import_backup"),
        "import_excel": t("menu.import_excel"), "load_sample_project": t("menu.load_sample_project"),
        "download_excel_template": t("menu.download_excel_template"), "recent_projects": t("menu.recent_projects"),
    }
    cfg.TOOLBAR_BUTTONS = {
        "new_rebar": t("tb.new_rebar"), "edit": t("tb.edit"), "delete": t("tb.delete"),
        "print_listofer": t("tb.print_listofer"), "cutting_plan": t("tb.cutting_plan"),
        "agent_insights": t("tb.agent_insights"), "lap_splice": t("tb.lap_splice"),
        "scrap_manager": t("tb.scrap_manager"), "stock_manager": t("tb.stock_manager"), "projects": t("tb.projects"),
    }
    cfg.ERROR_MSGS = {
        "no_project": t("err.no_project"), "wrong_password": t("err.wrong_password"),
        "access_denied": t("err.access_denied"), "delete_confirm": t("err.delete_confirm"),
        "no_selection": t("err.no_selection"),
    }

load_language_from_config()
apply_to_config_globals()
