# Architecture Research

**Domain:** Next.js frontend + Python FastAPI backend with long-running AI jobs
**Researched:** 2026-03-21
**Confidence:** HIGH

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Cloudflare Tunnel (Public)                       │
│  app.sastaspace.com  ─→  ingress rule  ─→  localhost:3000 (Next.js) │
│  api.sastaspace.com  ─→  ingress rule  ─→  localhost:8080 (FastAPI) │
└──────────────────────────────────────────────────────────────────────┘
        │                                         │
        ▼                                         ▼
┌───────────────────┐                   ┌────────────────────────┐
│   Next.js (3000)  │   HTTP / SSE      │   FastAPI (8080)       │
│                   │ ──────────────→   │                        │
│  Landing page     │                   │  POST /api/redesign    │
│  Progress UI      │  ◄──── SSE ────  │    → crawl()           │
│  Result display   │                   │    → redesign()        │
│  Contact form     │                   │    → deploy()          │
│                   │                   │  GET /api/redesign/    │
│  Route Handlers:  │                   │    {id}/stream         │
│  /api/redesign    │                   │  GET /{subdomain}/     │
│  (proxy to FastAPI│                   │  POST /api/contact     │
│   + forward SSE)  │                   │                        │
└───────────────────┘                   └────────────────────────┘
                                                 │
                                                 ▼
                                        ┌────────────────┐
                                        │ claude-code-api│
                                        │ gateway (:8000)│
                                        └────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Next.js App (port 3000) | UI rendering, SEO landing page, progress display, contact form | App Router with RSC for landing, client components for interactive parts |
| Next.js Route Handlers | Proxy API calls to FastAPI, forward SSE streams, hide backend URL from browser | `/app/api/redesign/route.ts` forwards to FastAPI |
| FastAPI (port 8080) | Orchestrate redesign pipeline, stream progress via SSE, serve completed redesigns | Existing server extended with `/api/redesign` and SSE endpoints |
| Cloudflare Tunnel | Expose both services on public subdomains, handle TLS | Single `cloudflared` with ingress rules for two hostnames |
| claude-code-api (port 8000) | AI gateway -- translates OpenAI SDK calls to Claude Code | Existing, no changes needed |

## Recommended Project Structure

```
sastaspace/                          # project root (existing)
├── sastaspace/                      # Python package (existing)
│   ├── cli.py                       # CLI commands (existing)
│   ├── config.py                    # Settings (existing)
│   ├── crawler.py                   # Playwright crawler (existing)
│   ├── redesigner.py                # AI redesign (existing)
│   ├── deployer.py                  # File deploy (existing)
│   ├── server.py                    # FastAPI app (extend)
│   └── api/                         # NEW: API route handlers
│       ├── __init__.py
│       ├── redesign.py              # POST /api/redesign + SSE stream
│       └── contact.py               # POST /api/contact
├── web/                             # NEW: Next.js frontend
│   ├── app/
│   │   ├── layout.tsx               # Root layout with fonts, metadata
│   │   ├── page.tsx                 # Landing page (RSC)
│   │   ├── redesign/
│   │   │   └── [id]/
│   │   │       └── page.tsx         # Result page
│   │   └── api/
│   │       └── redesign/
│   │           └── route.ts         # Proxy to FastAPI SSE
│   ├── components/
│   │   ├── url-input.tsx            # URL submission form
│   │   ├── progress-display.tsx     # SSE-powered progress UI
│   │   ├── redesign-preview.tsx     # iframe result display
│   │   └── contact-form.tsx         # Lead capture form
│   ├── lib/
│   │   └── api.ts                   # FastAPI client helpers
│   ├── next.config.ts
│   ├── package.json
│   └── tailwind.config.ts
├── tests/                           # Python tests (existing)
├── sites/                           # Runtime output (existing)
├── pyproject.toml                   # Python deps (existing)
├── Makefile                         # Extended with `dev` target
└── cloudflared-config.yml           # Tunnel ingress rules
```

### Structure Rationale

- **`web/` at root (not `frontend/`):** Concise, standard. Sits alongside the Python package as a peer, not nested inside it.
- **`sastaspace/api/` sub-package:** Separates API endpoint logic from the existing server.py which handles static file serving. Keeps server.py focused on what it already does.
- **Next.js App Router:** Use App Router (not Pages Router) -- it handles SSE in Route Handlers natively, supports React Server Components for the SEO-critical landing page, and is the current standard.
- **No monorepo tooling (no Turborepo/Nx):** Overkill for one JS app + one Python package. A simple Makefile with `make dev` that runs both processes is sufficient.

