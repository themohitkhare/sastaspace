# Quick Task 260322-mg1: Replace Local Playwright with Browserless k8s Service

**Status:** Complete
**Date:** 2026-03-22
**Duration:** ~5 min (3 parallel agents)

## What Changed

### Task 1: Infrastructure + Config
- **k8s/browserless.yaml** — New Deployment + Service for `ghcr.io/browserless/chromium:latest` (port 3000, 2Gi memory limit, readiness probe on `/json/version`)
- **k8s/configmap.yaml** — Added `BROWSERLESS_URL: "ws://browserless:3000"`
- **docker-compose.yml** — Added `browserless` service (port 3100:3000, healthcheck)
- **sastaspace/config.py** — Added `browserless_url: str = "ws://localhost:3100"` to Settings

### Task 2: Crawler Refactor
- **sastaspace/crawler.py** — `_browser_context()` now accepts `browserless_url`, uses `connect_over_cdp()` when set, falls back to local `launch()`. Both `crawl()` and `enhanced_crawl()` skip `_ensure_chromium()` when remote. All extraction logic unchanged.

### Task 3: Dockerfile Slim-down
- **backend/Dockerfile** — Removed ~20 Chromium system deps + `playwright install chromium`. Kept only `curl` + `libmagic1`.
- **k8s/worker.yaml** — Reduced resources: 512Mi→256Mi requests, 2Gi→1Gi limits, 1000m→500m CPU

## Impact
- Backend Docker image: ~1.5GB → ~200MB (estimate — Chromium + deps removed)
- Worker pod memory: 2Gi → 1Gi limit
- Browser execution isolated in dedicated Browserless pod with pooling (CONCURRENT=5)
- Local dev: falls back to local Playwright if BROWSERLESS_URL not set

## Commits
- `35a6f0f4` — Browserless k8s service, docker-compose, config
- `2b4e8813` — Crawler CDP WebSocket connection
- `603affd7` — Strip Chromium from Dockerfile, reduce worker resources
