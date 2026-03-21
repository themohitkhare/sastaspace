# Technology Stack

**Analysis Date:** 2026-03-21

## Languages

**Primary:**
- Python 3.11+ — Backend server, crawler, redesigner, CLI (`sastaspace/`, `tests/`)
- TypeScript 5 — Frontend Next.js app, components, API routes (`web/src/`)

**Secondary:**
- CSS (Tailwind v4 via PostCSS) — Frontend styling

## Runtime

**Backend:**
- Python 3.11 minimum (`requires-python = ">=3.11"` in `pyproject.toml`)
- Docker image: `python:3.11-slim`

**Frontend:**
- Node.js 22 LTS
- Docker image: `node:22-alpine`

## Package Managers

**Backend:**
- `uv` — primary development package manager; `uv sync`, `uv run`
- Lockfile: `uv.lock` present and committed
- Docker installs via `pip` directly (simpler in container)

**Frontend:**
- `npm` — `package-lock.json` present
- Path alias `@/` resolves to `web/src/` (defined in `web/tsconfig.json`)

## Frameworks

**Backend Core:**
- FastAPI 0.135.1 — HTTP API server with SSE streaming (`sastaspace/server.py`)
- Uvicorn 0.42.0 — ASGI server (`uvicorn sastaspace.server:app`)
- Pydantic 2.12.5 / pydantic-settings 2.13.1 — typed settings + request validation (`sastaspace/config.py`)

**Backend Utilities:**
- Playwright 1.58.0 — headless Chromium crawling (`sastaspace/crawler.py`)
- BeautifulSoup4 4.14.3 — HTML parsing for content extraction (`sastaspace/crawler.py`)
- openai 2.29.0 — OpenAI-compatible SDK pointed at local claude-code-api gateway (`sastaspace/redesigner.py`)
- nh3 0.3.3 — Rust-backed HTML sanitizer applied to all AI-generated output (`sastaspace/server.py`)
- Click 8.3.1 + Rich 13.x — CLI (`sastaspace/cli.py`)

**Frontend Core:**
- Next.js 16.2.1 — App Router, `output: "standalone"` (`web/next.config.ts`)
- React 19.2.4 + React DOM 19.2.4

**Frontend UI:**
- `@base-ui/react` 1.3.0 — headless UI primitives
- `radix-ui` 1.4.3 — component primitives
- `shadcn` 4.1.0 — component distribution
- `class-variance-authority` 0.7.1 + `clsx` 2.1.1 + `tailwind-merge` 3.5.0 — className utilities
- `lucide-react` 0.577.0 — icon set
- `motion` 12.38.0 — animation
- `@marsidev/react-turnstile` 1.4.2 — Cloudflare Turnstile bot protection widget

**Frontend Email:**
- `resend` 6.9.4 — email delivery from Next.js API route (`web/src/app/api/contact/route.ts`)

**Testing:**
- Backend: pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"` in `pyproject.toml`)
- Frontend unit: Vitest 4.1.0 + `@testing-library/react` 16.3.2 (jsdom environment, `web/vitest.config.ts`)
- Frontend E2E: Playwright `@playwright/test` 1.58.2 (Chromium only, 1 worker, `web/playwright.config.ts`)

**Build/Lint:**
- `@tailwindcss/postcss` v4 — Tailwind CSS processing
- `@vitejs/plugin-react` 6.0.1 — React support in Vitest
- ESLint 9 + `eslint-config-next` 16.2.1 — frontend linting
- Ruff 0.8+ — Python linting/formatting (line-length 100, py311 target, rules E/F/I/UP)
- hatchling — Python build backend

## Key Dependencies

**Critical:**
- `openai` 2.29.0 — all AI redesign calls go through this client; API key is `"claude-code"` (not real), base URL is `claude_code_api_url`. Breaking this breaks the redesign pipeline.
- `playwright` 1.58.0 — Chromium binary must be installed separately (`playwright install chromium`); required for all crawls
- `nh3` 0.3.3 — sanitizes every AI-generated HTML before it is served; critical security layer
- `resend` 6.9.4 — sole email delivery mechanism for contact form

**Infrastructure:**
- `pydantic-settings` 2.13.1 — all backend config flows through `sastaspace/config.py`
- `beautifulsoup4` 4.14.3 — HTML parsing in crawler

## Configuration

**Environment Variables (Backend):**
- `CLAUDE_CODE_API_URL` — gateway URL (default: `http://localhost:8000/v1`)
- `SASTASPACE_SITES_DIR` — persistent sites volume path (default: `./sites`)
- `SERVER_PORT` — FastAPI listen port (default: `8080`)
- `CLAUDE_MODEL` — model identifier (default: `claude-sonnet-4-5-20250929`)
- `CORS_ORIGINS` — comma-separated allowed origins (default: `http://localhost:3000`)
- `RATE_LIMIT_MAX` — max requests per IP per window (default: `3`)
- `RATE_LIMIT_WINDOW_SECONDS` — window size in seconds (default: `3600`)
- `ANTHROPIC_API_KEY` — consumed by claude-code-api gateway, not this app directly

