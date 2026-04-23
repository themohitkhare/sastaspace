> Pivot in progress: this repo is being migrated to the Project Bank architecture (see design-log/001-project-bank-foundations.md).

<!-- GSD:project-start source:PROJECT.md -->
## Project

**SastaSpace — AI Website Redesigner**

SastaSpace is a lead generation tool and AI-powered website redesigner. Anyone can enter their domain URL and receive a free, Claude AI-generated redesign of their website — then hire the owner as a consultant to build the real thing. The full-stack application (FastAPI backend + Next.js frontend) is built and functional in development. Next step is production readiness via containerization and E2E testing.

**Core Value:** Users see a stunning AI redesign of their own website and immediately want to hire you to make it real.

### Constraints

- **Tech stack**: Next.js frontend, Python/FastAPI backend — keep these separate
- **Deployment**: Cloudflare tunnel exposes local ports — both Next.js and FastAPI need to be accessible
- **No auth**: Completely open, no signup required
- **Design quality**: The website is itself a portfolio piece — it must look exceptional
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.11+ — Backend server, crawler, redesigner, CLI (`sastaspace/`, `tests/`)
- TypeScript 5 — Frontend Next.js app, components, API routes (`web/src/`)
- CSS (Tailwind v4 via PostCSS) — Frontend styling
## Runtime
- Python 3.11 minimum (`requires-python = ">=3.11"` in `pyproject.toml`)
- Docker image: `python:3.11-slim`
- Node.js 22 LTS
- Docker image: `node:22-alpine`
## Package Managers
- `uv` — primary development package manager; `uv sync`, `uv run`
- Lockfile: `uv.lock` present and committed
- Docker installs via `pip` directly (simpler in container)
- `npm` — `package-lock.json` present
- Path alias `@/` resolves to `web/src/` (defined in `web/tsconfig.json`)
## Frameworks
- FastAPI 0.135.1 — HTTP API server with SSE streaming (`sastaspace/server.py`)
- Uvicorn 0.42.0 — ASGI server (`uvicorn sastaspace.server:app`)
- Pydantic 2.12.5 / pydantic-settings 2.13.1 — typed settings + request validation (`sastaspace/config.py`)
- Playwright 1.58.0 — headless Chromium crawling (`sastaspace/crawler.py`)
- BeautifulSoup4 4.14.3 — HTML parsing for content extraction (`sastaspace/crawler.py`)
- openai 2.29.0 — OpenAI-compatible SDK pointed at local claude-code-api gateway (`sastaspace/redesigner.py`)
- nh3 0.3.3 — Rust-backed HTML sanitizer applied to all AI-generated output (`sastaspace/server.py`)
- Click 8.3.1 + Rich 13.x — CLI (`sastaspace/cli.py`)
- Next.js 16.2.1 — App Router, `output: "standalone"` (`web/next.config.ts`)
- React 19.2.4 + React DOM 19.2.4
- `@base-ui/react` 1.3.0 — headless UI primitives
- `radix-ui` 1.4.3 — component primitives
- `shadcn` 4.1.0 — component distribution
- `class-variance-authority` 0.7.1 + `clsx` 2.1.1 + `tailwind-merge` 3.5.0 — className utilities
- `lucide-react` 0.577.0 — icon set
- `motion` 12.38.0 — animation
- `@marsidev/react-turnstile` 1.4.2 — Cloudflare Turnstile bot protection widget
- `resend` 6.9.4 — email delivery from Next.js API route (`web/src/app/api/contact/route.ts`)
- Backend: pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"` in `pyproject.toml`)
- Frontend unit: Vitest 4.1.0 + `@testing-library/react` 16.3.2 (jsdom environment, `web/vitest.config.ts`)
- Frontend E2E: Playwright `@playwright/test` 1.58.2 (Chromium only, 1 worker, `web/playwright.config.ts`)
- `@tailwindcss/postcss` v4 — Tailwind CSS processing
- `@vitejs/plugin-react` 6.0.1 — React support in Vitest
- ESLint 9 + `eslint-config-next` 16.2.1 — frontend linting
- Ruff 0.8+ — Python linting/formatting (line-length 100, py311 target, rules E/F/I/UP)
- hatchling — Python build backend
## Key Dependencies
- `openai` 2.29.0 — all AI redesign calls go through this client; API key is `"claude-code"` (not real), base URL is `claude_code_api_url`. Breaking this breaks the redesign pipeline.
- `playwright` 1.58.0 — Chromium binary must be installed separately (`playwright install chromium`); required for all crawls
- `nh3` 0.3.3 — sanitizes every AI-generated HTML before it is served; critical security layer
- `resend` 6.9.4 — sole email delivery mechanism for contact form
- `pydantic-settings` 2.13.1 — all backend config flows through `sastaspace/config.py`
- `beautifulsoup4` 4.14.3 — HTML parsing in crawler
## Configuration
- `CLAUDE_CODE_API_URL` — gateway URL (default: `http://localhost:8000/v1`)
- `SASTASPACE_SITES_DIR` — persistent sites volume path (default: `./sites`)
- `SERVER_PORT` — FastAPI listen port (default: `8080`)
- `CLAUDE_MODEL` — model identifier (default: `claude-sonnet-4-5-20250929`)
- `CORS_ORIGINS` — comma-separated allowed origins (default: `http://localhost:3000`)
- `RATE_LIMIT_MAX` — max requests per IP per window (default: `3`)
- `RATE_LIMIT_WINDOW_SECONDS` — window size in seconds (default: `3600`)
- `ANTHROPIC_API_KEY` — consumed by claude-code-api gateway, not this app directly
- `NEXT_PUBLIC_BACKEND_URL` — FastAPI backend URL for SSE + iframe preview
- `RESEND_API_KEY` — Resend email API key (server-only)
- `OWNER_EMAIL` — contact form destination email (server-only)
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY` — Cloudflare Turnstile public key
- `TURNSTILE_SECRET_KEY` — Cloudflare Turnstile secret (server-only)
- `NEXT_PUBLIC_ENABLE_TURNSTILE` — set to `"false"` to disable bot protection (default: enabled)
- `NEXT_PUBLIC_BASE_URL` — canonical URL for metadata (default: `https://sastaspace.com`)
- `web/next.config.ts` — minimal; sets `output: "standalone"`
- `web/tsconfig.json` — strict TypeScript, `@/` alias to `src/`
- `pyproject.toml` — project metadata, dependency declarations, ruff config, pytest config
## Deployment Tooling
- `backend/Dockerfile` — `python:3.11-slim`; installs system Chromium deps + Playwright; runs `uvicorn`
- `web/Dockerfile` — multi-stage `node:22-alpine`; copies standalone Next.js output; runs `node server.js`
- `claude-code-api/docker/Dockerfile` — `ubuntu:24.04`; installs Claude CLI via `claude.ai/install.sh`; entrypoint handles auth from mounted `~/.claude`
- `web/Dockerfile.test` — Playwright E2E test runner image
- `docker-compose.yml` — three services: `backend`, `frontend`, `tests` (test profile only)
- Network: `sastaspace` bridge; `sites_data` named volume for generated HTML
- Health checks on all services; `frontend` depends on `backend: service_healthy`
- E2E tests run via `docker compose --profile test run tests`
- Platform: MicroK8s on self-hosted single Linux node
- Registry: `localhost:32000` (MicroK8s built-in local registry)
- Namespace: `sastaspace` (`k8s/namespace.yaml`)
- Manifests:
- Resource limits per pod: `256Mi–1Gi` RAM, `100m–500m` CPU
- GitHub Actions: `.github/workflows/deploy.yml`
- Trigger: push to `main` or manual `workflow_dispatch`
- Runner: self-hosted (`linux, amd64`) — runs directly on the MicroK8s server
- Pipeline: checkout → build 3 images (tagged `latest` + `${{ github.sha }}`) → push to `localhost:32000` → `kubectl apply -f k8s/` (namespace first) → rolling restart → rollout status verification
- `make deploy` — rsync to `REMOTE_HOST` (default `192.168.0.38`), build/push images via SSH, apply manifests
- `make k8s-apply` — apply k8s manifests only
- `make deploy-logs` / `deploy-status` / `deploy-down` — operations helpers
- `cloudflared/config.yml` — Cloudflare Zero Trust tunnel template (`<TUNNEL_UUID>` placeholder, not yet active)
- Routes `^/api/.*` to port 8080, everything else to port 3000
- Grafana — dashboard (`grafana/provisioning/`)
- Loki — log aggregation (`loki/loki-config.yml`)
- Promtail — log shipping (`promtail/promtail-config.yml`)
## Platform Requirements
- Python 3.11+, `uv` installed
- Node.js 22+, npm
- `make install` bootstraps Python env and Chromium: `uv sync && uv run playwright install chromium`
- `make dev` starts both FastAPI (port 8080) + Next.js (port 3000) concurrently
- claude-code-api gateway must be running on `localhost:8000` for redesigns to work
- Self-hosted Linux server with MicroK8s + Docker + GitHub Actions self-hosted runner
- Claude authentication: `~/.claude` directory on host, mounted read-only into `claude-code-api` pod
- Domains: `sastaspace.com` (frontend), `api.sastaspace.com` (backend)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- `kebab-case.tsx` for all component files: `url-input-form.tsx`, `contact-form.tsx`, `progress-view.tsx`
- `kebab-case.ts` for all lib/hook files: `sse-client.ts`, `url-utils.ts`, `use-redesign.ts`
- Hooks prefixed with `use-`: `use-redesign.ts`
- API routes follow Next.js App Router convention: `src/app/api/contact/route.ts`
- `snake_case.py` for all source modules: `crawler.py`, `redesigner.py`, `deployer.py`, `server.py`
- Test files mirror source: `test_crawler.py` mirrors `crawler.py`, `test_server.py` mirrors `server.py`
- Named exports for components: `export function UrlInputForm(...)`, `export function ContactForm(...)`
- Named exports for hooks: `export function useRedesign()`
- Named exports for lib functions: `export function validateUrl(...)`, `export function streamRedesign(...)`
- camelCase for all functions and variables
- SCREAMING_SNAKE_CASE for module-level constants: `STEPS`, `STEP_INTERMEDIATE_VALUES`, `STEP_LABELS`
- `snake_case` for all functions: `make_app`, `get_client_ip`, `derive_subdomain`
- Module-level constants in SCREAMING_SNAKE_CASE: `SAMPLE_HTML` in tests
- Private/internal helpers prefixed with underscore: `_ensure_chromium`, `_extract_images`, `_extract_nav_links`
- PascalCase for interfaces and type aliases: `UrlInputFormProps`, `RedesignState`, `StepState`, `SSEEvent`
- Discriminated unions for state machines: `RedesignState` uses `status` as the discriminant
- `type FormStatus = "idle" | "submitting" | "success" | "error"` — string literal unions over enums
- Interface props named `{ComponentName}Props`: `ContactFormProps`, `UrlInputFormProps`, `ProgressViewProps`
- Pydantic models for request schemas: `class RedesignRequest(BaseModel):`
- Dataclasses for results: `CrawlResult`, `DeployResult`
- pydantic-settings for config: `class Settings(BaseSettings):`
- Image names: `sastaspace-{service}` (e.g., `sastaspace-frontend`, `sastaspace-backend`)
- k8s resource names match service role: `frontend`, `backend`, `claude-code-api`
- k8s namespace: `sastaspace` (all resources scoped to this namespace)
## Code Style
- Prettier is not separately configured; ESLint handles style via `eslint-config-next`
- Config: `web/eslint.config.mjs` — extends `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- Flat config format (ESLint v9): `defineConfig([...nextVitals, ...nextTs])`
- Ruff for both linting and formatting: `[tool.ruff]` in `pyproject.toml`
- Line length: 100 characters
- Target: Python 3.11+
- Lint rules selected: `E` (pycodestyle), `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- Run: `uv run ruff check sastaspace/ tests/` and `uv run ruff format --check sastaspace/ tests/`
## Import Organization
- Path alias `@` maps to `src/` — configured in `web/vitest.config.ts` and Next.js
- Standard library first (sorted): `import asyncio`, `import json`, `import os`
- Third-party next: `from fastapi import FastAPI`, `from pydantic import BaseModel`
- Local last: `from sastaspace.config import Settings`, `from sastaspace.crawler import crawl`
- Ruff `I` rule enforces isort ordering
## Client vs Server Boundaries (Next.js)
- All interactive components begin with `"use client"` directive
- `"use client"` files: `app-flow.tsx`, `url-input-form.tsx`, `contact-form.tsx`, `progress-view.tsx`, `step-indicator.tsx`, `use-redesign.ts`
- Server components (no directive): `src/app/page.tsx`, `src/app/layout.tsx`, `src/app/[subdomain]/page.tsx`
- API routes are always server-side: `src/app/api/contact/route.ts`
## Error Handling
- Wrap entire handler body in `try/catch`
- Return `Response.json({ error: "..." }, { status: N })` for errors
- Return `Response.json({ ok: true })` for success
- Status codes: `400` for validation failures, `500` for unexpected/infrastructure errors
- Silent honeypot rejection: return `200 ok:true` to not reveal detection (not a 4xx)
- `try/catch` around async operations; catch block sets error state
- Empty catch blocks are used when aborting is intentional: `catch { if (controller.signal.aborted) return; }`
- Malformed SSE events silently skipped: `catch { // Skip malformed events silently }`
- Error messages shown to users are human-readable strings, not raw error objects
- FastAPI raises `HTTPException` for route-level errors
- Module-level functions return structured result objects; errors surfaced via SSE `error` events
- `from __future__ import annotations` used in server.py for forward references
## State Management Patterns
- Complex component state modeled as discriminated union types
- `useRedesign` hook in `src/hooks/use-redesign.ts` manages the full app flow via `RedesignState`
- State transitions are explicit — each event handler calls `setState` with a complete new state object
- `useRef` used for mutable values that don't trigger re-render: `abortRef`, `debounceRef`
- `useCallback` used consistently for handlers passed as props
- Individual `useState` calls per field (not a single form object): `name`, `email`, `message`
- Validation errors in `Record<string, string>` map: `errors.name`, `errors.email`
- Errors cleared on field change (not on submit): inline `setErrors((prev) => { delete n.fieldName; return n; })`
- `noValidate` on all `<form>` elements — custom inline validation only, no browser tooltips
## Logging
- `console.error` used for server-side errors: `console.error("Resend error:", error)`
- No structured logging library in the frontend
- No logging framework detected in explored files; uses print-style output in CLI (`rich` library present)
## Comments
- Inline comments for non-obvious decisions: `// Honeypot — return success to not reveal detection (per D-10)`
- Reference codes like `D-09`, `D-10`, `FLAG-01` used to cross-reference decision documents
- `// eslint-disable-next-line` comments used sparingly for intentional rule suppression
- Module-level comment with file path: `# sastaspace/server.py`, `# tests/test_server.py`
- Docstrings on factory/helper functions: `"""Create the FastAPI app bound to a specific sites directory."""`
- Section separator comments in tests: `# --- CrawlResult dataclass tests ---`
## Deployment Conventions
- Frontend (`web/Dockerfile`): multi-stage build — `builder` stage on `node:22-alpine`, `runner` stage on `node:22-alpine`
- Backend (`backend/Dockerfile`): single-stage on `python:3.11-slim`
- Test runner (`web/Dockerfile.test`): based on `mcr.microsoft.com/playwright:v1.52.0-noble`
- Always tag both `:latest` and `:{github.sha}` in CI: enables rollback
- Local registry: `localhost:32000/sastaspace-{service}`
- Image name pattern: `sastaspace-{service}` (frontend, backend, claude-code-api)
- All resources in `sastaspace` namespace — `namespace.yaml` applied before other manifests
- Each service has both `Deployment` and `Service` in the same YAML file (separated by `---`)
- `PersistentVolumeClaim` co-located with the Deployment that uses it: `backend.yaml` contains the PVC
- Resource limits on all containers: `requests: memory 256Mi / cpu 100m`, `limits: memory 1Gi / cpu 500m`
- `readinessProbe` on every deployment via `httpGet` — no livenessProbe
- Secrets injected via `secretRef` (not env vars inline): `envFrom: - secretRef: name: sastaspace-env`
- Non-secret env vars set inline under `env:` in the manifest
- Self-hosted runner: `runs-on: [self-hosted, linux, amd64]`
- Trigger: push to `main` branch or `workflow_dispatch`
- Job timeout: 30 minutes
- Deploy order: build all images → push to registry → `kubectl apply` manifests → rolling restart → wait for rollout → verify
- `namespace.yaml` applied explicitly before `k8s/` to avoid namespace-not-found errors
- Rollout wait with `--timeout=300s` (5 minutes per deployment)
- `env_file: path: .env / required: false` — `.env` is optional, no hard failure if absent
- Health checks on every service mirror Dockerfile HEALTHCHECK
- `depends_on: condition: service_healthy` enforces startup ordering
- `tests` service in `profiles: [test]` — not started by default, only with `--profile test`
- Named volumes for persistence: `sites_data` mounted at `/data/sites`
- `make ci` = `lint` + `test` — single command for CI validation
- `make deploy` = rsync to remote + build images on remote + push + k8s apply + rolling restart
- Deployment targets use SSH to remote host (not local Docker daemon)
- `.PHONY` declared for all non-file targets
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Three distinct services: FastAPI backend, Next.js frontend, claude-code-api gateway
- Core product loop is a 3-step async pipeline: Crawl → Redesign (AI) → Deploy
- Frontend communicates with backend exclusively via a single SSE endpoint (`POST /redesign`)
- Backend stores redesigned sites as static HTML files on a persistent volume and serves them directly — no database
- Site registry is a flat JSON file (`_registry.json`) on disk
- The AI inference call goes through `claude-code-api`, an OpenAI-compatible proxy wrapping Claude Code CLI
- A parallel CLI entrypoint (`sastaspace`) runs the same pipeline synchronously for local/dev use
## Layers
- Purpose: Developer/local-use entry point for the full redesign pipeline
- Location: `sastaspace/cli.py`
- Contains: Click commands (`redesign`, `list`, `open`, `remove`, `serve`)
- Depends on: `crawler`, `redesigner`, `deployer`, `server` modules, `config`
- Used by: Developers directly via `sastaspace` CLI command (installed via `pyproject.toml`)
- Purpose: Exposes the redesign pipeline as an HTTP service for the frontend
- Location: `sastaspace/server.py`
- Contains: `POST /redesign` (SSE stream), `GET /` (registry admin dashboard), `GET /{subdomain}/` and `GET /{subdomain}/{path}` (static site serving)
- Depends on: `crawler`, `redesigner`, `deployer`, `config`
- Used by: Next.js frontend via `NEXT_PUBLIC_BACKEND_URL`
- Purpose: The three discrete steps of the AI redesign pipeline
- Location: `sastaspace/crawler.py`, `sastaspace/redesigner.py`, `sastaspace/deployer.py`
- Contains: `crawl()` (async), `redesign()` (sync, uses `asyncio.to_thread` in server), `deploy()` (sync)
- Depends on: Playwright (crawl), OpenAI Python client → claude-code-api (redesign), stdlib only (deploy)
- Used by: Both `server.py` and `cli.py`
- Purpose: Centralised settings via pydantic-settings, reads from `.env` and environment
- Location: `sastaspace/config.py`
- Contains: `Settings` class with fields: `claude_code_api_url`, `sites_dir`, `server_port`, `claude_model`, `cors_origins`, `rate_limit_max`, `rate_limit_window_seconds`
- `SASTASPACE_SITES_DIR` env var takes precedence over `.env` for `sites_dir` (used by Docker)
- Purpose: Public web UI for submitting URLs and viewing AI redesign results
- Location: `web/src/`
- Contains: App Router pages, React components, SSE client library, hooks
- Depends on: `NEXT_PUBLIC_BACKEND_URL` env var to reach the FastAPI backend
- Purpose: OpenAI-compatible API wrapper over Claude Code CLI
- Location: `claude-code-api/` (separate git repo, also containerised in k8s)
- Exposes: `POST /v1/chat/completions`, `GET /health` at port 8000
- Used by: `sastaspace/redesigner.py` via `openai.OpenAI(base_url=api_url)` client
## Data Flow
- All UI state lives in `useRedesign` hook as a discriminated union: `idle | connecting | progress | done | error`
- SSE events (`crawling`, `redesigning`, `deploying`, `done`, `error`) drive all state transitions
- On `done`, `useEffect` in `web/src/components/app-flow.tsx` calls `router.push(/${subdomain})` — no global state store needed
## Key Abstractions
- Purpose: Structured representation of a crawled webpage; the data contract between crawler and redesigner
- Location: `sastaspace/crawler.py`
- Pattern: Python `@dataclass` with `error: str = ""` sentinel field; `to_prompt_context()` serialises to LLM-ready markdown
- Purpose: Discriminated union driving all UI transitions from idle to result
- Location: `web/src/hooks/use-redesign.ts`
- Pattern: TypeScript discriminated union: `{ status: "idle" } | { status: "connecting" } | { status: "progress"; currentStep, domain, steps } | { status: "done"; subdomain, originalUrl, domain } | { status: "error"; message, url }`
- Purpose: Runtime configuration via environment variables
- Location: `sastaspace/config.py`
- Pattern: `pydantic_settings.BaseSettings` — all env vars read at startup with sensible defaults
- Purpose: Factory function creating the FastAPI application bound to a specific sites directory
- Location: `sastaspace/server.py`
- Pattern: Allows tests and Docker to inject a custom `sites_dir`; module-level `app` is the uvicorn default instance
## Entry Points
- Location: `sastaspace/server.py` — module-level `app = make_app(_settings.sites_dir)`
- Triggers: `uvicorn sastaspace.server:app` (Docker CMD, CLI `serve` command, `ensure_running()` subprocess)
- Responsibilities: Rate limiting (in-process dict), concurrency control (semaphore), SSE streaming, static site serving
- Location: `web/src/app/layout.tsx`, `web/src/app/page.tsx`
- Triggers: `node server.js` (Docker standalone) or `npm run dev`
- Responsibilities: Landing page, real-time progress tracking via SSE, result display with iframe preview, contact form
- Location: `web/src/app/api/contact/route.ts`
- Triggers: `POST /api/contact` from frontend contact form on result pages
- Responsibilities: Honeypot check, Cloudflare Turnstile verification, email dispatch via Resend SDK
- Location: `sastaspace/cli.py` — entrypoint `sastaspace.cli:main`
- Triggers: `sastaspace <command>` installed via `[project.scripts]` in `pyproject.toml`
## Error Handling
- `crawl()` sets `CrawlResult.error` on any exception — caller checks before proceeding (error-as-value)
- `redesigner.py` raises `RedesignError` on invalid Claude output (missing DOCTYPE, missing `</html>`, empty response)
- `server.py` wraps the entire `redesign_stream()` generator in a broad `except Exception` that emits a generic SSE `error` event
- `cli.py` catches `RedesignError` and generic exceptions separately with distinct Rich error panels
- Frontend `useRedesign`: `try/catch` around `for await` loop; aborted `AbortController` signals silently terminate the loop
- `deploy()` uses atomic write-then-rename (`os.replace`) to prevent corrupt registry files on crash
## Cross-Cutting Concerns
- `nh3.clean()` sanitises AI-generated HTML before writing to disk
- `_validate_html()` checks for DOCTYPE and `</html>` before accepting Claude's response
- Frontend contact route: honeypot field check, field presence check, Cloudflare Turnstile token verification
## Deployment Architecture
```
```
- All manifests in `k8s/` — 5 files: `namespace.yaml`, `backend.yaml`, `frontend.yaml`, `claude-code-api.yaml`, `ingress.yaml`
- All deployments: 1 replica; resource limits 1Gi memory / 500m CPU; requests 256Mi / 100m
- Backend uses a `PersistentVolumeClaim` (`sites-pvc`, 10Gi, `ReadWriteOnce`) mounted at `/data/sites` — this is where all redesigned HTML files live
- All images pulled from local microk8s registry at `localhost:32000` (no Docker Hub)
- Ingress: nginx with `proxy-body-size: 50m` and `proxy-read-timeout: 300` (required for long SSE streams)
- `claude-code-api` pod mounts host path `/home/mkhare/.claude` read-only for Claude credentials
- `docker-compose.yml`: three services — `backend`, `frontend`, `tests` (test profile only)
- Backend: volume `sites_data` named volume at `/data/sites`; `CLAUDE_CODE_API_URL=http://host.docker.internal:8000/v1` (routes to host-side claude-code-api)
- Frontend: `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080`; waits for backend healthcheck (`service_healthy`)
- `backend/Dockerfile`: Python 3.11-slim with Playwright/Chromium system deps; Playwright installs Chromium at build time
- `web/Dockerfile`: Multi-stage Node 22 Alpine; Stage 1 builds Next.js in standalone mode; Stage 2 copies `.next/standalone`, `static`, `public` — minimal production image
- Workflow: `.github/workflows/deploy.yml`
- Trigger: push to `main` branch, or manual `workflow_dispatch`
- Runner: `self-hosted, linux, amd64` — the production machine runs its own CI jobs
- Pipeline steps: checkout → build 3 Docker images (backend, frontend, claude-code-api) → push to `localhost:32000` with both `:latest` and `:{git-sha}` tags → `kubectl apply -f k8s/` → rolling restart all 3 deployments → wait for rollout status (300s timeout each) → verify with pod/service/ingress listing
- `make deploy`: rsync source to remote, build images on remote, apply k8s manifests, rolling restart
- `make deploy-status`: `kubectl get pods,svc,ingress -n sastaspace`
- `make deploy-logs`: tail combined logs from frontend + backend pods
- `make deploy-down`: delete entire `sastaspace` namespace
- `cloudflared` — Cloudflare tunnel routing public traffic to microk8s nginx port 80; survives reboot
- `claude-code-api` — OpenAI-compatible Claude proxy on `localhost:8000` (also has a k8s containerised variant)
- `docker` — container runtime
- Firewall (UFW): only ports 22, 80, 443 open inbound; k8s API port 16443 and vLLM port 8001 are blocked
- `loki/` — Loki log aggregation config directory
- `promtail/` — Promtail log shipper config directory
- `grafana/provisioning/` — Grafana provisioning directory (empty — no dashboards provisioned)
- No Prometheus metrics instrumentation in application code
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
