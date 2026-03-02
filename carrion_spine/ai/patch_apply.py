"""Apply a single-file unified diff to baseline. MVP: line-by-line hunk application."""

from __future__ import annotations

import re
from typing import List


def apply_unified_patch(baseline: str, patch: str) -> str:
    """
    Apply a single-file unified diff to baseline. Returns patched content.
    Raises ValueError if patch cannot be applied.
    """
    baseline_lines = baseline.splitlines()
    result: List[str] = list(baseline_lines)
    lines = patch.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*(?:@@)?", line)
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            i += 1
            new_lines: List[str] = []
            while i < len(lines):
                cur = lines[i]
                if cur.startswith("@@"):
                    break
                if cur.startswith("+"):
                    if not cur.startswith("+++"):
                        new_lines.append(cur[1:])
                elif cur.startswith("-"):
                    pass  # removed line
                else:
                    new_lines.append(cur[1:] if cur.startswith(" ") else cur)
                i += 1
            # 1-based to 0-based
            idx = old_start - 1
            if idx < 0:
                idx = 0
            # Replace old_count lines with new_lines
            head = result[:idx]
            tail = result[idx + old_count:]
            result = head + new_lines + tail
            continue
        i += 1
    return "\n".join(result)
