# Codebase Structure

**Analysis Date:** 2026-03-21

## Directory Layout

```
sastaspace/                        # project root
├── sastaspace/                    # Python backend package
│   ├── __init__.py
│   ├── cli.py                     # Click CLI entrypoint; pipeline orchestration
│   ├── config.py                  # pydantic-settings Settings class
│   ├── crawler.py                 # Playwright web crawler + CrawlResult dataclass
│   ├── deployer.py                # Filesystem deploy + JSON registry management
│   ├── redesigner.py              # Claude AI integration; HTML validation
│   └── server.py                  # FastAPI server; make_app() factory; ensure_running()
├── web/                           # Next.js frontend application
│   ├── src/
│   │   ├── app/                   # Next.js App Router
│   │   │   ├── layout.tsx         # Root layout; font loading; metadata
│   │   │   ├── page.tsx           # Home page — renders <AppFlow />
│   │   │   ├── [subdomain]/       # Dynamic route for result pages
│   │   │   │   └── page.tsx       # Renders <ResultView subdomain={...} />
│   │   │   ├── api/
│   │   │   │   └── contact/
│   │   │   │       └── route.ts   # POST /api/contact; Resend email; Turnstile
│   │   │   ├── globals.css        # Tailwind base styles; CSS custom properties
│   │   │   ├── manifest.ts        # PWA manifest
│   │   │   ├── robots.ts          # robots.txt
│   │   │   ├── sitemap.ts         # sitemap.xml
│   │   │   ├── opengraph-image.tsx
│   │   │   ├── apple-icon.tsx
│   │   │   ├── icon.tsx
│   │   │   └── favicon.ico
│   │   ├── components/
│   │   │   ├── app-flow.tsx       # Top-level state machine component; routes between views
│   │   │   ├── backgrounds/       # Background visual components
│   │   │   ├── landing/           # Landing page sections
│   │   │   │   ├── hero-section.tsx
│   │   │   │   ├── how-it-works.tsx
│   │   │   │   └── url-input-form.tsx
│   │   │   ├── progress/          # In-progress redesign view
│   │   │   │   ├── progress-view.tsx
│   │   │   │   └── step-indicator.tsx
│   │   │   ├── result/            # Result/share page components
│   │   │   │   ├── result-view.tsx
│   │   │   │   └── contact-form.tsx
│   │   │   └── ui/                # shadcn/ui primitives (Button, Input, etc.)
│   │   ├── hooks/
│   │   │   └── use-redesign.ts    # SSE state machine hook; drives AppFlow
│   │   ├── lib/
│   │   │   ├── sse-client.ts      # streamRedesign() async generator; SSE parser
│   │   │   ├── url-utils.ts       # validateUrl(), extractDomain()
│   │   │   └── utils.ts           # cn() Tailwind class merge utility
│   │   └── __tests__/             # Vitest unit tests for frontend
│   ├── e2e/                       # Playwright E2E tests
│   ├── public/                    # Static assets (icons, images)
│   ├── Dockerfile                 # Multi-stage Node 22 Alpine build (standalone mode)
│   ├── Dockerfile.test            # Playwright E2E test runner image
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── playwright.config.ts
│   ├── vitest.config.ts
│   ├── components.json            # shadcn/ui config
│   └── package.json
├── backend/
│   └── Dockerfile                 # Python 3.11-slim + Playwright/Chromium system deps
├── k8s/                           # Kubernetes manifests (microk8s, namespace: sastaspace)
│   ├── namespace.yaml             # sastaspace namespace definition
│   ├── backend.yaml               # FastAPI Deployment + Service + PersistentVolumeClaim (10Gi)
│   ├── frontend.yaml              # Next.js Deployment + Service
│   ├── claude-code-api.yaml       # claude-code-api Deployment + Service; mounts ~/.claude hostPath
│   └── ingress.yaml               # nginx Ingress; routes sastaspace.com and api.sastaspace.com
├── .github/
│   └── workflows/
│       └── deploy.yml             # CI/CD: build images → push to local registry → kubectl apply → rollout
├── tests/                         # pytest suite for Python backend
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_crawler.py
│   ├── test_deployer.py
│   ├── test_redesigner.py
│   └── test_server.py
├── claude-code-api/               # Submodule/separate repo — OpenAI-compatible Claude proxy
│   ├── claude_code_api/           # Python package
│   │   ├── api/                   # FastAPI routes
│   │   ├── core/                  # Claude Code CLI integration
│   │   ├── models/                # Pydantic models
│   │   └── utils/
│   └── docker/
│       └── Dockerfile
├── components/                    # UI component library reference (design assets)
│   ├── marketing-blocks/          # Landing page block templates
│   └── ui-components/             # Atomic UI component templates
├── sites/                         # Runtime output (gitignored)
│   ├── _registry.json             # JSON array of all deployed site metadata
│   ├── .server_port               # Active server port written by ensure_running()
│   ├── .server.log                # Uvicorn subprocess stdout/stderr
│   └── {subdomain}/               # One directory per redesign
│       ├── index.html             # AI-generated single-file redesign
│       └── metadata.json          # {subdomain, original_url, timestamp, status}
├── cloudflared/
│   └── config.yml                 # Cloudflare Zero Trust tunnel config template
├── loki/                          # Loki log aggregation config (not active in compose)
├── promtail/                      # Promtail log shipper config (not active in compose)
├── grafana/
│   └── provisioning/              # Grafana provisioning (empty — not yet configured)
├── docs/
│   └── DEPLOYMENT.md              # Full production server setup guide
├── sites/                         # Runtime-generated (gitignored)
├── .planning/
│   ├── codebase/                  # GSD codebase analysis documents
│   ├── milestones/
│   └── phases/                    # Phase planning files (01–09)
├── pyproject.toml                 # Python project metadata, deps, ruff, pytest config
├── docker-compose.yml             # Local dev/test: backend + frontend + tests services
├── Makefile                       # install / lint / test / deploy / k8s-apply targets
├── uv.lock                        # uv lockfile
└── .env.example                   # Documents required environment variables
```

