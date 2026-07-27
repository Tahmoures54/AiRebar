# utils/bvbs_import.py
"""
BVBS Import – AI Rebar
Import bars from a BVBS XML file into the current project.
Uses strict validation for critical fields and smart parameter guessing.
"""

import os
import json
import datetime
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional

from db.models import RebarModel, ListoferModel
from shapes.definitions import default_shape_registry
from utils.logger import setup_logger

logger = setup_logger('AI_Rebar.BVBS_Import')

# ----------------------------------------------------------------------
# Reverse mapping: BVBS numerical code -> BS8666 short code
# ----------------------------------------------------------------------
_BVBS_TO_BS = {
    "0": "00", "1": "01", "2": "02", "3": "03",
    "4": "11", "5": "12", "6": "13", "7": "14", "8": "15",
    "9": "21", "10": "22", "11": "23", "12": "24", "13": "25",
    "14": "26", "15": "27", "16": "28", "17": "29",
    "18": "31", "19": "32", "20": "33", "21": "34", "22": "35", "23": "36",
    "24": "41", "25": "44", "26": "46", "27": "47",
    "28": "51", "29": "52", "30": "53", "31": "54", "32": "55", "33": "56",
    "34": "61", "35": "62", "36": "63", "37": "64",
    "38": "71", "39": "72", "40": "73", "41": "74", "42": "75", "43": "77",
    "44": "81", "45": "82", "46": "98", "99": "99"
}

# ----------------------------------------------------------------------
# Fast lookup: BS short code -> full shape name
# ----------------------------------------------------------------------
def _build_bs_to_name_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for full_name in default_shape_registry.flat_shapes:
        if " - " in full_name:
            short_code = full_name.split(" - ")[0].strip()
            mapping[short_code] = full_name
        else:
            mapping[full_name] = full_name
    return mapping

_BS_TO_SHAPE_NAME = _build_bs_to_name_map()


def _bvbs_to_shape_name(bvbs_code: str) -> Optional[str]:
    """Map a BVBS shape code to the full shape name used in the app.
    Returns None if the mapping fails (unknown code).
    """
    bs_code = _BVBS_TO_BS.get(bvbs_code)
    if bs_code is None:
        return None
    return _BS_TO_SHAPE_NAME.get(bs_code)


# ----------------------------------------------------------------------
# Main import functions
# ----------------------------------------------------------------------
def import_bvbs(project_id: int, filepath: str) -> Tuple[int, int]:
    """
    Import all bars from a BVBS file into the project.
    Returns (success_count, error_count).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML file: {e}")

    ns = {'ns': 'http://www.bvbs.de'}
    bars = root.findall('ns:Bar', ns)
    if not bars:
        bars = root.findall('Bar')
    if not bars:
        logger.warning("No <Bar> elements found in BVBS file.")
        return 0, 0

    success = 0
    errors = 0

    for bar in bars:
        bar_id = "?"
        try:
            bar_id = bar.findtext('ID', '?')

            # ----- Critical fields validation -----
            dia_str = bar.findtext('Diameter')
            if dia_str is None:
                raise ValueError("Missing diameter")
            diameter = float(dia_str)
            if diameter <= 0:
                raise ValueError(f"Invalid diameter: {diameter}")

            qty_str = bar.findtext('Quantity', '1')
            quantity = int(qty_str)
            if quantity <= 0:
                raise ValueError(f"Invalid quantity: {quantity}")

            bvbs_shape_code = bar.findtext('ShapeCode', '0').strip()
            shape_name = _bvbs_to_shape_name(bvbs_shape_code)
            if shape_name is None:
                raise ValueError(f"Unknown BVBS shape code: {bvbs_shape_code}")

            # Length (optional - if missing, 0 is used, but params must compensate)
            length_str = bar.findtext('Length')
            length = float(length_str) if length_str else 0.0

            # Position & Listofer
            listofer_no = bar.findtext('Listofer', 'L-001')
            position = bar.findtext('Position', '1')
            grade = bar.findtext('Grade', None)  # None triggers default grade in add

            # Parameters
            params: Dict[str, float] = {}
            for param in bar.findall('Param'):
                name = param.get('name', '')
                value = float(param.text or 0)
                params[name] = value

            if not params:
                # Smart parameter guessing based on shape and total length
                params = _guess_params_from_shape(shape_name, length, diameter)

            dimensions = json.dumps(params)

            lid = ListoferModel.get_or_create(project_id, listofer_no, "")

            RebarModel.add(
                listofer_id=lid,
                pos=position,
                diameter=diameter,
                shape_name=shape_name,
                dimensions=dimensions,
                quantity=quantity,
                location="",
                element_type="",
                user="BVBS Import",
                date=datetime.datetime.now().isoformat(),
                grade=grade
            )
            success += 1

        except Exception as e:
            logger.error(f"Error importing bar {bar_id}: {e}", exc_info=True)
            errors += 1

    logger.info(f"BVBS import finished: {success} succeeded, {errors} failed.")
    return success, errors


def import_bvbs_preview(project_id: int, filepath: str) -> Tuple[List[Dict], int]:
    """
    Return a preview of the first 50 bars and the total count.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {'ns': 'http://www.bvbs.de'}
    bars = root.findall('ns:Bar', ns) or root.findall('Bar')
    total = len(bars)

    preview = []
    for bar in bars[:50]:
        bvbs_shape_code = bar.findtext('ShapeCode', '0').strip()
        shape_name = _bvbs_to_shape_name(bvbs_shape_code) or "???"
        preview.append({
            'id': bar.findtext('ID', ''),
            'diameter': bar.findtext('Diameter', '?'),
            'quantity': bar.findtext('Quantity', '?'),
            'length': bar.findtext('Length', '?'),
            'listofer': bar.findtext('Listofer', '?'),
            'position': bar.findtext('Position', '?'),
            'grade': bar.findtext('Grade', ''),
            'shape_name': shape_name,
        })
    return preview, total


# ----------------------------------------------------------------------
# Smart parameter guessing using the shape registry
# ----------------------------------------------------------------------
def _guess_params_from_shape(shape_name: str, total_length: float, diameter: float) -> Dict[str, float]:
    """
    Attempt to estimate shape parameters from a given total length.
    Uses the shape's default parameters and scales them proportionally
    to match the target length.
    """
    shape_def = default_shape_registry.get_shape_def(shape_name)
    if not shape_def:
        return {"A": total_length}

    # Get sensible default parameters for the shape
    defaults = default_shape_registry.get_default_params(shape_name)
    if not defaults:
        # No defaults known, fallback to even split
        param_names = shape_def.get("params", [])
        if not param_names:
            return {"A": total_length}
        return {p: total_length / len(param_names) for p in param_names}

    # Compute the reference cut length with default parameters
    try:
        ref_length = default_shape_registry.calc_shape_length(shape_name, defaults, diameter)
    except Exception:
        ref_length = 0.0

    if ref_length > 0 and total_length > 0:
        scale = total_length / ref_length
        # Scale each default parameter proportionally
        return {p: defaults[p] * scale for p in defaults}
    else:
        # If reference length is zero or total length zero, fallback to even split
        param_names = list(defaults.keys())
        if not param_names:
            return {"A": total_length}
        return {p: total_length / len(param_names) for p in param_names}