"""Minimal tests: config parsing and readiness (doctor) checks."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def test_load_config_minimal(tmp_path: Path) -> None:
    """Load a minimal valid TOML config."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[spine]
data_dir = "data"
backup_dir = "backups"
config_roots = ["/srv/7dtd"]
module_access_roles = []
"""
    )
    from carrion_spine.config_loader import load_config

    loaded = load_config(config_file)
    assert loaded.settings is not None
    assert len(loaded.settings.config_roots) == 1
    assert str(loaded.settings.config_roots[0]).endswith("7dtd")
    assert loaded.sqlite_path == tmp_path / "data" / "spine.sqlite"
    assert loaded.backup_dir == tmp_path / "backups"
    assert len(loaded.roots) == 1


def test_load_config_rejects_backup_inside_root(tmp_path: Path) -> None:
    """Backup dir must be outside config roots."""
    root_dir = tmp_path / "game"
    root_dir.mkdir()
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f"""
[spine]
data_dir = "data"
backup_dir = "game/backups"
config_roots = ["{root_dir.as_posix()}"]
module_access_roles = []
"""
    )
    from carrion_spine.config_loader import load_config

    with pytest.raises(ValueError, match="backup_dir must be outside"):
        load_config(config_file)


def test_readiness_checks_pass(tmp_path: Path) -> None:
    """Readiness checks pass when dirs exist and are writable."""
    root_dir = tmp_path / "root"
    backup_dir = tmp_path / "backups"
    data_dir = tmp_path / "data"
    root_dir.mkdir()
    backup_dir.mkdir()
    data_dir.mkdir()
    sqlite_path = data_dir / "spine.sqlite"

    from carrion_spine.discovery import ConfigRoot
    from carrion_spine.readiness import run_readiness_checks

    results = run_readiness_checks(
        roots=[ConfigRoot(token="t", path=root_dir)],
        backup_dir=backup_dir,
        data_dir=data_dir,
        sqlite_path=sqlite_path,
    )
    assert all(r.ok for r in results)


def test_readiness_checks_fail_missing_root(tmp_path: Path) -> None:
    """Readiness fails when root does not exist."""
    from carrion_spine.discovery import ConfigRoot
    from carrion_spine.readiness import run_readiness_checks

    missing = tmp_path / "missing"
    backup_dir = tmp_path / "backups"
    data_dir = tmp_path / "data"
    backup_dir.mkdir()
    data_dir.mkdir()
    sqlite_path = data_dir / "spine.sqlite"

    results = run_readiness_checks(
        roots=[ConfigRoot(token="t", path=missing)],
        backup_dir=backup_dir,
        data_dir=data_dir,
        sqlite_path=sqlite_path,
    )
    root_results = [r for r in results if r.name.startswith("root:")]
    assert len(root_results) == 1 and not root_results[0].ok
