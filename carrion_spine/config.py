from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(slots=True, frozen=True)
class CarrionSpineSettings:
    """Runtime settings for the Carrion: Spine module."""

    config_roots: Sequence[Path]
    module_access_roles: Sequence[int]
    file_profile_roles: Mapping[str, Sequence[int]] = field(default_factory=dict)
    max_upload_bytes: int = 5 * 1024 * 1024
    backup_dir: Path = Path("/var/backups/carrion_spine")
    backup_keep: int = 10