## Architectural Patterns

### Pattern 1: SSE for Long-Running Job Progress

**What:** FastAPI streams progress events to the client via Server-Sent Events. The redesign endpoint kicks off the crawl/redesign/deploy pipeline and yields status updates as each stage completes.

**When to use:** Jobs that take 30-60 seconds where the user needs to know something is happening. SSE is unidirectional (server to client), which is exactly this use case.

**Why SSE over WebSockets:** WebSockets are bidirectional -- unnecessary here since the client only listens. SSE auto-reconnects, works over HTTP/1.1, and passes through Cloudflare tunnels without special configuration. FastAPI has built-in SSE support since v0.135.0 (bump the current `>=0.115.0` pin).

**Why SSE over polling:** Polling at 1s intervals for a 60s job = 60 requests. SSE = 1 persistent connection. Less load, lower latency for updates, simpler client code.

**Trade-offs:** SSE is limited to ~6 concurrent connections per browser per domain (HTTP/1.1 limit). Not a problem here -- users run one redesign at a time.

**FastAPI side:**
```python
from fastapi.sse import EventSourceResponse, ServerSentEvent

@router.post("/api/redesign", response_class=EventSourceResponse)
async def start_redesign(request: RedesignRequest):
    async def event_stream():
        yield ServerSentEvent(data={"stage": "crawling", "message": "Crawling website..."}, event="progress")
        crawl_result = await crawl(request.url)

        yield ServerSentEvent(data={"stage": "redesigning", "message": "AI is redesigning..."}, event="progress")
        html = redesign(crawl_result, api_url, model)

        yield ServerSentEvent(data={"stage": "deploying", "message": "Deploying preview..."}, event="progress")
        deploy_result = deploy(request.url, html, sites_dir)

        yield ServerSentEvent(data={"stage": "complete", "url": f"/{deploy_result.subdomain}/"}, event="complete")

    return EventSourceResponse(event_stream())
```

**Next.js client side:**
```typescript
const eventSource = new EventSource('/api/redesign?url=' + encodeURIComponent(url));
eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  setProgress(data);
});
eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  router.push(`/redesign/${data.subdomain}`);
  eventSource.close();
});
```

### Pattern 2: Next.js Route Handler as SSE Proxy

**What:** The browser connects to `Next.js /api/redesign`, which opens a connection to `FastAPI /api/redesign` and forwards the SSE stream byte-for-byte. The browser never knows about FastAPI.

**When to use:** When you want to keep the backend URL hidden from the browser, avoid CORS entirely, or add frontend-side logic (rate limiting, validation) before forwarding.

**Trade-offs:** Adds one hop of latency (negligible on localhost). Slightly more code. But eliminates all CORS issues because the browser only talks to one origin.

**Example:**
```typescript
// web/app/api/redesign/route.ts
export async function POST(request: Request) {
  const body = await request.json();
  const upstream = await fetch('http://localhost:8080/api/redesign', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  // Forward the SSE stream directly
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Pattern 3: Direct FastAPI Calls with CORS (Alternative)

**What:** Skip the Next.js proxy. The browser calls FastAPI directly. Configure CORS on FastAPI to allow the Next.js origin.

**When to use:** Simpler setup if you are comfortable exposing the FastAPI URL. Fine for a local-first tool.

**Trade-offs:** Requires CORS middleware on FastAPI. Both origins must be exposed through the tunnel. Slightly leakier abstraction (backend URL visible in browser network tab). But fewer moving parts.

**CORS configuration (if using this pattern):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.sastaspace.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Recommendation:** Start with the proxy pattern (Pattern 2). It is marginally more work but eliminates CORS entirely. If it becomes cumbersome, switching to direct calls + CORS is straightforward.

## Data Flow

### Primary Flow: User Submits URL for Redesign

```
User enters URL on landing page
    │
    ▼
[Next.js Client Component] ── POST {url} ──→ [Next.js Route Handler /api/redesign]
                                                        │
                                                        ▼ (proxy)
                                              [FastAPI POST /api/redesign]
                                                        │
                                              ┌─────────┴─────────┐
                                              │  SSE Event Stream  │
                                              ├────────────────────┤
                                              │ event: progress    │
                                              │ data: {crawling}   │
                                              │                    │
                                              │ ── crawl(url) ──   │
                                              │                    │
                                              │ event: progress    │
                                              │ data: {redesigning}│
                                              │                    │
                                              │ ── redesign() ──   │
                                              │                    │
                                              │ event: progress    │
                                              │ data: {deploying}  │
                                              │                    │
                                              │ ── deploy() ──     │
                                              │                    │
                                              │ event: complete    │
                                              │ data: {subdomain}  │
                                              └────────────────────┘
                                                        │
                                              (stream forwarded back
                                               through Next.js proxy)
                                                        │
                                                        ▼