## Directory Purposes

**`sastaspace/` (Python package):**
- Purpose: All Python application source code — the backend pipeline and server
- Contains: One module per responsibility; no subdirectories
- Key files: `server.py` (HTTP API), `cli.py` (CLI), `crawler.py` (data model + crawl), `redesigner.py` (AI call)

**`web/` (Next.js app):**
- Purpose: Public-facing web UI
- Contains: App Router pages, React components, hooks, utilities, tests
- Key files: `src/components/app-flow.tsx` (state machine), `src/hooks/use-redesign.ts` (SSE hook), `src/lib/sse-client.ts` (SSE parser)

**`backend/`:**
- Purpose: Docker build context for the Python backend only
- Contains: `Dockerfile` — installs system deps for Playwright Chromium

**`k8s/`:**
- Purpose: All Kubernetes manifests for the `sastaspace` namespace
- Contains: One YAML file per service + namespace + ingress
- Deployed via: `kubectl apply -f k8s/` in CI or `make k8s-apply`

**`tests/` (Python):**
- Purpose: pytest test suite for the Python backend
- Contains: One test file per source module, named `test_{module}.py`
- Config: `pyproject.toml` `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`

**`web/src/__tests__/` and `web/e2e/`:**
- Purpose: Frontend unit tests (Vitest) and E2E tests (Playwright)
- Unit test config: `web/vitest.config.ts`
- E2E test config: `web/playwright.config.ts`; E2E runner image: `web/Dockerfile.test`

**`claude-code-api/`:**
- Purpose: The OpenAI-compatible API gateway that wraps Claude Code CLI
- Contains: Separate Python package with its own `pyproject.toml`, `.venv`, tests, Docker config
- Note: Has its own `.git` — treated as a submodule or embedded repo, not part of the main package

**`components/`:**
- Purpose: Reference library of marketing and UI component templates (design inspiration/copy-paste source)
- Contains: `marketing-blocks/` (heroes, features, pricing, etc.), `ui-components/` (atomic components)
- Note: These are template files, not imported into the application

**`sites/`:**
- Purpose: All runtime output — deployed HTML redesigns, site metadata, server state
- Generated: Yes (by application at runtime)
- Committed: No (gitignored)

**`cloudflared/`:**
- Purpose: Cloudflare Zero Trust tunnel configuration template
- Note: `config.yml` has placeholder values `<TUNNEL_UUID>` and `<HOSTNAME>` — must be populated manually

**`docs/`:**
- Purpose: Operational documentation
- Key file: `DEPLOYMENT.md` — complete step-by-step production server setup (OS, GPU drivers, microk8s, tunnel, firewall, etc.)

## Key File Locations

**Entry Points:**
- `sastaspace/server.py`: Module-level `app = make_app(...)` — used by uvicorn (`CMD` in `backend/Dockerfile`)
- `sastaspace/cli.py`: `main()` Click group — registered as `sastaspace` in `pyproject.toml`
- `web/src/app/page.tsx`: Next.js home route — renders `<AppFlow />`
- `web/src/app/[subdomain]/page.tsx`: Dynamic result route — renders `<ResultView />`
- `web/src/app/api/contact/route.ts`: Contact form API handler

**Configuration:**
- `pyproject.toml`: Python project metadata, dependencies, ruff config, pytest `asyncio_mode`
- `sastaspace/config.py`: `Settings` class — all backend runtime config with defaults
- `web/next.config.ts`: Next.js config (standalone output mode required for Docker)
- `web/tsconfig.json`: TypeScript config; `@/` path alias maps to `web/src/`
- `web/components.json`: shadcn/ui component config
- `.env.example`: Documents all required environment variables
- `docker-compose.yml`: Local dev/test service definitions
- `k8s/`: Production k8s manifests

