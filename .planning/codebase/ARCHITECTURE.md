# Architecture

**Analysis Date:** 2026-03-21

## Pattern Overview

**Overall:** Decoupled multi-service pipeline — Python FastAPI backend, Next.js frontend, and a claude-code-api AI gateway, communicating via SSE streaming over HTTP.

**Key Characteristics:**
- Three distinct services: FastAPI backend, Next.js frontend, claude-code-api gateway
- Core product loop is a 3-step async pipeline: Crawl → Redesign (AI) → Deploy
- Frontend communicates with backend exclusively via a single SSE endpoint (`POST /redesign`)
- Backend stores redesigned sites as static HTML files on a persistent volume and serves them directly — no database
- Site registry is a flat JSON file (`_registry.json`) on disk
- The AI inference call goes through `claude-code-api`, an OpenAI-compatible proxy wrapping Claude Code CLI
- A parallel CLI entrypoint (`sastaspace`) runs the same pipeline synchronously for local/dev use

## Layers

**CLI Layer:**
- Purpose: Developer/local-use entry point for the full redesign pipeline
- Location: `sastaspace/cli.py`
- Contains: Click commands (`redesign`, `list`, `open`, `remove`, `serve`)
- Depends on: `crawler`, `redesigner`, `deployer`, `server` modules, `config`
- Used by: Developers directly via `sastaspace` CLI command (installed via `pyproject.toml`)

**HTTP API Layer (FastAPI):**
- Purpose: Exposes the redesign pipeline as an HTTP service for the frontend
- Location: `sastaspace/server.py`
- Contains: `POST /redesign` (SSE stream), `GET /` (registry admin dashboard), `GET /{subdomain}/` and `GET /{subdomain}/{path}` (static site serving)
- Depends on: `crawler`, `redesigner`, `deployer`, `config`
- Used by: Next.js frontend via `NEXT_PUBLIC_BACKEND_URL`

**Pipeline Layer:**
- Purpose: The three discrete steps of the AI redesign pipeline
- Location: `sastaspace/crawler.py`, `sastaspace/redesigner.py`, `sastaspace/deployer.py`
- Contains: `crawl()` (async), `redesign()` (sync, uses `asyncio.to_thread` in server), `deploy()` (sync)
- Depends on: Playwright (crawl), OpenAI Python client → claude-code-api (redesign), stdlib only (deploy)
- Used by: Both `server.py` and `cli.py`

**Configuration Layer:**
- Purpose: Centralised settings via pydantic-settings, reads from `.env` and environment
- Location: `sastaspace/config.py`
- Contains: `Settings` class with fields: `claude_code_api_url`, `sites_dir`, `server_port`, `claude_model`, `cors_origins`, `rate_limit_max`, `rate_limit_window_seconds`
- `SASTASPACE_SITES_DIR` env var takes precedence over `.env` for `sites_dir` (used by Docker)

**Frontend Layer (Next.js App Router):**
- Purpose: Public web UI for submitting URLs and viewing AI redesign results
- Location: `web/src/`
- Contains: App Router pages, React components, SSE client library, hooks
- Depends on: `NEXT_PUBLIC_BACKEND_URL` env var to reach the FastAPI backend

**AI Gateway Layer (claude-code-api):**
- Purpose: OpenAI-compatible API wrapper over Claude Code CLI
- Location: `claude-code-api/` (separate git repo, also containerised in k8s)
- Exposes: `POST /v1/chat/completions`, `GET /health` at port 8000
- Used by: `sastaspace/redesigner.py` via `openai.OpenAI(base_url=api_url)` client

## Data Flow

**Redesign Request (frontend-initiated):**

1. User submits URL in `web/src/components/landing/hero-section.tsx`
2. `useRedesign` hook (`web/src/hooks/use-redesign.ts`) calls `streamRedesign()` from `web/src/lib/sse-client.ts`
3. `POST /redesign` hits FastAPI backend — backend checks rate limit and semaphore, returns SSE stream
4. Backend acquires `_redesign_semaphore` (global concurrency = 1) via `asyncio.Semaphore`
5. **Step 1 — Crawl:** `crawl(url)` launches headless Chromium via Playwright, returns `CrawlResult` dataclass (title, HTML, screenshot PNG as base64, colors, fonts, headings, nav links, sections)
6. SSE event `crawling` emitted with `progress: 10`
7. **Step 2 — Redesign:** `redesign(crawl_result, api_url, model)` called in thread (`asyncio.to_thread`). Builds structured prompt from `CrawlResult.to_prompt_context()`, sends to claude-code-api with screenshot as vision input via OpenAI SDK. Claude returns a complete single-file HTML document.
8. SSE event `redesigning` emitted with `progress: 40`
9. HTML sanitised with `nh3.clean()`
10. **Step 3 — Deploy:** `deploy(url, html, sites_dir)` called in thread. Derives slug from URL hostname, writes `sites/{slug}/index.html` and `metadata.json`, atomically updates `sites/_registry.json`
11. SSE event `deploying` emitted with `progress: 80`
12. SSE event `done` emitted with `progress: 100`, `subdomain`, `url`
13. Frontend `useRedesign` receives `done` event — `useEffect` in `app-flow.tsx` calls `router.push(/${subdomain})`
14. Next.js `[subdomain]/page.tsx` renders `ResultView` which iframes `{NEXT_PUBLIC_BACKEND_URL}/{subdomain}/` — served by FastAPI directly from disk

