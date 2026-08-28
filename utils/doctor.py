# utils/doctor.py
"""System Doctor – diagnostic report for RebarAgent installation and data integrity."""

from __future__ import annotations

import importlib
import os
import platform
import sys
import traceback
from typing import List


def generate_system_report() -> str:
    lines: List[str] = []
    lines.append("RebarAgent – System Doctor")
    lines.append("=" * 60)

    lines.append("\n[Environment]")
    lines.append(f"  Python     : {sys.version.split()[0]} ({platform.system()} {platform.machine()})")
    lines.append(f"  Executable : {sys.executable}")
    try:
        from config import BASE_DIR, DB_PATH, TRIAL_PERIOD_DAYS
        lines.append(f"  Base dir   : {BASE_DIR}")
        lines.append(f"  Database   : {DB_PATH}  (exists={os.path.isfile(DB_PATH)})")
        lines.append(f"  Trial days : {TRIAL_PERIOD_DAYS}")
    except Exception as e:
        lines.append(f"  Config load failed: {e}")

    lines.append("\n[Dependencies]")
    for mod_name, label in [
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("reportlab", "reportlab"),
        ("numpy", "numpy"),
        ("pulp", "PuLP"),
        ("mip", "python-mip"),
        ("svgwrite", "svgwrite"),
        ("tkinter", "tkinter"),
    ]:
        try:
            m = importlib.import_module(mod_name)
            ver = getattr(m, "__version__", "ok")
            lines.append(f"  ✓ {label:<12} {ver}")
        except Exception as e:
            lines.append(f"  ✗ {label:<12} MISSING ({e})")

    try:
        from shapes.definitions import default_shape_registry, STANDARD_DISPLAY_MAP
        from shapes import constants
        from shapes.drawing import DRAW_FUNCTIONS

        lines.append(f"\n[Shapes]")
        lines.append(f"  Total shapes loaded: {len(default_shape_registry.flat_shapes)}")

        lines.append("\n[Standards]")
        for code in STANDARD_DISPLAY_MAP.keys():
            keys = default_shape_registry.get_shape_keys_by_standard(code)
            known = "YES" if code in getattr(constants, "STANDARDS", {}) else "NO"
            lines.append(f"  - {code:>4}: {len(keys):>4} shapes | constants: {known}")

        required = ("code", "params", "calc_length", "draw_func", "standard_code")
        missing_count = bad_calc = missing_draw = 0

        for k, s in default_shape_registry.flat_shapes.items():
            if not isinstance(s, dict):
                missing_count += 1
                continue
            for rk in required:
                if rk not in s:
                    missing_count += 1
                    break
            try:
                params = default_shape_registry.get_default_params(k)
                _ = float(s["calc_length"](params, 10.0))
            except Exception:
                bad_calc += 1
            df = s.get("draw_func", "draw_generic")
            if df in ("draw_svg_template", "draw_custom_segmented"):
                continue
            if df not in DRAW_FUNCTIONS and df != "draw_generic":
                missing_draw += 1

        lines.append("\n[Shape Contract]")
        lines.append(f"  Missing required keys (approx): {missing_count}")
        lines.append(f"  calc_length failures (approx):  {bad_calc}")
        lines.append(f"  draw_func not in DRAW_FUNCTIONS: {missing_draw}")

    except Exception as e:
        lines.append("\n[Shapes] Doctor section crashed:")
        lines.append(str(e))
        lines.append(traceback.format_exc())

    lines.append("\n[Optimizer]")
    try:
        from logic.optimizer import optimize_cuts, PULP_AVAILABLE
        lines.append(f"  PuLP available: {PULP_AVAILABLE}")
        bins = optimize_cuts([2.0, 3.0, 4.0, 1.5], 12.0)
        total_pieces = sum(len(b) for b in bins)
        lines.append(f"  Smoke test bins={len(bins)}, pieces={total_pieces}")
    except Exception as e:
        lines.append(f"  Optimizer smoke test failed: {e}")

    lines.append("\n" + "=" * 60)
    lines.append("End of report.")
    return "\n".join(lines)
