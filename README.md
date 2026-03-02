# Carrion: Spine — Discord-first Config Editor for 7 Days to Die

Carrion: Spine is a Discord-first configuration editor module for 7 Days to Die server administration. It supports indexed discovery, attachment-based edit sessions, validation, diffs, conflict-safe apply, and audit logging using SQLite.

## Features

- Recursive scan and persistent indexing of XML/JSON/YAML/INI configs
- Human-friendly nicknames for indexed files
- Slash command flow for listing and editing configs (`/mm ...`)
- Format and profile-based validation (e.g., `serverconfig.xml`, `serveradmin.xml`)
- Unified diff generation with summary and excerpt/full output handling
- Atomic apply with hash conflict detection and rolling backups
- Role-based access controls and SQLite audit trails

## Development

- Python: 3.11+
- Install deps: `pip install -U discord.py`
- Run bot: integrate `carrion_spine.commands.setup` in your bot startup
- Quick syntax check: `python -m compileall carrion_spine`

> TODO: Add full local/dev/prod setup instructions and systemd unit example.
