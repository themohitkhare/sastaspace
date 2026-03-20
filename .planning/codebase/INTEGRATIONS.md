# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**AI / LLM:**
- claude-code-api (local gateway) — OpenAI-compatible HTTP API gateway that proxies to Claude
  - SDK/Client: `openai` Python SDK (`sastaspace/redesigner.py` line 7)
  - Base URL: `http://localhost:8000/v1` (configurable via `CLAUDE_CODE_API_URL`)
  - Auth: `api_key="claude-code"` (hardcoded dummy value; auth is handled by the gateway)
  - Model: configurable via `CLAUDE_MODEL` env var (default: `claude-sonnet-4-5-20250929`)
  - Usage: `client.chat.completions.create(...)` with multimodal content (screenshot base64 + text)
  - Max tokens: 16,000 per request
  - This is NOT the official Anthropic API; it is a local proxy. `ANTHROPIC_API_KEY` is consumed by the gateway, not this app.

**Web Crawling (external sites, arbitrary URLs):**
- Any public URL — Playwright headless Chromium makes requests to arbitrary target websites
  - Implementation: `sastaspace/crawler.py`, `async def crawl(url: str)`
  - Browser: Chromium via `playwright.async_api.async_playwright`
  - UA string: Chrome 120 on macOS (set in `sastaspace/crawler.py` line 153)
  - Timeout: 30 seconds per page load (`wait_until="networkidle"`)

**Google Fonts:**
- Referenced in system prompt (`sastaspace/redesigner.py` line 27): AI-generated HTML uses `@import` from `fonts.googleapis.com`
- This is a passive dependency — the generated HTML files make outbound requests when served in a browser. The Python code itself makes no direct Google Fonts calls.

## Data Storage

**Databases:**
- None — no database. All persistence is via local filesystem.

**File Storage:**
- Local filesystem — all redesigned sites saved to `sites/{subdomain}/index.html`
- Registry: `sites/_registry.json` — JSON array tracking all deployed redesigns with subdomain, original URL, timestamp, status
- Per-site metadata: `sites/{subdomain}/metadata.json`
- Server state: `sites/.server_port` — persisted port number for the running preview server
- Server logs: `sites/.server.log` — appended to by detached uvicorn subprocess
- Default path: `./sites` (configurable via `SITES_DIR` env var)
- Implementation: `sastaspace/deployer.py`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None — this is a local developer tool with no user authentication
- The claude-code-api gateway handles Anthropic API key auth externally

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Uvicorn subprocess logs appended to `sites/.server.log` when server runs in background (`sastaspace/server.py` line 134)
- Foreground `serve` command streams uvicorn logs directly to terminal
- CLI errors surfaced via Rich `Panel` with `[red]...[/red]` formatting

## CI/CD & Deployment

**Hosting:**
- Local machine only — no cloud deployment

**CI Pipeline:**
- `make ci` runs `make lint` then `make test` (see `Makefile`)
- Lint: `uv run ruff check` + `uv run ruff format --check`
- Test: `uv run pytest tests/ -v`
- No GitHub Actions or external CI configuration detected

## Environment Configuration

**Required env vars (for full functionality):**
- `ANTHROPIC_API_KEY` — consumed by the external claude-code-api gateway process, not directly by this Python code

**Optional env vars (with defaults):**
- `CLAUDE_CODE_API_URL` — gateway base URL (default: `http://localhost:8000/v1`)
- `SITES_DIR` — output directory (default: `./sites`)
- `SERVER_PORT` — preview server port (default: `8080`)
- `CLAUDE_MODEL` — Claude model identifier (default: `claude-sonnet-4-5-20250929`)

**Secrets location:**
- `.env` file at project root (gitignored); template at `.env.example`
- `pydantic-settings` loads `.env` automatically via `sastaspace/config.py`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (generated HTML may cause browsers to call `fonts.googleapis.com`, but no server-side outbound webhooks)

---

*Integration audit: 2026-03-21*
