"""SQLite persistence for user profiles, sessions, and saved work.

Pure data access — no request or business logic (that lives in ``auth.py`` and
the routes). Tables are created lazily on first connection (idempotent), so
callers just import and use. The database file path comes from ``COSMIC_DB_PATH``
and defaults to ``data/cosmic.db`` under the project root.
"""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB = os.path.join(_ROOT, "data", "cosmic.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    theme         TEXT,
    is_admin      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_searches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    params     TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_uploads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename   TEXT NOT NULL,
    kind       TEXT,
    result     TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS custom_objects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL,
    x_norm     REAL NOT NULL,
    y_norm     REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""

# Which paths we've already run the schema against (schema is idempotent).
_initialized: set = set()


def _db_path() -> str:
    return os.environ.get("COSMIC_DB_PATH", _DEFAULT_DB)


def get_conn() -> sqlite3.Connection:
    """Open a connection, creating the schema on first use for this path."""
    path = _db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path not in _initialized:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
        _initialized.add(path)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that post-date the original schema, for existing databases."""
    user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "theme" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN theme TEXT")
    if "is_admin" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── users ─────────────────────────────────────────────────────────────────────
def create_user(
    username: str,
    email: Optional[str],
    password_hash: str,
    salt: str,
    is_admin: bool = False,
) -> int:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, salt, created_at, "
            "is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, password_hash, salt, _now(), int(is_admin)),
        )
        conn.commit()
        return cur.lastrowid


def set_user_admin(user_id: int, is_admin: bool) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?", (int(is_admin), user_id)
        )
        conn.commit()


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def set_user_theme(user_id: int, theme: str) -> None:
    """Persist the user's chosen UI theme to their profile."""
    with closing(get_conn()) as conn:
        conn.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user_id))
        conn.commit()


# ── sessions ──────────────────────────────────────────────────────────────────
def create_session(user_id: int, token_hash: str) -> None:
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at) VALUES (?, ?, ?)",
            (token_hash, user_id, _now()),
        )
        conn.commit()


def get_user_by_token(token_hash: str) -> Optional[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id "
            "WHERE s.token_hash = ?",
            (token_hash,),
        ).fetchone()


def delete_session(token_hash: str) -> None:
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()


# ── saved searches ────────────────────────────────────────────────────────────
def add_search(user_id: int, name: str, params: dict) -> int:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO saved_searches (user_id, name, params, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, name, json.dumps(params), _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_searches(user_id: int) -> list:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM saved_searches WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_search_dict(r) for r in rows]


def delete_search(user_id: int, search_id: int) -> bool:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "DELETE FROM saved_searches WHERE id = ? AND user_id = ?",
            (search_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def _search_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "params": json.loads(row["params"]),
        "created_at": row["created_at"],
    }


# ── saved uploads ─────────────────────────────────────────────────────────────
def add_upload(user_id: int, filename: str, kind: Optional[str], result: dict) -> int:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO saved_uploads (user_id, filename, kind, result, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, filename, kind, json.dumps(result), _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_uploads(user_id: int) -> list:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM saved_uploads WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_upload_dict(r) for r in rows]


def delete_upload(user_id: int, upload_id: int) -> bool:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "DELETE FROM saved_uploads WHERE id = ? AND user_id = ?",
            (upload_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def _upload_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "kind": row["kind"],
        "result": json.loads(row["result"]),
        "created_at": row["created_at"],
    }


# ── custom scene objects ──────────────────────────────────────────────────────
def add_custom_object(
    user_id: int, name: str, kind: str, x_norm: float, y_norm: float
) -> int:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO custom_objects (user_id, name, kind, x_norm, y_norm, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, kind, x_norm, y_norm, _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_custom_objects(user_id: int) -> list:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM custom_objects WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return [_custom_object_dict(r) for r in rows]


def delete_custom_object(user_id: int, object_id: int) -> bool:
    with closing(get_conn()) as conn:
        cur = conn.execute(
            "DELETE FROM custom_objects WHERE id = ? AND user_id = ?",
            (object_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def _custom_object_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row["kind"],
        "x_norm": row["x_norm"],
        "y_norm": row["y_norm"],
        "created_at": row["created_at"],
    }
