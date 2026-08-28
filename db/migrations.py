# db/migrations.py
"""Versioned SQLite schema migrations for RebarAgent."""

from __future__ import annotations

import logging
import sqlite3
from typing import Callable, List, Tuple

logger = logging.getLogger("RebarAgent.Migrations")

SCHEMA_VERSION = 3


def _table_columns(conn: sqlite3.Connection, table: str) -> set:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r[1] for r in rows}
    except Exception:
        return set()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    cols = _table_columns(conn, table)
    if column not in cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
            logger.info("Added column %s.%s", table, column)
        except sqlite3.OperationalError as e:
            logger.warning("Could not add %s.%s: %s", table, column, e)


def migrate_to_1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS inventory_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            created_at TEXT NOT NULL,
            rolled_back INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_listofers_project ON listofers(project_id);
        CREATE INDEX IF NOT EXISTS idx_rebars_listofer ON rebars(listofer_id);
        CREATE INDEX IF NOT EXISTS idx_scraps_project ON scraps(project_id);
        CREATE INDEX IF NOT EXISTS idx_stock_project ON stock(project_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_project ON inventory_ledger(project_id);
        """
    )


def migrate_to_2(conn: sqlite3.Connection) -> None:
    _add_column_if_missing(conn, "rebars", "grade", "TEXT DEFAULT 'A3'")
    _add_column_if_missing(conn, "rebars", "standard", "TEXT DEFAULT 'bs'")
    _add_column_if_missing(conn, "projects", "created_at", "TEXT")
    _add_column_if_missing(conn, "projects", "notes", "TEXT")
    _add_column_if_missing(conn, "stock", "grade", "TEXT DEFAULT 'A3'")
    _add_column_if_missing(conn, "scraps", "listofer_number", "TEXT")


def migrate_to_3(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS backup_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL,
            note TEXT
        );
        """
    )
    _add_column_if_missing(conn, "cutting_plans", "data_hash", "TEXT")
    _add_column_if_missing(conn, "cutting_plans", "confirmed", "INTEGER DEFAULT 0")


MIGRATIONS: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, migrate_to_1),
    (2, migrate_to_2),
    (3, migrate_to_3),
]


def get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT)")
        row = conn.execute("SELECT value FROM app_meta WHERE key = 'schema_version'").fetchone()
        if row and str(row[0]).isdigit():
            return int(row[0])
    except Exception as e:
        logger.warning("Could not read schema_version: %s", e)
    return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT INTO app_meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(version),),
    )


def run_migrations(conn: sqlite3.Connection) -> int:
    current = get_schema_version(conn)
    if current > SCHEMA_VERSION:
        logger.warning("DB schema_version=%s newer than app %s", current, SCHEMA_VERSION)
        return current
    for target, fn in MIGRATIONS:
        if current >= target:
            continue
        logger.info("Running migration → v%s (%s)", target, fn.__name__)
        try:
            fn(conn)
            set_schema_version(conn, target)
            conn.commit()
            current = target
            logger.info("Migration v%s OK", target)
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.error("Migration v%s failed: %s", target, e, exc_info=True)
            try:
                set_schema_version(conn, target)
                conn.commit()
                current = target
            except Exception:
                pass
    if current < SCHEMA_VERSION:
        try:
            set_schema_version(conn, SCHEMA_VERSION)
            conn.commit()
            current = SCHEMA_VERSION
        except Exception:
            pass
    return current
