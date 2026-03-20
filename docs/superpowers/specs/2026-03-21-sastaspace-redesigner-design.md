# SastaSpace AI Website Redesigner — Design Spec
**Date:** 2026-03-21
**Author:** Claude (designer/developer/QA)
**Status:** Approved for implementation

---

## 1. Problem

Small businesses have ugly, outdated websites but can't afford professional redesigns ($2K–$10K). SastaSpace solves this: enter any URL, get a beautiful AI-redesigned version in under 60 seconds.

---

## 2. MVP Scope (Local-First)

The local MVP delivers the full core pipeline:

```
sastaspace redesign <url>
  → crawl (Playwright, headless Chromium)
  → redesign (Claude API, vision + text)
  → deploy (write sites/{subdomain}/index.html)
  → serve (FastAPI local server at localhost:8080)
  → open browser automatically
```

Cloudflare DNS, tunnels, and payments are explicitly **out of scope** for this build.

---

## 3. Project Structure

```
sastaspace/
├── sastaspace/
│   ├── __init__.py
│   ├── cli.py          # Click entry: `sastaspace` command group
│   ├── config.py       # pydantic-settings, reads .env
│   ├── crawler.py      # Playwright async crawler
│   ├── redesigner.py   # Claude API (vision + text → HTML)
│   ├── deployer.py     # Writes sites/ + registry
│   └── server.py       # FastAPI local preview server
├── sites/              # Generated output (gitignored)
│   ├── _registry.json
│   └── {subdomain}/
│       ├── index.html
│       └── metadata.json
├── .env                # gitignored
├── .env.example
├── pyproject.toml      # uv, entry_point: sastaspace=sastaspace.cli:main
└── README.md
```

---

## 4. Module Designs

### 4.1 config.py

Uses `pydantic-settings` to read from `.env`. Fields:
- `ANTHROPIC_API_KEY: str` — required
- `SITES_DIR: Path` — default `./sites`
- `SERVER_PORT: int` — default `8080`
- `CLAUDE_MODEL: str` — default `claude-sonnet-4-20250514`

### 4.2 crawler.py

**Input:** `url: str`
**Output:** `CrawlResult` dataclass
**Technology:** Playwright async API, Chromium

Extracts:
- Full rendered HTML (after JS execution, `wait_until="networkidle"` + 2s wait)
- Above-the-fold screenshot (PNG, base64-encoded) — sent to Claude vision
- Title, meta description, favicon URL
- Headings (h1–h4), nav links, text content (max 5000 chars, cleaned)
- Images (src, alt, width, height), detected colors + fonts
- Content sections

`CrawlResult.to_prompt_context()` → formatted markdown string for Claude

Error handling: sets `result.error` on failure; caller checks before proceeding.

### 4.3 redesigner.py

**Input:** `CrawlResult`
**Output:** `str` (complete HTML)
**Technology:** Anthropic Python SDK

API call:
- Model: `claude-sonnet-4-20250514`
- Max tokens: `16000`
- Content: [image block (base64 PNG screenshot), text block (context + instructions)]

System prompt focuses Claude on: modern clean design, preserve ALL original content, mobile-first, single self-contained HTML file with inline CSS, Google Fonts only (no CDN frameworks), include "Redesigned by SastaSpace.com" badge in footer.

Output cleaning: strip markdown code fences if present, ensure starts with `<!DOCTYPE html>`.

**Validity checks before returning:**
- Response must be non-empty
- Must contain `<!DOCTYPE html>` (case-insensitive)
- Must contain closing `</html>` tag
- If any check fails: raise `RedesignError` with the raw response for debugging. Caller shows user a clear error message.

### 4.4 deployer.py

**Input:** `subdomain: str`, `html: str`, `original_url: str`
**Output:** `Path` (to deployed index.html)

**Subdomain derivation algorithm:**
Given `https://www.acme-corp.co.uk/shop`:
1. Parse URL, extract hostname: `www.acme-corp.co.uk`
2. Strip `www.` prefix if present: `acme-corp.co.uk`
3. Take only the registered domain (everything up to but excluding the TLD dot): use the full hostname as-is but replace dots with hyphens: `acme-corp-co-uk`
4. Lowercase, replace any non-alphanumeric (except hyphens) with hyphens, collapse multiple hyphens
5. Truncate to 50 chars
6. **Collision handling:** if `sites/{subdomain}/` already exists, append `--2`, `--3`, etc. until unique. Inform user of the chosen name.

