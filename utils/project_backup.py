# utils/project_backup.py
"""Export / backup a single project to a portable JSON file."""

from __future__ import annotations

import json
import datetime
from typing import Any, Dict, Optional

from db.models import ProjectModel, RebarModel, ListoferModel, ScrapModel, StockModel
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.Backup")


def export_project_json(project_id: int, project_name: str = "", client: str = "") -> Dict[str, Any]:
    listofers = []
    try:
        numbers = ListoferModel.get_numbers(project_id) or []
        for num in numbers:
            listofers.append(
                {
                    "number": num,
                    "description": ListoferModel.get_description_by_number(project_id, num) or "",
                }
            )
    except Exception as e:
        logger.error("listofers: %s", e)

    rebars = []
    try:
        for row in RebarModel.get_for_project(project_id) or []:
            rebars.append(
                {
                    "listofer": row[1],
                    "listofer_desc": row[2],
                    "pos": row[3],
                    "diameter": row[4],
                    "shape_name": row[5],
                    "dimensions": row[6],
                    "quantity": row[7],
                    "location": row[8],
                    "element_type": row[9],
                    "grade": row[12] if len(row) > 12 else None,
                    "standard": row[13] if len(row) > 13 else None,
                }
            )
    except Exception as e:
        logger.error("rebars: %s", e)

    scraps = []
    try:
        for row in ScrapModel.get_all_scraps(project_id) or []:
            scraps.append(
                {
                    "id": row[0],
                    "diameter": row[1],
                    "length_mm": row[2],
                    "grade": row[3],
                    "date_created": row[4],
                    "used": row[5],
                    "listofer_number": row[6] if len(row) > 6 else None,
                }
            )
    except Exception as e:
        logger.error("scraps: %s", e)

    stock = []
    try:
        for row in StockModel.get_all(project_id=project_id) or []:
            stock.append(
                {
                    "id": row[0],
                    "project_id": row[1],
                    "diameter": row[2],
                    "length": row[3],
                    "quantity": row[4],
                    "grade": row[5] if len(row) > 5 else None,
                }
            )
    except Exception as e:
        logger.error("stock: %s", e)

    return {
        "format": "RebarAgent.ProjectBackup",
        "version": 1,
        "exported_at": datetime.datetime.now().isoformat(),
        "project": {"id": project_id, "name": project_name, "client": client},
        "listofers": listofers,
        "rebars": rebars,
        "scraps": scraps,
        "stock": stock,
    }


def save_project_backup(path: str, project_id: int, project_name: str = "", client: str = "") -> str:
    data = export_project_json(project_id, project_name, client)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_backup_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid backup file.")
    if data.get("format") not in (None, "RebarAgent.ProjectBackup"):
        if "rebars" not in data and "listofers" not in data:
            raise ValueError("Unrecognized backup format.")
    return data


def import_project_backup(
    path: str,
    new_name: Optional[str] = None,
    include_scraps: bool = True,
    include_stock: bool = True,
) -> Dict[str, Any]:
    data = load_backup_file(path)
    proj_meta = data.get("project") or {}
    name = (new_name or proj_meta.get("name") or "Restored Project").strip()
    client = (proj_meta.get("client") or "").strip()
    try:
        existing = {r[1] for r in (ProjectModel.get_all() or [])}
        base = name
        n = 2
        while name in existing:
            name = f"{base} ({n})"
            n += 1
    except Exception:
        pass

    project_id = ProjectModel.create(name, client or None)
    listofer_ids = {}

    for lf in data.get("listofers") or []:
        num = lf.get("number")
        if num is None or num == "":
            continue
        desc = lf.get("description") or ""
        try:
            lid = ListoferModel.get_or_create(project_id, str(num), desc)
            listofer_ids[str(num)] = lid
        except Exception as e:
            logger.error("import listofer %s: %s", num, e)

    rebar_count = 0
    for bar in data.get("rebars") or []:
        try:
            lf_num = str(bar.get("listofer") or "")
            if lf_num not in listofer_ids:
                lid = ListoferModel.get_or_create(
                    project_id, lf_num or "1", bar.get("listofer_desc") or ""
                )
                listofer_ids[lf_num or "1"] = lid
            lid = listofer_ids[lf_num or "1"]
            dims = bar.get("dimensions")
            if isinstance(dims, dict):
                dims_s = json.dumps(dims, ensure_ascii=False)
            else:
                dims_s = dims if dims is not None else "{}"
            RebarModel.add(
                lid,
                bar.get("pos") or "",
                float(bar.get("diameter") or 0),
                bar.get("shape_name") or "00",
                dims_s,
                int(bar.get("quantity") or 1),
                bar.get("location") or "",
                bar.get("element_type") or "",
                "import",
                datetime.datetime.now().isoformat()[:10],
                grade=bar.get("grade"),
                standard=bar.get("standard") or "bs",
            )
            rebar_count += 1
        except Exception as e:
            logger.error("import rebar: %s", e)

    scrap_count = 0
    if include_scraps:
        for s in data.get("scraps") or []:
            try:
                sid = ScrapModel.add_scrap(
                    project_id,
                    float(s.get("diameter") or 0),
                    float(s.get("length_mm") or 0),
                    grade=s.get("grade"),
                    listofer_number=s.get("listofer_number"),
                )
                if s.get("used") in (1, True, "1", "true"):
                    try:
                        ScrapModel.mark_as_used(sid)
                    except Exception:
                        pass
                scrap_count += 1
            except Exception as e:
                logger.error("import scrap: %s", e)

    stock_count = 0
    if include_stock:
        for s in data.get("stock") or []:
            try:
                StockModel.add(
                    project_id,
                    float(s.get("diameter") or 0),
                    float(s.get("length") or 0),
                    int(s.get("quantity") or 0),
                    grade=s.get("grade"),
                )
                stock_count += 1
            except Exception as e:
                logger.error("import stock: %s", e)

    return {
        "project_id": project_id,
        "name": name,
        "client": client,
        "listofers": len(listofer_ids),
        "rebars": rebar_count,
        "scraps": scrap_count,
        "stock": stock_count,
    }
