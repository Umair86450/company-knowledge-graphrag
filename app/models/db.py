# app/models/db.py

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_connection() -> sqlite3.Connection:
    db_path = _project_root() / "database" / "chat.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db() -> None:
    schema_path = _project_root() / "database" / "schema.sql"

    with schema_path.open("r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_connection() as conn:
        conn.executescript(schema_sql)


def get_or_create_user(username: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if row:
            return int(row["id"])

        cur = conn.execute(
            "INSERT INTO users (username) VALUES (?)",
            (username,),
        )
        return int(cur.lastrowid)


def create_session(user_id: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (user_id) VALUES (?)",
            (user_id,),
        )
        return int(cur.lastrowid)


def update_claude_session(session_id: int, claude_session_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET claude_session_id = ? WHERE id = ?",
            (claude_session_id, session_id),
        )


def get_session(session_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

        return dict(row) if row else None


def add_message(session_id: int, role: str, content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )


def get_messages(session_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

        return [dict(row) for row in rows]