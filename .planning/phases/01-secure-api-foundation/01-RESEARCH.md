# Phase 1: Secure API Foundation - Research

**Researched:** 2026-03-21
**Domain:** FastAPI SSE endpoint, rate limiting, HTML sanitization, CORS
**Confidence:** HIGH

## Summary

Phase 1 adds a `POST /redesign` SSE endpoint to the existing FastAPI app in `server.py`, hardened with IP rate limiting, a concurrency semaphore, LLM output sanitization via nh3, and CORS configuration. All decisions are locked via CONTEXT.md -- no architectural alternatives need exploring.

The key technical discovery is that FastAPI 0.135+ (already installed at 0.135.1) provides built-in `EventSourceResponse` and `ServerSentEvent` classes in `fastapi.sse`, which handle keep-alive pings, `Cache-Control: no-cache`, and `X-Accel-Buffering: no` headers automatically. The CONTEXT.md specifies `StreamingResponse` with `media_type="text/event-stream"`, but the built-in `EventSourceResponse` with `ServerSentEvent` is the idiomatic FastAPI 0.135+ approach and produces correctly formatted SSE with less boilerplate. This is noted as a recommendation.

An important finding: `crawler.crawl()` is already an `async def` function (uses `async_playwright`), so it does NOT need `asyncio.to_thread()`. Only `redesigner.redesign()` and `deployer.deploy()` are synchronous and need thread wrapping.

**Primary recommendation:** Use `fastapi.sse.EventSourceResponse` with `ServerSentEvent` for the SSE endpoint. Use `asyncio.to_thread()` for the two sync functions. All other decisions from CONTEXT.md are directly implementable as specified.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- SSE via POST + StreamingResponse with media_type="text/event-stream" (note: recommend EventSourceResponse instead -- see Architecture Patterns)
- Rich event payload: {job_id, message, progress, url/subdomain (done), error (error)}
- In-memory rate limiting dict[str, list[float]] sliding window
- 429 JSON (not SSE) for rate limit/concurrency violations
- Rate check first, then semaphore check
- Localhost (127.0.0.1, ::1) exempt from rate limiting
- All attempts count against rate limit (not just successes)
- nh3 sanitization: silently proceed
- Error: send error SSE event then close cleanly
- All code in server.py (extend make_app())
- New settings in config.py Settings class
- CORS origins env-var configurable
- asyncio.Semaphore(1) for concurrency cap
- Progress values: crawling=10, redesigning=40, deploying=80, done=100
- job_id: UUID4 per request

### Claude's Discretion
- Exact in-memory data structure for rate limiter cleanup (e.g. when to prune old timestamps)
- asyncio.to_thread() call signature for both redesigner.redesign() and deployer.deploy()
- IP extraction method (X-Forwarded-For header vs request.client.host, with fallback)

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | POST /redesign endpoint accepts URL, streams SSE progress events | FastAPI EventSourceResponse/ServerSentEvent pattern verified; POST SSE supported |
| API-02 | SSE stream emits named step events: crawling, redesigning, deploying, done, error | ServerSentEvent `event` parameter maps directly to named events |
| API-03 | redesign() wrapped in asyncio.to_thread() to avoid blocking | Verified: redesign() and deploy() are sync; crawl() is already async |
| API-04 | Concurrency cap: max 1 simultaneous redesign (asyncio.Semaphore) | asyncio.Semaphore(1) with try_acquire pattern documented |
| API-05 | IP rate limiting: max 3/hour/IP | Sliding window dict[str, list[float]] pattern documented |
| API-06 | LLM output HTML sanitized with nh3 | nh3.clean() API verified, default tags strip script/style |
| API-07 | CORS configured for Next.js frontend origin | CORSMiddleware pattern documented with env-var origins |
| API-08 | fastapi bumped to >=0.135.0 | Already at 0.135.1; built-in SSE support verified working |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.135.0 (installed: 0.135.1) | Web framework with built-in SSE | Already in project; 0.135+ has native EventSourceResponse |
| nh3 | >=0.3.3 | HTML sanitization | Rust-backed ammonia bindings; 20x faster than bleach; de facto replacement |
| pydantic-settings | >=2.0.0 (installed) | Settings management | Already in project for config.py |
| uvicorn | >=0.32.0 (installed) | ASGI server | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| starlette | (transitive via fastapi) | CORSMiddleware, Request | Already available; CORS middleware import |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| EventSourceResponse | StreamingResponse + manual SSE formatting | StreamingResponse requires manual `event: X\ndata: Y\n\n` formatting, no auto keep-alive, no auto headers. EventSourceResponse handles all of this. |
| In-memory rate limiter | slowapi / redis | Overkill for single-process, low-traffic lead-gen app |
| nh3 | bleach | bleach is deprecated; nh3 is the official replacement |

