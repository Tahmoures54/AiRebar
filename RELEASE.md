# RebarAgent Release Checklist

## Soft launch

1. Build Windows exe (`python build_exe.py`)
2. Smoke: Sample Project → Cutting Plan → Confirm → Savings report
3. Test Excel template download + import
4. Verify WhatsApp license flow (+989160684552)
5. Rotate `REBARAGENT_LICENSE_SECRET` for production keys
6. Trial limits: 14 days / record cap

## Notes

- Offline desktop app; internet only for license/purchase links
- Do not commit `license.dat` or customer keys
