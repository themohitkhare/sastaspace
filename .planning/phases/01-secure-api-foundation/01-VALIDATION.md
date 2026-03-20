---
phase: 1
slug: secure-api-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-asyncio 0.24+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto" already set) |
| **Quick run command** | `uv run pytest tests/test_server.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_server.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | API-01..08 | unit/integration | `uv run pytest tests/test_server.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | API-01, API-02 | integration | `uv run pytest tests/test_server.py::test_redesign_sse_stream tests/test_server.py::test_sse_event_names -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | API-03 | unit | `uv run pytest tests/test_server.py::test_to_thread_wrapping -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | API-04 | integration | `uv run pytest tests/test_server.py::test_concurrency_cap -x` | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 1 | API-05 | unit | `uv run pytest tests/test_server.py::test_rate_limit -x` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 1 | API-06 | unit | `uv run pytest tests/test_server.py::test_nh3_sanitization -x` | ❌ W0 | ⬜ pending |
| 1-02-06 | 02 | 1 | API-07 | integration | `uv run pytest tests/test_server.py::test_cors_allows_configured_origin tests/test_server.py::test_cors_blocks_unknown_origin -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | API-08 | smoke | `uv run python -c "from fastapi.sse import EventSourceResponse"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_server.py` — stubs for all Phase 1 endpoint tests (rate limit, concurrency, SSE stream, CORS, sanitization)
- [ ] `tests/conftest.py` — shared fixtures (FastAPI TestClient, mock crawl/redesign/deploy functions)

*Framework already configured in pyproject.toml; pytest and pytest-asyncio already in dev dependencies. No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE events render in browser DevTools | API-01, API-02 | Requires live browser + running server | Open DevTools Network tab, POST to /redesign with valid URL, confirm event stream visible with named events |
| Cloudflare tunnel IP extraction | API-05 | CF-Connecting-IP header only present behind CF tunnel | Make request through CF tunnel, confirm rate limit triggers on 4th request from same public IP |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