**Installation:**
```bash
uv add "nh3>=0.3.3"
```

**Version verification:**
- fastapi 0.135.1 -- confirmed installed and `from fastapi.sse import EventSourceResponse, ServerSentEvent` works
- nh3 0.3.3 -- latest on PyPI as of 2026-02-14; NOT yet installed (must add to pyproject.toml)

## Architecture Patterns

### Recommended Project Structure
```
sastaspace/
  config.py      # Add cors_origins, rate_limit_max, rate_limit_window_seconds
  server.py      # Add /redesign endpoint, rate limiter, semaphore, CORS middleware
  crawler.py     # Unchanged (already async)
  redesigner.py  # Unchanged (called via asyncio.to_thread)
  deployer.py    # Unchanged (called via asyncio.to_thread)
```

### Pattern 1: SSE via EventSourceResponse + ServerSentEvent (POST)
**What:** FastAPI 0.135+ built-in SSE support with typed event objects
**When to use:** Any SSE streaming endpoint
**Why over StreamingResponse:** Automatic keep-alive pings (15s), Cache-Control headers, X-Accel-Buffering header, correct Content-Type, and structured event construction via ServerSentEvent.

**Note:** CONTEXT.md specifies `StreamingResponse`. The recommendation is `EventSourceResponse` because it IS the FastAPI 0.135+ approach and produces identical wire format with less code and better defaults. If the planner prefers strict adherence to CONTEXT.md wording, `StreamingResponse` with manual formatting works fine too.

```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
from collections.abc import AsyncIterable
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.post("/redesign", response_class=EventSourceResponse)
async def redesign_endpoint(body: RedesignRequest, request: Request) -> AsyncIterable[ServerSentEvent]:
    # Rate limit + semaphore checks happen BEFORE yielding
    # (return JSONResponse 429 if blocked -- see Pattern 3)

    job_id = str(uuid4())

    yield ServerSentEvent(
        data=json.dumps({"job_id": job_id, "message": "Crawling your site...", "progress": 10}),
        event="crawling"
    )

    # crawl() is async -- await directly, no to_thread needed
    crawl_result = await crawl(url)

    yield ServerSentEvent(
        data=json.dumps({"job_id": job_id, "message": "Claude is redesigning...", "progress": 40}),
        event="redesigning"
    )

    # redesign() is sync -- wrap in to_thread
    html = await asyncio.to_thread(redesign, crawl_result, settings.claude_code_api_url, settings.claude_model)
    html = nh3.clean(html)

    yield ServerSentEvent(
        data=json.dumps({"job_id": job_id, "message": "Deploying your redesign...", "progress": 80}),
        event="deploying"
    )

    # deploy() is sync -- wrap in to_thread
    result = await asyncio.to_thread(deploy, url, html, settings.sites_dir)

    yield ServerSentEvent(
        data=json.dumps({"job_id": job_id, "message": "Done!", "progress": 100, "url": f"/{result.subdomain}/", "subdomain": result.subdomain}),
        event="done"
    )
```

**CRITICAL CAVEAT -- SSE generator cannot return early with a different response type.** Rate limit and concurrency checks that return 429 JSON cannot be inside the generator. They MUST happen before the generator starts. Two approaches:

**Approach A (recommended):** Separate the checks from the generator. The endpoint function does checks first, then returns EventSourceResponse wrapping a separate async generator:
```python
@app.post("/redesign")
async def redesign_endpoint(body: RedesignRequest, request: Request):
    # Check rate limit
    ip = get_client_ip(request)
    if is_rate_limited(ip):
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded...", "retry_after": ...})

    # Check concurrency
    if semaphore.locked():
        return JSONResponse(status_code=429, content={"error": "A redesign is already in progress..."})

    # Record the attempt (counts against rate limit)
    record_request(ip)

    # Return SSE stream
    return EventSourceResponse(redesign_stream(body.url))
```

