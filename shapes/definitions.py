# shapes/definitions.py
"""
Unified shape definitions for reinforcement bars.

This registry merges:
1) BS8666 categorized numeric shapes from shapes.standards.bs8666._REGISTRY
2) International standards shapes from shapes.standards.* modules (SHAPES dict)
   - Uses STANDARDS_DICT if available
   - Otherwise imports each standards module directly (robust fallback)
3) Any JSON standards found in shapes/standards/*.json
4) Custom shapes from database

Key improvement:
- get_shape_keys_by_standard(code) returns ONLY that standard's shapes (even empty),
  and falls back to ALL shapes only when the standard code is unknown.
"""

from __future__ import annotations

import math
import json
import os
import logging
import threading
import importlib
from typing import Dict, Any, Optional, Callable

from . import constants as _constants

try:
    from .standards import STANDARDS_DICT, STANDARD_CODES  # type: ignore
except Exception:  # pragma: no cover
    STANDARDS_DICT = {}
    STANDARD_CODES = []

from .standards.bs8666 import (
    _REGISTRY,                # BS8666 numeric registry
    calculate_length,         # length calc for BS codes
)

logger = logging.getLogger("AI_Rebar.Shapes")

STANDARD_DISPLAY_MAP = {
    "bs":  "BS 8666 (UK)",
    "ir":  "Iran – Mabhas 9",
    "aci": "ACI 318 – USA",
    "ec":  "Eurocode 2",
    "is":  "IS 2502 – India",
    "gb":  "GB 50010 – China",
    "jis": "JIS G 3112 – Japan",
    "as":  "AS 3600 – Australia",
    "nbr": "NBR 6118 – Brazil",
}

# Which python module implements each standard (file names under shapes/standards/)
PY_STANDARD_MODULES = {
    "ir":  "mabhas9",
    "aci": "aci318",
    "ec":  "eurocode2",
    "is":  "is2502",
    "gb":  "gb50010",
    "jis": "jis",
    "as":  "as3600",
    "nbr": "nbr6118",
    # 'bs' handled separately via bs8666 categories
}

_BS_DRAW_MAP = {
    "00": "draw_straight",
    "11": "draw_l_bar",
    "12": "draw_z_bar",
    "13": "draw_double_cranked_bar",
    "14": "draw_double_cranked_bar",
    "15": "draw_multi_leg_chair",
    "16": "draw_multi_leg_chair",
    "21": "draw_closed_stirrup_90",
    "22": "draw_u_bar_with_hooks",
    "23": "draw_u_bar_with_hooks",
    "24": "draw_u_bar_with_hooks",
    "25": "draw_closed_stirrup_90",
    "26": "draw_multi_leg_stirrup",
    "27": "draw_closed_stirrup_90",
    "28": "draw_multi_leg_stirrup",
    "31": "draw_helical",
    "32": "draw_helical",
    "33": "draw_helical",
    "34": "draw_helical",
    "35": "draw_helical",
    "36": "draw_helical",
    "41": "draw_chair",
    "42": "draw_chair",
    "43": "draw_chair",
    "44": "draw_chair",
    "45": "draw_chair",
    "46": "draw_chair",
    "47": "draw_chair",
    "48": "draw_chair",
    "51": "draw_closed_stirrup_90",
    "52": "draw_closed_stirrup_90",
    "53": "draw_closed_stirrup_90",
    "54": "draw_multi_leg_stirrup",
    "55": "draw_multi_leg_stirrup",
    "56": "draw_helical",
    "57": "draw_helical",
    "58": "draw_helical",
    "59": "draw_helical",
    "61": "draw_chair",
    "62": "draw_chair",
    "63": "draw_spacer_bar",
    "64": "draw_spacer_bar",
    "65": "draw_multi_leg_chair",
    "66": "draw_u_bar_with_hooks",
    "67": "draw_multi_leg_stirrup",
    "68": "draw_multi_leg_chair",
    "70": "draw_closed_stirrup_90",
    "71": "draw_closed_stirrup_90",
    "72": "draw_u_bar",
    "73": "draw_u_bar_with_hooks",
    "74": "draw_u_bar",
    "75": "draw_multi_leg_stirrup",
    "76": "draw_multi_leg_stirrup",
    "77": "draw_circular_tie",
    "78": "draw_circular_tie",
    "79": "draw_circular_tie",
    "81": "draw_l_bar",
    "82": "draw_straight_with_90_hook",
    "83": "draw_z_bar",
    "84": "draw_double_hook_90",
    "85": "draw_l_bar_with_hook",
    "86": "draw_s_bar",
    "87": "draw_s_bar",
    "88": "draw_s_bar",
    "89": "draw_s_bar",
    "90": "draw_u_bar",
    "91": "draw_l_bar",
    "92": "draw_z_bar",
    "93": "draw_s_bar",
    "94": "draw_u_bar",
    "95": "draw_multi_leg_stirrup",
    "96": "draw_z_bar",
    "97": "draw_z_bar",
    "98": "draw_u_bar",
    "99": "draw_custom",
}

