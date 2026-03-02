# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.2.0] - TBD

### Added

- Python package layout with `pyproject.toml` (Hatch).
- Console script entrypoint: `carrion-spine` with subcommands `init`, `doctor`, `run`.
- TOML config file support and config loader.
- CLI `init`: interactive prompts, writes `config.toml` and `.env.example`.
- CLI `doctor`: checks roots, backup dir, SQLite path; Discord intents reminder.
- CLI `run`: minimal host that loads Spine from config and env token.
- Dockerfile and docker-compose.yml for containerized deployment.
- CLI `install-systemd`: generates unit file and tmpfiles.d snippet.
- `/mm spine setup` guided wizard for readiness checks (admin-only).
- Improved `/mm config list` and `/mm config pull` responses (filter examples, hash/profile info).
- README split into Quickstart, Docker, and Production systemd paths; first successful change tutorial.

### Changed

- Config driven by `config.toml` (and env overrides) instead of code-only settings.
- Default data paths: `./data/spine.sqlite`, `./backups/` (dev) or `/var/backups/carrion_spine` (prod).

### Security

- Backup dir must be outside configured config roots (validated at load).
- Hardening defaults in Docker and systemd examples.

## [0.1.0] - Initial release

- Config discovery and indexing (XML, JSON, YAML, INI).
- Slash commands: `/mm config pull`, `/mm config list`, `/mm edit <nickname>`.
- Attachment-based edit workflow with validation, diff, apply/cancel.
- Atomic writes, conflict detection, audit log.
