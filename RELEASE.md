# RebarAgent v1.6.0 – Final Release Notes

## Product
Offline desktop **Bar Bending Schedule (BBS)** + **1D cutting optimization** for detailers and site engineers.

- English UI (default) + full Persian i18n
- Iran-first commerce via WhatsApp **+989160684552**
- Trial / Pro / Office / Lifetime licensing

## What is included
- Multi-standard shape library (BS, ACI, EC2, Mabhas 9, …)
- Cutting optimizer: multi-stock lengths, kerf, min usable scrap, utilization metrics
- Smart inventory: Scrap Bank + Stock Manager; Confirm Plan + reversible ledger
- Agent brain: health score, Insights, coach tips
- Sample project, Excel import/template, savings report
- Exports: Excel, PDF, HTML, BVBS
- Modular codebase (`logic/` + `ui/` split for maintainability)

## Install
```bash
git clone https://github.com/Tahmoures54/AiRebar.git RebarAgent
cd RebarAgent
python -m venv venv && source venv/bin/activate   # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```
Or: `pip install -e .` then `rebaragent`

## Build Windows EXE
```bash
pip install pyinstaller
python build_exe.py
# → dist/RebarAgent/
```

## Pre-ship checklist
- [x] `pytest tests/ -q` → **32 passed**
- [x] APP_VERSION / pyproject = **1.6.0**
- [x] WhatsApp sales number in config
- [ ] Manual smoke on Windows: Sample → Cutting → Confirm → Export
- [ ] Generate trial/pro keys with `generate_license.py`
- [ ] Change `REBARAGENT_LICENSE_SECRET` for production

## Do not ship
`*.db`, `logs/`, `license.dat`, customer data, default secret if customized

## Support
WhatsApp: +989160684552
