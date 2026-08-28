# logic/sample_project.py
"""Create a ready-to-demo sample project so first-time users see value in minutes."""

from __future__ import annotations

import datetime
import json
from typing import Any, Dict

from db.models import ProjectModel, ListoferModel, RebarModel, StockModel, ScrapModel
from config import DEFAULT_REBAR_GRADE
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.SampleProject")

SAMPLE_NAME = "Demo – Foundation (Sample)"
SAMPLE_CLIENT = "RebarAgent Demo"


def sample_project_exists() -> bool:
    try:
        for row in ProjectModel.get_all() or []:
            if row[1] and SAMPLE_NAME in str(row[1]):
                return True
    except Exception:
        pass
    return False


def create_sample_project(force: bool = False) -> Dict[str, Any]:
    if sample_project_exists() and not force:
        for row in ProjectModel.get_all() or []:
            if row[1] and SAMPLE_NAME in str(row[1]):
                return {"project_id": row[0], "name": row[1], "existing": True}

    pid = ProjectModel.create(SAMPLE_NAME, SAMPLE_CLIENT)
    today = datetime.datetime.now().isoformat()[:10]

    lf_f = ListoferModel.get_or_create(pid, "F-01", "Foundation – Strip FOOT-1")
    lf_c = ListoferModel.get_or_create(pid, "C-01", "Column stubs")

    bars = [
        (lf_f, "B1", 16.0, "00", {"A": 5200}, 24, "Foundation", "Footing"),
        (lf_f, "B2", 16.0, "00", {"A": 3800}, 18, "Foundation", "Footing"),
        (lf_f, "B3", 12.0, "00", {"A": 2500}, 30, "Foundation", "Footing"),
        (lf_f, "B4", 12.0, "00", {"A": 1800}, 20, "Foundation", "Footing"),
        (lf_f, "S1", 10.0, "00", {"A": 900}, 40, "Foundation", "Stirrup"),
        (lf_c, "V1", 20.0, "00", {"A": 4500}, 12, "Column", "Vertical"),
        (lf_c, "V2", 20.0, "00", {"A": 3200}, 8, "Column", "Vertical"),
        (lf_c, "T1", 10.0, "00", {"A": 1100}, 36, "Column", "Tie"),
    ]

    n_rebars = 0
    for lid, pos, dia, shape, dims, qty, loc, et in bars:
        try:
            RebarModel.add(
                lid, pos, dia, shape, json.dumps(dims), qty,
                loc, et, "demo", today,
                grade=DEFAULT_REBAR_GRADE, standard="bs",
            )
            n_rebars += 1
        except Exception as e:
            logger.error("sample rebar %s: %s", pos, e)

    stock_lines = 0
    for dia, length_mm, qty in (
        (16.0, 12000, 15), (12.0, 12000, 20), (20.0, 12000, 8),
        (10.0, 12000, 10), (16.0, 6000, 5), (12.0, 6000, 8),
    ):
        try:
            StockModel.add(pid, dia, length_mm, qty, grade=DEFAULT_REBAR_GRADE)
            stock_lines += 1
        except Exception as e:
            logger.error("sample stock: %s", e)

    scraps = 0
    for dia, length_mm in ((16.0, 2400), (12.0, 1800), (20.0, 3100), (10.0, 950)):
        try:
            ScrapModel.add_scrap(pid, dia, length_mm, grade=DEFAULT_REBAR_GRADE, listofer_number="F-01")
            scraps += 1
        except Exception as e:
            logger.error("sample scrap: %s", e)

    return {
        "project_id": pid,
        "name": SAMPLE_NAME,
        "client": SAMPLE_CLIENT,
        "rebars": n_rebars,
        "stock_lines": stock_lines,
        "scraps": scraps,
        "existing": False,
    }
