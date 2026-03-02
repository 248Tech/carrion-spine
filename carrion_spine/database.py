from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS config_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL UNIQUE,
    full_path TEXT NOT NULL UNIQUE,
    root_token TEXT NOT NULL,
    file_type TEXT NOT NULL,
    last_modified REAL NOT NULL,
    file_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_config_index_root_token ON config_index(root_token);
CREATE INDEX IF NOT EXISTS idx_config_index_file_type ON config_index(file_type);

CREATE TABLE IF NOT EXISTS edit_sessions (
    session_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    nickname TEXT NOT NULL,
    original_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'applied', 'cancelled')),
    uploaded_path TEXT,
    FOREIGN KEY(nickname) REFERENCES config_index(nickname)
);

CREATE INDEX IF NOT EXISTS idx_edit_sessions_user ON edit_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_edit_sessions_status ON edit_sessions(status);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    nickname TEXT NOT NULL,
    full_path TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    diff_summary TEXT,
    status TEXT NOT NULL,
    validation_result TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_nickname ON audit_log(nickname);

CREATE TABLE IF NOT EXISTS spine_state (
    guild_id INTEGER PRIMARY KEY,
    audit_channel_id INTEGER,
    updated_at TEXT NOT NULL
);
"""


@dataclass(slots=True, frozen=True)
class ConfigRecord:
    id: int
    nickname: str
    full_path: str
    root_token: str
    file_type: str
    last_modified: float
    file_hash: str


@dataclass(slots=True, frozen=True)
class EditSessionRecord:
    session_id: str
    user_id: int
    nickname: str
    original_hash: str
    created_at: str
    status: str
    uploaded_path: str | None


class Database:
    """SQLite data access with thread-offloaded API for async code."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)

    async def replace_index_records(self, records: Iterable[ConfigRecord]) -> None:
        await asyncio.to_thread(self._replace_index_records_sync, list(records))

    def _replace_index_records_sync(self, records: list[ConfigRecord]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM config_index")
            conn.executemany(
                """
                INSERT INTO config_index (
                    nickname, full_path, root_token, file_type, last_modified, file_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.nickname,
                        r.full_path,
                        r.root_token,
                        r.file_type,
                        r.last_modified,
                        r.file_hash,
                    )
                    for r in records
                ],
            )

    async def list_configs(self, root_filter: str | None = None) -> list[ConfigRecord]:
        return await asyncio.to_thread(self._list_configs_sync, root_filter)

    def _list_configs_sync(self, root_filter: str | None) -> list[ConfigRecord]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if root_filter:
                rows = conn.execute(
                    """
                    SELECT id, nickname, full_path, root_token, file_type, last_modified, file_hash
                    FROM config_index
                    WHERE root_token = ?
                    ORDER BY nickname
                    """,
                    (root_filter,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, nickname, full_path, root_token, file_type, last_modified, file_hash
                    FROM config_index
                    ORDER BY nickname
                    """
                ).fetchall()
        return [ConfigRecord(**dict(row)) for row in rows]

    async def get_config_by_nickname(self, nickname: str) -> ConfigRecord | None:
        return await asyncio.to_thread(self._get_config_by_nickname_sync, nickname)

    def _get_config_by_nickname_sync(self, nickname: str) -> ConfigRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT id, nickname, full_path, root_token, file_type, last_modified, file_hash
                FROM config_index
                WHERE nickname = ?
                """,
                (nickname,),
            ).fetchone()
        if not row:
            return None
        return ConfigRecord(**dict(row))

    async def create_session(self, session: EditSessionRecord) -> None:
        await asyncio.to_thread(self._create_session_sync, session)

    def _create_session_sync(self, session: EditSessionRecord) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO edit_sessions (
                    session_id, user_id, nickname, original_hash, created_at, status, uploaded_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.user_id,
                    session.nickname,
                    session.original_hash,
                    session.created_at,
                    session.status,
                    session.uploaded_path,
                ),
            )

    async def get_session(self, session_id: str) -> EditSessionRecord | None:
        return await asyncio.to_thread(self._get_session_sync, session_id)

    def _get_session_sync(self, session_id: str) -> EditSessionRecord | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT session_id, user_id, nickname, original_hash, created_at, status, uploaded_path
                FROM edit_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if not row:
            return None
        return EditSessionRecord(**dict(row))

    async def update_session_status(
        self, session_id: str, status: str, uploaded_path: str | None = None
    ) -> None:
        await asyncio.to_thread(self._update_session_status_sync, session_id, status, uploaded_path)

    def _update_session_status_sync(
        self, session_id: str, status: str, uploaded_path: str | None
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE edit_sessions
                SET status = ?, uploaded_path = COALESCE(?, uploaded_path)
                WHERE session_id = ?
                """,
                (status, uploaded_path, session_id),
            )

    async def insert_audit(
        self,
        *,
        user_id: int,
        nickname: str,
        full_path: str,
        timestamp: str,
        diff_summary: str | None,
        status: str,
        validation_result: str,
    ) -> None:
        await asyncio.to_thread(
            self._insert_audit_sync,
            user_id,
            nickname,
            full_path,
            timestamp,
            diff_summary,
            status,
            validation_result,
        )

    def _insert_audit_sync(
        self,
        user_id: int,
        nickname: str,
        full_path: str,
        timestamp: str,
        diff_summary: str | None,
        status: str,
        validation_result: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    user_id, nickname, full_path, timestamp, diff_summary, status, validation_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, nickname, full_path, timestamp, diff_summary, status, validation_result),
            )

    async def get_audit_channel_id(self, guild_id: int) -> int | None:
        return await asyncio.to_thread(self._get_audit_channel_id_sync, guild_id)

    def _get_audit_channel_id_sync(self, guild_id: int) -> int | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT audit_channel_id FROM spine_state WHERE guild_id = ?",
                (guild_id,),
            ).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    async def set_audit_channel(self, guild_id: int, channel_id: int | None) -> None:
        await asyncio.to_thread(self._set_audit_channel_sync, guild_id, channel_id)

    def _set_audit_channel_sync(self, guild_id: int, channel_id: int | None) -> None:
        from datetime import UTC, datetime
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO spine_state (guild_id, audit_channel_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    audit_channel_id = excluded.audit_channel_id,
                    updated_at = excluded.updated_at
                """,
                (guild_id, channel_id, datetime.now(UTC).isoformat()),
            )

    async def get_last_applied(self, nickname: str) -> str | None:
        return await asyncio.to_thread(self._get_last_applied_sync, nickname)

    def _get_last_applied_sync(self, nickname: str) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT timestamp FROM audit_log
                WHERE nickname = ? AND status = 'applied'
                ORDER BY timestamp DESC LIMIT 1
                """,
                (nickname,),
            ).fetchone()
        return str(row[0]) if row else None

