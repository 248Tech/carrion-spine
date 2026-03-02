"""Load Carrion: Spine configuration from TOML and environment."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CarrionSpineSettings
from .discovery import ConfigRoot


@dataclass(slots=True)
class LoadedConfig:
    """Fully resolved config: settings, paths, and roots for discovery."""

    settings: CarrionSpineSettings
    config_path: Path
    data_dir: Path
    sqlite_path: Path
    upload_dir: Path
    diff_dir: Path
    backup_dir: Path
    roots: list[ConfigRoot]


def _get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or default


def _path_from_config(value: Any, base_dir: Path, env_key: str | None = None) -> Path:
    """Resolve a path from config; env override if env_key given."""
    raw: str | None = _get_env(env_key) if env_key else None
    if raw is None and value is not None:
        raw = str(value).strip()
    if not raw:
        raise ValueError(f"Missing required path (config or env {env_key or 'N/A'})")
    p = Path(raw)
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def _int_list(value: Any) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    return [int(value)]


def _path_list(value: Any, base_dir: Path) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_path_from_config(x, base_dir, None) for x in value]
    return [_path_from_config(value, base_dir, None)]


def load_config(config_path: Path) -> LoadedConfig:
    """
    Load and validate config from TOML. Env overrides:
    - DISCORD_TOKEN
    - CARRION_SPINE_DATA_DIR
    - CARRION_SPINE_BACKUP_DIR
    """
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    base_dir = config_path.parent.resolve()

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    spine = data.get("spine") or data.get("carrion_spine") or data
    if not isinstance(spine, dict):
        raise ValueError("Config must have a [spine] or [carrion_spine] section")

    # Paths (with env overrides)
    data_dir = _path_from_config(
        spine.get("data_dir", "data"),
        base_dir,
        "CARRION_SPINE_DATA_DIR",
    )
    backup_dir = _path_from_config(
        spine.get("backup_dir", "backups"),
        base_dir,
        "CARRION_SPINE_BACKUP_DIR",
    )

    sqlite_path = data_dir / "spine.sqlite"
    upload_dir = data_dir / "mm_uploads"
    diff_dir = data_dir / "mm_diffs"

    # Config roots: list of paths or [[roots]] with path + optional token
    config_roots_raw = spine.get("config_roots")
    roots_config = spine.get("roots")  # list of { path, token? }

    roots: list[ConfigRoot] = []
    root_paths: list[Path] = []

    if roots_config and isinstance(roots_config, list):
        for r in roots_config:
            if not isinstance(r, dict):
                continue
            path = _path_from_config(r.get("path"), base_dir)
            token = (r.get("token") or path.name).strip().lower().replace(" ", "-") or "cfg"
            roots.append(ConfigRoot(token=token, path=path))
            root_paths.append(path)
    if config_roots_raw:
        for p in _path_list(config_roots_raw, base_dir):
            if p not in root_paths:
                token = p.name.lower().replace(" ", "-") or "cfg"
                roots.append(ConfigRoot(token=token, path=p))
                root_paths.append(p)

    if not roots:
        raise ValueError("At least one config root must be set (config_roots or [spine.roots])")

    # Backup dir must be outside config roots (safe default)
    backup_resolved = backup_dir.resolve()
    for rp in root_paths:
        rp_resolved = rp.resolve()
        try:
            backup_resolved.relative_to(rp_resolved)
        except ValueError:
            continue  # not under this root, ok
        else:
            raise ValueError(
                f"backup_dir must be outside config roots: {backup_dir} is under {rp_resolved}"
            )

    module_roles = _int_list(spine.get("module_access_roles"))
    profile_roles_raw = spine.get("file_profile_roles") or {}
    file_profile_roles: dict[str, tuple[int, ...]] = {}
    if isinstance(profile_roles_raw, dict):
        for k, v in profile_roles_raw.items():
            file_profile_roles[k] = tuple(_int_list(v))

    max_upload = int(spine.get("max_upload_bytes", 5 * 1024 * 1024))
    if max_upload <= 0 or max_upload > 50 * 1024 * 1024:
        raise ValueError("max_upload_bytes must be between 1 and 52428800 (50MB)")
    backup_keep = int(spine.get("backup_keep", 10))
    if backup_keep < 1 or backup_keep > 100:
        raise ValueError("backup_keep must be between 1 and 100")

    settings = CarrionSpineSettings(
        config_roots=root_paths,
        module_access_roles=module_roles,
        file_profile_roles=file_profile_roles,
        max_upload_bytes=max_upload,
        backup_dir=backup_resolved,
        backup_keep=backup_keep,
    )

    return LoadedConfig(
        settings=settings,
        config_path=config_path,
        data_dir=data_dir,
        sqlite_path=sqlite_path,
        upload_dir=upload_dir,
        diff_dir=diff_dir,
        backup_dir=backup_resolved,
        roots=roots,
    )


def load_config_from_env() -> LoadedConfig | None:
    """Load config from path in CARRION_SPINE_CONFIG env var. Returns None if unset."""
    path_str = os.environ.get("CARRION_SPINE_CONFIG")
    if not path_str or not path_str.strip():
        return None
    return load_config(Path(path_str).resolve())
