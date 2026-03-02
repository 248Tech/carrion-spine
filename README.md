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

Choose one of three ways to run Spine: **Quickstart** (pipx / venv + CLI), **Docker Compose**, or **Production systemd**.

---

### Quickstart (pipx or venv)

One-command local install for hobby and admin use.

```bash
git clone https://github.com/248Tech/carrion-spine.git
cd carrion-spine
python3 -m venv .venv && source .venv/bin/activate   # or on Windows: .venv\Scripts\Activate.ps1
pip install -e .
carrion-spine init
# Edit config.toml and set DISCORD_TOKEN in .env (see .env.example)
carrion-spine doctor
carrion-spine run
```

- `carrion-spine init` creates `config.toml` and `.env.example` (interactive prompts).
- `carrion-spine doctor` checks roots, backup dir, SQLite path; run before first `run`.
- `carrion-spine run` starts the bot using `config.toml` and `DISCORD_TOKEN`.

Optional: install globally with `pipx install .` then run `carrion-spine` from anywhere.

---

### Docker Compose

Repeatable containerized deploy. Bind-mount your config roots and use env for the token.

```bash
git clone https://github.com/248Tech/carrion-spine.git
cd carrion-spine
cp .env.example .env   # set DISCORD_TOKEN
# Create config.toml (e.g. with carrion-spine init) and set data_dir=/var/lib/carrion-spine, backup_dir=/var/backups/carrion_spine
# In compose.yaml, adjust the config roots volume (e.g. - /srv/7dtd:/srv/7dtd:rw)
docker compose up -d
```

See `compose.yaml` for volumes (data, backups, config roots). The image runs as non-root with reduced capabilities.

---

### Production systemd

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
EnvironmentFile=-/etc/carrion-spine/env
Environment="CARRION_SPINE_CONFIG=/etc/carrion-spine/config.toml"
ExecStart=/usr/bin/carrion-spine run --config /etc/carrion-spine/config.toml
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

Generate unit and tmpfiles.d with the CLI (then copy the output into place):

```bash
carrion-spine install-systemd --user carrion --group carrion --config /etc/carrion-spine/config.toml
```

Deploy:

```bash
sudo systemctl daemon-reload
sudo systemctl enable carrion-spine
sudo systemctl start carrion-spine
sudo systemctl status carrion-spine
```

## First successful change (tutorial)

End-to-end flow for one edited config:

1. **Index configs**  
   In Discord: `/mm config pull`  
   Spine scans configured roots and builds the nickname index.

2. **List and pick**  
   `/mm config list` (or `/mm config list root_filter: 7dtd`)  
   Note a nickname, e.g. `serverconfig-7dtd`.

3. **Start edit**  
   `/mm edit nickname: serverconfig-7dtd`  
   Spine sends the file as an attachment and creates a session. Download the file, edit it locally.

4. **Upload and review**  
   In the same channel, upload your modified file and in the message include: `mm-session:<session_id>` (the ID was in the edit response).  
   Spine validates the file, shows a diff summary and inline excerpt (or a .diff attachment if long).

5. **Apply or cancel**  
   Use **Apply** to write the file atomically (with backup and conflict check) or **Cancel** to abandon.

6. **Verify**  
   Changes are written to disk; the audit log records the apply. Optional: use `/mm spine setup` to run readiness checks and confirm roots/backup/roles.

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