**Redesign Request (CLI-initiated):**

1. `sastaspace redesign <url>` runs the same `crawl → redesign → deploy` sequence synchronously with Rich progress spinner
2. `ensure_running()` spawns a detached uvicorn subprocess if preview server is not already listening on the port
3. Browser opens `http://localhost:{port}/{subdomain}/`

**State Management (frontend):**
- All UI state lives in `useRedesign` hook as a discriminated union: `idle | connecting | progress | done | error`
- SSE events (`crawling`, `redesigning`, `deploying`, `done`, `error`) drive all state transitions
- On `done`, `useEffect` in `web/src/components/app-flow.tsx` calls `router.push(/${subdomain})` — no global state store needed

## Key Abstractions

**CrawlResult:**
- Purpose: Structured representation of a crawled webpage; the data contract between crawler and redesigner
- Location: `sastaspace/crawler.py`
- Pattern: Python `@dataclass` with `error: str = ""` sentinel field; `to_prompt_context()` serialises to LLM-ready markdown

**RedesignState (frontend):**
- Purpose: Discriminated union driving all UI transitions from idle to result
- Location: `web/src/hooks/use-redesign.ts`
- Pattern: TypeScript discriminated union: `{ status: "idle" } | { status: "connecting" } | { status: "progress"; currentStep, domain, steps } | { status: "done"; subdomain, originalUrl, domain } | { status: "error"; message, url }`

**Settings:**
- Purpose: Runtime configuration via environment variables
- Location: `sastaspace/config.py`
- Pattern: `pydantic_settings.BaseSettings` — all env vars read at startup with sensible defaults

**make_app(sites_dir):**
- Purpose: Factory function creating the FastAPI application bound to a specific sites directory
- Location: `sastaspace/server.py`
- Pattern: Allows tests and Docker to inject a custom `sites_dir`; module-level `app` is the uvicorn default instance

## Entry Points

**Backend HTTP server:**
- Location: `sastaspace/server.py` — module-level `app = make_app(_settings.sites_dir)`
- Triggers: `uvicorn sastaspace.server:app` (Docker CMD, CLI `serve` command, `ensure_running()` subprocess)
- Responsibilities: Rate limiting (in-process dict), concurrency control (semaphore), SSE streaming, static site serving

**Next.js application:**
- Location: `web/src/app/layout.tsx`, `web/src/app/page.tsx`
- Triggers: `node server.js` (Docker standalone) or `npm run dev`
- Responsibilities: Landing page, real-time progress tracking via SSE, result display with iframe preview, contact form

**Contact API route:**
- Location: `web/src/app/api/contact/route.ts`
- Triggers: `POST /api/contact` from frontend contact form on result pages
- Responsibilities: Honeypot check, Cloudflare Turnstile verification, email dispatch via Resend SDK

**CLI:**
- Location: `sastaspace/cli.py` — entrypoint `sastaspace.cli:main`
- Triggers: `sastaspace <command>` installed via `[project.scripts]` in `pyproject.toml`

## Error Handling

**Strategy:** Errors are caught at pipeline boundaries and surfaced as SSE `error` events or `SystemExit(1)` in CLI. Individual pipeline steps raise exceptions; callers handle them.

**Patterns:**
- `crawl()` sets `CrawlResult.error` on any exception — caller checks before proceeding (error-as-value)
- `redesigner.py` raises `RedesignError` on invalid Claude output (missing DOCTYPE, missing `</html>`, empty response)
- `server.py` wraps the entire `redesign_stream()` generator in a broad `except Exception` that emits a generic SSE `error` event
- `cli.py` catches `RedesignError` and generic exceptions separately with distinct Rich error panels
- Frontend `useRedesign`: `try/catch` around `for await` loop; aborted `AbortController` signals silently terminate the loop
- `deploy()` uses atomic write-then-rename (`os.replace`) to prevent corrupt registry files on crash

## Cross-Cutting Concerns

**Logging:** No structured logging framework. Uvicorn access logs write to `sites/.server.log` when spawned as subprocess. `console.error` used in Next.js API route.

