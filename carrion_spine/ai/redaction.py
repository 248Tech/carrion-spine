"""Secret redaction before sending content to LLM. Log only that redaction occurred."""

from __future__ import annotations

import re
from typing import Tuple


# Key names that often precede secrets (case-insensitive)
_SECRET_KEYS = re.compile(
    r"\b("
    r"api[_-]?key|apikey|"
    r"token|"
    r"password|passwd|pwd|"
    r"secret|"
    r"auth[_-]?token|"
    r"bot[_-]?token|"
    r"discord[_-]?token|"
    r"steam[_-]?key|steamkey|"
    r"private[_-]?key"
    r")\s*[:=]\s*[\"']?([^\"'\\s]{8,})[\"']?",
    re.IGNORECASE,
)

# Discord bot token pattern (rough: 3 numeric segments)
_DISCORD_TOKEN = re.compile(r"\b(\d{17,})\.([A-Za-z0-9_-]{23,})\.([A-Za-z0-9_-]{6,})\b")

# Generic long base64-like or hex secrets
_STEAM_LIKE = re.compile(r"\b([A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5})\b")
_PLACEHOLDER = "<<REDACTED>>"


def redact_secrets(text: str) -> Tuple[str, bool]:
    """
    Redact common secret patterns. Returns (redacted_text, redaction_applied).
    Caller must log only that redaction occurred; never log the original secret.
    """
    if not text or not text.strip():
        return text, False
    applied = False
    out = text

    def repl_key(_m: re.Match[str]) -> str:
        nonlocal applied
        applied = True
        return _m.group(1) + " = " + _PLACEHOLDER

    out = _SECRET_KEYS.sub(repl_key, out)

    if _DISCORD_TOKEN.search(out):
        out = _DISCORD_TOKEN.sub(_PLACEHOLDER, out)
        applied = True
    if _STEAM_LIKE.search(out):
        out = _STEAM_LIKE.sub(_PLACEHOLDER, out)
        applied = True

    return out, applied
