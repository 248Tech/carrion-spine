from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class DiffSummary:
    added: int
    removed: int

    def as_text(self) -> str:
        return f"+{self.added} -{self.removed}"


@dataclass(slots=True, frozen=True)
class DiffResult:
    full_text: str
    excerpt_text: str
    summary: DiffSummary
    is_truncated: bool


def count_diff_lines(diff_lines: list[str]) -> DiffSummary:
    added = 0
    removed = 0
    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return DiffSummary(added=added, removed=removed)


def generate_unified_diff(
    *,
    old_text: str,
    new_text: str,
    old_label: str = "original",
    new_label: str = "modified",
    context_lines: int = 3,
    excerpt_lines: int = 80,
) -> DiffResult:
    """Create full and excerpt diffs for Discord display."""
    diff_lines = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=old_label,
            tofile=new_label,
            n=context_lines,
            lineterm="",
        )
    )
    full = "\n".join(diff_lines) or "(no changes)"
    excerpt = "\n".join(diff_lines[:excerpt_lines]) or "(no changes)"
    return DiffResult(
        full_text=full,
        excerpt_text=excerpt,
        summary=count_diff_lines(diff_lines),
        is_truncated=len(diff_lines) > excerpt_lines,
    )


def write_diff_attachment(diff_text: str, out_path: Path) -> Path:
    """Persist long diff for upload as Discord attachment."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(diff_text, encoding="utf-8")
    return out_path

