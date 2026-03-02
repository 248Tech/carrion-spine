"""Strict output contracts for patch (unified diff only) and full (file content only)."""

from __future__ import annotations

import re
from typing import Tuple


# Unified diff: must contain at least one hunk (@@ -start,count +start,count)
_HUNK = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*", re.MULTILINE)

# Markdown code fences (we reject these in full mode)
_FENCE = re.compile(r"^```[\w]*\s*\n", re.MULTILINE)


def validate_patch_output(raw: str, max_bytes: int = 200_000) -> Tuple[str | None, str]:
    """
    Validate that output is a single-file unified diff only.
    Returns (normalized_diff, "") on success, (None, error_message) on failure.
    """
    if not raw or not raw.strip():
        return None, "Empty output; expected unified diff only."
    if len(raw.encode("utf-8")) > max_bytes:
        return None, f"Patch output exceeds max size ({max_bytes} bytes)."
    stripped = raw.strip()
    lines = stripped.splitlines()
    if not lines:
        return None, "No lines in output."
    # Must look like unified diff: --- / +++ lines and at least one @@ hunk
    if not stripped.startswith("--- ") and not any(line.startswith("--- ") for line in lines[:5]):
        return None, "Output does not look like a unified diff (missing ---/+++)."
    if not any(line.startswith("@@") for line in lines):
        return None, "Output does not contain a diff hunk (@@)."
    # Reject if it contains obvious non-diff content (e.g. markdown or commentary)
    for i, line in enumerate(lines[:20]):
        if line.strip() and not line.startswith(("---", "+++", "@@", " ", "+", "-")):
            if "```" in line or "here is" in line.lower() or "below" in line.lower():
                return None, "Output contains commentary or markdown; expected unified diff only."
    return stripped, ""


def validate_full_output(raw: str, max_bytes: int = 200_000) -> Tuple[str | None, str]:
    """
    Validate that output is plain file content only (no markdown fences or commentary).
    Returns (normalized_content, "") on success, (None, error_message) on failure.
    """
    if not raw:
        return None, "Empty output; expected file content only."
    if len(raw.encode("utf-8")) > max_bytes:
        return None, f"Full output exceeds max size ({max_bytes} bytes)."
    stripped = raw.strip()
    if _FENCE.search(stripped):
        return None, "Output contains markdown code fences; expected plain file content only."
    if stripped.startswith("Here ") or stripped.startswith("Below ") or "```" in stripped:
        return None, "Output contains commentary or markdown; expected file content only."
    return stripped, ""
