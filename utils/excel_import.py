# utils/excel_import.py
"""Import rebars from a simple Excel template into a project."""

from __future__ import annotations

import json
import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from db.models import ListoferModel, RebarModel
from config import DEFAULT_REBAR_GRADE
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.ExcelImport")

COL_MAP = {
    "listofer": ["listofer", "listofer_no", "lf", "lf_no", "sheet", "bbs"],
    "pos": ["pos", "mark", "bar_mark", "ref", "position"],
    "diameter": ["diameter", "dia", "d", "ø", "phi"],
    "shape": ["shape", "shape_code", "shape_name", "code"],
    "quantity": ["quantity", "qty", "count", "n"],
    "a": ["a", "dim_a", "length", "l"],
    "b": ["b", "dim_b"],
    "c": ["c", "dim_c"],
    "d": ["d", "dim_d"],
    "e": ["e", "dim_e"],
    "grade": ["grade", "steel_grade"],
    "location": ["location", "loc", "zone"],
    "element": ["element", "element_type", "member"],
    "standard": ["standard", "std"],
    "description": ["description", "listofer_desc", "desc"],
}


def _norm(s) -> str:
    return str(s).strip().lower().replace(" ", "_") if s is not None else ""


def _map_columns(columns) -> Dict[str, str]:
    mapping = {}
    norms = {_norm(c): c for c in columns}
    for canon, aliases in COL_MAP.items():
        for a in aliases:
            if a in norms:
                mapping[canon] = norms[a]
                break
    return mapping


def read_import_preview(path: str, max_rows: int = 20) -> Dict[str, Any]:
    df = pd.read_excel(path, engine="openpyxl")
    df = df.dropna(how="all")
    colmap = _map_columns(df.columns)
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "mapped": colmap,
        "preview": df.head(max_rows).fillna("").astype(str).values.tolist(),
        "missing_required": [k for k in ("diameter", "quantity") if k not in colmap],
    }


def import_rebars_from_excel(
    path: str,
    project_id: int,
    default_listofer: str = "IMP-01",
    user: str = "excel_import",
) -> Dict[str, Any]:
    df = pd.read_excel(path, engine="openpyxl")
    df = df.dropna(how="all")
    colmap = _map_columns(df.columns)
    if "diameter" not in colmap or "quantity" not in colmap:
        raise ValueError(
            "Excel must have columns for Diameter and Quantity "
            f"(found: {list(df.columns)})"
        )

    today = datetime.datetime.now().isoformat()[:10]
    imported = 0
    skipped = 0
    errors: List[str] = []
    listofer_cache: Dict[str, int] = {}

    for idx, row in df.iterrows():
        try:
            dia = float(row[colmap["diameter"]])
            qty = int(float(row[colmap["quantity"]]))
            if dia <= 0 or qty <= 0:
                skipped += 1
                continue

            lf_num = str(row[colmap["listofer"]]).strip() if "listofer" in colmap else default_listofer
            if not lf_num or lf_num.lower() == "nan":
                lf_num = default_listofer
            lf_desc = ""
            if "description" in colmap:
                lf_desc = str(row[colmap["description"]] or "")
                if lf_desc.lower() == "nan":
                    lf_desc = ""

            if lf_num not in listofer_cache:
                listofer_cache[lf_num] = ListoferModel.get_or_create(project_id, lf_num, lf_desc)
            lid = listofer_cache[lf_num]

            pos = str(row[colmap["pos"]]) if "pos" in colmap else f"R{idx+1}"
            if pos.lower() == "nan":
                pos = f"R{idx+1}"

            shape = str(row[colmap["shape"]]).strip() if "shape" in colmap else "00"
            if not shape or shape.lower() == "nan":
                shape = "00"

            dims = {}
            for key in ("a", "b", "c", "d", "e"):
                if key in colmap:
                    try:
                        val = float(row[colmap[key]])
                        if val > 0:
                            dims[key.upper()] = val
                    except Exception:
                        pass

            grade = DEFAULT_REBAR_GRADE
            if "grade" in colmap:
                g = str(row[colmap["grade"]]).strip()
                if g and g.lower() != "nan":
                    grade = g

            location = ""
            if "location" in colmap:
                location = str(row[colmap["location"]] or "")
                if location.lower() == "nan":
                    location = ""

            element = ""
            if "element" in colmap:
                element = str(row[colmap["element"]] or "")
                if element.lower() == "nan":
                    element = ""

            standard = "bs"
            if "standard" in colmap:
                s = str(row[colmap["standard"]] or "bs").strip()
                if s and s.lower() != "nan":
                    standard = s

            RebarModel.add(
                lid, pos, dia, shape, json.dumps(dims), qty,
                location, element, user, today,
                grade=grade, standard=standard,
            )
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {idx}: {e}")
            if len(errors) > 15:
                break

    return {
        "imported": imported,
        "skipped": skipped,
        "listofers": len(listofer_cache),
        "errors": errors,
    }


def create_import_template(path: str) -> str:
    df = pd.DataFrame(
        [
            {
                "Listofer": "F-01",
                "Description": "Foundation",
                "Pos": "B1",
                "Diameter": 16,
                "Shape": "00",
                "A": 5200,
                "B": "",
                "C": "",
                "Quantity": 24,
                "Grade": DEFAULT_REBAR_GRADE,
                "Location": "Foundation",
                "Element": "Footing",
            },
            {
                "Listofer": "F-01",
                "Description": "Foundation",
                "Pos": "B2",
                "Diameter": 12,
                "Shape": "00",
                "A": 2500,
                "B": "",
                "C": "",
                "Quantity": 30,
                "Grade": DEFAULT_REBAR_GRADE,
                "Location": "Foundation",
                "Element": "Footing",
            },
        ]
    )
    df.to_excel(path, index=False, engine="openpyxl")
    return path
