# Architecture

## Module layout

- **discovery** — Recursive scan of config roots; supported types XML, JSON, YAML, INI; stable nickname generation (filename + folder token, disambiguated); content hashing; path containment checks.
- **database** — Persistent index of config files (nickname, path, type, hash, root token); edit sessions (manual or AI); AI proposal records; audit log; optional spine state (e.g. audit channel per guild).
- **validation** — Format validators (well-formed XML/JSON/YAML/INI; XML hardened against DOCTYPE/ENTITY); file profiles (e.g. serverconfig.xml, serveradmin.xml) with required nodes and optional bounds.
- **diffing** — Unified diff generation; excerpt and full diff; line add/remove summary.
- **sessions** — Session lifecycle; upload storage; size and binary checks.
- **apply** — Conflict check (live file hash vs session hash); temp write, fsync, atomic rename; backup creation and rotation.
- **permissions** — Role-based checks (module access, file-profile access).
- **commands** — Discord cog: `/mm config pull/list`, `/mm edit`, `/mm spine setup/set-audit-channel`, `/mm ai suggest`; attachment handler for uploads; Apply/Cancel and AI Revise views.
- **ai** — Redaction, output contracts (patch/full), patch application, policy checks (blocklist, serveradmin restriction); provider interface and implementations (OpenAI, local HTTP).

## Data flow

1. **Index** — `config pull` scans roots, builds records (nickname, path, type, hash), replaces the index table.
2. **Edit start** — User runs `edit <nickname>`. Bot resolves nickname, reads file, creates session with baseline hash, sends file and session id.
3. **Upload** — User uploads modified file with `mm-session:<id>`. Bot stores upload, validates format and profile, builds diff, shows Apply/Cancel.
4. **Apply** — User clicks Apply. Bot re-hashes live file; if mismatch, abort. Else create backup, write via temp file + rename, update session status, write audit record.
5. **AI flow** — User runs `ai suggest`. Bot reads baseline, optionally redacts, calls provider, validates output (patch or full), runs validation and policy, writes proposed file, creates session and proposal record, shows diff and Apply/Cancel/Revise. Apply path is the same as manual.

## Session lifecycle

Sessions are created in status `pending` with the file’s baseline hash and (after upload or AI) the path to the proposed content. Apply sets status `applied` and writes audit; Cancel sets `cancelled` and writes audit. Sessions are keyed by session_id; AI sessions link to an ai_proposals row for provider and content hashes.

## Validation pipeline

For every proposed write (manual upload or AI proposal): (1) format validation (parse/well-formed); (2) profile validation if a profile matches the path; (3) for AI, policy check (blocklist keys, serveradmin restriction). If any step fails, the user sees the error and no write occurs. On Apply, conflict check (hash) runs before the atomic write.
