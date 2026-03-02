# Command Reference

## Discord commands

All `/mm` commands require the user to have a role in `module_access_roles`. Responses are ephemeral.

### /mm config pull

Scans configured roots for XML, JSON, YAML, and INI files and replaces the index. Returns the number of files indexed and a short sample (nickname, relative path, file type, hash prefix, last applied if known). Only paths under config roots are indexed.

### /mm config list [root_filter]

Lists indexed configs: nickname and relative path. Optional **root_filter** filters by root token (e.g. folder name). Up to 100 entries; if empty, suggests running pull or changing the filter.

### /mm edit <nickname>

Starts an attachment-based edit. Resolves nickname to the file, reads it, creates a session, and sends the file plus a session id. You then upload your modified file in the same channel with message text containing `mm-session:<session_id>`. The bot validates type, size, and content, then shows a diff and Apply/Cancel. File-profile role checks apply if configured.

### /mm spine setup

Runs readiness checks: each config root (exists, writable), backup dir (creatable/writable), data dir (writable). Verifies that all `module_access_roles` exist in the guild. Reports the optional audit channel if set. Use after deployment to confirm the environment.

### /mm spine set-audit-channel [channel]

Sets or clears the guild’s optional audit channel. Omit channel to clear.

### /mm ai suggest target:<nickname> instruction:<text> [mode] [temperature]

Requires `[ai]` enabled and user in `suggest_roles`. **target** is a config nickname. **instruction** is the change to request. **mode**: `patch` (unified diff) or `full` (full file). **temperature**: 0.0–1.0 (default from config). Returns a diff, proposal attachment, and Apply / Cancel / Revise Prompt. Apply requires `apply_roles`. Full details: [ai.md](ai.md).

---

## CLI commands

Config file: default `config.toml`; override with `--config <path>` or `CARRION_SPINE_CONFIG`. Token: `DISCORD_TOKEN` (or env var name set at init).

| Command | Description |
|---------|-------------|
| `carrion-spine init [--path <path>]` | Interactive setup; writes config and `.env.example`. |
| `carrion-spine doctor [--config <path>]` | Runs readiness checks; exits non-zero on critical failure. |
| `carrion-spine run [--config <path>]` | Starts the bot. Requires token in environment. |
| `carrion-spine install-systemd [--user] [--group] [--config] [--workdir]` | Prints systemd unit and tmpfiles.d; does not install. |

**Edge cases:** If `doctor` fails on a root, ensure the path exists and the process has read and write access. For `run`, the working directory is the config file’s parent unless overridden; ensure `data_dir` and `backup_dir` in config are valid from that context.
