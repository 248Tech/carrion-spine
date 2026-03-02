# Discord Bot Setup for Carrion: Spine

Full step-by-step guide to creating the Discord bot, inviting it, configuring roles and channels, and running Carrion: Spine (pipx, venv, or Docker). For a one-screen quickstart, see the [README](../README.md#discord-bot-setup-quickstart).

---

## A) Goals

- **One-command local install** for hobby and admin users (e.g. `pipx install carrion-spine` then `init` / `doctor` / `run`).
- **Repeatable production deploy** for operators (systemd or Docker) with bind mounts and env-based config.
- **Safe-by-default config** with minimal footguns (backup dir outside roots, validation before apply, conflict detection).
- **Guided UX inside Discord** so operators can validate readiness and complete edits without reading docs mid-incident (e.g. `/mm spine setup`, `/mm config pull`, `/mm edit`).

**Non-goals:** Redesigning workflow semantics (diff-first, validation-gated, conflict-checked behavior stays as-is).

---

## B) Prerequisites

- **OS:** Linux server (primary target); Docker supported on Linux and elsewhere. Windows/macOS are supported for local dev and CLI.
- **Python:** 3.11 or newer.
- **Access:** Discord server admin (to create/invite bot, create roles/channels) and filesystem access to the config roots Spine will index and edit.
- **Security:** Do not run the bot as root. Use a dedicated user (e.g. `carrion`) for production.

---

## C) Create the bot in Discord Developer Portal (step-by-step)

1. **Create application**  
   Go to [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → name it (e.g. "Carrion Spine").

2. **Add bot user**  
   In the left sidebar: **Bot** → **Add Bot** → confirm.

3. **Copy token**  
   Under **Bot** → **Token** → **Reset Token** (or **View**) → copy the token.  
   **Never commit this.** Store it in an environment variable (e.g. `DISCORD_TOKEN`) or in a `.env` file that is gitignored.

4. **Required settings**
   - **Privileged Gateway Intents**  
     - **Message Content:** Leave disabled unless you rely on non-slash message parsing (e.g. uploads with `mm-session:...` in the message body). Slash commands do **not** require Message Content. If you use the attachment-based edit workflow, the bot must read message content in channels where users upload files; enable **Message Content** in that case.
   - **Other intents:** Enable only what you need (e.g. **Server Members** only if you use member-based checks). Slash commands themselves require the **applications.commands** OAuth2 scope at invite time, not an intent.

---

## D) Invite the bot (OAuth2 URL Generator)

1. In the Developer Portal, open your application → **OAuth2** → **URL Generator**.
2. **Scopes:** tick **bot** and **applications.commands**.
3. **Bot permissions** (minimum recommended):
   - Send Messages  
   - Embed Links  
   - Attach Files  
   - Read Message History  
   - Use Application Commands  
   - If you use threads: **Create Public Threads**, **Send Messages in Threads**.
4. Copy the generated URL, open it in a browser, choose your server, and authorize.  
   Slash commands may take a short time to appear (propagation delay).

---

## E) Discord-side configuration

### 1. Roles

- Create roles as needed (e.g. "Spine Operator", "Spine Admin").
- Map them to Carrion: Spine via `config.toml`. Example (replace IDs with your guild’s role IDs):

```toml
[spine]
# Role IDs that can use /mm commands (module access)
module_access_roles = [1234567890123456789, 9876543210987654321]

# Optional: restrict who can edit specific file profiles
# file_profile_roles = { "serverconfig.xml" = [1234567890123456789] }
```

- To get role IDs: enable **Developer Mode** (User Settings → App Settings → Developer Mode), then right-click the role in Server Settings → **Copy ID**.

### 2. Channels

- Use a dedicated ops channel for config edits so only authorized members have access.
- Optional: if your deployment supports an audit channel, set it (e.g. via `/mm spine set-audit-channel`) so audit events can be posted there.

---

## F) How to get Role IDs and Channel IDs

1. Enable **Developer Mode:** User Settings → App Settings → **Developer Mode** → On.
2. **Role ID:** Server Settings → Roles → right-click role → **Copy ID**.
3. **Channel ID:** Right-click the channel in the sidebar → **Copy ID**.

Use these IDs in `config.toml` (e.g. `module_access_roles`) and, if applicable, for audit channel configuration.

---

## G) Local install path (pipx recommended)

```bash
pipx install carrion-spine
carrion-spine init
carrion-spine doctor
carrion-spine run
```

- **Config:** By default Spine uses `config.toml` in the current directory. Override with `--config /path/to/config.toml` for `init` / `doctor` / `run`, or set the environment variable `CARRION_SPINE_CONFIG` (e.g. for `run`).
- **Token:** Set `DISCORD_TOKEN` in the environment or in a `.env` file in the same directory (if your run method loads it). Example: `export DISCORD_TOKEN=your_token_here` before `carrion-spine run`.

---

## H) Local install path (venv)

```bash
git clone https://github.com/248Tech/carrion-spine.git
cd carrion-spine
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e .
carrion-spine init
carrion-spine doctor
carrion-spine run
```

Use the same `--config` or `CARRION_SPINE_CONFIG` and `DISCORD_TOKEN` as in section G.

---

## I) Docker / Compose path

Use a minimal Compose setup with read-only config mount, read-write roots (if you want apply to write), and dedicated volumes for data and backups.

**Example `compose.yaml`:**

```yaml
services:
  spine:
    build: .
    image: carrion-spine:latest
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
    read_only: true
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]
    tmpfs: [ /tmp ]

volumes:
  spine-data:
  spine-backups:
```

- **config.toml:** Mount read-only; ensure `data_dir` and `backup_dir` inside the container match the volume paths (e.g. `/var/lib/carrion-spine`, `/var/backups/carrion_spine`) and `config_roots` match the bind-mounted paths (e.g. `/srv/7dtd`).
- **Roots:** Mount config roots read-write (`rw`) so Apply can write files.
- **DISCORD_TOKEN:** Provided via `env_file: .env` or `environment`.

**Example host layout:**

```
/path/to/carrion-spine/
  .env              # DISCORD_TOKEN=...
  config.toml       # from carrion-spine init, paths adjusted for container
  compose.yaml      # as above
  /srv/7dtd         # config roots (bind-mounted into container)
```

---

## J) First successful run checklist

1. **Bot online**  
   After `carrion-spine run` (or `docker compose up -d`), the bot should show as online in your server.

2. **Slash commands**  
   In a channel where the bot can post, type `/mm`. You should see commands under the `mm` group (e.g. `/mm config pull`, `/mm config list`, `/mm edit`, `/mm spine setup`). If not, wait a few minutes (propagation) or re-invite with the **applications.commands** scope.

3. **Index and list**
   - Run `/mm config pull`. Expected: a reply like “Indexed N config files” (and possibly a short sample).
   - Run `/mm config list` (optionally with a root filter). Expected: a list of nicknames and paths.
   - If enabled, run `/mm spine setup` in Discord to check readiness; otherwise run `carrion-spine doctor` locally.

---

## K) First edit mini-walkthrough (end-to-end)

1. **Start edit**  
   `/mm edit nickname: <nickname>` (e.g. from `/mm config list`). The bot sends the current file as an attachment and a session ID.

2. **Edit locally**  
   Download the attachment, edit the file, then upload it in the **same channel** and in the message body include `mm-session:<session_id>` (from the bot’s reply).

3. **Validation and diff**  
   The bot validates the file and shows a diff summary (and inline excerpt or a .diff attachment). Fix any validation errors and re-upload if needed.

4. **Apply**  
   Use the **Apply** button to write the file. Spine performs an atomic write, creates a backup, and records the change in the audit log. If the file changed on disk since the session started, you’ll get a conflict (hash mismatch); run `/mm config pull` and start a new edit if needed.

5. **Confirm**  
   Check the target file on disk and, if configured, any audit channel or log to confirm the apply was recorded.

---

## L) Troubleshooting

| Issue | What to check |
|-------|----------------|
| **Slash commands don’t show up** | Invite must use scope **applications.commands**. Re-invite with that scope. Wait a few minutes for global command propagation. |
| **403 Missing Access** | Bot needs permission in the channel (Send Messages, Embed Links, Attach Files, Read Message History, Use Application Commands). Check channel-specific overwrites and role permissions. If Spine restricts by role, ensure your user has one of the roles in `module_access_roles` (and file-profile roles if used). |
| **Validation failed** | Read the error in the bot’s reply (format or profile rule). Fix the file (e.g. XML well-formedness, required nodes/values). Profile rules are defined in code (e.g. serverconfig.xml, serveradmin.xml); see project docs or source if needed. |
| **Cannot write file** | Bot process must have write access to the config root and backup dir. Check filesystem permissions, Docker volume mounts (`rw`), and that the process is not running as root. Run `carrion-spine doctor` (or `/mm spine setup` if enabled) to verify paths. |
| **Conflict detected (hash mismatch)** | The file on disk changed after you started the edit. Run `/mm config pull` to refresh the index, then start a new edit with the current file. |

---

## M) Security notes

- **Token:** Never paste the bot token into chat, config files committed to git, or screenshots. Use environment variables or a local `.env` file that is gitignored.
- **Process:** Do not run the bot as root. Use a dedicated system user (e.g. `carrion`) for production.
- **Permissions:** Grant the bot and roles the minimum permissions needed (Send Messages, Embed Links, Attach Files, Read Message History, Use Application Commands; add thread permissions only if you use threads).
- **Backups and audit:** Configure backup and audit retention (e.g. `backup_keep` in config, and any audit log retention) and review them periodically.

---

## N) Acceptance criteria

A reviewer can:

1. Create a bot in the Discord Developer Portal and copy the token.
2. Configure token (env or `.env`), role IDs, and config roots in `config.toml`.
3. Start the bot via pipx (`carrion-spine init` → `doctor` → `run`) or Docker (`docker compose up -d`).
4. Run `/mm config pull` and see “Indexed N config files” (or an empty index if roots are empty).
5. Complete one full edit/apply cycle: `/mm edit` → download → edit → upload with `mm-session:...` → Apply → confirm on disk and in audit.
