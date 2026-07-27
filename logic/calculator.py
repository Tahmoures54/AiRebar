# logic/calculator.py
"""
Basic reinforcement calculations: weight and lap splice length.
Lap splice implemented for ACI 318-19 (default).
"""

import math
import logging
from config import WEIGHT_COEFFICIENT

logger = logging.getLogger("AI_Rebar.Calculator")


def calculate_weight(dia_mm: float, length_mm: float) -> tuple:
    if dia_mm <= 0 or length_mm < 0:
        raise ValueError("Diameter must be > 0 and length >= 0")

    unit_weight = (dia_mm ** 2) * WEIGHT_COEFFICIENT  # kg/m
    total_weight = unit_weight * (length_mm / 1000.0)
    return unit_weight, total_weight


def calculate_total_weight(dia_mm: float, length_mm: float, quantity: int) -> float:
    if quantity < 0:
        raise ValueError("Quantity must be >= 0")
    _, single = calculate_weight(dia_mm, length_mm)
    return single * quantity


def calculate_lap_splice(
    dia: float,
    fy: float = 500.0,
    fc: float = 25.0,
    bar_coating: str = "uncoated",
    concrete_type: str = "normal",
    top_bar: bool = False,
    epoxy_coated: bool = False,
    epoxy_cover_sufficient: bool = True,
    standard: str = "ACI318",
) -> float:

    if standard.upper() != "ACI318":
        logger.warning(f"Standard '{standard}' is not implemented; falling back to ACI 318-19.")
        standard = "ACI318"

    if fc <= 0 or fy <= 0 or dia <= 0:
        raise ValueError("fc, fy, dia must be positive")

    psi_t = 1.0
    psi_e = 1.0
    psi_s = 1.0
    psi_g = 1.0
    lam = 1.0 if concrete_type == "normal" else 0.85

    if top_bar:
        psi_t = 1.3

    is_coated = (bar_coating == "coated") or epoxy_coated
    if is_coated:
        psi_e = 1.2 if epoxy_cover_sufficient else 1.5

    if fy > 550:
        psi_g = fy / 550.0

    if dia <= 19:
        denom = 2.1 * lam * math.sqrt(fc)
    else:
        denom = 1.7 * lam * math.sqrt(fc)

    if denom <= 0:
        raise ValueError("Invalid denominator; check fc and concrete type")

    ld = (fy * psi_t * psi_e * psi_s) / denom * dia
    ld *= psi_g

    lap = 1.3 * ld
    return max(lap, 300.0)


def calculate_lap_splice_simple(dia, fc, fy, condition="Tension"):
    top = condition in ("Top", "Tension")
    return calculate_lap_splice(dia, fy=fy, fc=fc, top_bar=top)