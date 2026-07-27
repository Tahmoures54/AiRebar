# logic/bbs_generator.py
"""
Generate Bar Bending Schedule (BBS) data from database records.

- Calculates cut length using ShapeRegistry (mm)
- Calculates piece weight and total weight (kg)
- Includes grade and standard (if available)

Notes:
- RebarModel.get_for_project() in the updated DB layer returns:
  (id, listofer_number, listofer_desc, pos, diameter, shape_name,
   dimensions, quantity, location, element_type, added_by, date_added,
   grade, standard)
  but this module is still backward-compatible with older tuples.
"""

from __future__ import annotations

import json
from typing import List, Dict, Optional, Any, Tuple

from db.models import RebarModel
from shapes.definitions import default_shape_registry
from config import WEIGHT_COEFFICIENT, DEFAULT_REBAR_GRADE
from utils.logger import setup_logger

logger = setup_logger("AI_Rebar.BBSGenerator")


def _safe_json_loads(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            obj = json.loads(value)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _unpack_row(row: Tuple) -> dict:
    """
    Supports both new and old schemas.
    Returns dict with all keys used by generate_bbs_data().
    """
    # Newest expected: 14 columns
    if len(row) >= 14:
        (rebar_id, lf_number, lf_desc, pos, diameter, shape_name,
         dims_json, quantity, location, element_type,
         added_by, date_added, grade, standard) = row
    # Older: 13 columns (no standard)
    elif len(row) == 13:
        (rebar_id, lf_number, lf_desc, pos, diameter, shape_name,
         dims_json, quantity, location, element_type,
         added_by, date_added, grade) = row
        standard = ""
    # Oldest: 12 columns (no grade/standard)
    else:
        (rebar_id, lf_number, lf_desc, pos, diameter, shape_name,
         dims_json, quantity, location, element_type,
         added_by, date_added) = row
        grade = DEFAULT_REBAR_GRADE
        standard = ""

    return {
        "id": rebar_id,
        "listofer_number": lf_number or "",
        "listofer_desc": lf_desc or "",
        "pos": pos or "",
        "diameter": diameter,
        "shape_name": shape_name or "",
        "dimensions_raw": dims_json,
        "quantity": quantity,
        "location": location or "",
        "element_type": element_type or "",
        "added_by": added_by or "",
        "date_added": date_added or "",
        "grade": grade or DEFAULT_REBAR_GRADE,
        "standard": (standard or ""),
    }


def generate_bbs_data(project_id: int, listofer_number: Optional[str] = None) -> List[Dict]:
    rows = RebarModel.get_for_project(project_id, listofer_number=listofer_number)
    bbs_rows: List[Dict] = []

    for row in rows:
        data = _unpack_row(row)

        # diameter / quantity
        try:
            diameter = float(data["diameter"] or 0.0)
        except Exception:
            diameter = 0.0

        try:
            quantity = int(data["quantity"] or 1)
        except Exception:
            quantity = 1
        if quantity <= 0:
            quantity = 1

        shape_name =