**Approach B:** Use `response_class=EventSourceResponse` on the decorator and yield -- but then you CANNOT return a JSONResponse for 429 errors. This approach does not work for this use case.

**Verdict: Use Approach A.** The endpoint is a regular `async def` that performs checks and explicitly returns either JSONResponse (429) or EventSourceResponse (SSE stream).

### Pattern 2: asyncio.to_thread() for Sync Functions
**What:** Run blocking sync functions in a thread without blocking the event loop
**When to use:** Wrapping `redesigner.redesign()` and `deployer.deploy()`

```python
# Source: Python stdlib docs
import asyncio

# redesigner.redesign(crawl_result, api_url, model) -> str
html = await asyncio.to_thread(
    redesign,
    crawl_result,
    settings.claude_code_api_url,
    settings.claude_model,
)

# deployer.deploy(url, html, sites_dir, subdomain=None) -> DeployResult
result = await asyncio.to_thread(
    deploy,
    url,
    html,
    settings.sites_dir,
)
```

**Note:** `crawler.crawl(url)` is `async def` -- call with `await crawl(url)` directly. Do NOT wrap in to_thread.

### Pattern 3: Rate Limiter + Semaphore Guard
**What:** In-memory sliding window rate limiter + asyncio.Semaphore for concurrency
**When to use:** Before starting the SSE stream

```python
import time
from asyncio import Semaphore

# Module-level state (inside make_app or as closure variables)
_rate_limit_store: dict[str, list[float]] = {}
_redesign_semaphore = Semaphore(1)

def is_rate_limited(ip: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Check sliding window. Returns (is_limited, retry_after_seconds)."""
    now = time.time()
    timestamps = _rate_limit_store.get(ip, [])
    # Prune expired timestamps
    cutoff = now - window_seconds
    timestamps = [t for t in timestamps if t > cutoff]
    _rate_limit_store[ip] = timestamps

    if len(timestamps) >= max_requests:
        retry_after = int(timestamps[0] - cutoff) + 1
        return True, retry_after
    return False, 0

def record_request(ip: str) -> None:
    """Record a request timestamp for rate limiting."""
    _rate_limit_store.setdefault(ip, []).append(time.time())
```

**Semaphore usage in endpoint:**
```python
async with _redesign_semaphore:
    async for event in _do_redesign_pipeline(url, job_id):
        yield event
```

Wait -- the semaphore wraps the generator body, but we need `semaphore.locked()` for a non-blocking check. Use `_redesign_semaphore.locked()` to check, then `async with` inside the generator to actually hold it. This creates a TOCTOU race. Better approach: use `try_acquire`:

```python
# In endpoint (before returning EventSourceResponse):
if _redesign_semaphore.locked():
    return JSONResponse(status_code=429, content={"error": "A redesign is already in progress..."})

# In the generator:
async def redesign_stream(url: str) -> AsyncIterable[ServerSentEvent]:
    acquired = _redesign_semaphore.acquire_nowait()  # Non-blocking
    # Note: acquire_nowait() is not a method on asyncio.Semaphore
```

Actually, `asyncio.Semaphore` does not have `acquire_nowait()`. The standard pattern:

```python
# Check without acquiring (TOCTOU is acceptable here -- worst case, 2 jobs run):
if _redesign_semaphore.locked():
    return JSONResponse(...)

# Inside the generator, actually acquire:
async def redesign_stream(url: str):
    async with _redesign_semaphore:
        # ... yield events ...
```

The TOCTOU window is negligible for a single-user lead-gen tool. If two requests arrive at the exact same instant, both pass the check, but the semaphore ensures only one runs at a time (the other waits). This is acceptable -- the 429 is a fast-rejection optimization, not a hard guarantee.

**Better alternative:** Skip the pre-check entirely. Try to acquire with timeout=0 inside the generator wrapper:

