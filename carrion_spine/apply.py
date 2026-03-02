from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from .discovery import sha256_file


@dataclass(slots=True, frozen=True)
class ApplyResult:
    ok: bool
    message: str
    new_hash: str | None = None
    backup_path: str | None = None


def _ensure_inside_any_root(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve(strict=True)
    for root in roots:
        try:
            resolved.relative_to(root.resolve(strict=True))
            return True
        except ValueError:
            continue
    return False


def _rotate_backups(backup_dir: Path, stem: str, keep: int) -> None:
    candidates = sorted(backup_dir.glob(f"{stem}.*.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in candidates[keep:]:
        old.unlink(missing_ok=True)


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", delete=False, dir=path.parent, prefix=".mmtmp-") as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_path = Path(tmp.name)

    os.replace(temp_path, path)
    # Best effort: flush directory metadata.
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _apply_edit_sync(
    *,
    live_path: Path,
    edited_payload: bytes,
    expected_hash: str,
    allowed_roots: list[Path],
    backup_dir: Path,
    backup_keep: int,
) -> ApplyResult:
    if not live_path.exists():
        return ApplyResult(False, "Live file no longer exists.")
    if not _ensure_inside_any_root(live_path, allowed_roots):
        return ApplyResult(False, "Target file is outside configured roots.")

    current_hash = sha256_file(live_path)
    if current_hash != expected_hash:
        return ApplyResult(False, "Live file changed since pull. Re-run /mm config pull.")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup_path = backup_dir / f"{live_path.name}.{timestamp}.bak"
    backup_path.write_bytes(live_path.read_bytes())
    _rotate_backups(backup_dir, live_path.name, backup_keep)

    _atomic_write_bytes(live_path, edited_payload)
    return ApplyResult(True, "Applied atomically.", sha256_file(live_path), str(backup_path))


async def apply_edit(
    *,
    live_path: Path,
    edited_payload: bytes,
    expected_hash: str,
    allowed_roots: list[Path],
    backup_dir: Path,
    backup_keep: int,
) -> ApplyResult:
    """
    Conflict-safe apply:
    1) re-hash live file and compare with session hash
    2) rolling backup
    3) fsync + atomic rename
    """
    return await asyncio.to_thread(
        _apply_edit_sync,
        live_path=live_path,
        edited_payload=edited_payload,
        expected_hash=expected_hash,
        allowed_roots=allowed_roots,
        backup_dir=backup_dir,
        backup_keep=backup_keep,
    )

