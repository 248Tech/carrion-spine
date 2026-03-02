from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import discord

from .database import Database, EditSessionRecord
from .validation import reject_probably_binary


@dataclass(slots=True, frozen=True)
class SessionContext:
    session_id: str
    user_id: int
    nickname: str
    original_hash: str
    created_at: str


class SessionManager:
    """Manage edit session lifecycle and uploaded files."""

    def __init__(self, db: Database, upload_dir: Path, max_upload_bytes: int) -> None:
        self.db = db
        self.upload_dir = upload_dir
        self.max_upload_bytes = max_upload_bytes

    async def create_pending_session(
        self, *, user_id: int, nickname: str, original_hash: str
    ) -> SessionContext:
        session_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        record = EditSessionRecord(
            session_id=session_id,
            user_id=user_id,
            nickname=nickname,
            original_hash=original_hash,
            created_at=created_at,
            status="pending",
            uploaded_path=None,
        )
        await self.db.create_session(record)
        return SessionContext(
            session_id=session_id,
            user_id=user_id,
            nickname=nickname,
            original_hash=original_hash,
            created_at=created_at,
        )

    async def cancel_session(self, session_id: str) -> None:
        await self.db.update_session_status(session_id, "cancelled")

    async def mark_applied(self, session_id: str) -> None:
        await self.db.update_session_status(session_id, "applied")

    async def store_upload(self, session_id: str, attachment: discord.Attachment) -> Path:
        """
        Validate and persist uploaded edited file.

        Security checks:
        - size cap
        - basic binary rejection
        """
        if attachment.size > self.max_upload_bytes:
            raise ValueError(f"Upload too large (>{self.max_upload_bytes} bytes).")

        payload = await attachment.read()
        if reject_probably_binary(payload):
            raise ValueError("Binary files are not allowed.")

        out_path = self.upload_dir / f"{session_id}-{attachment.filename}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(out_path.write_bytes, payload)
        await self.db.update_session_status(session_id, "pending", str(out_path))
        return out_path

    @staticmethod
    def make_apply_custom_id(session_id: str) -> str:
        return f"mm_apply:{session_id}"

    @staticmethod
    def make_cancel_custom_id(session_id: str) -> str:
        return f"mm_cancel:{session_id}"

    @staticmethod
    def parse_custom_id(custom_id: str) -> tuple[str, str] | None:
        if ":" not in custom_id:
            return None
        action, session_id = custom_id.split(":", 1)
        if action not in {"mm_apply", "mm_cancel"}:
            return None
        return action, session_id

