# logic/validation.py
"""End-to-end validation for positions, stock, and cutting readiness."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from shapes.definitions import default_shape_registry


class ValidationIssue:
    __slots__ = ("level", "code", "message", "context")

    def __init__(self, level: str, code: str, message: str, context: Optional[dict] = None):
        self.level = level
        self.code = code
        self.message = message
        self.context = context or {}

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message, "context": self.context}


def validate_position(shape_name, dimensions, diameter, quantity=1, standard=None):
    issues = []
    if not shape_name:
        issues.append(ValidationIssue("error", "shape.missing", "Shape is required"))
        return issues
    defn = default_shape_registry.get_shape_def(shape_name)
    if not defn:
        ok, msg = default_shape_registry.validate_shape_key(shape_name)
        if not ok:
            issues.append(ValidationIssue("error", "shape.unknown", msg or f"Unknown shape: {shape_name}"))
            return issues
    if diameter is None or float(diameter) <= 0:
        issues.append(ValidationIssue("error", "diameter.invalid", "Diameter must be positive"))
    if quantity is None or int(quantity) <= 0:
        issues.append(ValidationIssue("error", "quantity.invalid", "Quantity must be a positive integer"))
    if isinstance(dimensions, str):
        try:
            dims = json.loads(dimensions) if dimensions else {}
        except json.JSONDecodeError:
            issues.append(ValidationIssue("error", "dimensions.json", "Dimensions JSON is invalid"))
            return issues
    elif isinstance(dimensions, dict):
        dims = dimensions
    else:
        dims = {}
    shape = default_shape_registry.get_shape_def(shape_name)
    if shape:
        for p in shape.get("params") or []:
            if p not in dims:
                issues.append(ValidationIssue("warning", "dimensions.missing_param", f"Parameter '{p}' missing", {"param": p}))
            else:
                try:
                    if float(dims[p]) < 0:
                        issues.append(ValidationIssue("error", "dimensions.negative", f"Parameter '{p}' cannot be negative", {"param": p}))
                except (TypeError, ValueError):
                    issues.append(ValidationIssue("error", "dimensions.nan", f"Parameter '{p}' is not a number", {"param": p}))
        try:
            length = default_shape_registry.calc_shape_length(shape_name, dims, float(diameter or 10))
            if length <= 0:
                issues.append(ValidationIssue("error", "length.non_positive", "Computed cut length must be positive"))
            elif length > 30000:
                issues.append(ValidationIssue("warning", "length.very_long", f"Cut length {length:.0f} mm is unusually long"))
        except Exception as e:
            issues.append(ValidationIssue("error", "length.calc_failed", f"Length calculation failed: {e}"))
        sc = (shape.get("standard_code") or "").lower()
        if standard and sc and sc not in ("custom", "json") and standard.lower() != sc:
            issues.append(ValidationIssue("warning", "standard.mismatch", f"Shape standard '{sc}' differs from '{standard}'"))
    return issues


def validate_project_positions(rows):
    issues = []
    if not rows:
        issues.append(ValidationIssue("warning", "project.empty", "Project has no positions"))
        return issues
    for row in rows:
        try:
            shape = row[5] if len(row) > 5 else ""
            dia = row[4] if len(row) > 4 else 0
            dims = row[6] if len(row) > 6 else "{}"
            qty = row[7] if len(row) > 7 else 1
            std = row[13] if len(row) > 13 else None
            pos = row[3] if len(row) > 3 else "?"
            for iss in validate_position(str(shape or ""), dims, float(dia or 0), int(qty or 0), std):
                iss.context = {**(iss.context or {}), "pos": pos, "shape": shape}
                issues.append(iss)
        except Exception as e:
            issues.append(ValidationIssue("error", "row.invalid", f"Bad rebar row: {e}"))
    return issues


def validate_stock_coverage(demand_by_dia, stock_rows):
    issues = []
    available = {}
    for row in stock_rows or []:
        try:
            dia = float(row[2])
            length = float(row[3])
            qty = int(row[4] or 0)
            available[dia] = available.get(dia, 0.0) + length * qty
        except Exception:
            continue
    for dia, need in (demand_by_dia or {}).items():
        have = available.get(float(dia), 0.0)
        if have <= 0:
            issues.append(ValidationIssue("warning", "stock.missing", f"No stock for Ø{dia:g} (need {need:.0f} mm)", {"diameter": dia}))
        elif have < need:
            issues.append(ValidationIssue("warning", "stock.short", f"Stock short for Ø{dia:g}: have {have:.0f} need {need:.0f}", {"diameter": dia}))
    return issues


def summarize(issues):
    errors = sum(1 for i in issues if i.level == "error")
    warnings = sum(1 for i in issues if i.level == "warning")
    infos = sum(1 for i in issues if i.level == "info")
    return errors, warnings, infos
