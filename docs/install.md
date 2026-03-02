# Installation and Configuration

## Full config schema

Config is TOML. Main section: `[spine]` or `[carrion_spine]`. Paths are relative to the config file directory unless absolute.

**Required / common:**

| Key | Description | Default |
|-----|-------------|---------|
| `config_roots` | List of paths to scan (e.g. `["/srv/7dtd"]`). At least one required. | — |
| `data_dir` | Directory for database, uploads, and diff files. | `"data"` |
| `backup_dir` | Where rolling backups are stored. Must be outside every config root. | `"backups"` |
| `module_access_roles` | Discord role IDs that can use `/mm` commands. | — |
| `backup_keep` | Number of backups per file to keep. | 10 (1–100) |
| `max_upload_bytes` | Max size for uploaded edits (bytes). | 5 MiB (max 50 MiB) |

**Optional:**

| Key | Description |
|-----|-------------|
| `file_profile_roles` | Map profile name to role IDs, e.g. `{ "serverconfig.xml" = [123, 456] }`. |
| `roots` | Array of `{ path = "...", token = "..." }` for explicit root tokens. |

Environment overrides: `CARRION_SPINE_DATA_DIR`, `CARRION_SPINE_BACKUP_DIR`. The config file path for the run command can be set with `CARRION_SPINE_CONFIG`.

## Role IDs

Discord role IDs are 64-bit integers. Enable Developer Mode in Discord (User Settings → App Settings → Developer Mode), then right-click a role in Server Settings → Copy ID. Put those IDs in `module_access_roles` (and optionally in `file_profile_roles` for per-file access).

## Environment variables

- **DISCORD_TOKEN** — Bot token (required for `carrion-spine run`). Prefer `.env` or systemd `EnvironmentFile`; never commit.
- **CARRION_SPINE_CONFIG** — Path to `config.toml` when using `carrion-spine run`.
- **CARRION_SPINE_DATA_DIR** — Override `data_dir` from config.
- **CARRION_SPINE_BACKUP_DIR** — Override `backup_dir` from config.

## CLI commands

- **`carrion-spine init [--path <path>]`** — Interactive setup; writes `config.toml` and `.env.example`. Default path: `config.toml`.
- **`carrion-spine doctor [--config <path>]`** — Load config and check roots, backup dir, and data dir; warns about token and intents. Exit code non-zero if a critical check fails.
- **`carrion-spine run [--config <path>]`** — Start the bot (sets `CARRION_SPINE_CONFIG` from `--config`). Requires `DISCORD_TOKEN`.
- **`carrion-spine install-systemd [--user] [--group] [--config] [--workdir]`** — Print systemd unit and tmpfiles.d snippet. See [systemd.md](systemd.md).

Config path: default `config.toml` in current directory. Override with `--config` or `CARRION_SPINE_CONFIG`.

## Troubleshooting

- **Slash commands do not appear** — Invite the bot with the `applications.commands` scope. Wait a few minutes; re-invite if needed.
- **403 / Missing Access** — Bot needs Send Messages, Embed Links, Attach Files, Read Message History, Use Application Commands. User must have a role in `module_access_roles`. Check channel and role permissions.
- **Validation failed** — Bot reply includes the reason (e.g. malformed XML, missing node). Fix the file and re-upload.
- **Permission denied on write** — Process must write to config roots and `backup_dir`. Run `carrion-spine doctor` or `/mm spine setup`. In Docker, ensure roots and backup volume are mounted read-write.
- **Conflict detected** — File on disk changed since the session started. Run `/mm config pull` and start a new edit.
