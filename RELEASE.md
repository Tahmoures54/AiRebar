# RebarAgent – Release Checklist (v1.6.0)

## Product
Offline desktop BBS + 1D cutting optimization for detailers / site engineers.
Iran-first commerce (WhatsApp), English default UI + full Persian i18n.

## Pre-release checks
- [x] Unit tests: `pytest tests/ -q`
- [ ] Smoke: Sample project → Cutting → Confirm → Savings → Export
- [ ] Trial: 14 days / 80 records
- [ ] License generate + activate; WhatsApp prefilled message
- [ ] Language en/fa in Settings
- [ ] System Doctor
- [ ] `python build_exe.py` on Windows

## Commercial
| Plan | Code | List IRR |
|------|------|----------|
| Pro 3m | pro_3m | 2,900,000 |
| Pro 6m | pro_6m | 4,900,000 |
| Pro 1y | pro_1y | 7,900,000 |
| Office 1y | office_1y | 14,900,000 |
| Lifetime | unlimited | 24,900,000 |

WhatsApp: +989160684552

## Version locations
- `config.APP_VERSION` = 1.6.0
- `pyproject.toml` version
- `CHANGELOG.md`

## Do not ship
Customer `.db`, `logs/`, `license.dat`, secrets
