# shapes/constants.py
"""
Bending constants, hook allowances, bend deductions, and minimum bending radii
for various design standards.

Supports (internal codes):
  - ir   : Iran – Mabhas 9
  - aci  : ACI 318
  - bs   : BS 8666
  - ec   : Eurocode 2
  - is   : IS 2502
  - gb   : GB 50010 (China)
  - jis  : JIS (Japan)
  - as   : AS 3600 (Australia)
  - nbr  : NBR 6118 (Brazil)
  - iso  : ISO 3766 (generic)

All dimensions are in millimetres.

This module is the single source of truth for standard-dependent values.
It keeps backward compatibility with legacy globals + functions while providing
an OO API via BendingStandard.

Thread-safety:
  - Global standard switching is protected by a lock.
"""

from __future__ import annotations

from typing import Dict, Any, Literal, List, Optional
import threading

from config import WEIGHT_COEFFICIENT  # kept for compatibility


# ----------------------------------------------------------------------
# Required keys for a valid standard definition
# ----------------------------------------------------------------------
REQUIRED_KEYS: List[str] = [
    "hook_90_allowance",
    "hook_135_allowance",
    "hook_180_allowance",
    "bend_90_deduction",
    "bend_135_deduction",
    "bend_180_deduction",
    "bend_45_deduction",
    "bend_radius_small_d",
    "bend_radius_large_d",
    "min_stirrup_hook_length",
    "name",
]