```python
@app.post("/redesign")
async def redesign_endpoint(body: RedesignRequest, request: Request):
    ip = get_client_ip(request)

    # Rate limit check
    if ip not in ("127.0.0.1", "::1"):
        limited, retry_after = is_rate_limited(ip, settings.rate_limit_max, settings.rate_limit_window_seconds)
        if limited:
            return JSONResponse(status_code=429, content={"error": f"Rate limit exceeded. Try again in {retry_after // 60} minutes.", "retry_after": retry_after})

    # Record attempt
    if ip not in ("127.0.0.1", "::1"):
        record_request(ip)

    # Concurrency check -- try non-blocking acquire
    try:
        _redesign_semaphore.release()  # No -- this is wrong
    except:
        pass

    # Simplest correct approach:
    if _redesign_semaphore.locked():
        return JSONResponse(status_code=429, content={"error": "A redesign is already in progress. Please wait and try again."})

    return EventSourceResponse(redesign_stream(body.url, job_id))
```

**Final recommendation:** Use `_redesign_semaphore.locked()` as a pre-check, then `async with _redesign_semaphore` in the generator. The TOCTOU race is a non-issue for this app's traffic level.

### Pattern 4: IP Extraction with Cloudflare Fallback
**What:** Extract real client IP behind Cloudflare tunnel
**When to use:** Rate limiting IP identification

```python
def get_client_ip(request: Request) -> str:
    """Extract client IP, preferring Cloudflare/proxy headers."""
    # Cloudflare-specific header (most reliable behind CF tunnel)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip

    # Standard proxy header
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(",")[0].strip()

    # Direct connection fallback
    if request.client:
        return request.client.host

    return "unknown"
```

**Security note:** These headers can be spoofed if traffic bypasses Cloudflare. For a lead-gen tool this is acceptable -- rate limiting is a soft guard, not a security boundary.

### Anti-Patterns to Avoid
- **Using `response_class=EventSourceResponse` on the decorator when you need conditional 429 responses:** The decorator approach forces the return type. Instead, return `EventSourceResponse(generator)` explicitly.
- **Wrapping `crawler.crawl()` in `asyncio.to_thread()`:** crawl() is already async. Wrapping an async function in to_thread will fail or behave incorrectly.
- **Putting rate limit state in `app.state`:** For this simple case, module-level (or closure-level inside make_app) dicts are simpler and equivalent. App.state adds indirection for no benefit.
- **Using `asyncio.Semaphore` from outside `make_app` then sharing across workers:** This is single-process (uvicorn without workers), so module-level is fine. If multiple workers were used, the semaphore would not be shared.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML sanitization | Regex-based tag stripping | `nh3.clean(html)` | nh3 handles edge cases (nested tags, attribute injection, malformed HTML) |
| SSE formatting | Manual `f"event: {name}\ndata: {json}\n\n"` strings | `ServerSentEvent(data=..., event=...)` | Handles escaping, multi-line data, keep-alive pings |
| CORS headers | Manual `Access-Control-*` headers | `CORSMiddleware` | Handles preflight OPTIONS, Vary headers, credential rules |

**Key insight:** SSE formatting looks trivial but has edge cases (data with newlines must be split into multiple `data:` lines; keep-alive pings prevent proxy timeouts). `ServerSentEvent` handles these correctly.

## Common Pitfalls

### Pitfall 1: Generator Cannot Return Different Response Types
**What goes wrong:** Trying to yield SSE events AND return a JSONResponse 429 from the same function
**Why it happens:** An async generator function always returns an async generator -- it cannot conditionally return a different response
**How to avoid:** Separate the guard checks (rate limit, semaphore) into the outer endpoint function. Only enter the generator after all checks pass.
**Warning signs:** Endpoint returns EventSourceResponse for errors instead of 429 JSON

### Pitfall 2: Playwright Sync API in Async Event Loop
**What goes wrong:** Calling sync Playwright functions from an async context raises "cannot use Sync API inside asyncio loop"
**Why it happens:** Playwright detects the running event loop and refuses sync calls
**How to avoid:** `crawler.crawl()` is already async -- await it directly. `redesigner.redesign()` uses the OpenAI SDK (sync, not Playwright) -- wrapping in `asyncio.to_thread()` is correct. `deployer.deploy()` does filesystem I/O only -- `asyncio.to_thread()` prevents blocking.
**Warning signs:** "It looks like you are using Playwright Sync API inside the asyncio loop" error

### Pitfall 3: Rate Limit Store Memory Leak
**What goes wrong:** Old timestamps accumulate forever for IPs that visited once
**Why it happens:** No cleanup of IPs whose timestamps all expired
**How to avoid:** Prune expired timestamps on every check. Optionally, also prune empty IP keys. For a low-traffic lead-gen app, this is sufficient -- no background cleanup task needed.
**Warning signs:** Monotonically growing dict size over weeks

