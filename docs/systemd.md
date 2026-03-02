# Production systemd Deployment

## Generate unit and tmpfiles

```bash
carrion-spine install-systemd --user carrion --group carrion --config /etc/carrion-spine/config.toml
```

Copy the printed unit to `/etc/systemd/system/carrion-spine.service` and the tmpfiles.d snippet to `/etc/tmpfiles.d/carrion-spine.conf`.

## File ownership

Create a dedicated user and group (e.g. `carrion`). Create `/etc/carrion-spine/` and place `config.toml` there. Use an env file (e.g. `/etc/carrion-spine/env`) for `DISCORD_TOKEN` and set ownership so only the service user can read it:

```bash
chown -R carrion:carrion /etc/carrion-spine
chmod 600 /etc/carrion-spine/env
```

Ensure the service user can write to config roots and to the backup directory (e.g. `/var/backups/carrion_spine`). tmpfiles.d can create data and backup dirs with correct ownership.

## Hardened unit example

The generator prints a unit similar to:

```ini
[Unit]
Description=Carrion Spine Discord Bot Module Host
After=network.target

[Service]
Type=simple
User=carrion
Group=carrion
WorkingDirectory=/etc/carrion-spine
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=-/etc/carrion-spine/env
Environment="CARRION_SPINE_CONFIG=/etc/carrion-spine/config.toml"
ExecStart=/usr/bin/carrion-spine run --config /etc/carrion-spine/config.toml
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/lib/carrion-spine /var/backups/carrion_spine /srv/7dtd

[Install]
WantedBy=multi-user.target
```

Adjust `ReadWritePaths` to your config roots and data/backup paths.

## Service management

```bash
sudo systemctl daemon-reload
sudo systemctl enable carrion-spine
sudo systemctl start carrion-spine
sudo systemctl status carrion-spine
```

Logs: `journalctl -u carrion-spine -f`.