# ----------------------------------------------------------------------
# Standard factor database
# Notes:
# - *_allowance values are multipliers of diameter d (mm) to compute a base hook length.
# - bend_*_deduction values are multipliers of diameter d (mm).
# - bend_radius_* are multipliers of diameter to compute minimum centre-line radius.
# ----------------------------------------------------------------------
STANDARDS: Dict[str, Dict[str, Any]] = {
    "ir": {
        "name": "Iran - Mabhas 9 (1400)",
        "hook_90_allowance": 12.0,
        "hook_135_allowance": 6.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 3.0,
        "bend_180_deduction": 1.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,   # r >= 2d for d <= 16
        "bend_radius_large_d": 2.5,   # r >= 2.5d for d > 16
        "min_stirrup_hook_length": 75.0,
    },
    "aci": {
        "name": "ACI 318-19 (American)",
        "hook_90_allowance": 12.0,
        "hook_135_allowance": 6.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 3.0,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 76.0,  # ~3 inches
    },
    "bs": {
        "name": "BS 8666:2005 (United Kingdom)",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
    "ec": {
        "name": "Eurocode 2 (EN 1992-1-1)",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
    "is": {
        "name": "IS 2502:1963 (Indian)",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },

    # ---- Added to fix: Unknown standard: gb/jis/as/nbr ----
    # These are reasonable defaults aligned with EC/BS style until you
    # decide to implement country-specific tables.
    "gb": {
        "name": "GB 50010 (China) – Default Factors",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
    "jis": {
        "name": "JIS (Japan) – Default Factors",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
    "as": {
        "name": "AS 3600 (Australia) – Default Factors",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
    "nbr": {
        "name": "NBR 6118 (Brazil) – Default Factors",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },

    "iso": {
        "name": "ISO 3766:2003 (International)",
        "hook_90_allowance": 10.0,
        "hook_135_allowance": 5.0,
        "hook_180_allowance": 4.0,
        "bend_90_deduction": 2.0,
        "bend_135_deduction": 2.5,
        "bend_180_deduction": 2.0,
        "bend_45_deduction": 0.5,
        "bend_radius_small_d": 2.0,
        "bend_radius_large_d": 2.5,
        "min_stirrup_hook_length": 70.0,
    },
}


def _validate_standard_config(code: str, cfg: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Standard '{code}' is missing required keys: {missing}")


for _code, _cfg in STANDARDS.items():
    _validate_standard_config(_code, _cfg)


# ----------------------------------------------------------------------
# Object-Oriented API
# ----------------------------------------------------------------------
class BendingStandard:
    """
    Represents one design standard. Safe to instantiate and use anywhere.
    """

    def __init__(self, standard_code: str = "ir"):
        standard_code = (standard_code or "").strip().lower()
        if standard_code not in STANDARDS:
            raise ValueError(f"Unknown standard: {standard_code}")
        cfg = STANDARDS[standard_code]
        _validate_standard_config(standard_code, cfg)

        self.code = standard_code
        self.config = cfg
        self.name = cfg["name"]

    def to_dict(self) -> Dict[str, Any]:
        return self.config.copy()

    def get_bending_radius(self, d: float) -> float:
        """Minimum centre-line bending radius (mm) for bar diameter d (mm)."""
        d = float(d or 0.0)
        if d <= 0:
            return 0.0
        if d <= 16.0:
            return self.config["bend_radius_small_d"] * d
        return self.config["bend_radius_large_d"] * d

    def get_hook_length(
        self,
        d: float,
        angle: Literal[90, 135, 180],
        style: str = "standard",
        enforce_min: bool = True,
    ) -> float:
        """
        Straight length of a hook (mm) beyond the bend.

        style:
          - 'standard': use code factor and optionally enforce min_stirrup_hook_length
          - 'heavy'   : enforce stronger minimum (>= max(10d, 100mm))
        enforce_min:
          - True keeps backward-compatible behavior (min_stirrup_hook_length clamp)
        """
        d = float(d or 0.0)
        if d <= 0:
            return 0.0

        factor_key = f"hook_{int(angle)}_allowance"
        base = self.config[factor_key] * d

        if style == "heavy":
            return max(base, max(10.0 * d, 100.0))

        if enforce_min:
            return max(base, float(self.config["min_stirrup_hook_length"]))
        return base

    def stirrup_hook_length(self, diameter_mm: float, angle: Literal[90, 135, 180] = 135) -> float:
        return self.get_hook_length(diameter_mm, angle, style="standard", enforce_min=True)

    def bend_deduction(self, diameter_mm: float, angle: Literal[45, 90, 135, 180]) -> float:
        diameter_mm = float(diameter_mm or 0.0)
        if diameter_mm <= 0:
            return 0.0
        factor_key = f"bend_{int(angle)}_deduction"
        return self.config[factor_key] * diameter_mm


# ----------------------------------------------------------------------
# Global state (backward compatibility) + thread-safe switching
# ----------------------------------------------------------------------
_standard_lock = threading.RLock()

CURRENT_STANDARD: str = "ir"
default_standard = BendingStandard(CURRENT_STANDARD)

# Legacy globals (initialized)
HOOK_90_DEG_ALLOWANCE_FACTOR = default_standard.config["hook_90_allowance"]
HOOK_135_DEG_ALLOWANCE_FACTOR = default_standard.config["hook_135_allowance"]
HOOK_180_DEG_ALLOWANCE_FACTOR = default_standard.config["hook_180_allowance"]
BEND_DEDUCTION_90_DEG_FACTOR = default_standard.config["bend_90_deduction"]
BEND_DEDUCTION_135_DEG_FACTOR = default_standard.config["bend_135_deduction"]
BEND_DEDUCTION_180_DEG_FACTOR = default_standard.config["bend_180_deduction"]
BEND_DEDUCTION_45_DEG_FACTOR = default_standard.config["bend_45_deduction"]
MIN_STIRRUP_HOOK_LENGTH = default_standard.config["min_stirrup_hook_length"]
BEND_RADIUS_SMALL_D_FACTOR = default_standard.config["bend_radius_small_d"]
BEND_RADIUS_LARGE_D_FACTOR = default_standard.config["bend_radius_large_d"]


def set_standard(standard_name: str):
    """
    Activate a design standard globally (updates default_standard).
    Thread-safe.
    """
    global default_standard, CURRENT_STANDARD
    global HOOK_90_DEG_ALLOWANCE_FACTOR, HOOK_135_DEG_ALLOWANCE_FACTOR
    global HOOK_180_DEG_ALLOWANCE_FACTOR, BEND_DEDUCTION_90_DEG_FACTOR
    global BEND_DEDUCTION_135_DEG_FACTOR, BEND_DEDUCTION_180_DEG_FACTOR
    global BEND_DEDUCTION_45_DEG_FACTOR, MIN_STIRRUP_HOOK_LENGTH
    global BEND_RADIUS_SMALL_D_FACTOR, BEND_RADIUS_LARGE_D_FACTOR

    code = (standard_name or "").strip().lower()
    with _standard_lock:
        new_std = BendingStandard(code)
        default_standard = new_std
        CURRENT_STANDARD = code

        # Update legacy globals
        HOOK_90_DEG_ALLOWANCE_FACTOR = new_std.config["hook_90_allowance"]
        HOOK_135_DEG_ALLOWANCE_FACTOR = new_std.config["hook_135_allowance"]
        HOOK_180_DEG_ALLOWANCE_FACTOR = new_std.config["hook_180_allowance"]
        BEND_DEDUCTION_90_DEG_FACTOR = new_std.config["bend_90_deduction"]
        BEND_DEDUCTION_135_DEG_FACTOR = new_std.config["bend_135_deduction"]
        BEND_DEDUCTION_180_DEG_FACTOR = new_std.config["bend_180_deduction"]
        BEND_DEDUCTION_45_DEG_FACTOR = new_std.config["bend_45_deduction"]
        MIN_STIRRUP_HOOK_LENGTH = new_std.config["min_stirrup_hook_length"]
        BEND_RADIUS_SMALL_D_FACTOR = new_std.config["bend_radius_small_d"]
        BEND_RADIUS_LARGE_D_FACTOR = new_std.config["bend_radius_large_d"]


def get_current_standard_name() -> str:
    return default_standard.name


def get_standard_factors(standard: Optional[str] = None) -> dict:
    if standard is None:
        return default_standard.to_dict()
    code = (standard or "").strip().lower()
    if code not in STANDARDS:
        raise ValueError(f"Unknown standard: {code}")
    return STANDARDS[code].copy()


# ----------------------------------------------------------------------
# Legacy wrappers (keep old API stable)
# ----------------------------------------------------------------------
def get_bending_radius(d: float) -> float:
    return default_standard.get_bending_radius(d)


def get_hook_length(d: float, angle: int, style: str = "standard") -> float:
    # Accept any int angle; validate to supported set
    if int(angle) not in (90, 135, 180):
        raise ValueError(f"Unsupported hook angle: {angle}")
    return default_standard.get_hook_length(d, int(angle), style=style, enforce_min=True)


def stirrup_hook_length(diameter_mm: float, angle: int = 135) -> float:
    if int(angle) not in (90, 135, 180):
        raise ValueError(f"Unsupported hook angle: {angle}")
    return default_standard.stirrup_hook_length(diameter_mm, int(angle))


def bend_deduction(diameter_mm: float, angle: int) -> float:
    if int(angle) not in (45, 90, 135, 180):
        raise ValueError(f"Unsupported bend angle: {angle}")
    return default_standard.bend_deduction(diameter_mm, int(angle))


# ----------------------------------------------------------------------
# Extra (optional) helper – kept harmless and useful
# ----------------------------------------------------------------------
def bar_weight_kg_per_m(diameter_mm: float) -> float:
    """
    Approximate bar weight (kg/m). Kept compatible with existing config coefficient usage.
    If your project uses a different formula, adjust WEIGHT_COEFFICIENT in config.py.
    """
    d = float(diameter_mm or 0.0)
    return WEIGHT_COEFFICIENT * (d ** 2)