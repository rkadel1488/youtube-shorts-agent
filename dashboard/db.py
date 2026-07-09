"""
SQLite storage for the dashboard: accounts (per-platform credentials,
encrypted) and jobs (run history/logs). Deliberately plain sqlite3 (stdlib)
— this app runs single-process on one VPS, no need for a heavier DB.
"""
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from crypto import decrypt_dict, encrypt_dict

DB_PATH = Path(os.getenv("DASHBOARD_DB_PATH", str(Path(__file__).parent / "dashboard.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL CHECK(platform IN ('youtube', 'meta')),
    label TEXT NOT NULL,
    credentials_enc TEXT NOT NULL,
    post_to_instagram INTEGER DEFAULT 1,   -- only meaningful for platform='meta'
    post_to_facebook INTEGER DEFAULT 1,    -- only meaningful for platform='meta'
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'trend',   -- 'trend' or 'clip'
    status TEXT NOT NULL DEFAULT 'running',  -- running | success | failed
    account_ids TEXT,                      -- JSON list of account ids targeted
    source TEXT,                           -- topic title, or source YouTube URL for clips
    result_json TEXT,                      -- JSON: per-platform post results
    log TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
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


# ── accounts ──────────────────────────────────────────────────────────────────

def add_account(platform: str, label: str, credentials: dict,
                post_to_instagram: bool = True, post_to_facebook: bool = True) -> int:
    if platform not in ("youtube", "meta"):
        raise ValueError(f"Unknown platform: {platform}")
    with conn() as c:
        cur = c.execute(
            "INSERT INTO accounts (platform, label, credentials_enc, post_to_instagram, "
            "post_to_facebook) VALUES (?,?,?,?,?)",
            (platform, label, encrypt_dict(credentials),
             int(post_to_instagram), int(post_to_facebook)),
        )
        return cur.lastrowid


def list_accounts(enabled_only: bool = False) -> list[dict]:
    q = "SELECT * FROM accounts"
    if enabled_only:
        q += " WHERE enabled = 1"
    q += " ORDER BY id"
    with conn() as c:
        rows = c.execute(q).fetchall()
    return [dict(r) for r in rows]


def get_account(account_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return dict(row) if row else None


def get_account_credentials(account_id: int) -> dict:
    acc = get_account(account_id)
    if not acc:
        raise ValueError(f"No account with id {account_id}")
    return decrypt_dict(acc["credentials_enc"])


def update_account_credentials(account_id: int, credentials: dict) -> None:
    """Used e.g. to persist a refreshed YouTube token after upload."""
    with conn() as c:
        c.execute("UPDATE accounts SET credentials_enc = ? WHERE id = ?",
                  (encrypt_dict(credentials), account_id))


def set_account_enabled(account_id: int, enabled: bool) -> None:
    with conn() as c:
        c.execute("UPDATE accounts SET enabled = ? WHERE id = ?", (int(enabled), account_id))


def delete_account(account_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM accounts WHERE id = ?", (account_id,))


# ── jobs ──────────────────────────────────────────────────────────────────────

def update_job_source(job_id: int, source: str) -> None:
    with conn() as c:
        c.execute("UPDATE jobs SET source = ? WHERE id = ?", (source, job_id))


def create_job(kind: str, account_ids: list[int], source: str = "") -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO jobs (kind, status, account_ids, source) VALUES (?,?,?,?)",
            (kind, "running", json.dumps(account_ids), source),
        )
        return cur.lastrowid


def finish_job(job_id: int, status: str, result: dict, log_text: str = "") -> None:
    with conn() as c:
        c.execute(
            "UPDATE jobs SET status=?, result_json=?, log=?, finished_at=? WHERE id=?",
            (status, json.dumps(result), log_text[-8000:], time.strftime("%Y-%m-%d %H:%M:%S"), job_id),
        )


def list_jobs(limit: int = 50) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_job(job_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


# ── settings (key/value, e.g. audience timezone) ──────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with conn() as c:
        c.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
