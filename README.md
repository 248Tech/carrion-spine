# Carrion: Spine

## What It Is

Carrion: Spine is a Discord-first configuration control plane for 7 Days to Die server administration. It indexes config files under configurable roots, exposes them by stable nicknames, and lets operators edit via Discord using an attachment-based workflow. All changes are validated (format and profile), diff-reviewed, conflict-checked against the live file, and applied atomically with rolling backups. Audit logging records every validation failure, apply, and cancel. Optional AI suggest (MVP) generates single-file proposals that go through the same pipeline; the model never applies changes automatically.

## Architecture Overview

- **discovery** — Recursively scans configured roots for XML, JSON, YAML, and INI files; builds stable nicknames (filename + folder token, disambiguated); computes SHA-256 hashes; enforces path containment so no file outside roots is indexed or edited.
- **sessions** — Edit sessions (manual or AI) store session_id, user_id, nickname, original_hash, status, and optional uploaded_path; AI proposals are tied to sessions and recorded in `ai_proposals` with provider metadata and content hashes.
- **validation** — Two layers: format (well-formed XML/JSON/YAML/INI; XML hardened against DOCTYPE/ENTITY) and profile (e.g. serverconfig.xml, serveradmin.xml, ServerTools XML with required nodes and optional numeric bounds). Invalid content is rejected before any write.
- **diffing** — Uses `difflib.unified_diff`; produces a short excerpt and a full diff attachment when large; summary counts added/removed lines for the operator.
- **apply** — Re-hashes the live file; if it differs from the session’s original_hash, apply is aborted. Writes to a temp file, fsyncs, then atomically renames onto the target. Creates a timestamped backup and rotates backups by `backup_keep`.
- **audit logging** — SQLite `audit_log`: user_id, nickname, full_path, timestamp, diff_summary, status, validation_result; for AI applies, actor_type, ai_proposal_id, provider, model.
- **AI provider abstraction (MVP)** — Pluggable providers (OpenAI-compatible, local HTTP e.g. Ollama) via a simple interface; output is constrained to unified diff (patch mode) or full file content (full mode); no automatic apply.

## Command Surface

### Discord Commands

All commands under the `mm` group require the user to have a role in `module_access_roles` (and, where applicable, `file_profile_roles`). Responses are ephemeral unless noted.

- **`/mm config pull`**  
  Scans configured roots, discovers supported config files, and replaces the SQLite config index. Returns a count and a short sample (nickname, relative path, file type, hash prefix, last applied timestamp when available). Safety: only paths under configured roots are indexed; path containment is enforced.

- **`/mm config list [root_filter]`**  
  Lists indexed configs (nickname and relative path). Optional `root_filter` filters by root token (e.g. the folder name used as token). Returns up to 100 entries plus a truncation note. If empty, suggests running pull or adjusting the filter.

- **`/mm edit <nickname>`**  
  Starts an attachment-based edit session. Resolves nickname to the indexed file, reads the current content, creates a pending session with the file’s hash, and sends the file as an attachment plus the session id. The user must later upload a modified file in the same channel with message text containing `mm-session:<session_id>`. Safety: module and file-profile role checks; upload is validated (type, size, non-binary); format and profile validation run before showing the diff and Apply/Cancel buttons.

- **`/mm spine setup`**  
  Runs readiness checks: each config root (exists, writable), backup dir (creatable/writable), SQLite data dir (writable). Verifies that all `module_access_roles` exist in the guild. Reports optional audit channel if set. Intended for operators to confirm the environment before use.

- **`/mm spine set-audit-channel [channel]`**  
  Sets or clears the guild’s optional audit channel (stored in SQLite `spine_state`). Omit channel to clear.

- **`/mm ai suggest target:<nickname> instruction:<text> [mode] [temperature]`**  
  MVP. Requires `[ai]` in config with `enabled = true` and the user in `suggest_roles`. Resolves nickname, reads baseline, optionally redacts secrets, calls the configured provider (patch or full mode), validates output contract, applies patch if needed, runs format and profile validation and policy checks (e.g. blocklist keys, serveradmin.xml restriction). Creates an edit session (type `ai`) and an `ai_proposals` row; returns a diff summary, proposal.diff attachment, and Apply / Cancel / Revise Prompt buttons. Apply uses the same pipeline as manual edits and requires `apply_roles`; audit logs with actor_type and proposal metadata. AI never applies automatically.

### CLI Commands

Config is read from `config.toml` by default; override with `--config <path>` or set `CARRION_SPINE_CONFIG`. The bot token is taken from `DISCORD_TOKEN` (or the env var name configured at init).