**Environment Variables (Frontend):**
- `NEXT_PUBLIC_BACKEND_URL` — FastAPI backend URL for SSE + iframe preview
- `RESEND_API_KEY` — Resend email API key (server-only)
- `OWNER_EMAIL` — contact form destination email (server-only)
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY` — Cloudflare Turnstile public key
- `TURNSTILE_SECRET_KEY` — Cloudflare Turnstile secret (server-only)
- `NEXT_PUBLIC_ENABLE_TURNSTILE` — set to `"false"` to disable bot protection (default: enabled)
- `NEXT_PUBLIC_BASE_URL` — canonical URL for metadata (default: `https://sastaspace.com`)

**Build Config Files:**
- `web/next.config.ts` — minimal; sets `output: "standalone"`
- `web/tsconfig.json` — strict TypeScript, `@/` alias to `src/`
- `pyproject.toml` — project metadata, dependency declarations, ruff config, pytest config

## Deployment Tooling

**Containerization:**
- `backend/Dockerfile` — `python:3.11-slim`; installs system Chromium deps + Playwright; runs `uvicorn`
- `web/Dockerfile` — multi-stage `node:22-alpine`; copies standalone Next.js output; runs `node server.js`
- `claude-code-api/docker/Dockerfile` — `ubuntu:24.04`; installs Claude CLI via `claude.ai/install.sh`; entrypoint handles auth from mounted `~/.claude`
- `web/Dockerfile.test` — Playwright E2E test runner image

**Docker Compose (local dev + integration tests):**
- `docker-compose.yml` — three services: `backend`, `frontend`, `tests` (test profile only)
- Network: `sastaspace` bridge; `sites_data` named volume for generated HTML
- Health checks on all services; `frontend` depends on `backend: service_healthy`
- E2E tests run via `docker compose --profile test run tests`

**Kubernetes (production — MicroK8s):**
- Platform: MicroK8s on self-hosted single Linux node
- Registry: `localhost:32000` (MicroK8s built-in local registry)
- Namespace: `sastaspace` (`k8s/namespace.yaml`)
- Manifests:
  - `k8s/backend.yaml` — Deployment + Service + PersistentVolumeClaim (10Gi, `ReadWriteOnce`)
  - `k8s/frontend.yaml` — Deployment + Service
  - `k8s/claude-code-api.yaml` — Deployment + Service; mounts host `/home/mkhare/.claude` as `hostPath` for Claude auth
  - `k8s/ingress.yaml` — nginx Ingress for `sastaspace.com`, `www.sastaspace.com`, `api.sastaspace.com`; proxy body 50m, read timeout 300s
- Resource limits per pod: `256Mi–1Gi` RAM, `100m–500m` CPU

**CI/CD:**
- GitHub Actions: `.github/workflows/deploy.yml`
- Trigger: push to `main` or manual `workflow_dispatch`
- Runner: self-hosted (`linux, amd64`) — runs directly on the MicroK8s server
- Pipeline: checkout → build 3 images (tagged `latest` + `${{ github.sha }}`) → push to `localhost:32000` → `kubectl apply -f k8s/` (namespace first) → rolling restart → rollout status verification

**Manual Deploy (Makefile):**
- `make deploy` — rsync to `REMOTE_HOST` (default `192.168.0.38`), build/push images via SSH, apply manifests
- `make k8s-apply` — apply k8s manifests only
- `make deploy-logs` / `deploy-status` / `deploy-down` — operations helpers

**Tunneling (alternative to k8s ingress):**
- `cloudflared/config.yml` — Cloudflare Zero Trust tunnel template (`<TUNNEL_UUID>` placeholder, not yet active)
- Routes `^/api/.*` to port 8080, everything else to port 3000

**Observability:**
- Grafana — dashboard (`grafana/provisioning/`)
- Loki — log aggregation (`loki/loki-config.yml`)
- Promtail — log shipping (`promtail/promtail-config.yml`)

## Platform Requirements

**Development:**
- Python 3.11+, `uv` installed
- Node.js 22+, npm
- `make install` bootstraps Python env and Chromium: `uv sync && uv run playwright install chromium`
- `make dev` starts both FastAPI (port 8080) + Next.js (port 3000) concurrently
- claude-code-api gateway must be running on `localhost:8000` for redesigns to work

**Production:**
- Self-hosted Linux server with MicroK8s + Docker + GitHub Actions self-hosted runner
- Claude authentication: `~/.claude` directory on host, mounted read-only into `claude-code-api` pod
- Domains: `sastaspace.com` (frontend), `api.sastaspace.com` (backend)

---

*Stack analysis: 2026-03-21*
