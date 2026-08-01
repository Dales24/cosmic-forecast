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
-- Every per-user lookup filters on user_id; without these SQLite full-scans the
-- table. (`sessions.token_hash` and `users.username` are already indexed by
-- their PRIMARY KEY / UNIQUE constraints.)
CREATE INDEX IF NOT EXISTS idx_sessions_user       ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_searches_user       ON saved_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_user        ON saved_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_objects_user ON custom_objects(user_id);
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


# ── Owned-row helpers ─────────────────────────────────────────────────────────
# Saved searches, uploads and custom objects are all "rows belonging to a user"
# and were three copies of the same insert/list/delete. Sharing them keeps the
# `AND user_id = ?` ownership check in one place, where it can't be forgotten
# when a fourth table is added.
#
# Table and column names here are module-private literals, never caller input —
# only values are ever parameterised.


def _insert_owned(table: str, columns: tuple[str, ...], values: tuple) -> int:
    """Insert one row with a `created_at` stamp; returns the new row id."""
    placeholders = ", ".join("?" for _ in range(len(columns) + 1))
    with closing(get_conn()) as conn:
        cur = conn.execute(
            f"INSERT INTO {table} ({', '.join(columns)}, created_at) "
            f"VALUES ({placeholders})",
            (*values, _now()),
        )
        conn.commit()
        return cur.lastrowid


def _list_owned(table: str, user_id: int, to_dict) -> list:
    """Every row this user owns, newest first."""
    with closing(get_conn()) as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE user_id = ? ORDER BY id DESC", (user_id,)
        ).fetchall()
    return [to_dict(row) for row in rows]


def _delete_owned(table: str, user_id: int, row_id: int) -> bool:
    """Delete one row only if this user owns it. False when there was no match."""
    with closing(get_conn()) as conn:
        cur = conn.execute(
            f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (row_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


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
    return _insert_owned(
        "saved_searches",
        ("user_id", "name", "params"),
        (user_id, name, json.dumps(params)),
    )


def list_searches(user_id: int) -> list:
    return _list_owned("saved_searches", user_id, _search_dict)


def delete_search(user_id: int, search_id: int) -> bool:
    return _delete_owned("saved_searches", user_id, search_id)


def _search_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "params": json.loads(row["params"]),
        "created_at": row["created_at"],
    }


# ── saved uploads ─────────────────────────────────────────────────────────────
def add_upload(user_id: int, filename: str, kind: Optional[str], result: dict) -> int:
    return _insert_owned(
        "saved_uploads",
        ("user_id", "filename", "kind", "result"),
        (user_id, filename, kind, json.dumps(result)),
    )


def list_uploads(user_id: int) -> list:
    return _list_owned("saved_uploads", user_id, _upload_dict)


def delete_upload(user_id: int, upload_id: int) -> bool:
    return _delete_owned("saved_uploads", user_id, upload_id)


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
    return _insert_owned(
        "custom_objects",
        ("user_id", "name", "kind", "x_norm", "y_norm"),
        (user_id, name, kind, x_norm, y_norm),
    )


def list_custom_objects(user_id: int) -> list:
    return _list_owned("custom_objects", user_id, _custom_object_dict)


def delete_custom_object(user_id: int, object_id: int) -> bool:
    return _delete_owned("custom_objects", user_id, object_id)


def _custom_object_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "kind": row["kind"],
        "x_norm": row["x_norm"],
        "y_norm": row["y_norm"],
        "created_at": row["created_at"],
    }