- **`carrion-spine init [--path <path>]`**  
  Interactive setup: prompts for bot token env name, config roots, backup dir, and module access role IDs. Writes a `config.toml` and a `.env.example` (no real token). Default output path is `config.toml`.

- **`carrion-spine doctor [--config <path>]`**  
  Loads config and runs the same readiness checks as `/mm spine setup` (roots, backup dir, SQLite path writable). Warns if `DISCORD_TOKEN` is unset or placeholder and reminds about intents/permissions. Exits non-zero if any critical check fails.

- **`carrion-spine run [--config <path>]`**  
  Sets `CARRION_SPINE_CONFIG` to the chosen config path, then starts a minimal Discord bot that loads the `carrion_spine.commands` extension. Requires `DISCORD_TOKEN` (or equivalent) in the environment.

- **`carrion-spine install-systemd [--user] [--group] [--config] [--workdir]`**  
  Prints a systemd unit file and a tmpfiles.d snippet for data/backup dirs. Defaults: user/group `carrion`, config `/etc/carrion-spine/config.toml`. Does not install; you copy the output into place then run `systemctl daemon-reload`, `enable`, `start`.

## Configuration

Config is TOML. The main section is `[spine]` (or `[carrion_spine]`). Paths can be absolute or relative to the config file directory. Environment overrides: `CARRION_SPINE_DATA_DIR`, `CARRION_SPINE_BACKUP_DIR`; `CARRION_SPINE_CONFIG` for the config file path when using the CLI run command.

**Required / common:**

- **config_roots** — List of directory paths to scan for config files (e.g. `["/srv/7dtd"]`). At least one required.
- **data_dir** — Directory for SQLite DB, uploads, and diff files. Default `"data"`. SQLite path is `data_dir/spine.sqlite`; uploads and diffs under `data_dir/mm_uploads` and `data_dir/mm_diffs`.
- **backup_dir** — Where rolling backups are stored. Default `"backups"`. Must be outside every config root (validated at load).
- **module_access_roles** — List of Discord role IDs that can use `/mm` commands (pull, list, edit, spine setup, etc.).
- **backup_keep** — Number of backups to keep per file (default 10; 1–100).
- **max_upload_bytes** — Max size for uploaded edits (default 5 MiB; max 50 MiB).

**Optional:**

- **file_profile_roles** — Map profile name to list of role IDs (e.g. `{ "serverconfig.xml" = [123, 456] }`) for profile-specific access.
- **roots** — Array of tables `{ path = "...", token = "..." }` to define roots with an explicit token for list filtering; if omitted, tokens are derived from path names.

**AI (optional `[ai]` section):**

- **enabled** — If true and provider is allowed, `/mm ai suggest` is available. Default false.
- **provider** — `"openai"` or `"local_http"`. If `allow_external` is false and provider is not `local_http`, AI is forced off.
- **allow_external** — If false, only `local_http` is allowed. Default false.
- **mode_default** — `"patch"` or `"full"`. Default `"patch"`.
- **redact_secrets** — Redact common secret patterns before sending content to the provider. Default true.
- **max_input_bytes**, **max_output_bytes** — Caps (default 200_000 each).
- **temperature_default** — Default temperature (e.g. 0.2).
- **suggest_roles**, **apply_roles** — Role IDs for who can run suggest and who can apply AI proposals; default to `module_access_roles` when omitted.
- **\[ai.openai]** — `api_key_env` (e.g. `"OPENAI_API_KEY"`), `model` (e.g. `"gpt-4o-mini"`).
- **\[ai.local_http]** — `url` (e.g. `"http://localhost:11434/v1/chat/completions"`), `model` (e.g. `"llama3.1"`).

## Installation

### Quickstart

```bash
git clone https://github.com/248Tech/carrion-spine.git
cd carrion-spine
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e .
carrion-spine init
# Edit config.toml and set DISCORD_TOKEN (e.g. in .env)
carrion-spine doctor
carrion-spine run
```

Or install globally with `pipx install .` and run `carrion-spine` from any directory (use `--config` if config is not in the current directory).

### Docker

Use the project’s `compose.yaml`: bind-mount `config.toml` and config roots; set `DISCORD_TOKEN` via `env_file` or environment; mount volumes for data and backups. Example:

```bash
# Set DISCORD_TOKEN in .env; create config.toml (e.g. carrion-spine init)
# In config.toml set data_dir and backup_dir to container paths if needed, e.g. /var/lib/carrion-spine, /var/backups/carrion_spine
docker compose up -d
```

Adjust the config roots volume in `compose.yaml` to match your host paths (e.g. `/srv/7dtd:/srv/7dtd:rw`).

