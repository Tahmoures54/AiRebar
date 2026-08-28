# ui/cutting_plan_db.py
"""Persist cutting plans (draft/confirmed) and inventory ledger hooks."""
from __future__ import annotations

import datetime
import json
import hashlib
import sqlite3
from typing import Any, Optional

from config import DATABASE_FILE, DB_PATH
from db.models import ScrapModel
from utils.logger import setup_logger

logger = setup_logger("RebarAgent.CuttingPlanDB")


def _ensure_cutting_plans_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cutting_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                listofer_filter TEXT,
                stock_len REAL NOT NULL,
                data_hash TEXT NOT NULL,
                plans_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def _compute_data_hash(project_id, listofer_filter, stock_len):
    from db.models import RebarModel
    rebars = RebarModel.get_for_project(project_id, listofer_filter)
    scraps = ScrapModel.get_all_scraps(project_id)
    data_dict = {
        "project_id": project_id,
        "listofer_filter": listofer_filter,
        "stock_len": stock_len,
        "rebars": [
            {"id": r[0], "lf": r[1], "pos": r[3], "dia": r[4],
             "shape": r[5], "dims": r[6], "qty": r[7], "grade": r[12]}
            for r in rebars
        ],
        "scraps": [
            {"id": s[0], "dia": s[1], "len": s[2], "grade": s[3], "used": s[5], "lf": s[6]}
            for s in scraps
        ],
    }
    raw = json.dumps(data_dict, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_plan(project_id, listofer_filter, stock_len, data_hash):
    _ensure_cutting_plans_table()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(
                """SELECT plans_json, status FROM cutting_plans
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (project_id, listofer_filter, stock_len, data_hash),
            )
            row = cur.fetchone()
            if row:
                plans_json, status = row
                plans = json.loads(plans_json)
                restored = {}
                for key_str, value in plans.items():
                    if key_str.startswith("_") or not (key_str.startswith("(") and "," in key_str):
                        restored[key_str] = value
                        continue
                    try:
                        parts = key_str.strip("()").split(",", 1)
                        dia = float(parts[0].strip())
                        grade = parts[1].strip().strip("'\"")
                        restored[(dia, grade)] = value
                    except Exception:
                        restored[key_str] = value
                return restored, status
    except Exception as e:
        logger.warning(f"Failed to load cached plan: {e}")
    return None, None


def _save_plan(project_id, listofer_filter, stock_len, data_hash, plans_per_group, status="draft"):
    _ensure_cutting_plans_table()
    serializable = {}
    for key, data in plans_per_group.items():
        if isinstance(key, tuple) and len(key) == 2:
            dia, grade = key
            serializable[f"({dia}, '{grade}')"] = data
        else:
            serializable[str(key)] = data
    plans_json = json.dumps(serializable)
    now = datetime.datetime.now().isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """DELETE FROM cutting_plans
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?""",
                (project_id, listofer_filter, stock_len, data_hash),
            )
            conn.execute(
                """INSERT INTO cutting_plans
                   (project_id, listofer_filter, stock_len, data_hash, plans_json, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, listofer_filter, stock_len, data_hash, plans_json, status, now),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save plan: {e}")


def _confirm_plan(project_id, listofer_filter, stock_len, data_hash):
    _ensure_cutting_plans_table()
    now = datetime.datetime.now().isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """UPDATE cutting_plans SET status = 'confirmed', updated_at = ?
                   WHERE project_id = ? AND listofer_filter IS ? AND stock_len = ? AND data_hash = ?""",
                (now, project_id, listofer_filter, stock_len, data_hash),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to confirm plan: {e}")
