# AI Assistance (MVP)

`/mm ai suggest` generates a single-file proposal from a configured LLM. Proposals go through the same validation and apply pipeline as manual edits. **AI never auto-applies.**

## Provider configuration

Optional `[ai]` section in `config.toml`:

- **enabled** — Set true to enable suggest. Default false.
- **provider** — `"openai"` or `"local_http"`.
- **allow_external** — If false, only `local_http` is allowed (default). Set true to allow OpenAI.
- **mode_default** — `"patch"` (unified diff only) or `"full"` (full file content). Default `"patch"`.
- **redact_secrets** — Redact common secret patterns before sending content to the provider. Default true.
- **max_input_bytes**, **max_output_bytes** — Caps (default 200_000).
- **temperature_default** — Model temperature (e.g. 0.2).
- **suggest_roles** — Role IDs that can run `/mm ai suggest`. Defaults to `module_access_roles` if omitted.
- **apply_roles** — Role IDs that can apply AI proposals. Defaults to `module_access_roles` if omitted.

**OpenAI:** `[ai.openai]` — `api_key_env` (e.g. `"OPENAI_API_KEY"`), `model` (e.g. `"gpt-4o-mini"`). Set the API key in the environment.

**Local HTTP (e.g. Ollama):** `[ai.local_http]` — `url` (e.g. `"http://localhost:11434/v1/chat/completions"`), `model` (e.g. `"llama3.1"`).

## Role gating

- **suggest_roles** — Who can run `/mm ai suggest`.
- **apply_roles** — Who can click Apply on an AI proposal. Apply also respects existing file-profile and module access checks.

## Redaction

When `redact_secrets` is true, common patterns (e.g. api_key, password, token) in the file content are redacted before sending to the provider. Only a flag that redaction occurred is stored; the original secret is never logged.

## Patch vs full mode

- **patch** — Model is asked to output only a unified diff. Spine validates and applies the diff to the baseline to get the proposed file, then runs validation and policy checks.
- **full** — Model is asked to output only the complete file content (no markdown or commentary). That content is validated and checked by policy.

Invalid output (e.g. markdown or extra text) causes the proposal to fail; the user sees an error and can retry or use manual edit.

## Safety behavior

- Proposals are validated (format and profile) and checked by policy (e.g. blocklist keys, serveradmin.xml restriction). Invalid or policy-blocked content is rejected.
- Apply uses the same conflict check and atomic write as manual edits. Audit logs record AI applies with actor type and proposal metadata.
- `allow_external` defaults to false so only a local HTTP provider is used unless explicitly enabled.