### systemd

Generate unit and tmpfiles.d with:

```bash
carrion-spine install-systemd --user carrion --group carrion --config /etc/carrion-spine/config.toml
```

Copy the printed unit to `/etc/systemd/system/` and the tmpfiles.d snippet to `/etc/tmpfiles.d/`. Create `/etc/carrion-spine/config.toml` and an env file with `DISCORD_TOKEN`. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable carrion-spine
sudo systemctl start carrion-spine
```

## First Successful Edit (Step-by-step)

1. **Index** — In Discord, run `/mm config pull`. The bot scans roots and replies with how many files were indexed and a short sample.
2. **List** — Run `/mm config list` (optionally with a `root_filter`). Pick a nickname (e.g. `serverconfig-7dtd`).
3. **Start edit** — Run `/mm edit nickname: <nickname>`. The bot sends the file as an attachment and a session id (e.g. `mm-session:abc123...`).
4. **Edit locally** — Download the attachment, edit the file, then in the same channel upload the modified file and in the message body include `mm-session:<session_id>`.
5. **Diff and validation** — The bot validates format and profile, then shows a diff summary and an excerpt (or a .diff attachment if long). If validation fails, the reply explains why; fix and re-upload.
6. **Apply or cancel** — Use the Apply button to write the file (conflict check, backup, atomic write) or Cancel to abandon. Only the session owner can use the buttons.
7. **Audit** — The action (applied or cancelled) is recorded in `audit_log` with user, nickname, path, timestamp, status, and validation result.

## AI Assistance (MVP)

`/mm ai suggest` generates a single-file proposal (patch or full content) from the configured LLM. The output is validated (unified-diff or plain-content contract), optionally redacted, then run through the same format and profile validation and policy layer as manual edits. Proposals are stored as edit sessions (type `ai`) with linked `ai_proposals` rows (prompt/input/output hashes, provider, model). Apply and Cancel use the same pipeline as manual edits; Apply also requires `apply_roles`. Revise Prompt opens a modal to submit a new instruction and create a new proposal (same baseline from disk). AI never applies changes automatically; `allow_external` defaults to false so only a local HTTP provider is allowed unless explicitly enabled.

## Troubleshooting

- **Slash commands do not appear** — Ensure the bot was invited with the `applications.commands` scope. Wait a few minutes for global command propagation. Re-invite with that scope if needed.
- **403 or “Missing Access”** — The bot needs channel permissions (e.g. Send Messages, Embed Links, Attach Files, Read Message History, Use Application Commands). The user must have a role in `module_access_roles` (and, for specific files, in `file_profile_roles` if configured). Check channel overwrites and role list.
- **Validation failed** — The reply includes the validator message (e.g. malformed XML, missing required node, or profile rule). Fix the file and re-upload (or, for AI, adjust the instruction or try again).
- **Permission denied on write** — The process must be able to write to the config root and to `backup_dir`. Run `carrion-spine doctor` (or `/mm spine setup`) to verify. In Docker, ensure the config roots and backup volume are mounted read-write and the process is not running as root.
- **Conflict detected** — The live file’s hash no longer matches the session’s original hash (file changed after the session started). Run `/mm config pull` to refresh the index, then start a new edit.

## Security Model

- **Root confinement** — Only paths under configured roots are indexed; path resolution rejects traversal outside those roots.
- **Upload limits** — Size and type checks; binary content is rejected.
- **XML hardening** — DOCTYPE and ENTITY are rejected to reduce XXE risk.
- **Validation before write** — Format and profile validation run before any diff is applied; invalid content is never written.
- **Diff-first** — Operators see a diff (and validation result) before choosing Apply.
- **Conflict check** — Apply re-hashes the live file and aborts if it differs from the session’s stored hash.
- **Atomic write** — Content is written to a temp file, fsync’d, then renamed onto the target; rolling backups are created first.
- **Backup location** — `backup_dir` must be outside config roots (enforced at config load).
- **Audit** — Every validation failure, apply, and cancel is logged with user, path, status, and validation result; AI applies include actor_type and proposal metadata.
- **Secrets** — Token and secrets belong in environment or env files, not in config committed to version control. AI redaction (when enabled) reduces what is sent to the provider; it does not replace access control.

## Roadmap

Planned improvements: broader profile coverage for 7DTD configs; optional incremental indexing (e.g. via filesystem events); clearer errors (e.g. line/column where possible); and continued hardening and deployment guidance. AI remains MVP (single-file, no auto-apply).

## License

MIT. See `LICENSE` in the repository.