**Validation:**
- `nh3.clean()` sanitises AI-generated HTML before writing to disk
- `_validate_html()` checks for DOCTYPE and `</html>` before accepting Claude's response
- Frontend contact route: honeypot field check, field presence check, Cloudflare Turnstile token verification

**Rate limiting:** In-process dict (`_rate_limit_store`) keyed by client IP (`cf-connecting-ip` header preferred). Default: 3 requests per 3600-second window per IP. Localhost is exempt. Does not survive restarts.

**Concurrency:** `asyncio.Semaphore(1)` limits simultaneous redesign jobs to 1. Frontend receives HTTP 429 if semaphore is already locked (checked before acquiring, not after).

**Authentication:** Backend has no authentication. Security relies on rate limiting, single-concurrency semaphore, and Cloudflare Turnstile for the contact form.

## Deployment Architecture

**Production topology:**

```
Internet
    |
    v
Cloudflare Edge  (DDoS protection, TLS termination, CDN cache)
    |
    v  QUIC/HTTP2 — zero open inbound ports on server
cloudflared (systemd service)  — Cloudflare Zero Trust tunnel
    |
    v  HTTP to localhost:80
microk8s nginx Ingress controller  (namespace: sastaspace)
    |
    |-- sastaspace.com / www.sastaspace.com ----> frontend Service :3000
    |                                             (Next.js pod, k8s/frontend.yaml)
    |
    `-- api.sastaspace.com --------------------> backend Service :8080
                                                  (FastAPI pod, k8s/backend.yaml)
                                                      |
                                                      v
                                              claude-code-api Service :8000
                                              (pod, k8s/claude-code-api.yaml)
```

**Kubernetes (microk8s, `sastaspace` namespace):**
- All manifests in `k8s/` — 5 files: `namespace.yaml`, `backend.yaml`, `frontend.yaml`, `claude-code-api.yaml`, `ingress.yaml`
- All deployments: 1 replica; resource limits 1Gi memory / 500m CPU; requests 256Mi / 100m
- Backend uses a `PersistentVolumeClaim` (`sites-pvc`, 10Gi, `ReadWriteOnce`) mounted at `/data/sites` — this is where all redesigned HTML files live
- All images pulled from local microk8s registry at `localhost:32000` (no Docker Hub)
- Ingress: nginx with `proxy-body-size: 50m` and `proxy-read-timeout: 300` (required for long SSE streams)
- `claude-code-api` pod mounts host path `/home/mkhare/.claude` read-only for Claude credentials

**Docker (local dev / docker-compose):**
- `docker-compose.yml`: three services — `backend`, `frontend`, `tests` (test profile only)
- Backend: volume `sites_data` named volume at `/data/sites`; `CLAUDE_CODE_API_URL=http://host.docker.internal:8000/v1` (routes to host-side claude-code-api)
- Frontend: `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080`; waits for backend healthcheck (`service_healthy`)
- `backend/Dockerfile`: Python 3.11-slim with Playwright/Chromium system deps; Playwright installs Chromium at build time
- `web/Dockerfile`: Multi-stage Node 22 Alpine; Stage 1 builds Next.js in standalone mode; Stage 2 copies `.next/standalone`, `static`, `public` — minimal production image

**CI/CD (GitHub Actions):**
- Workflow: `.github/workflows/deploy.yml`
- Trigger: push to `main` branch, or manual `workflow_dispatch`
- Runner: `self-hosted, linux, amd64` — the production machine runs its own CI jobs
- Pipeline steps: checkout → build 3 Docker images (backend, frontend, claude-code-api) → push to `localhost:32000` with both `:latest` and `:{git-sha}` tags → `kubectl apply -f k8s/` → rolling restart all 3 deployments → wait for rollout status (300s timeout each) → verify with pod/service/ingress listing

**Manual deploy via Makefile:**
- `make deploy`: rsync source to remote, build images on remote, apply k8s manifests, rolling restart
- `make deploy-status`: `kubectl get pods,svc,ingress -n sastaspace`
- `make deploy-logs`: tail combined logs from frontend + backend pods
- `make deploy-down`: delete entire `sastaspace` namespace

**Host-level services on production machine (non-k8s, systemd):**
- `cloudflared` — Cloudflare tunnel routing public traffic to microk8s nginx port 80; survives reboot
- `claude-code-api` — OpenAI-compatible Claude proxy on `localhost:8000` (also has a k8s containerised variant)
- `docker` — container runtime
- Firewall (UFW): only ports 22, 80, 443 open inbound; k8s API port 16443 and vLLM port 8001 are blocked

**Observability stack (configured but not yet wired into docker-compose):**
- `loki/` — Loki log aggregation config directory
- `promtail/` — Promtail log shipper config directory
- `grafana/provisioning/` — Grafana provisioning directory (empty — no dashboards provisioned)
- No Prometheus metrics instrumentation in application code

---

*Architecture analysis: 2026-03-21*
