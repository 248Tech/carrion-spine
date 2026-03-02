"""Minimal tests: AI redaction, patch contract, [ai] config."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_redact_secrets_detects_key_value() -> None:
    from carrion_spine.ai.redaction import redact_secrets

    text = "api_key = sk-abc123xyz789"
    out, applied = redact_secrets(text)
    assert applied is True
    assert "sk-abc123xyz789" not in out
    assert "<<REDACTED>>" in out


def test_redact_secrets_no_secret() -> None:
    from carrion_spine.ai.redaction import redact_secrets

    text = "ServerName = My Server"
    out, applied = redact_secrets(text)
    assert applied is False
    assert out == text


def test_validate_patch_output_valid_diff() -> None:
    from carrion_spine.ai.contracts import validate_patch_output

    diff = "--- a/file\n+++ b/file\n@@ -1,3 +1,4 @@\n line1\n+newline\n line2\n"
    normalized, err = validate_patch_output(diff)
    assert err == ""
    assert normalized is not None
    assert "@@" in normalized


def test_validate_patch_output_rejects_empty() -> None:
    from carrion_spine.ai.contracts import validate_patch_output

    norm, err = validate_patch_output("")
    assert norm is None
    assert "Empty" in err


def test_validate_patch_output_rejects_markdown() -> None:
    from carrion_spine.ai.contracts import validate_patch_output

    text = "Here is the diff:\n```diff\n--- a\n+++ b\n"
    norm, err = validate_patch_output(text)
    assert norm is None
    assert "commentary" in err or "markdown" in err.lower()


def test_validate_full_output_rejects_fence() -> None:
    from carrion_spine.ai.contracts import validate_full_output

    text = "```xml\n<root/>\n```"
    norm, err = validate_full_output(text)
    assert norm is None
    assert "fence" in err.lower() or "markdown" in err.lower()


def test_load_config_ai_section_defaults(tmp_path: Path) -> None:
    from carrion_spine.config_loader import load_config

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[spine]
data_dir = "data"
backup_dir = "backups"
config_roots = ["/srv/7dtd"]
module_access_roles = []

[ai]
enabled = true
provider = "local_http"
redact_secrets = true
allow_external = false
"""
    )
    loaded = load_config(config_file)
    assert loaded.ai_config is not None
    assert loaded.ai_config.enabled is True
    assert loaded.ai_config.provider == "local_http"
    assert loaded.ai_config.allow_external is False
    assert loaded.ai_config.mode_default == "patch"
    assert loaded.ai_config.redact_secrets is True
    assert loaded.ai_config.max_input_bytes == 200_000
    assert loaded.ai_config.max_output_bytes == 200_000