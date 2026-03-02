"""Policy layer: blocklist keys, deny serveradmin.xml unless elevated."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

# Keys that must not be edited by AI (MVP: blocklist)
BLOCKLIST_KEYS = frozenset(
    {
        "password", "passwd", "api_key", "apikey", "token", "secret",
        "adminpassword", "telnetpassword", "steamwebapi_key",
    }
)

# Filename that requires elevated role to edit (MVP: serveradmin.xml)
RESTRICTED_FILENAME = "serveradmin.xml"


def policy_check(
    *,
    file_path: Path,
    proposed_content: str,
    has_elevated_role: bool,
) -> tuple[bool, str]:
    """
    Run policy checks on proposed content and path.
    Returns (ok, error_message). ok=False means reject.
    """
    path_name = file_path.name.lower()
    if path_name == RESTRICTED_FILENAME and not has_elevated_role:
        return False, "Edits to serveradmin.xml require elevated role."
    # Block if proposed content sets a blocklisted key (e.g. XML property name="password" with value)
    content_lower = proposed_content.lower()
    for key in BLOCKLIST_KEYS:
        # XML property name="key" or name='key'
        if f'name="{key}"' in content_lower or f"name='{key}'" in content_lower:
            return False, f"Policy: edits containing sensitive key '{key}' are blocked."
    return True, ""