[Next.js Client Component] receives SSE events, updates progress UI
    │
    ▼ (on "complete" event)
Router navigates to /redesign/[subdomain]
    │
    ▼
[Next.js Result Page] renders iframe pointing at FastAPI /{subdomain}/
```

### Secondary Flow: View Completed Redesign

```
User visits /redesign/[subdomain]
    │
    ▼
[Next.js RSC page] ── fetches metadata from FastAPI /api/sites/{subdomain}
    │
    ▼
Renders page with iframe src="https://api.sastaspace.com/{subdomain}/"
    (iframe loads the full redesign HTML directly from FastAPI)
```

### State Management

No global state store needed. The application is a linear flow with three states:

```
[idle] ──submit──→ [in-progress] ──complete──→ [result]
                        │
                   SSE events update
                   local component state
                   (useState + useEffect)
```

React `useState` in the progress component is sufficient. No Redux, Zustand, or context providers required for this flow.

### Key Data Flows

1. **Redesign submission:** Browser POST -> Next.js proxy -> FastAPI -> SSE stream back through proxy -> browser
2. **Result viewing:** Browser navigates to result page -> RSC fetches metadata from FastAPI -> iframe loads redesign HTML from FastAPI
3. **Contact form:** Browser POST -> Next.js Route Handler -> email service (SendGrid/SMTP) or local JSON file

## Deployment Architecture: Cloudflare Tunnel

### Single Tunnel, Two Hostnames

Use one `cloudflared` process with ingress rules mapping two hostnames to two local ports:

```yaml
# cloudflared-config.yml
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: app.sastaspace.com
    service: http://localhost:3000
  - hostname: api.sastaspace.com
    service: http://localhost:8080
  - service: http_status:404
```

**If using the proxy pattern (recommended):** Only `app.sastaspace.com` needs to be exposed. The Next.js Route Handler calls FastAPI on `localhost:8080` internally. This means only one public hostname, simpler tunnel config, and the FastAPI port is never exposed to the internet.

```yaml
# Simpler config with proxy pattern
ingress:
  - hostname: sastaspace.com
    service: http://localhost:3000
  - service: http_status:404