### Pitfall 4: SSE Connection Held Open After Error
**What goes wrong:** Client sees "error" event but connection stays open
**Why it happens:** Generator yields error event but doesn't return
**How to avoid:** After yielding the error ServerSentEvent, `return` from the generator immediately. EventSourceResponse will close the connection.
**Warning signs:** Browser shows "streaming..." indefinitely after error

### Pitfall 5: CORS Blocks POST with JSON Body
**What goes wrong:** Browser sends OPTIONS preflight for POST with Content-Type: application/json; server returns 405
**Why it happens:** CORSMiddleware not configured with `allow_methods=["POST"]` or `allow_headers=["Content-Type"]`
**How to avoid:** Configure `allow_methods=["POST", "GET"]` and `allow_headers=["Content-Type"]` (or `["*"]`)
**Warning signs:** "CORS policy: No 'Access-Control-Allow-Origin' header" in browser console

### Pitfall 6: Pydantic Settings comma-separated list parsing
**What goes wrong:** `cors_origins: list[str]` from env var `CORS_ORIGINS="http://localhost:3000,http://localhost:8080"` doesn't parse
**Why it happens:** Pydantic Settings v2 requires explicit JSON for list env vars by default, or a custom validator
**How to avoid:** Use `@field_validator('cors_origins', mode='before')` to split on comma, or set `env_parse_enums_as_values=True`. Simplest: use JSON format in env var: `CORS_ORIGINS='["http://localhost:3000"]'`, or add a before-validator.
**Warning signs:** Validation error on startup about list type

## Code Examples

### Complete nh3 Sanitization
```python
# Source: https://nh3.readthedocs.io/
import nh3

# Default clean() strips <script>, <style>, event handlers, etc.
# Keeps safe HTML: <p>, <h1>-<h6>, <a>, <img>, <ul>, <ol>, <li>, <table>, etc.
sanitized_html = nh3.clean(raw_html)

# The default allowed tags and attributes are sensible for this use case.
# LLM-generated HTML typically contains: headings, paragraphs, divs, spans,
# links, images, lists, tables, and inline styles.
# nh3 defaults strip: <script>, <iframe>, <object>, <embed>, <form>, <input>,
# event handler attributes (onclick, onerror, etc.)

# For this project: call nh3.clean(html) with defaults.
# No custom tag/attribute configuration needed.
```

### CORSMiddleware Configuration
```python
# Source: https://fastapi.tiangolo.com/tutorial/cors/
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["http://localhost:3000"]
    allow_credentials=False,  # No cookies/auth needed
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

### Config Settings Extension
```python
# In config.py
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Existing
    claude_code_api_url: str = "http://localhost:8000/v1"
    sites_dir: Path = Path("./sites")
    server_port: int = 8080
    claude_model: str = "claude-sonnet-4-5-20250929"

    # New for Phase 1
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_max: int = 3
    rate_limit_window_seconds: int = 3600

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Support comma-separated env var: CORS_ORIGINS="http://localhost:3000,http://example.com"
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
```

### Request Body Model
```python
from pydantic import BaseModel, HttpUrl

class RedesignRequest(BaseModel):
    url: str  # Validated as URL in redesigner/crawler, not here (keep it simple)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sse-starlette third-party package | fastapi.sse built-in EventSourceResponse | FastAPI 0.135.0 (2025) | No external SSE dependency needed |
| bleach for HTML sanitization | nh3 (Rust-backed) | bleach deprecated 2023 | 20x faster, actively maintained |
| Manual SSE string formatting | ServerSentEvent dataclass | FastAPI 0.135.0 | Type-safe, handles edge cases |

**Deprecated/outdated:**
- `sse-starlette` package: still works but unnecessary with FastAPI 0.135+
- `bleach`: officially deprecated, replaced by nh3

## Open Questions

1. **EventSourceResponse vs StreamingResponse**
   - What we know: CONTEXT.md says "StreamingResponse with media_type=text/event-stream". FastAPI 0.135+ provides EventSourceResponse which is purpose-built for SSE.
   - What's unclear: Whether user has a strong preference for StreamingResponse specifically, or was referencing it as the general approach
   - Recommendation: Use EventSourceResponse. It produces identical wire format, adds keep-alive pings, and is the documented FastAPI 0.135+ way. If strict CONTEXT adherence is required, StreamingResponse with manual formatting works but is more code.

