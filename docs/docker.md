# Docker Deployment

## Volume layout

- **config.toml** — Mount read-only at `/etc/carrion-spine/config.toml` (or set `CARRION_SPINE_CONFIG` to match). Create via `carrion-spine init` or copy your own.
- **Config roots** — Bind-mount the directories Spine will read and write (e.g. `/srv/7dtd:/srv/7dtd:rw`). Must be read-write so Apply can write files.
- **Data volume** — Persistent volume for database, uploads, and diff files. In the example this is `spine-data` mounted at `/var/lib/carrion-spine`. Set `data_dir = "/var/lib/carrion-spine"` in config when using this layout.
- **Backup volume** — Persistent volume for backups, outside config roots. Example: `spine-backups` at `/var/backups/carrion_spine`. Set `backup_dir = "/var/backups/carrion_spine"` in config.

## Permissions

The image runs as a non-root user. Ensure the mounted config roots and volumes are writable by that user (or run with appropriate UID/GID). If you mount a host path for roots, the host directory must be readable and writable by the container user.

## Production tips

- Use `env_file: .env` for `DISCORD_TOKEN`; do not hardcode the token in the compose file.
- Keep `read_only: true` and use named volumes or bind mounts for writable paths so the container filesystem stays read-only.
- Set `restart: unless-stopped` so the bot restarts after crashes or host reboot.
- For multiple config roots, add one volume per root and set `config_roots` in `config.toml` to the paths inside the container.