STANDARDS_DIR = os.path.join(os.path.dirname(__file__), "standards")


class ShapeRegistry:
    """
    Central registry for all reinforcement bar shapes.
    """

    REQUIRED_KEYS = ("code", "params", "calc_length", "draw_func", "standard_code")

    def __init__(self):
        self._lock = threading.Lock()
        self.categorized_shapes: Dict[str, Dict[str, dict]] = {}
        self.flat_shapes: Dict[str, dict] = {}
        self._shapes_by_standard_code: Dict[str, list] = {}
        self.refresh()

    # ---------------------------
    # Utility: detect "shape dict"
    # ---------------------------
    def _looks_like_shape_def(self, v):
        return isinstance(v, dict) and (
            "params" in v or "calc_length" in v or "length_formula" in v or "code" in v
        )

    def _flatten_possible_categories(self, shapes_dict):
        """
        Accept either:
        - flat dict: {shape_key: shape_def}
        - categorized dict: {cat_name: {shape_key: shape_def}}
        Return flat dict.
        """
        if not isinstance(shapes_dict, dict):
            return {}

        # already flat?
        if any(self._looks_like_shape_def(v) for v in shapes_dict.values()):
            return shapes_dict

        # categorized?
        flat = {}
        for _, sub in shapes_dict.items():
            if isinstance(sub, dict) and any(self._looks_like_shape_def(v) for v in sub.values()):
                flat.update(sub)
        return flat

    def _infer_standard_code_from_key_or_code(self, shape_key: str, shape_def: dict, fallback: str = "unknown") -> str:
        # Prefer explicit
        sc = (shape_def.get("standard_code") or "").strip().lower()
        if sc:
            return sc

        # Try from code like "ACI-01"
        code = str(shape_def.get("code") or "")
        lead = code.split("-")[0].strip().lower()
        if lead in STANDARD_DISPLAY_MAP:
            return lead
        if lead == "ec2":
            return "ec"

        # Try from key like "ACI-01 - ..."
        key_lead = str(shape_key).split(" - ")[0].split("-")[0].strip().lower()
        if key_lead in STANDARD_DISPLAY_MAP:
            return key_lead
        if key_lead == "ec2":
            return "ec"

        return fallback

    def _normalize_shape_def(self, shape_key: str, shape_def: dict, standard_code: Optional[str] = None) -> dict:
        """
        Enforce a stable internal contract for every shape definition.
        """
        if not isinstance(shape_def, dict):
            return {}

        s = dict(shape_def)

        # code
        if not s.get("code"):
            s["code"] = str(shape_key).split(" - ")[0].strip()

        # params
        if not isinstance(s.get("params"), list):
            s["params"] = []

        # standard_code
        if standard_code:
            s["standard_code"] = standard_code
        else:
            s["standard_code"] = self._infer_standard_code_from_key_or_code(shape_key, s, fallback=s.get("standard_code", "unknown"))

        # draw_func
        s.setdefault("draw_func", "draw_generic")

        # calc_length
        if "calc_length" not in s or not callable(s.get("calc_length")):
            # JSON style
            if "length_formula" in s and isinstance(s["length_formula"], str):
                formula_str = s["length_formula"]
                s["calc_length"] = lambda p, d, f=formula_str: self._eval_formula_safe(f, p, d)
            else:
                s["calc_length"] = lambda p, d: 0.0  # safe fallback

        return s

    def _annotate_standard(self, shapes: dict, standard_code: str) -> dict:
        out = {}
        for k, v in (shapes or {}).items():
            if not isinstance(v, dict):
                continue
            out[k] = self._normalize_shape_def(k, v, standard_code=standard_code)
        return out

    # ----------------------------------------------------------------------
    # Refresh / load
    # ----------------------------------------------------------------------
    def refresh(self):
        with self._lock:
            merged: Dict[str, Dict[str, dict]] = {}

            # 1) BS8666 sub-categories
            merged.update(self._build_bs8666_category_dict())

            # 2) International python standards
            std_shapes = self._load_international_python_standards()
            for std_code, display_name in STANDARD_DISPLAY_MAP.items():
                if std_code == "bs":
                    continue
                shapes = std_shapes.get(std_code, {})
                if shapes:
                    merged[display_name] = self._annotate_standard(shapes, std_code)
                else:
                    logger.debug(f"No python shapes loaded for '{std_code}' ({display_name})")

            # 3) JSON standards
            json_cats = self._load_all_standard_jsons()
            # normalize JSON too (standard_code inferred best-effort)
            normalized_json = {}
            for cat_name, shapes in (json_cats or {}).items():
                if not isinstance(shapes, dict):
                    continue
                cat_shapes = {}
                for k, v in shapes.items():
                    # try to infer standard code from category label
                    sc = "json"
                    cat_shapes[k] = self._normalize_shape_def(k, v, standard_code=sc)
                normalized_json[cat_name] = cat_shapes
            merged.update(normalized_json)

            # 4) Custom shapes
            custom_cat = self._load_custom_shapes_from_db()
            if custom_cat:
                # normalize custom too
                merged["Custom Shapes"] = {
                    k: self._normalize_shape_def(k, v, standard_code="custom") for k, v in custom_cat.items()
                }

            self.categorized_shapes = merged

            # Flat dictionary
            flat: Dict[str, dict] = {}
            for shapes in merged.values():
                if isinstance(shapes, dict):
                    for key, data in shapes.items():
                        flat[key] = data
            self.flat_shapes = flat

            # lookup by standard code
            self._shapes_by_standard_code = {code: [] for code in STANDARD_DISPLAY_MAP.keys()}

            # BS list
            bs_shapes = []
            for cat_name, shapes in merged.items():
                if isinstance(cat_name, str) and cat_name.startswith("BS8666") and isinstance(shapes, dict):
                    bs_shapes.extend(list(shapes.keys()))
            self._shapes_by_standard_code["bs"] = sorted(set(bs_shapes))

            # Other standards
            for std_code, display_name in STANDARD_DISPLAY_MAP.items():
                if std_code == "bs":
                    continue
                shapes = merged.get(display_name, {})
                self._shapes_by_standard_code[std_code] = sorted(list(shapes.keys())) if isinstance(shapes, dict) else []

            # Custom included (optional)
            if custom_cat:
                custom_keys = list(custom_cat.keys())
                for code in list(self._shapes_by_standard_code.keys()):
                    self._shapes_by_standard_code[code] = sorted(set(self._shapes_by_standard_code[code] + custom_keys))
                self._shapes_by_standard_code["custom"] = sorted(custom_keys)

            for code in STANDARD_DISPLAY_MAP.keys():
                logger.info(f"Standard '{code}' loaded {len(self._shapes_by_standard_code.get(code, []))} shapes")
            logger.info(f"ShapeRegistry loaded {len(self.flat_shapes)} shapes successfully.")

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def get_shape_keys_by_standard(self, code: str) -> list:
        code = (code or "").strip().lower()
        if code in self._shapes_by_standard_code:
            return self._shapes_by_standard_code.get(code, [])
        return sorted(self.flat_shapes.keys())

    def get_shape_def(self, key: str) -> dict:
        return self.flat_shapes.get(key)

    def get_default_params(self, key: str) -> dict:
        shape = self.get_shape_def(key)
        if not shape:
            return {}
        defaults = {}
        for p in shape.get("params", []):
            if p == "D":
                defaults[p] = 200.0
            elif p == "Lap":
                defaults[p] = 400.0
            elif p in ("N", "Sides"):
                defaults[p] = 6.0
            else:
                defaults[p] = 100.0
        return defaults

    def calc_shape_length(self, key: str, params: dict, diameter_mm: float) -> float:
        shape = self.get_shape_def(key)
        if not shape:
            raise KeyError(f"Unknown shape key: {key}")
        return float(shape["calc_length"](params, diameter_mm))

    # ------------------------------------------------------------------
    # Load international python standards
    # ------------------------------------------------------------------
    def _load_international_python_standards(self) -> dict:
        """
        Build dict: {standard_code: flat_shapes_dict}
        Priority:
          1) STANDARDS_DICT[code] if present
          2) Import module shapes.standards.<module> and read SHAPES
        """
        result: Dict[str, Dict[str, dict]] = {}

        if isinstance(STANDARDS_DICT, dict):
            for code, shapes in STANDARDS_DICT.items():
                if not code:
                    continue
                code = str(code).strip().lower()
                flat = self._flatten_possible_categories(shapes)
                if flat:
                    result.setdefault(code, {}).update(flat)

        for code, module_name in PY_STANDARD_MODULES.items():
            try:
                mod = importlib.import_module(f"shapes.standards.{module_name}")
                shapes = getattr(mod, "SHAPES", None)
                flat = self._flatten_possible_categories(shapes)
                if flat:
                    result.setdefault(code, {})
                    for k, v in flat.items():
                        result[code].setdefault(k, v)
            except Exception as e:
                logger.debug(f"Could not import/load SHAPES for {code} ({module_name}): {e}")

        return result

    # ------------------------------------------------------------------
    # BS8666 sub‑categories
    # ------------------------------------------------------------------
    def _build_bs8666_category_dict(self):
        categories = {
            "BS8666 - Straight & Hooks": ["00", "82", "84"],
            "BS8666 - L, Z & Single Plane Bends": ["11", "12", "13", "14", "15", "16"],
            "BS8666 - Stirrups & Links": [
                "21", "22", "23", "24", "25", "26", "27", "28",
                "70", "71", "72", "73", "74", "75", "76"
            ],
            "BS8666 - Spiral & Helical": ["31", "32", "33", "34", "35", "36", "56", "57", "58", "59"],
            "BS8666 - Raker & Bent Bars": ["41", "42", "43", "44", "45", "46", "47", "48"],
            "BS8666 - Overlap / Anchor Shapes": ["51", "52", "53", "54", "55"],
            "BS8666 - Complex Links & Chairs": ["61", "62", "63", "64", "65", "66", "67", "68"],
            "BS8666 - Circular & Curved": ["77", "78", "79"],
            "BS8666 - End Treatments & Specials": [
                "81", "83", "85", "86", "87", "88", "89", "90",
                "91", "92", "93", "94", "95", "96", "97", "98"
            ],
            "BS8666 - Custom": ["99"],
        }

        categorized = {}
        for cat_name, code_list in categories.items():
            cat_shapes: Dict[str, dict] = {}
            for code in code_list:
                shape = _REGISTRY.get(code)
                if not shape:
                    continue

                display_name = f"{shape.code} - {shape.name}"
                draw_func = _BS_DRAW_MAP.get(code, "draw_generic")

                def make_calc(shape_code):
                    return lambda dims, d: calculate_length(shape_code, dims, d)

                cat_shapes[display_name] = self._normalize_shape_def(display_name, {
                    "code": shape.code,
                    "params": shape.params,
                    "calc_length": make_calc(code),
                    "draw_func": draw_func,
                    "standard_code": "bs",
                }, standard_code="bs")

            if cat_shapes:
                categorized[cat_name] = cat_shapes

        return categorized

    # ------------------------------------------------------------------
    # JSON standards
    # ------------------------------------------------------------------
    def _eval_formula_safe(self, formula_str, params, dia):
        class ConstRef:
            pass

        const_ref = ConstRef()
        for attr in dir(_constants):
            if attr.isupper():
                setattr(const_ref, attr, getattr(_constants, attr))

        local_vars = {
            "p": params,
            "dia": dia,
            "math": math,
            "abs": abs,
            "sqrt": math.sqrt,
            "pi": math.pi,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "radians": math.radians,
            "degrees": math.degrees,
            "_p_const": const_ref,
        }
        try:
            return float(eval(formula_str, {"__builtins__": {}}, local_vars))
        except Exception as e:
            logger.error(f"Formula evaluation failed: '{formula_str}'. Error: {e}")
            return 0.0

    def _load_standard_from_json(self, filename):
        filepath = os.path.join(STANDARDS_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        standard_name = data.get("standard", os.path.splitext(filename)[0])
        categories = data.get("categories", {})
        result = {}

        for cat_name, shapes in categories.items():
            full_cat = f"{standard_name} - {cat_name}"
            cat_shapes = {}
            for shape_name, sdef in shapes.items():
                calc_fn = lambda p, d, f=sdef["length_formula"]: self._eval_formula_safe(f, p, d)
                cat_shapes[shape_name] = {
                    "code": sdef.get("code", ""),
                    "params": sdef.get("params", []),
                    "calc_length": calc_fn,
                    "draw_func": "draw_svg_template",
                    "svg_template": sdef.get("svg_template", ""),
                    "labels": sdef.get("labels", []),
                    "standard": standard_name,
                }
            if cat_shapes:
                result[full_cat] = cat_shapes

        return result

    def _load_all_standard_jsons(self):
        merged = {}
        if os.path.isdir(STANDARDS_DIR):
            for fname in sorted(os.listdir(STANDARDS_DIR)):
                if fname.lower().endswith(".json"):
                    try:
                        merged.update(self._load_standard_from_json(fname))
                    except Exception as e:
                        logger.error(f"Error loading JSON standard '{fname}': {e}")
        return merged

    # ------------------------------------------------------------------
    # Custom shapes from database
    # ------------------------------------------------------------------
    def _load_custom_shapes_from_db(self):
        custom_category = {}
        try:
            from db.models import CustomShapeModel

            shapes = CustomShapeModel.get_all()
            for s in shapes:
                definition = s["definition"]
                if isinstance(definition, str):
                    try:
                        definition = json.loads(definition)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in custom shape {s.get('code', 'unknown')}")
                        continue

                params_set = set()
                for seg in definition.get("segments", []):
                    if seg.get("type") == "line":
                        params_set.add(seg.get("param"))
                    elif seg.get("type") == "arc":
                        params_set.add(seg.get("radius_param", "r"))

                for hook_key in ("start_hook", "end_hook"):
                    hook = definition.get(hook_key)
                    if hook:
                        params_set.add(hook.get("length_param", "Lh1" if hook_key == "start_hook" else "Lh2"))

                if not params_set:
                    params_set.add("L")

                param_list = sorted(params_set)

                def make_calc(defn):
                    return lambda p, d: self._calc_custom_length(defn, p, d)

                shape_key = f"{s['code']} - {s['name']}"
                custom_category[shape_key] = {
                    "code": s["code"],
                    "params": param_list,
                    "calc_length": make_calc(definition),
                    "draw_func": "draw_custom_segmented",
                    "definition": definition,
                    "standard_code": "custom",
                }

        except Exception as e:
            logger.error(f"Failed to load custom shapes from DB: {e}", exc_info=True)

        return custom_category

    def _calc_custom_length(self, definition, params, d):
        total = 0.0
        for seg in definition.get("segments", []):
            if seg["type"] == "line":
                total += float(params.get(seg["param"], 0))
            elif seg["type"] == "arc":
                angle = float(seg.get("angle", 90))
                R = float(params.get(seg.get("radius_param", "r"), 0)) + d / 2.0
                total += math.radians(angle) * R

        if definition.get("start_hook"):
            total += float(params.get(definition["start_hook"]["length_param"], 0))
        if definition.get("end_hook"):
            total += float(params.get(definition["end_hook"]["length_param"], 0))

        return total


default_shape_registry = ShapeRegistry()