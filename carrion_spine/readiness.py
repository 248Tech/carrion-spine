"""Readiness checks for roots, backup dir, SQLite path. Used by CLI doctor and /mm spine setup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .discovery import ConfigRoot


@dataclass(slots=True, frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str


def run_readiness_checks(
    *,
    roots: Sequence[ConfigRoot],
    backup_dir: Path,
    data_dir: Path,
    sqlite_path: Path,
) -> list[CheckResult]:
    """Run all readiness checks; return list of results. No I/O in event loop (run in thread)."""
    results: list[CheckResult] = []

    for root in roots:
        p = root.path
        if not p.exists():
            results.append(CheckResult("root:" + root.token, False, f"{p} does not exist"))
        elif not p.is_dir():
            results.append(CheckResult("root:" + root.token, False, f"{p} is not a directory"))
        else:
            try:
                (p / ".spine_check").write_text("")
                (p / ".spine_check").unlink()
                results.append(CheckResult("root:" + root.token, True, f"{p} exists and is RW"))
            except OSError as e:
                results.append(CheckResult("root:" + root.token, False, f"{p} not writable: {e}"))

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / ".spine_check").write_text("")
        (backup_dir / ".spine_check").unlink()
        results.append(CheckResult("backup_dir", True, f"{backup_dir} OK"))
    except OSError as e:
        results.append(CheckResult("backup_dir", False, f"Cannot create or write: {e}"))

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        if sqlite_path.exists():
            sqlite_path.touch()
        else:
            sqlite_path.write_text("")
            sqlite_path.unlink()
        results.append(CheckResult("sqlite", True, f"{sqlite_path} writable"))
    except OSError as e:
        results.append(CheckResult("sqlite", False, f"Not writable: {e}"))

    return results