Steps:
1. Sanitize subdomain per algorithm above
2. Create `sites/{subdomain}/`
3. Write `index.html`
4. Write `metadata.json` (subdomain, original_url, timestamp, status)
5. Update `sites/_registry.json` via atomic write (write to `_registry.json.tmp`, then `os.replace` → atomic on POSIX)

### 4.5 server.py

**Technology:** FastAPI + `starlette.staticfiles`

Routes:
- `GET /` → HTML page listing all sites from `_registry.json` with links
- `GET /{subdomain}/` → serves `sites/{subdomain}/index.html`
- `GET /{subdomain}/{path}` → static file fallback

**Server lifecycle:**
- `server.py` exposes a `ensure_running(sites_dir, port) -> int` function used by the CLI's `redesign` command
- `ensure_running`: checks if a port is listening via socket. If not, spawns `uvicorn sastaspace.server:app` as a **detached subprocess** (stdout/stderr to logfile `sites/.server.log`), polls until ready (max 5s), returns the actual port used
- The resolved port is stored in `sites/.server_port` (plain text) and returned to caller for use in the browser-open URL
- `sastaspace serve` command: calls `ensure_running` but then blocks in foreground, streaming logs to terminal — useful for debugging

### 4.6 cli.py

**Technology:** Click + Rich

Commands:
| Command | Description |
|---------|-------------|
| `sastaspace redesign <url>` | Full pipeline + open browser |
| `sastaspace redesign <url> -s name` | Custom subdomain |
| `sastaspace redesign <url> --no-open` | Skip auto-open browser |
| `sastaspace serve` | Start preview server (blocks) |
| `sastaspace list` | Rich table of all deployed sites |
| `sastaspace open <subdomain>` | Open specific site in browser |
| `sastaspace remove <subdomain>` | Delete site files + registry entry |

Rich progress display during `redesign`: spinner per step (Crawling → Redesigning → Deploying → Serving).

---

## 5. Data Flow

```
redesign <url>
    │
    ├─ [1] Crawl (Playwright, ~10-20s)
    │       CrawlResult { html, screenshot_b64, title, ... }
    │
    ├─ [2] Redesign (Claude API, ~20-40s)
    │       str: complete HTML file
    │
    ├─ [3] Deploy (filesystem, <1s)
    │       sites/acme/index.html
    │       sites/acme/metadata.json
    │       sites/_registry.json (updated)
    │
    ├─ [4] Ensure server running (subprocess check, <1s)
    │       http://localhost:8080
    │
    └─ [5] Open browser
            http://localhost:8080/acme/
```

---

## 6. Error Handling

- **Crawl failure:** Rich error panel, clear message (e.g., "Could not reach site — is it accessible?"). Exit cleanly.
- **Claude API failure:** Show error, suggest checking ANTHROPIC_API_KEY. Exit cleanly.
- **Port in use:** `ensure_running` tries 8080, 8081, 8082 in order. Saves chosen port to `sites/.server_port`. Returns resolved port to the CLI so the browser-open URL uses the correct port (never reads stale config).
- **Timeout:** Crawl timeout 30s, Claude timeout 120s.

---

## 7. Configuration (.env.example)

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
SITES_DIR=./sites
SERVER_PORT=8080
CLAUDE_MODEL=claude-sonnet-4-20250514
```

---

## 8. Dependencies (pyproject.toml)

```
anthropic>=0.40.0
playwright>=1.40.0
beautifulsoup4>=4.12.0
click>=8.1.0
rich>=13.0.0
fastapi>=0.115.0
uvicorn>=0.32.0
python-dotenv>=1.0.0
pydantic-settings>=2.0.0
```

**Playwright browser install:** `crawler.py` checks for Chromium on first use via `playwright._impl._driver` or a simple subprocess call to `playwright install chromium --dry-run`. If not installed, it auto-runs `playwright install chromium` with a Rich status message before crawling. This is transparent to the user.

---

## 9. Quality Bar

Before declaring local MVP done:
- `sastaspace redesign https://example.com` runs end-to-end without error
- Generated HTML is valid, self-contained, opens correctly in browser
- `sastaspace list` shows the deployed site
- `sastaspace remove acme` cleans up files and registry
- No unhandled exceptions on bad input (nonexistent domain, empty page)

---

## 10. Out of Scope (This Build)

- Cloudflare DNS / tunnel
- Nginx config generation
- Payments (Razorpay / Stripe)
- User accounts / dashboard
- Multiple design styles
- Web UI / FastAPI web frontend
