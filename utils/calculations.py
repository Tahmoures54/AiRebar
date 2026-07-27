# utils/calculations.py
"""
Utility functions for rebar calculations: length, weight.
Centralises formulas and uses the unified shape registry.
Supports high‑precision Decimal arithmetic for large‑scale projects.
"""

import json
from decimal import Decimal, getcontext
from shapes.definitions import default_shape_registry
from config import WEIGHT_COEFFICIENT, MM_TO_M_FACTOR   # e.g. 1000.0

# Set a reasonable precision for Decimal if used (e.g. 28 significant digits)
getcontext().prec = 28


def calculate_shape_length_mm(shape_name, dimensions_json, diameter):
    """
    Compute the total developed length of a rebar shape in millimetres.

    Args:
        shape_name: str, shape key as stored in the shape registry
        dimensions_json: JSON string or dict with dimension labels/values
        diameter: int or float, rebar diameter in mm

    Returns:
        float: length in mm
    """
    if isinstance(dimensions_json, str):
        try:
            dims = json.loads(dimensions_json)
        except (json.JSONDecodeError, TypeError):
            dims = {}
    else:
        dims = dimensions_json or {}
    return default_shape_registry.calc_shape_length(shape_name, dims, diameter)


def calculate_weight_kg(diameter_mm, length_mm, quantity=1, use_decimal=False):
    """
    Calculate the weight of a rebar piece (or multiple pieces) in kilograms.

    Formula: length_m * (diameter_mm^2) * coefficient * quantity
    where length_m = length_mm / 1000 and coefficient = WEIGHT_COEFFICIENT.

    If use_decimal is True, the calculation is performed with high‑precision
    Decimal arithmetic (useful for very large projects to avoid floating‑point
    rounding issues). Otherwise standard float is used.

    Args:
        diameter_mm: float, diameter in mm
        length_mm: float, length in mm
        quantity: int, number of bars (default 1)
        use_decimal: bool, switch to Decimal arithmetic

    Returns:
        float (or Decimal if use_decimal is True): total weight in kg
    """
    if use_decimal:
        dia = Decimal(str(diameter_mm))
        length = Decimal(str(length_mm))
        qty = Decimal(str(quantity))
        coeff = Decimal(str(WEIGHT_COEFFICIENT))
        factor = Decimal(str(MM_TO_M_FACTOR))
        length_m = length / factor
        return length_m * (dia ** 2) * coeff * qty
    else:
        length_m = length_mm / MM_TO_M_FACTOR
        return length_m * (diameter_mm ** 2) * WEIGHT_COEFFICIENT * quantity


def calculate_weight(diameter_mm, length_mm, use_decimal=False):
    """
    Return unit weight of a single bar and its total weight (same as unit).
    Used by BBSTreeview for computing (unit_wt, total_wt) where total_wt is for qty=1.

    Args:
        diameter_mm: float
        length_mm: float
        use_decimal: bool

    Returns:
        tuple: (unit_weight_kg, weight_kg) for one piece
    """
    w = calculate_weight_kg(diameter_mm, length_mm, quantity=1, use_decimal=use_decimal)
    return w, w


def calculate_total_weight(rebars, use_decimal=False):
    """
    Compute total weight of a list of rebar rows (as returned from database).

    Each row is a tuple:
    (id, listofer_id, pos, desc, diameter, shape_name, dimensions_json, quantity, ...)

    Args:
        rebars: list of tuples from RebarModel queries
        use_decimal: bool, switch to Decimal arithmetic for high precision

    Returns:
        float (or Decimal): total weight in kg
    """
    total = Decimal('0') if use_decimal else 0.0
    for r in rebars:
        dia = r[4]
        shape = r[5]
        dims = r[6]
        qty = r[7]
        try:
            length_mm = calculate_shape_length_mm(shape, dims, dia)
        except Exception:
            length_mm = 0.0
        total += calculate_weight_kg(dia, length_mm, qty, use_decimal=use_decimal)
    return total