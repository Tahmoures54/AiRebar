# db/database.py
"""
Database Manager – AI Rebar
Handles SQLite connection, table creation, and provides
a central execute/fetch interface.
"""

import sqlite3
import threading
import os
from config import DB_PATH


class DatabaseManager:
    """Thread‑safe singleton‑like manager for SQLite access."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path=None):
        if getattr(self, "_initialised", False):
            return

        self.db_path = db_path or DB_PATH

        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._local = threading.local()
        self._initialised = True
        self._create_tables()

    @property
    def connection(self):
        # thread-local connection
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path, timeout=30)
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
        return self._local.connection

    def _create_tables(self):
        conn = self.connection
        cursor = conn.cursor()

        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client TEXT,
                last_accessed TEXT
            );

            CREATE TABLE IF NOT EXISTS listofers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                number TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS rebars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listofer_id INTEGER NOT NULL,
                pos TEXT,
                diameter REAL NOT NULL,
                shape_name TEXT,
                dimensions TEXT,
                quantity INTEGER DEFAULT 1,
                location TEXT,
                element_type TEXT,
                added_by TEXT,
                date_added TEXT,
                grade TEXT DEFAULT 'A3',
                standard TEXT DEFAULT 'bs',
                FOREIGN KEY (listofer_id) REFERENCES listofers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS scraps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                diameter REAL NOT NULL,
                length_mm REAL NOT NULL,
                grade TEXT DEFAULT 'A3',
                date_created TEXT,
                used INTEGER DEFAULT 0,
                listofer_number TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                diameter REAL NOT NULL,
                length REAL NOT NULL,     -- mm
                quantity INTEGER DEFAULT 0,
                grade TEXT DEFAULT 'A3',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS custom_shapes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                definition TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cutting_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                listofer_filter TEXT,
                stock_length_m REAL NOT NULL,
                data_hash TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cutting_plan_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                bar_index INTEGER NOT NULL,
                bar_length_m REAL NOT NULL,
                is_scrap INTEGER DEFAULT 0,
                FOREIGN KEY (plan_id) REFERENCES cutting_plans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cutting_plan_pieces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bar_id INTEGER NOT NULL,
                piece_index INTEGER NOT NULL,
                length_m REAL NOT NULL,
                pos TEXT,
                listofer_no TEXT,
                dia REAL,
                grade TEXT,
                FOREIGN KEY (bar_id) REFERENCES cutting_plan_bars(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cutting_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                listofer_number TEXT NOT NULL,
                rebar_id INTEGER NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (rebar_id) REFERENCES rebars(id) ON DELETE CASCADE
            );

            -- Helpful indexes (speed)
            CREATE INDEX IF NOT EXISTS idx_listofers_project ON listofers(project_id);
            CREATE INDEX IF NOT EXISTS idx_rebars_listofer   ON rebars(listofer_id);
            CREATE INDEX IF NOT EXISTS idx_scraps_proj_dia_used ON scraps(project_id, diameter, used);
            CREATE INDEX IF NOT EXISTS idx_stock_proj_dia ON stock(project_id, diameter);
            """
        )
        conn.commit()

    def setup_database(self):
        self._create_tables()

    def execute(self, query, params=(), commit=False):
        conn = self.connection
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        return cursor.lastrowid

    def fetchone(self, query, params=()):
        conn = self.connection
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        conn = self.connection
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def close(self):
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


# Singleton instance
db = DatabaseManager()