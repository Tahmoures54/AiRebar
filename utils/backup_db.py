# utils/backup_db.py
"""Full SQLite database backup / restore (also re-exported from project_backup)."""

from __future__ import annotations

import datetime
import os
import shutil
import sqlite3
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("RebarAgent.BackupDB")


def backup_full_database(dest_path: Optional[str] = None, note: str = "") -> str:
    from db.database import db
    from config import DB_PATH

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if not dest_path:
        base = os.path.splitext(DB_PATH)[0]
        dest_path = f"{base}.backup-{ts}.db"
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
    try:
        dest = sqlite3.connect(dest_path)
        try:
            db.connection.backup(dest)
        finally:
            dest.close()
    except Exception as e:
        logger.warning("SQLite backup() failed (%s); copy2", e)
        try:
            db.connection.commit()
        except Exception:
            pass
        shutil.copy2(DB_PATH, dest_path)
    try:
        db.execute(
            "INSERT INTO backup_log(path, kind, created_at, note) VALUES (?, ?, ?, ?)",
            (dest_path, "full_db", datetime.datetime.now().isoformat(), note or ""),
            commit=True,
        )
    except Exception:
        pass
    logger.info("Full DB backup → %s", dest_path)
    return dest_path


def restore_full_database(src_path: str) -> str:
    from config import DB_PATH
    from db.database import DatabaseManager

    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)
    try:
        inst = DatabaseManager._instance
        if inst is not None:
            conn = getattr(getattr(inst, "_local", None), "connection", None)
            if conn is not None:
                conn.close()
                inst._local.connection = None
    except Exception as e:
        logger.warning("close before restore: %s", e)
    if os.path.isfile(DB_PATH):
        safety = DB_PATH + ".pre-restore-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(DB_PATH, safety)
        logger.info("Safety copy → %s", safety)
    shutil.copy2(src_path, DB_PATH)
    logger.info("Restored DB from %s", src_path)
    return DB_PATH
