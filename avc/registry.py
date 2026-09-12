from __future__ import annotations

import sqlite3
from pathlib import Path

from avc.db import utcnow

REGISTRY = Path.home() / ".avc" / "registry.sqlite"


def connect_registry() -> sqlite3.Connection:
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(REGISTRY))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            root_path TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            last_opened_at TEXT NOT NULL
        );
        """
    )
    return conn


def register_project(root: Path, name: str) -> dict:
    root = root.resolve()
    conn = connect_registry()
    try:
        now = utcnow()
        existing = conn.execute(
            "SELECT id FROM projects WHERE root_path = ?", (str(root),)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE projects SET name = ?, last_opened_at = ? WHERE id = ?",
                (name, now, existing["id"]),
            )
            pid = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO projects (name, root_path, created_at, last_opened_at) VALUES (?, ?, ?, ?)",
                (name, str(root), now, now),
            )
            pid = cur.lastrowid
        conn.commit()
        return {"id": pid, "name": name, "root": str(root)}
    finally:
        conn.close()


def list_projects() -> list[dict]:
    conn = connect_registry()
    try:
        rows = conn.execute(
            "SELECT id, name, root_path, created_at, last_opened_at FROM projects ORDER BY last_opened_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "root": r["root_path"],
                "created_at": r["created_at"],
                "last_opened_at": r["last_opened_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_project(project_id: int) -> dict:
    conn = connect_registry()
    try:
        row = conn.execute(
            "SELECT id, name, root_path FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if not row:
            raise KeyError(project_id)
        conn.execute(
            "UPDATE projects SET last_opened_at = ? WHERE id = ?",
            (utcnow(), project_id),
        )
        conn.commit()
        return {"id": row["id"], "name": row["name"], "root": row["root_path"]}
    finally:
        conn.close()


def remove_project(project_id: int) -> None:
    conn = connect_registry()
    try:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()


def find_by_root(root: Path) -> dict | None:
    conn = connect_registry()
    try:
        row = conn.execute(
            "SELECT id, name, root_path FROM projects WHERE root_path = ?",
            (str(root.resolve()),),
        ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "name": row["name"], "root": row["root_path"]}
    finally:
        conn.close()
