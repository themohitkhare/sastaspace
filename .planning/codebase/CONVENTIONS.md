# Coding Conventions

**Analysis Date:** 2026-03-21

## Naming Patterns

**TypeScript/React files:**
- `kebab-case.tsx` for all component files: `url-input-form.tsx`, `contact-form.tsx`, `progress-view.tsx`
- `kebab-case.ts` for all lib/hook files: `sse-client.ts`, `url-utils.ts`, `use-redesign.ts`
- Hooks prefixed with `use-`: `use-redesign.ts`
- API routes follow Next.js App Router convention: `src/app/api/contact/route.ts`

**Python files:**
- `snake_case.py` for all source modules: `crawler.py`, `redesigner.py`, `deployer.py`, `server.py`
- Test files mirror source: `test_crawler.py` mirrors `crawler.py`, `test_server.py` mirrors `server.py`

**TypeScript functions:**
- Named exports for components: `export function UrlInputForm(...)`, `export function ContactForm(...)`
- Named exports for hooks: `export function useRedesign()`
- Named exports for lib functions: `export function validateUrl(...)`, `export function streamRedesign(...)`
- camelCase for all functions and variables
- SCREAMING_SNAKE_CASE for module-level constants: `STEPS`, `STEP_INTERMEDIATE_VALUES`, `STEP_LABELS`

**Python functions:**
- `snake_case` for all functions: `make_app`, `get_client_ip`, `derive_subdomain`
- Module-level constants in SCREAMING_SNAKE_CASE: `SAMPLE_HTML` in tests
- Private/internal helpers prefixed with underscore: `_ensure_chromium`, `_extract_images`, `_extract_nav_links`

**TypeScript types:**
- PascalCase for interfaces and type aliases: `UrlInputFormProps`, `RedesignState`, `StepState`, `SSEEvent`
- Discriminated unions for state machines: `RedesignState` uses `status` as the discriminant
- `type FormStatus = "idle" | "submitting" | "success" | "error"` — string literal unions over enums
- Interface props named `{ComponentName}Props`: `ContactFormProps`, `UrlInputFormProps`, `ProgressViewProps`

**Python types:**
- Pydantic models for request schemas: `class RedesignRequest(BaseModel):`
- Dataclasses for results: `CrawlResult`, `DeployResult`
- pydantic-settings for config: `class Settings(BaseSettings):`

**k8s and Docker naming:**
- Image names: `sastaspace-{service}` (e.g., `sastaspace-frontend`, `sastaspace-backend`)
- k8s resource names match service role: `frontend`, `backend`, `claude-code-api`
- k8s namespace: `sastaspace` (all resources scoped to this namespace)

## Code Style

**TypeScript formatting:**
- Prettier is not separately configured; ESLint handles style via `eslint-config-next`
- Config: `web/eslint.config.mjs` — extends `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- Flat config format (ESLint v9): `defineConfig([...nextVitals, ...nextTs])`

**Python formatting:**
- Ruff for both linting and formatting: `[tool.ruff]` in `pyproject.toml`
- Line length: 100 characters
- Target: Python 3.11+
- Lint rules selected: `E` (pycodestyle), `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- Run: `uv run ruff check sastaspace/ tests/` and `uv run ruff format --check sastaspace/ tests/`

## Import Organization

**TypeScript (Next.js):**
1. React and framework imports: `import { useState } from "react"`, `import { useRouter } from "next/navigation"`
2. Third-party library imports: `import { motion } from "motion/react"`, `import { Globe } from "lucide-react"`
3. Internal path-aliased imports using `@/`: `import { validateUrl } from "@/lib/url-utils"`, `import { Button } from "@/components/ui/button"`
- Path alias `@` maps to `src/` — configured in `web/vitest.config.ts` and Next.js

**Python:**
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

**TypeScript API routes:**
- Wrap entire handler body in `try/catch`
- Return `Response.json({ error: "..." }, { status: N })` for errors
- Return `Response.json({ ok: true })` for success
- Status codes: `400` for validation failures, `500` for unexpected/infrastructure errors
- Silent honeypot rejection: return `200 ok:true` to not reveal detection (not a 4xx)

```typescript
// Pattern from src/app/api/contact/route.ts
export async function POST(request: NextRequest) {
  try {
    // ...validation...
    if (!name?.trim()) {
      return Response.json({ error: "All fields are required" }, { status: 400 });
    }
    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
```

**TypeScript client-side:**
- `try/catch` around async operations; catch block sets error state
- Empty catch blocks are used when aborting is intentional: `catch { if (controller.signal.aborted) return; }`
- Malformed SSE events silently skipped: `catch { // Skip malformed events silently }`
- Error messages shown to users are human-readable strings, not raw error objects

**Python:**
- FastAPI raises `HTTPException` for route-level errors
- Module-level functions return structured result objects; errors surfaced via SSE `error` events
- `from __future__ import annotations` used in server.py for forward references

