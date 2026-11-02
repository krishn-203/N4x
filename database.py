"""
N4X Bot — SQLite storage layer.
Channels, connected admins aur upload history yahan save hoti hai.
"""

import sqlite3
import threading
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    chat_id      INTEGER PRIMARY KEY,
    username     TEXT,
    title        TEXT,
    owner_name   TEXT,
    admin_phone  TEXT,
    connected_by INTEGER NOT NULL,
    connected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    full_name  TEXT,
    first_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    file_name   TEXT,
    file_type   TEXT,
    file_size   INTEGER,
    title       TEXT,
    description TEXT,
    message_id  INTEGER,
    created_at  TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%d/%m/%Y %I:%M %p")


class Database:
    """Thread-safe thin wrapper around sqlite3."""

    def __init__(self, path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------- users
    def touch_user(self, user_id: int, username: str | None, full_name: str) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO users (user_id, username, full_name, first_seen)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     username = excluded.username,
                     full_name = excluded.full_name""",
                (user_id, username, full_name, now()),
            )
            self._conn.commit()

    # ------------------------------------------------------------- channels
    def channel_of(self, user_id: int):
        """Is user ne jo channel connect kiya hai (ya None)."""
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM channels WHERE connected_by = ?", (user_id,)
            ).fetchone()

    def channel_by_chat(self, chat_id: int):
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM channels WHERE chat_id = ?", (chat_id,)
            ).fetchone()

    def save_channel(self, chat_id: int, username: str | None, title: str,
                     owner_name: str, admin_phone: str, connected_by: int) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO channels
                     (chat_id, username, title, owner_name, admin_phone, connected_by, connected_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET
                     username    = excluded.username,
                     title       = excluded.title,
                     owner_name  = excluded.owner_name,
                     admin_phone = excluded.admin_phone,
                     connected_by = excluded.connected_by,
                     connected_at = excluded.connected_at""",
                (chat_id, username, title, owner_name, admin_phone, connected_by, now()),
            )
            self._conn.commit()

    def delete_channel(self, chat_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
            self._conn.commit()

    # ------------------------------------------------------------- uploads
    def log_upload(self, chat_id: int, user_id: int, file_name: str, file_type: str,
                   file_size: int, title: str, description: str, message_id: int) -> int:
        with self._lock:
            cur = self._conn.execute(
                """INSERT INTO uploads
                     (chat_id, user_id, file_name, file_type, file_size,
                      title, description, message_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (chat_id, user_id, file_name, file_type, file_size,
                 title, description, message_id, now()),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def upload_count(self, chat_id: int) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM uploads WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return int(row["c"])

    def recent_uploads(self, chat_id: int, limit: int = 10):
        with self._lock:
            return self._conn.execute(
                """SELECT * FROM uploads WHERE chat_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (chat_id, limit),
            ).fetchall()
