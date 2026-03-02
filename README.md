# Carrion: Spine

Discord-first configuration control plane for 7 Days to Die, built as a module in the broader Carrion automation ecosystem.

Carrion: Spine provides a safe, operator-focused workflow for discovering, reviewing, validating, and applying server configuration changes through Discord interactions. It is designed for production environments where change control, traceability, and operational safety matter: edits are diff-first, validation-gated, conflict-checked, atomically written, and auditable.

## Why Carrion: Spine

Managing 7 Days to Die server configs by manual file edits over SSH, panel uploads, or ad hoc scripts is error-prone and hard to audit. Carrion: Spine addresses this by turning configuration edits into a controlled workflow:

- Index known config files across approved roots
- Pull and edit files through Discord
- Validate structure and profile rules before apply
- Review unified diffs before any write
- Detect live-file conflicts before commit
- Apply changes atomically with backups and audit logging

## Features

- Recursive discovery and indexing of `XML`, `JSON`, `YAML`, and `INI` files
- Stable, human-friendly nicknames for fast targeting
- Discord slash-command workflow (`/mm config pull`, `/mm config list`, `/mm edit`)
- Attachment-based edit sessions with explicit Apply/Cancel controls
- Two-layer validation:
  - format validation (parse/well-formed checks)
  - profile validation (e.g., `serverconfig.xml`, `serveradmin.xml`, ServerTools XML)
- Diff-first change review using unified diffs
- Conflict detection using content hashing before apply
- Atomic file writes (`temp + fsync + replace`) with rolling backups
- Role-based access control by Discord role ID
- SQLite-backed session state and audit log trail

## Problem Statement

Game server administration often lacks a reliable change-management layer. Common risks include malformed files, unreviewed edits, race conditions from concurrent updates, and no forensic trail of who changed what.

Carrion: Spine is built to reduce these operational risks by enforcing a secure and reviewable path from request to applied change.

## Installation

### 1) Clone the Repository

```bash
git clone https://github.com/248Tech/carrion-spine.git
cd carrion-spine
```

### 2) Create and Activate a Virtual Environment

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3) Install Dependencies

If your repo includes `requirements.txt`:

```bash
pip install -U pip
pip install -r requirements.txt
```

If not, install minimum runtime dependency directly:

```bash
pip install -U pip
pip install "discord.py>=2,<3"
```

Optional: `lxml` (if you choose it for XML profile parsing).

### 4) Load the Extension in Your Bot

```python
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=...)

async def main() -> None:
    async with bot:
        await bot.load_extension("carrion_spine.commands")
        await bot.start("YOUR_BOT_TOKEN")
```

### 5) Configure Roots and Permissions

Example settings object (adjust to your environment):

```python
from pathlib import Path
from carrion_spine.config import CarrionSpineSettings

settings = CarrionSpineSettings(
    config_roots=[
        Path("/srv/7dtd/main"),
        Path("/srv/7dtd/staging"),
    ],
    module_access_roles=[123456789012345678],
    file_profile_roles={
        "serverconfig.xml": [123456789012345678],
        "serveradmin.xml": [234567890123456789],
    },
    max_upload_bytes=5 * 1024 * 1024,
    backup_dir=Path("/var/backups/carrion_spine"),
    backup_keep=10,
)
```

### 6) Quick Compile Test

```bash
python -m compileall carrion_spine
```

## Production Deployment (systemd)

Use a dedicated service account and locked-down filesystem permissions.

Example unit file:

```ini
[Unit]
Description=Carrion Spine Discord Bot Module Host
After=network.target

[Service]
Type=simple
User=carrion
Group=carrion
WorkingDirectory=/opt/carrion-spine
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/carrion-spine/.env
ExecStart=/opt/carrion-spine/.venv/bin/python -m your_bot_entrypoint
Restart=always
RestartSec=5

# Hardening (adjust to your runtime needs)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/carrion-spine/data /var/backups/carrion_spine /srv/7dtd

[Install]
WantedBy=multi-user.target
```

Deploy:

```bash
sudo systemctl daemon-reload
sudo systemctl enable carrion-spine
sudo systemctl start carrion-spine
sudo systemctl status carrion-spine
```

## Security Model

Carrion: Spine is designed with defensive defaults:

- **Root confinement:** operations are restricted to configured config roots
- **Traversal resistance:** path checks prevent edits outside approved roots
- **Type/size checks:** uploads are limited and binary payloads are rejected
- **XML hardening:** external entity/DOCTYPE-style unsafe patterns are blocked
- **Validation gating:** malformed or profile-invalid files are rejected before apply
- **Diff-first control:** operators review changes before committing
- **Conflict detection:** live file hash is rechecked before write
- **Atomic apply:** write-temp, fsync, atomic replace workflow
- **Backup safety:** rolling backups stored outside public-facing directories
- **Auditability:** validation failures, applies, and cancels are logged in SQLite

Operational recommendations:

- Keep bot token in environment variables or systemd `EnvironmentFile`, never in source
- Restrict filesystem permissions for roots, backups, and SQLite DB
- Use least-privilege Discord role mappings
- Regularly review audit logs and backup retention policy

## Carrion Ecosystem

Carrion: Spine is part of a growing operations and automation ecosystem for 7 Days to Die administration.

- **Carrion: Spine**  
  https://github.com/248Tech/carrion-spine  
  Discord-first configuration control plane focused on safe, validated, auditable config changes.

- **7DTD Mastermind Donors**  
  https://github.com/248Tech/7dtd-mastermind-donors  
  Donor and access-management tooling for 7DTD communities, built to streamline role/entitlement operations.

- **RegionHealer v2**  
  https://github.com/248Tech/RegionHealer-v2  
  Region maintenance and remediation tooling aimed at improving world stability and reducing admin recovery overhead.

Together, these tools form a practical automation stack for safer server operations, with shared emphasis on reliability, traceability, and controlled execution.

## Coming Soon: Carrion Core

A unified orchestration framework is in development to coordinate Carrion modules under one control layer.

Planned goals:

- Centralized module management
- Lifecycle management for module startup, shutdown, and health
- Cross-module coordination and shared policy enforcement
- A primary control plane for operations visibility and governance

Carrion Core is being developed as an operational foundation, with compatibility and stability prioritized over rapid feature churn.

## Roadmap

- Expanded profile validation coverage for additional 7DTD config formats
- Optional incremental indexing via filesystem event monitoring
- Improved operator UX for large diffs and batched review flows
- Additional observability hooks for metrics and incident triage
- Continued hardening and deployment guidance for production environments

## License

MIT License. See `LICENSE` for details.
