# RebarAgent – Intelligent Bar Bending Schedule & Cutting Optimization

**Version 1.6.0** | Desktop BBS + smart cutting for detailers and site teams

RebarAgent is a professional **offline-first** desktop app for civil/structural engineers and rebar detailers. Create Bar Bending Schedules, optimize 1D cutting with multi-stock lengths, manage scrap and stock inventory, and export Excel / PDF / HTML / BVBS.

Repository: https://github.com/Tahmoures54/AiRebar

## Highlights (v1.6)

- **Cutting optimizer** – multi-length stock, kerf, min usable scrap, utilization metrics, confirm + rollback ledger
- **Smart inventory** – Scrap Bank + Stock Manager; apply only on Confirm Plan; Force Re-optimize restores stock/scraps
- **Agent brain** – health score, prioritized tips, one-click actions, Insights panel
- **First-win UX** – sample project, Excel import + template, coach strip, savings report after confirm
- **i18n** – English (default) + Persian
- **Commercial** – Trial / Pro / Office / Lifetime; WhatsApp purchase (+989160684552)

## Quick start

```bash
git clone https://github.com/Tahmoures54/AiRebar.git RebarAgent
cd RebarAgent
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Or: `pip install -e .` then `rebaragent`

## Main workflow

1. **New / Open project** (or **Load Sample Project**)
2. **Add positions** (New Pos) or **Import from Excel**
3. Set **Stock** (6 m / 12 m bars) and optional scraps
4. **Cutting Plan** → review waste → **Confirm Plan** → savings report
5. Export Excel / PDF / HTML / BVBS

## Requirements

Python 3.9+ · pandas · openpyxl · reportlab · numpy · PuLP · mip · svgwrite · qrcode · pillow · tkinter

## Structure

```
main.py, config.py, app_state.py
db/          SQLite
logic/       calculator, optimizer, inventory, agent_brain, sample_project
shapes/      multi-standard library
ui/          Tkinter windows
utils/       i18n, export, license, excel_import, project_backup
tests/
```

## Packaging

```bash
pip install pyinstaller
python build_exe.py   # → dist/RebarAgent/
```

## License & sales

Commercial / trial model. In-app License Management or WhatsApp **+989160684552**.

See `CHANGELOG.md` and `RELEASE.md` for full history and release checklist.
