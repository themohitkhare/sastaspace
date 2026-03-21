# Phase 5: Docker Infrastructure - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Containerize the full SastaSpace stack (FastAPI backend with Playwright, Next.js frontend, claude-code-api gateway) behind a single `docker compose up` command with proper networking, persistence, and health monitoring.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

All implementation choices are at Claude's discretion — pure infrastructure phase.

Key constraints:
- Backend needs Playwright + Chromium installed in container (Python 3.11+ base)
- Frontend builds Next.js in production mode (`next build` + `next start`)
- claude-code-api gateway: use the image from https://github.com/codingworkflow/claude-code-api
- Sites directory must be a Docker volume for persistence
- Single `.env` file for all configuration
- Health checks on all three services
- Docker network for inter-container communication

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Makefile` has `dev-api` and `dev-web` targets showing how services start
- `sastaspace/config.py` — Settings class with `claude_code_api_url`, `sites_dir`, `server_port`, `cors_origins`
- `web/.env.example` — frontend env var documentation

### Established Patterns
- Backend: `uvicorn sastaspace.server:app --host 127.0.0.1 --port 8080`
- Frontend: `next dev` / `next build` + `next start`
- Backend reads `SASTASPACE_SITES_DIR` env var for sites directory
- CORS origins configurable via `CORS_ORIGINS` env var

### Integration Points
- Frontend → Backend: `NEXT_PUBLIC_BACKEND_URL` (default `http://localhost:8080`)
- Backend → claude-code-api: `CLAUDE_CODE_API_URL` (default `http://localhost:8000/v1`)
- In Docker: services communicate via container names on shared network

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