2. **nh3 default tags vs LLM HTML needs**
   - What we know: nh3 defaults strip `<script>`, `<style>`, `<iframe>`, `<form>`, `<input>`. LLM HTML uses `<style>` tags extensively for CSS.
   - What's unclear: Whether nh3 default allowed tags include `<style>` -- it likely does NOT, which would strip ALL CSS from the redesigned page.
   - Recommendation: Test `nh3.clean()` on a sample LLM output. If `<style>` is stripped, configure: `nh3.clean(html, tags=nh3.ALLOWED_TAGS | {"style", "div", "span", "section", "header", "nav", "main", "footer", "figure", "figcaption"}, attributes={"*": {"class", "id", "style"}})`. This is a CRITICAL detail to verify during implementation.

3. **Localhost rate limit exemption for IPv4-mapped IPv6**
   - What we know: CONTEXT says exempt 127.0.0.1 and ::1
   - What's unclear: Some systems report localhost as `::ffff:127.0.0.1` (IPv4-mapped IPv6)
   - Recommendation: Also exempt `::ffff:127.0.0.1` in the localhost check

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.24+ |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | POST /redesign returns SSE stream | integration | `uv run pytest tests/test_server.py::test_redesign_sse_stream -x` | Wave 0 |
| API-02 | Named step events emitted in order | integration | `uv run pytest tests/test_server.py::test_sse_event_names -x` | Wave 0 |
| API-03 | Sync functions don't block event loop | unit | `uv run pytest tests/test_server.py::test_to_thread_wrapping -x` | Wave 0 |
| API-04 | Concurrent request rejected with 429 | integration | `uv run pytest tests/test_server.py::test_concurrency_cap -x` | Wave 0 |
| API-05 | 4th request in 1 hour returns 429 | unit | `uv run pytest tests/test_server.py::test_rate_limit -x` | Wave 0 |
| API-06 | Script tags stripped from HTML | unit | `uv run pytest tests/test_server.py::test_nh3_sanitization -x` | Wave 0 |
| API-07 | CORS allows localhost:3000, blocks others | integration | `uv run pytest tests/test_server.py::test_cors_configuration -x` | Wave 0 |
| API-08 | fastapi >=0.135.0 in pyproject.toml | smoke | `uv run python -c "from fastapi.sse import EventSourceResponse"` | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_server.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_server.py` -- all phase 1 endpoint tests (rate limit, concurrency, SSE stream, CORS, sanitization)
- [ ] `tests/conftest.py` -- shared fixtures (FastAPI TestClient, mock crawl/redesign/deploy functions)
- [ ] Framework already configured in pyproject.toml; pytest and pytest-asyncio in dev dependencies

## Sources

### Primary (HIGH confidence)
- FastAPI official SSE tutorial: https://fastapi.tiangolo.com/tutorial/server-sent-events/ -- EventSourceResponse, ServerSentEvent API
- FastAPI CORS tutorial: https://fastapi.tiangolo.com/tutorial/cors/ -- CORSMiddleware configuration
- nh3 documentation: https://nh3.readthedocs.io/ -- clean() API, parameters, defaults
- Local verification: `from fastapi.sse import EventSourceResponse, ServerSentEvent` confirmed working on installed 0.135.1

### Secondary (MEDIUM confidence)
- Cloudflare HTTP headers docs: https://developers.cloudflare.com/fundamentals/reference/http-headers/ -- CF-Connecting-IP header
- nh3 PyPI: https://pypi.org/project/nh3/ -- version 0.3.3 latest

### Tertiary (LOW confidence)
- nh3 default ALLOWED_TAGS may not include `<style>`, `<div>`, `<section>`, etc. -- needs runtime verification during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries verified installed or on PyPI, APIs confirmed
- Architecture: HIGH - SSE pattern verified against official FastAPI docs, function signatures confirmed from source code
- Pitfalls: HIGH - identified from direct code analysis (crawl is async, generator return type limitation) and official docs
- nh3 tag defaults: LOW - need to verify whether `<style>` is in default ALLOWED_TAGS at runtime

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable libraries, unlikely to change)