## State Management Patterns

**React state machines:**
- Complex component state modeled as discriminated union types
- `useRedesign` hook in `src/hooks/use-redesign.ts` manages the full app flow via `RedesignState`
- State transitions are explicit — each event handler calls `setState` with a complete new state object
- `useRef` used for mutable values that don't trigger re-render: `abortRef`, `debounceRef`
- `useCallback` used consistently for handlers passed as props

**Form state:**
- Individual `useState` calls per field (not a single form object): `name`, `email`, `message`
- Validation errors in `Record<string, string>` map: `errors.name`, `errors.email`
- Errors cleared on field change (not on submit): inline `setErrors((prev) => { delete n.fieldName; return n; })`
- `noValidate` on all `<form>` elements — custom inline validation only, no browser tooltips

## Logging

**TypeScript:**
- `console.error` used for server-side errors: `console.error("Resend error:", error)`
- No structured logging library in the frontend

**Python:**
- No logging framework detected in explored files; uses print-style output in CLI (`rich` library present)

## Comments

**TypeScript:**
- Inline comments for non-obvious decisions: `// Honeypot — return success to not reveal detection (per D-10)`
- Reference codes like `D-09`, `D-10`, `FLAG-01` used to cross-reference decision documents
- `// eslint-disable-next-line` comments used sparingly for intentional rule suppression

**Python:**
- Module-level comment with file path: `# sastaspace/server.py`, `# tests/test_server.py`
- Docstrings on factory/helper functions: `"""Create the FastAPI app bound to a specific sites directory."""`
- Section separator comments in tests: `# --- CrawlResult dataclass tests ---`

## Deployment Conventions

**Dockerfile patterns:**
- Frontend (`web/Dockerfile`): multi-stage build — `builder` stage on `node:22-alpine`, `runner` stage on `node:22-alpine`
  - Dependency files copied first to maximize Docker layer cache: `COPY package.json package-lock.json ./` before `COPY . .`
  - Next.js standalone output used: copies `.next/standalone`, `.next/static`, `public/`
  - `ENV HOSTNAME=0.0.0.0` and `ENV PORT=3000` set in runner stage
  - Healthcheck via `wget --spider`
- Backend (`backend/Dockerfile`): single-stage on `python:3.11-slim`
  - `pip install --no-cache-dir .` — installs from `pyproject.toml`
  - Playwright Chromium installed inside container: `playwright install chromium`
  - Healthcheck via `curl -f http://localhost:8080/`
- Test runner (`web/Dockerfile.test`): based on `mcr.microsoft.com/playwright:v1.52.0-noble`
  - Copies only test files and config (not all source): `COPY playwright.config.ts`, `COPY e2e/`, `COPY tsconfig.json`
  - `ENV BASE_URL=http://frontend:3000` — points to Docker network service name

**Image tagging:**
- Always tag both `:latest` and `:{github.sha}` in CI: enables rollback
- Local registry: `localhost:32000/sastaspace-{service}`
- Image name pattern: `sastaspace-{service}` (frontend, backend, claude-code-api)

**k8s manifest conventions (`k8s/` directory):**
- All resources in `sastaspace` namespace — `namespace.yaml` applied before other manifests
- Each service has both `Deployment` and `Service` in the same YAML file (separated by `---`)
- `PersistentVolumeClaim` co-located with the Deployment that uses it: `backend.yaml` contains the PVC
- Resource limits on all containers: `requests: memory 256Mi / cpu 100m`, `limits: memory 1Gi / cpu 500m`
- `readinessProbe` on every deployment via `httpGet` — no livenessProbe
- Secrets injected via `secretRef` (not env vars inline): `envFrom: - secretRef: name: sastaspace-env`
- Non-secret env vars set inline under `env:` in the manifest

**CI/CD (`deploy.yml`):**
- Self-hosted runner: `runs-on: [self-hosted, linux, amd64]`
- Trigger: push to `main` branch or `workflow_dispatch`
- Job timeout: 30 minutes
- Deploy order: build all images → push to registry → `kubectl apply` manifests → rolling restart → wait for rollout → verify
- `namespace.yaml` applied explicitly before `k8s/` to avoid namespace-not-found errors
- Rollout wait with `--timeout=300s` (5 minutes per deployment)

**docker-compose conventions:**
- `env_file: path: .env / required: false` — `.env` is optional, no hard failure if absent
- Health checks on every service mirror Dockerfile HEALTHCHECK
- `depends_on: condition: service_healthy` enforces startup ordering
- `tests` service in `profiles: [test]` — not started by default, only with `--profile test`
- Named volumes for persistence: `sites_data` mounted at `/data/sites`

**Makefile conventions:**
- `make ci` = `lint` + `test` — single command for CI validation
- `make deploy` = rsync to remote + build images on remote + push + k8s apply + rolling restart
- Deployment targets use SSH to remote host (not local Docker daemon)
- `.PHONY` declared for all non-file targets
