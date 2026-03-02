# Carrion: Spine

Discord-first configuration control plane for 7 Days to Die. Index config files by nickname, edit via Discord, then review a diff and apply. All changes are validated before write and applied with a backup.

**Carrion: Spine is safe by default. All changes require human approval.**

---

## 3-Step Mental Model

**Index** — Spine scans directories you configure and builds a list of config files (XML, JSON, YAML, INI). Each file gets a short nickname you use in Discord.

**Edit** — You ask for a file by nickname. Spine sends it to you. You change it locally and upload it back in the same channel. Spine checks the file and shows you a diff.

**Apply** — You choose Apply or Cancel. Only then is the file on disk updated. Apply creates a backup first and records the change. If the file changed since you started, Apply is blocked.

```
/mm config pull
      ↓
/mm edit <nickname>
      ↓
Upload edited file
      ↓
Diff + Validation
      ↓
Apply → Atomic write + Backup + Audit
```

---

## Choose Your Setup

- [Quick local setup](#quickstart-local--development) — pipx or venv, run in under 10 minutes
- [Docker](#docker-primary-install) (recommended for operators)
- [Production systemd](docs/systemd.md)
- [Enable AI](docs/ai.md) (optional)
- [Security details](docs/security.md)

---

## Docker (Primary install)

Put `config.toml` and `.env` (with `DISCORD_TOKEN`) next to `compose.yaml`. Adjust the config roots volume to your host path.

```yaml
services:
  spine:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - CARRION_SPINE_CONFIG=/etc/carrion-spine/config.toml
    volumes:
      - ./config.toml:/etc/carrion-spine/config.toml:ro
      - /srv/7dtd:/srv/7dtd:rw
      - spine-data:/var/lib/carrion-spine
      - spine-backups:/var/backups/carrion_spine

volumes:
  spine-data:
  spine-backups:
```

```bash
docker compose up -d
```

Details: [docs/docker.md](docs/docker.md)

---

## Quickstart (Local / Development)

**pipx (fast):** `pipx install .` then `carrion-spine init`, add `DISCORD_TOKEN` to `.env`, edit `config.toml`, run `carrion-spine doctor` and `carrion-spine run`.

**Development (venv):** clone repo, `python3 -m venv .venv && source .venv/bin/activate`, `pip install -e .`, then same init/doctor/run. After the bot is online, run `/mm spine setup` in Discord.

Full config and CLI: [docs/install.md](docs/install.md)

---

## First Successful Edit

1. `/mm config pull` — index your config roots
2. `/mm config list` — pick a nickname
3. `/mm edit nickname: <nickname>` — bot sends the file and a session id
4. Download, edit, then upload the file in the same channel with `mm-session:<session_id>` in the message
5. Review the diff and click **Apply**

---

## Command Surface

- **`/mm config pull`** — Scan roots and refresh the file index.
- **`/mm config list [root_filter]`** — List indexed files by nickname (optional filter).
- **`/mm edit <nickname>`** — Start an edit session; bot sends the file; you upload your version with the session id.
- **`/mm ai suggest target:<nickname> instruction:<text>`** — Ask the AI for a proposed change (optional; same review/apply flow).
- **`/mm spine setup`** — Run readiness checks (roots, backup dir, roles).

Full arguments and examples: [docs/commands.md](docs/commands.md)

---

## AI Assistance (optional)

`/mm ai suggest` generates a single-file proposal from a local or configured LLM. You get a diff and Apply / Cancel / Revise Prompt. Proposals go through the same validation and apply pipeline as manual edits. **AI never auto-applies.**

Example: `/mm ai suggest target:serverconfig-7dtd instruction:Set max players to 16`

Details and provider config: [docs/ai.md](docs/ai.md)

---

## Configuration

```toml
[spine]
config_roots = ["/srv/7dtd"]
module_access_roles = [123456789]
```

Most deployments only need `config_roots` and `module_access_roles`. Full schema: [docs/install.md](docs/install.md).

---

## Safety Summary

- **Diff-first** — You see the diff and validation result before choosing Apply.
- **Validation-gated** — Format and profile checks run first; invalid content is never written.
- **Conflict detection** — If the file changed on disk since you started, Apply is blocked.
- **Atomic write** — Write goes to a temp file then rename; a backup is created first.
- **Audit logging** — Every apply, cancel, and validation failure is recorded.

---

## License

MIT. See [LICENSE](LICENSE).
