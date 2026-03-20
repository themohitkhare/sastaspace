# Phase 1: Secure API Foundation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `POST /redesign` SSE endpoint to the existing FastAPI app in `server.py`. Harden it with IP rate limiting, a concurrency cap, LLM output sanitization, and CORS. The frontend (Phase 2+) will consume this endpoint. The existing static file serving and subprocess launcher in `server.py` remain unchanged.

</domain>

<decisions>
## Implementation Decisions

### SSE Event Payload Shape

All events use the named-event SSE format: `event: <name>\ndata: <json>\n\n`

Rich payload — every event carries `message` (human-readable), `progress` (0–100), and `job_id` (UUID generated per request):

```
event: crawling
data: {"job_id": "uuid", "message": "Crawling your site...", "progress": 10}

event: redesigning
data: {"job_id": "uuid", "message": "Claude is redesigning...", "progress": 40}

event: deploying
data: {"job_id": "uuid", "message": "Deploying your redesign...", "progress": 80}

event: done
data: {"job_id": "uuid", "message": "Done!", "progress": 100, "url": "/acme-corp/", "subdomain": "acme-corp"}

event: error
data: {"job_id": "uuid", "error": "<sanitized user-facing message>"}
```

- `job_id`: UUID4, generated at request start, included in every event
- `done` includes both `url` (relative path, e.g. `/acme-corp/`) and `subdomain` (slug, e.g. `acme-corp`)
- `error` carries only a sanitized user-facing string — no internal exception detail exposed

**Progress values:** crawling=10, redesigning=40, deploying=80, done=100

### Rate Limiting

- **Storage:** In-memory only — `dict[str, list[float]]` mapping IP → list of request timestamps
- **Algorithm:** Sliding window — filter out timestamps older than `rate_limit_window_seconds`, reject if count ≥ `rate_limit_max`
- **On hit:** HTTP 429 JSON response (not SSE): `{"error": "Rate limit exceeded. Try again in X minutes.", "retry_after": <seconds>}`
- **Check order:** Rate limit check runs FIRST, concurrency Semaphore check runs SECOND
- **Localhost exempt:** `127.0.0.1` and `::1` bypass rate limiting (development convenience)
- **Counting:** All submitted requests count — failed pipeline runs count the same as successes

### Concurrency Cap

- `asyncio.Semaphore(1)` — max 1 simultaneous redesign job
- On rejection (semaphore busy): HTTP 429 JSON: `{"error": "A redesign is already in progress. Please wait and try again."}`

### Error Handling Mid-Stream

- Any pipeline failure (crawl timeout, Claude API unreachable, deployer error) emits an `event: error` SSE event with sanitized message, then the generator returns cleanly (no abrupt disconnect)
- API offline (claude-code-api gateway at localhost:8000 unreachable): `"error": "Redesign service unavailable. Please try again later."`
- Crawl failure: `"error": "Could not reach that website. Check the URL and try again."`
- nh3 sanitization: always silently proceed with sanitized HTML — no warning logged, no failure

### Module Structure

- All new code added to `server.py` — `make_app()` extended with `/redesign` endpoint, rate limiter dict, and semaphore
- No new files created for Phase 1
- New settings added to existing `Settings` class in `config.py`:
  - `cors_origins: list[str]` — default `["http://localhost:3000"]`, overridable via `CORS_ORIGINS` env var (comma-separated)
  - `rate_limit_max: int` — default `3`
  - `rate_limit_window_seconds: int` — default `3600`
- CORS middleware added to `make_app()` using `fastapi.middleware.cors.CORSMiddleware`

### FastAPI Version

- Bump `fastapi` dependency to `>=0.135.0` in `pyproject.toml` for built-in `EventSourceResponse` / SSE support
- Use `fastapi.responses.StreamingResponse` with `media_type="text/event-stream"` (FastAPI 0.135+ approach)

### Claude's Discretion

- Exact in-memory data structure for rate limiter cleanup (e.g. when to prune old timestamps)
- asyncio.to_thread() call signature for both redesigner.redesign() and deployer.deploy()
- IP extraction method (X-Forwarded-For header vs request.client.host, with fallback)

</decisions>

<specifics>
## Specific Ideas

- SSE format follows the W3C EventSource spec: `event:` line, then `data:` line, then blank line
- Job ID enables future retry-without-rerun feature (not in Phase 1 scope, but payload is ready)
- The `done` event's `subdomain` field will be used by Phase 3 to construct the shareable result page URL

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/REQUIREMENTS.md` §API — API-01 through API-08 — exact requirements for this phase
- `.planning/ROADMAP.md` §Phase 1 — success criteria and goal statement

### Existing code (read before modifying)
- `sastaspace/server.py` — existing FastAPI app, `make_app()` factory to extend
- `sastaspace/config.py` — Pydantic Settings class to extend with new fields
- `sastaspace/redesigner.py` — synchronous `redesign(crawl_result)` function to wrap in `asyncio.to_thread()`
- `sastaspace/deployer.py` — synchronous `deploy(url, html, sites_dir)` function to wrap in `asyncio.to_thread()`
- `pyproject.toml` — dependency versions to update (fastapi, add nh3)

### Project state
- `.planning/STATE.md` — key decisions already made (SSE via POST, nh3, etc.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.Settings`: Pydantic settings with `.env` support — extend with `cors_origins`, `rate_limit_max`, `rate_limit_window_seconds`
- `deployer.derive_subdomain(url)`: already produces the slug used in the result URL — no need to re-derive in the endpoint
- `deployer.DeployResult.subdomain`: the slug to include in the `done` event's `subdomain` field
- `make_app(sites_dir)`: factory function pattern — add endpoint, middleware, and module-level state (semaphore, rate_limit_store) inside this function or as module globals

### Established Patterns
- FastAPI app created with `FastAPI(title=...)` — follow same factory pattern, don't replace `app = make_app(...)` at module bottom
- Pydantic Settings loaded from `.env` — add new fields with defaults, no breaking changes
- Synchronous functions (`redesigner.redesign`, `deployer.deploy`) — both need `asyncio.to_thread()` wrapping in the async endpoint

### Integration Points
- `server.py`'s `app` module-level var (`app = make_app(_default_sites_dir)`) is what uvicorn imports — must remain
- The SSE endpoint receives `url` from the POST body, passes it to `crawler.crawl()`, then to `redesigner.redesign()`, then to `deployer.deploy()`
- `nh3.clean(html)` is called on the HTML returned by `redesigner.redesign()` before passing to `deployer.deploy()`

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-secure-api-foundation*
*Context gathered: 2026-03-21*
