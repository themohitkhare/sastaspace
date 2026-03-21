# External Integrations

**Analysis Date:** 2026-03-21

## APIs & External Services

**AI / LLM:**
- claude-code-api (self-hosted gateway) — OpenAI-compatible HTTP proxy for Claude
  - SDK/Client: `openai` Python SDK (`sastaspace/redesigner.py`)
  - Base URL: `http://localhost:8000/v1` in dev; `http://claude-code-api:8000/v1` in k8s
  - Auth: `api_key="claude-code"` (dummy; actual auth handled by gateway via `~/.claude` mount)
  - Model: `claude-sonnet-4-5-20250929` (configurable via `CLAUDE_MODEL`)
  - Call: `client.chat.completions.create(...)` with multimodal content (base64 screenshot + text)
  - Max tokens: 16,000 per request
  - Gateway image: `localhost:32000/sastaspace-claude-code-api:latest` (deployed as k8s pod)
  - Gateway auth: `~/.claude` directory mounted from host as `hostPath` volume in `k8s/claude-code-api.yaml`

**Email:**
- Resend — transactional email delivery for contact form submissions
  - SDK/Client: `resend` npm package (`web/src/app/api/contact/route.ts`)
  - Auth: `RESEND_API_KEY` env var (server-only, never exposed to browser)
  - From address: `noreply@sastaspace.com`
  - Destination: `OWNER_EMAIL` env var
  - Triggered by: POST to `/api/contact` in Next.js

**Bot Protection:**
- Cloudflare Turnstile — invisible CAPTCHA on contact form
  - Client: `@marsidev/react-turnstile` (`web/src/components/result/contact-form.tsx`)
  - Server verification: POST to `https://challenges.cloudflare.com/turnstile/v0/siteverify`
  - Credentials: `NEXT_PUBLIC_TURNSTILE_SITE_KEY` (public) + `TURNSTILE_SECRET_KEY` (server-only)
  - Feature flag: set `NEXT_PUBLIC_ENABLE_TURNSTILE=false` to disable (dev convenience)

**Web Crawling (arbitrary external URLs):**
- Playwright headless Chromium — visits arbitrary target URLs supplied by users
  - Implementation: `sastaspace/crawler.py`, `async def crawl(url: str)`
  - UA: Chrome 120 on macOS
  - Timeout: 30s per page load (`wait_until="networkidle"`)

**Google Fonts (passive):**
- AI-generated HTML uses `@import` from `fonts.googleapis.com` per system prompt in `sastaspace/redesigner.py`
- No server-side calls; outbound request happens in the user's browser when viewing the redesigned site

## Data Storage

**Databases:**
- None — no database anywhere in the stack

**File Storage:**
- Local filesystem / PersistentVolumeClaim (10Gi, `ReadWriteOnce`) in k8s
  - Redesigned sites: `/data/sites/{subdomain}/index.html` (k8s) / `./sites/{subdomain}/index.html` (local)
  - Registry: `sites/_registry.json` — JSON array of all deployed redesigns (subdomain, original URL, timestamp)
  - Per-site metadata: `sites/{subdomain}/metadata.json`
  - Server state: `sites/.server_port`, `sites/.server.log` (local dev only)
  - Implementation: `sastaspace/deployer.py`
  - k8s PVC claim: `sites-pvc` in `k8s/backend.yaml`, mounted at `/data/sites`

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- No user authentication in the application
- Backend rate-limits by IP: 3 requests per 3600 seconds; localhost is exempt
- Concurrency limited: `asyncio.Semaphore(1)` — only one redesign at a time
- Claude authentication: handled entirely by the claude-code-api gateway (reads `~/.claude`)

## Monitoring & Observability

**Log Aggregation:**
- Loki — configuration at `loki/loki-config.yml`
- Promtail — log shipping, configuration at `promtail/promtail-config.yml`

**Dashboards:**
- Grafana — provisioning config at `grafana/provisioning/`

**Application Logs:**
- Backend: uvicorn stdout/stderr, visible in k8s via `kubectl logs`
- Frontend: Next.js stdout
- `make deploy-logs` tails both pod log streams

**Error Tracking:**
- No external error tracking (no Sentry or equivalent)

## CI/CD & Deployment

**Hosting:**
- Production: self-hosted Linux server running MicroK8s at `sastaspace.com` / `api.sastaspace.com`
- Images served from local Docker registry at `localhost:32000` (MicroK8s built-in)

**CI Pipeline:**
- GitHub Actions: `.github/workflows/deploy.yml`
- Trigger: push to `main`, or manual `workflow_dispatch`
- Runner: self-hosted (`linux, amd64`) — the production server itself
- Steps: checkout → build 3 Docker images → push to `localhost:32000` → `kubectl apply -f k8s/` → rolling restart → rollout verification
- No separate staging environment

**Local CI:**
- `make ci` = `make lint` + `make test`
- Ruff checks + pytest for Python
- No automated frontend test run in CI currently

**Tunnel / Reverse Proxy:**
- nginx Ingress controller (MicroK8s) routes:
  - `sastaspace.com` + `www.sastaspace.com` → frontend:3000
  - `api.sastaspace.com` → backend:8080
- Proxy body size: 50MB, read timeout: 300s (`k8s/ingress.yaml`)
- Cloudflare Zero Trust tunnel config template at `cloudflared/config.yml` (not yet activated — placeholder UUIDs)

## Environment Configuration

**Required env vars for full production functionality:**
- `RESEND_API_KEY` — Resend email API key
- `OWNER_EMAIL` — contact form destination
- `NEXT_PUBLIC_TURNSTILE_SITE_KEY` — Cloudflare Turnstile public key
- `TURNSTILE_SECRET_KEY` — Cloudflare Turnstile secret
- `ANTHROPIC_API_KEY` — consumed by claude-code-api gateway (via Kubernetes `sastaspace-env` secret)

**Optional with defaults:**
- `CLAUDE_CODE_API_URL` (default: `http://localhost:8000/v1`)
- `SASTASPACE_SITES_DIR` (default: `./sites`)
- `SERVER_PORT` (default: `8080`)
- `CLAUDE_MODEL` (default: `claude-sonnet-4-5-20250929`)
- `CORS_ORIGINS` (default: `http://localhost:3000`)
- `NEXT_PUBLIC_BACKEND_URL` (default: unset in production; set to `http://localhost:8080` in dev)
- `NEXT_PUBLIC_BASE_URL` (default: `https://sastaspace.com`)

**Secrets in k8s:**
- Kubernetes secret `sastaspace-env` in namespace `sastaspace`
- Backend pod loads it via `envFrom.secretRef` (`k8s/backend.yaml`)
- Frontend env vars are baked into the Docker image at build time (`NEXT_PUBLIC_*`) or set via k8s manifest env

**Secrets in local dev:**
- `.env` at project root (gitignored); template at `.env.example`
- `web/.env.example` has frontend-specific template

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- Resend API call on each contact form submission (POST from Next.js API route server-side)
- Cloudflare Turnstile verification (POST from Next.js API route server-side)
- All other outbound HTTP is from Playwright crawling user-supplied URLs (user-initiated, not webhook)

---

*Integration audit: 2026-03-21*
