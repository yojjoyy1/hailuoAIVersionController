from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'user',
    session_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS blobs (
    hash TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    content BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS record_files (
    record_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    hash TEXT NOT NULL,
    size INTEGER NOT NULL,
    PRIMARY KEY (record_id, path),
    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY (hash) REFERENCES blobs(hash)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    agent TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    baseline_record_id INTEGER,
    FOREIGN KEY (baseline_record_id) REFERENCES records(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    project_name TEXT NOT NULL,
    current_record_id INTEGER,
    active_session_id INTEGER,
    agent_kind TEXT NOT NULL DEFAULT 'cursor',
    FOREIGN KEY (current_record_id) REFERENCES records(id),
    FOREIGN KEY (active_session_id) REFERENCES sessions(id)
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path(root: Path) -> Path:
    return root / ".avc" / "avc.sqlite"


def migrate(conn: sqlite3.Connection) -> None:
    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    if "state" in tables:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(state)").fetchall()}
        if "agent_kind" not in cols:
            conn.execute(
                "ALTER TABLE state ADD COLUMN agent_kind TEXT NOT NULL DEFAULT 'cursor'"
            )
    if "sessions" in tables:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "agent" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN agent TEXT NOT NULL DEFAULT ''")


def connect(root: Path) -> sqlite3.Connection:
    path = db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


def init_db(root: Path, project_name: str, agent_kind: str = "cursor") -> sqlite3.Connection:
    conn = connect(root)
    conn.executescript(SCHEMA)
    migrate(conn)
    row = conn.execute("SELECT id FROM state WHERE id = 1").fetchone()
    if not row:
        conn.execute(
            "INSERT INTO state (id, project_name, current_record_id, active_session_id, agent_kind) VALUES (1, ?, NULL, NULL, ?)",
            (project_name, agent_kind),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '2')"
        )
    else:
        conn.execute(
            "UPDATE state SET project_name = ?, agent_kind = ? WHERE id = 1",
            (project_name, agent_kind),
        )
    conn.commit()
    return conn


def is_initialized(root: Path) -> bool:
    return db_path(root).is_file()
