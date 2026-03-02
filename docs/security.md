# Security Model

## Threat model

Spine is designed for operators who already have filesystem and Discord access. Threats in scope: accidental overwrites, malformed configs, race conditions (concurrent edits), and lack of accountability. Out of scope: hostile takeover of the host or Discord server (mitigation is access control and operational hygiene).

## Protections

- **Root confinement** — Only paths under configured roots are indexed or written. Path resolution rejects traversal outside those roots.
- **Upload limits** — Size and type checks; binary content is rejected.
- **XML hardening** — DOCTYPE and ENTITY are rejected to reduce XXE risk.
- **Validation before write** — Format and profile validation run before any apply; invalid content is never written.
- **Diff-first** — Operators see a diff and validation result before choosing Apply.
- **Conflict check** — Apply re-checks the live file; if it changed since the session started, Apply is blocked.
- **Atomic write** — Content is written to a temp file, synced, then renamed onto the target. Rolling backups are created first.
- **Backup location** — Backup dir must be outside config roots (enforced at config load).
- **Audit** — Every validation failure, apply, and cancel is logged (user, path, status, validation result). AI applies include actor type and proposal metadata.
- **Secrets** — Token and API keys belong in environment or env files, not in config committed to version control. AI redaction (when enabled) limits what is sent to the provider; it does not replace access control.

## Least privilege

- Run the bot as a dedicated user, not root.
- Grant only the Discord permissions needed (Send Messages, Embed Links, Attach Files, Read Message History, Use Application Commands).
- Use `module_access_roles` and optionally `file_profile_roles` to limit who can edit which files.
- Restrict filesystem permissions on config roots and backup dir so only the service user can write.

## Backups and audit retention

- Backups are rolling; `backup_keep` controls how many per file are retained. Store backups outside config roots and on durable storage.
- Audit records are appended; retention is not automatic. Plan for log rotation or archival if you need to cap size or comply with retention policy.