```

**CORS implications:** With the proxy pattern, CORS is a non-issue -- the browser only talks to one origin. With direct calls, you need CORS middleware on FastAPI and both hostnames exposed.

### Cloudflare Tunnel + SSE

Cloudflare tunnels support SSE without special configuration. The tunnel maintains the long-lived HTTP connection. However, Cloudflare has a default 100-second timeout for idle connections. Since the redesign pipeline takes 30-60 seconds and sends progress events throughout, this is not a concern -- the connection is never idle.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 concurrent users | Current architecture is fine. One redesign at a time runs serially. Multiple users queue behind each other. |
| 10-50 concurrent users | Add a task queue (Redis + Celery or `asyncio.Queue`). FastAPI accepts the job, returns a job ID immediately, client polls or SSE-subscribes for progress. |
| 50+ concurrent users | Not relevant for this product -- it is a lead gen tool on a single local machine, not a SaaS platform. |

### Scaling Priorities

1. **First bottleneck:** The `redesign()` call is synchronous and blocks the FastAPI event loop. Wrap it in `asyncio.to_thread()` so it runs in a thread pool and does not block other requests.
2. **Second bottleneck:** Playwright browser instances. Each `crawl()` launches a browser. More than a few concurrent crawls will exhaust memory. Not a concern for the intended scale, but if it becomes one, add a semaphore limiting concurrent crawls.

## Anti-Patterns

### Anti-Pattern 1: Polling for Progress

**What people do:** POST to start the job, return a job ID, then poll `GET /status/{id}` every second.
**Why it is wrong:** 60 requests per job instead of 1 SSE connection. Adds latency between actual progress and the client learning about it. More complex client code with retry logic and interval management.
**Do this instead:** Use SSE. The connection stays open, the server pushes events as they happen, and the client gets instant updates.

### Anti-Pattern 2: WebSocket for Unidirectional Data

**What people do:** Set up a WebSocket connection for server-to-client progress updates.
**Why it is wrong:** WebSockets require a protocol upgrade, more complex error handling, manual reconnection logic, and a separate connection lifecycle. Overkill when data only flows one direction.
**Do this instead:** Use SSE. It is built on standard HTTP, auto-reconnects, and is purpose-built for server-to-client streaming.

### Anti-Pattern 3: Running the Redesign Synchronously in the Request Handler

**What people do:** Call `crawl()` and `redesign()` directly in the FastAPI endpoint without async handling, blocking the entire server.
**Why it is wrong:** FastAPI uses a single event loop. A synchronous 60-second call blocks all other requests.
**Do this instead:** Use `async` for `crawl()` (already async) and wrap `redesign()` in `asyncio.to_thread()` since it makes a synchronous HTTP call to the AI gateway.

### Anti-Pattern 4: Putting Business Logic in Next.js Route Handlers

**What people do:** Put crawl/redesign orchestration logic in Next.js API routes to avoid having two servers.
**Why it is wrong:** The pipeline is Python (Playwright, OpenAI SDK). Moving it to Node.js means rewriting everything. The Next.js Route Handler should be a thin proxy, nothing more.
**Do this instead:** Keep all business logic in FastAPI. Next.js Route Handlers only proxy HTTP requests and forward SSE streams.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| claude-code-api (localhost:8000) | OpenAI SDK HTTP calls from `redesigner.py` | Existing, no changes needed |
| Email service (contact form) | SendGrid API or SMTP from Next.js Route Handler | Simple POST; or write to local JSON for MVP |
| Cloudflare Tunnel | `cloudflared` process with config YAML | One tunnel, one or two hostnames depending on proxy vs direct pattern |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Browser <-> Next.js | HTTP (pages + API routes) | Same origin, no CORS |
| Next.js Route Handler <-> FastAPI | HTTP on localhost:8080 | Internal only, not exposed to internet if using proxy pattern |
| FastAPI <-> claude-code-api | HTTP on localhost:8000 via OpenAI SDK | Existing pattern, no changes |
| FastAPI <-> Filesystem (sites/) | Direct file I/O | Existing deployer writes HTML; server reads and serves it |

## Build Order (Dependencies)

This ordering reflects what must exist before the next piece can work:

1. **FastAPI API endpoints** -- Add `/api/redesign` with SSE streaming to the existing server. This is the foundation everything else depends on. Can be tested with `curl` before any frontend exists.

2. **Next.js project scaffold** -- Create the `web/` directory with App Router, Tailwind, basic layout. No API integration yet -- just static pages.

3. **Next.js Route Handler (SSE proxy)** -- Wire up `/api/redesign` in Next.js to proxy to FastAPI. Test that SSE events flow through.

4. **Progress UI component** -- Client component that consumes the SSE stream and displays progress states. Depends on steps 1 and 3.

5. **Result page** -- Display the completed redesign in an iframe. Depends on step 1 (needs the subdomain URL from the complete event).

6. **Landing page design** -- The "hero" landing page with URL input. Can be built in parallel with steps 3-5 as a static RSC, then wired to the progress flow.

7. **Contact form** -- Independent of the redesign flow. Can be built last.

8. **Cloudflare tunnel config** -- Final step: expose the working system publicly.

**Critical path:** Steps 1 -> 3 -> 4 -> 5 are sequential dependencies. Steps 2, 6, 7 can be parallelized.

## Version Requirement Note

The existing `pyproject.toml` pins `fastapi>=0.115.0`. Built-in SSE support (`fastapi.sse.EventSourceResponse`) was added in FastAPI 0.135.0. The version pin must be bumped to `fastapi>=0.135.0` to use native SSE without the third-party `sse-starlette` package.

## Sources

- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- Built-in SSE since v0.135.0, HIGH confidence
- [sse-starlette on PyPI](https://pypi.org/project/sse-starlette/) -- Third-party alternative if older FastAPI needed, HIGH confidence
- [Next.js Route Handlers](https://nextjs.org/docs/app/building-your-application/routing/route-handlers) -- SSE proxy pattern, HIGH confidence
- [Cloudflare Tunnel Configuration](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/configuration-file/) -- Ingress rules for multiple services, HIGH confidence
- [Cloudflare Many Services One Cloudflared](https://blog.cloudflare.com/many-services-one-cloudflared/) -- Single tunnel multi-service pattern, HIGH confidence
- [Next.js SSE Discussion](https://github.com/vercel/next.js/discussions/48427) -- SSE support in Route Handlers, MEDIUM confidence

---
*Architecture research for: SastaSpace web frontend*
*Researched: 2026-03-21*
