"""
SQLite storage for the AI Shorts Maker: just render history (no accounts,
no credentials — this tool only generates videos for you to download and
post yourself, nothing auto-posts anywhere).
"""
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("DASHBOARD_DB_PATH", str(Path(__file__).parent / "dashboard.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS renders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'youtube',   -- 'youtube' or 'upload'
    status TEXT NOT NULL DEFAULT 'running', -- running | success | failed
    source TEXT,                            -- YouTube URL, or original uploaded filename
    hook_title TEXT,                        -- Claude's chosen hook title (youtube mode only)
    output_path TEXT,                       -- path to the finished vertical mp4
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def create_render(kind: str, source: str = "") -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO renders (kind, status, source) VALUES (?,?,?)",
            (kind, "running", source),
        )
        return cur.lastrowid


def finish_render(render_id: int, status: str, output_path: str = "",
                  hook_title: str = "", error: str = "") -> None:
    with conn() as c:
        c.execute(
            "UPDATE renders SET status=?, output_path=?, hook_title=?, error=?, "
            "finished_at=? WHERE id=?",
            (status, output_path, hook_title, error,
             time.strftime("%Y-%m-%d %H:%M:%S"), render_id),
        )


def list_renders(limit: int = 50) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM renders ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_render(render_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM renders WHERE id = ?", (render_id,)).fetchone()
    return dict(row) if row else None
