---
phase: 02
slug: next-js-scaffold-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python) + jest/vitest (Next.js) |
| **Config file** | `pyproject.toml` (pytest) / `package.json` (jest) |
| **Quick run command** | `uv run pytest tests/ -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -v && cd frontend && npm test -- --passWithNoTests` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -v && cd frontend && npm test -- --passWithNoTests`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | FRONT-01 | integration | `test -d frontend && cd frontend && node -e "require('./package.json')"` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | FRONT-02 | e2e | `cd frontend && npm run build -- --dry-run 2>/dev/null || true` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | FRONT-03 | integration | `make dev --dry-run 2>&1 | grep -q "next\|fastapi"` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | FRONT-04 | config | `grep -q "localhost:8080" .cloudflared/config.yml` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/` — Next.js app scaffold created via `create-next-app`
- [ ] `frontend/package.json` — shadcn/ui, Tailwind v4, tw-animate-css installed
- [ ] `Makefile` — `dev` target that starts both servers
- [ ] `.cloudflared/config.yml` — Cloudflare tunnel config with routing rules

*Wave 0 creates the scaffold structure before tests can run against it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `make dev` visually starts both servers | FRONT-03 | Requires terminal observation | Run `make dev`, verify both "Ready" messages appear |
| Next.js renders at localhost:3000 | FRONT-02 | Browser render required | Open localhost:3000, verify shadcn/ui component renders |
| Cloudflare tunnel routes /api/* to FastAPI | FRONT-04 | Requires active tunnel + credentials | Run `cloudflared tunnel run`, curl /api/health via tunnel URL |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