**Core Logic:**
- `sastaspace/crawler.py`: `CrawlResult` dataclass + `crawl()` async function
- `sastaspace/redesigner.py`: `redesign()`, `SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`
- `sastaspace/deployer.py`: `deploy()`, `derive_subdomain()`, `load_registry()`, `save_registry()`
- `web/src/hooks/use-redesign.ts`: All frontend state machine logic
- `web/src/lib/sse-client.ts`: SSE stream parser (`streamRedesign` async generator)

**Testing:**
- `tests/test_redesigner.py`: HTML cleaning, validation, OpenAI client mocking
- `tests/test_deployer.py`: Filesystem logic, registry operations, subdomain derivation
- `tests/test_server.py`: FastAPI `TestClient` tests + `ensure_running()` subprocess tests
- `web/src/__tests__/`: Vitest unit tests for frontend utilities and hooks
- `web/e2e/`: Playwright E2E tests; configured against `BASE_URL` env var

## Naming Conventions

**Python files:**
- Package modules: `snake_case.py` matching their responsibility (`crawler.py`, `deployer.py`)
- Test files: `test_{module_name}.py` in `tests/` directory (not co-located with source)

**TypeScript/React files:**
- Components: `kebab-case.tsx` (`hero-section.tsx`, `result-view.tsx`)
- Hooks: `use-{name}.ts` (`use-redesign.ts`)
- Utilities: `kebab-case.ts` (`sse-client.ts`, `url-utils.ts`, `utils.ts`)
- Pages: `page.tsx` (Next.js App Router convention)
- API routes: `route.ts` (Next.js App Router convention)

**Directories:**
- `sites/{subdomain}`: kebab-case slug derived from URL hostname (`acme-com`, `acme-corp-co-uk`)
- Collision suffix: `{subdomain}--2`, `{subdomain}--3` (double-hyphen to avoid ambiguity with single-hyphen slugs)
- k8s files: `{service-name}.yaml` matching the Deployment name

**Python symbols:**
- Public functions: `snake_case` (`crawl`, `redesign`, `deploy`, `ensure_running`)
- Private helpers: `_snake_case` prefix (`_clean_html`, `_validate_html`, `_extract_text`, `_load_config`)
- Dataclasses: `PascalCase` (`CrawlResult`, `DeployResult`)
- Exceptions: `PascalCase` + `Error` suffix (`RedesignError`)
- Prompt constants: `UPPER_SNAKE_CASE` (`SYSTEM_PROMPT`, `USER_PROMPT_TEMPLATE`)

## Where to Add New Code

**New pipeline stage (e.g., HTML optimisation, image extraction):**
- Implementation: `sastaspace/{stage_name}.py` — expose one public function
- Tests: `tests/test_{stage_name}.py`
- Wire-up: Add call in `redesign_stream()` in `sastaspace/server.py` AND `redesign_cmd` in `sastaspace/cli.py`

**New FastAPI route:**
- Add `@app.{method}(...)` inside `make_app()` in `sastaspace/server.py`
- Tests: `tests/test_server.py` using the TestClient fixture pattern

**New CLI command:**
- Add `@main.command(...)` function in `sastaspace/cli.py`
- Tests: `tests/test_cli.py`

**New configuration setting:**
- Add field with default to `Settings` in `sastaspace/config.py`
- Env var name is field name uppercased (pydantic-settings convention)

**New React component:**
- Feature-specific: `web/src/components/{feature-name}/{component-name}.tsx`
- Shared primitive: `web/src/components/ui/{component-name}.tsx` (shadcn/ui style)

**New frontend hook:**
- Location: `web/src/hooks/use-{name}.ts`

**New frontend utility:**
- Location: `web/src/lib/{name}.ts`

**New page route:**
- App Router page: `web/src/app/{route}/page.tsx`
- API route: `web/src/app/api/{route}/route.ts`

**New k8s service:**
- Add `k8s/{service-name}.yaml` with Deployment + Service objects
- Add build + push step to `.github/workflows/deploy.yml`
- Add rollout restart + status wait steps to CI workflow

## Special Directories

**`sites/`:**
- Purpose: Runtime output — all redesigned HTML files plus server state
- Generated: Yes (by application)
- Committed: No (in `.gitignore`)
- In production: backed by k8s PVC `sites-pvc` (10Gi), mounted at `/data/sites` in backend pod

**`web/.next/`:**
- Purpose: Next.js build output
- Generated: Yes
- Committed: No

**`web/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning workflow artifacts (codebase analysis, milestones, phases)
- Generated: Yes (by GSD commands)
- Committed: Yes

**`claude-code-api/`:**
- Purpose: Embedded separate repository for the AI gateway
- Generated: No (checked in or submodule)
- Committed: Yes (has its own `.git`)

---

*Structure analysis: 2026-03-21*
