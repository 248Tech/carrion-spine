from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .database import ConfigRecord

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".ini": "ini",
}


@dataclass(slots=True, frozen=True)
class ConfigRoot:
    """One indexed root and its human token for filtering."""

    token: str
    path: Path


def sha256_file(path: Path) -> str:
    """Compute deterministic SHA-256 hash for file content."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return token or "cfg"


def build_nickname(path: Path, root: ConfigRoot) -> str:
    """
    Build stable nickname from filename + folder token.

    Example: `serverconfig-core` for /roots/core/serverconfig.xml.
    """
    stem = sanitize_token(path.stem)
    try:
        rel = path.parent.relative_to(root.path)
        folder_token = sanitize_token(rel.parts[0]) if rel.parts else sanitize_token(root.token)
    except ValueError:
        folder_token = sanitize_token(root.token)
    return f"{stem}-{folder_token}"


def disambiguate_nickname(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base
    i = 2
    while True:
        candidate = f"{base}-{i}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


def is_within_root(path: Path, root: Path) -> bool:
    """Windows-safe containment check to prevent traversal."""
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (ValueError, FileNotFoundError):
        return False


def _scan_configs_sync(
    roots: Iterable[ConfigRoot],
    *,
    id_start: int = 0,
) -> list[ConfigRecord]:
    used_nicknames: set[str] = set()
    records: list[ConfigRecord] = []
    running_id = id_start

    for root in roots:
        root_resolved = root.path.resolve()
        if not root_resolved.exists() or not root_resolved.is_dir():
            continue

        for path in sorted(root_resolved.rglob("*")):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            # Strictly enforce edits/indexing only inside configured roots.
            if not is_within_root(path, root_resolved):
                continue
            nickname = disambiguate_nickname(build_nickname(path, root), used_nicknames)
            stat = path.stat()
            running_id += 1
            records.append(
                ConfigRecord(
                    id=running_id,
                    nickname=nickname,
                    full_path=str(path.resolve()),
                    root_token=root.token,
                    file_type=SUPPORTED_EXTENSIONS[ext],
                    last_modified=stat.st_mtime,
                    file_hash=sha256_file(path),
                )
            )
    return records


async def scan_configs(roots: Iterable[ConfigRoot]) -> list[ConfigRecord]:
    """
    Recursively scan configured roots and return indexed records.

    TODO: Optional watchdog-based incremental indexing.
    """
    return await asyncio.to_thread(_scan_configs_sync, list(roots))

