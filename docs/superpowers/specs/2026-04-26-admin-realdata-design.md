# Admin Panel — Real Data Wiring

**Date:** 2026-04-26  
**Status:** Approved  

---

## Problem

The admin panel at `admin.sastaspace.com` renders entirely mock data hardcoded in `apps/admin/src/lib/data.ts`. Comments cannot be moderated, TypeWars stats are fabricated, system metrics are fake, container statuses are made up, and logs are templates.

---

## Architecture

```
admin.sastaspace.com  (static Next.js, nginx)
  │
  ├── STDB reads ──► wss://stdb.sastaspace.com/sastaspace   (anonymous WebSocket)
  ├── STDB reads ──► wss://stdb.sastaspace.com/typewars     (anonymous WebSocket)
  │
  ├── Metrics / containers / logs ──► https://api.sastaspace.com  (new admin-api)
  │     GET  /system                  psutil, polled every 3 s
  │     GET  /containers              docker SDK, polled every 15 s
  │     GET  /logs/{container}        SSE — docker logs --follow
  │
  └── Write proxy ──────────────────► https://api.sastaspace.com
        POST   /stdb/comments/{id}/status   Google JWT → STDB owner call
        DELETE /stdb/comments/{id}          Google JWT → STDB owner call
```

**New infra:** one FastAPI container (`sastaspace-admin-api`, port 3160), one Cloudflare tunnel rule (`api.sastaspace.com → localhost:3160`), Docker socket bind-mounted read-only.

---

## Sub-project 1 — STDB live data

### Data sources

| Panel | Module | Tables subscribed |
|-------|--------|-------------------|
| Comments | `sastaspace` | `comment`, `user` |
| TypeWars | `typewars` | `player`, `region`, `global_war`, `battle_session` |

### Connection pattern

Both panels follow the same pattern already used in `apps/typewars`:

```ts
// shared hook: apps/admin/src/hooks/useStdb.ts
useStdb(module: 'sastaspace' | 'typewars', tables: string[])
  → { rows, loading, error }
```

- Connects anonymously (no token) — all tables are `public`
- `DbConnection.builder().withUri(STDB_URI).withDatabaseName(module)`
- Subscribes via `subscriptionBuilder().subscribe([...queries])`
- Tears down connection on component unmount

### Comments panel

- Replace `COMMENTS` mock with live `comment` rows
- Join `user` table on `comment.submitter` to get `display_name`
- Status filter, post filter, search all run client-side over the subscribed rows
- Moderation actions call the write proxy (see below)
- Optimistic UI: flip local row status immediately, revert on API error

### TypeWars panel

- Replace `LEGIONS` / `REGIONS` / `ACTIVE_BATTLES` mocks with live rows
- Legion standings aggregated client-side: group `player.season_damage` by `player.legion`
- Region map from `region` rows directly
- Active battles from `battle_session` where `active = true`
- Read-only — no write actions needed

### Write proxy

Comment moderation buttons send:

```
POST https://api.sastaspace.com/stdb/comments/{id}/status
Authorization: Bearer {google_id_token from localStorage}
Content-Type: application/json
{"status": "approved" | "flagged" | "rejected"}

DELETE https://api.sastaspace.com/stdb/comments/{id}
Authorization: Bearer {google_id_token}
```

Backend verifies JWT, checks email = `OWNER_EMAIL`, then calls `set_comment_status` / `delete_comment` as the STDB owner.

---

## Sub-project 2 — Admin API service (`services/admin-api/`)

### Structure

Mirrors `services/auth/` exactly:

```
services/admin-api/
  pyproject.toml
  Dockerfile
  .env               (gitignored — SPACETIME_TOKEN, OWNER_EMAIL, etc.)
  src/sastaspace_admin_api/
    __init__.py
    main.py           FastAPI app, all routes
    stdb.py           SpacetimeClient (copy from services/auth/)
    docker_client.py  Docker SDK wrapper
    system.py         psutil metrics
  tests/
    test_system.py
    test_containers.py
    test_logs.py
    test_stdb_proxy.py
```

### Endpoints

#### `GET /system`
Returns a single JSON object with current metrics. Client polls every 3 s.

```json
{
  "cpu": { "pct": 42.1, "cores": 16 },
  "mem": { "used_gb": 9.2, "total_gb": 32.0, "pct": 28.7, "swap_used_mb": 0, "swap_total_mb": 2048 },
  "disk": { "used_gb": 145, "total_gb": 500, "pct": 29.0, "mount": "/" },
  "gpu": { "pct": 38, "vram_used_mb": 4096, "vram_total_mb": 24576, "temp_c": 61, "model": "AMD Radeon RX 7900 XT" },
  "net": { "tx_bytes": 1234567, "rx_bytes": 9876543 },
  "uptime_s": 518400
}
```

GPU: attempt `nvidia-smi --query-gpu=...` subprocess; if unavailable attempt `rocm-smi`; if unavailable omit `gpu` key.

#### `GET /containers`
Returns array. Client polls every 15 s.

```json
[
  {
    "name": "sastaspace-stdb",
    "status": "running",
    "image": "clockworklabs/spacetime:latest",
    "started_at": "2026-04-20T10:12:00Z",
    "uptime_s": 518400,
    "mem_usage_mb": 124,
    "mem_limit_mb": 2048,
    "restart_count": 0
  }
]
```

Uses `docker.from_env().containers.list(all=True)` with `stats(stream=False)` for memory.

#### `GET /logs/{container}?tail=200&filter=`
SSE endpoint — `Content-Type: text/event-stream`.

- Validates `container` against the known container name list (whitelist, not arbitrary shell input).
- Runs `docker logs --follow --tail {tail} {container}` as an async subprocess.
- Each stdout/stderr line is emitted as:
  ```
  data: {"ts":"14:31:58.124","text":"INFO reducer ...","level":"info"}\n\n
  ```
- Level detection: regex for `ERROR`, `WARN`, `DEBUG` same as current `Logs.tsx`.
- Client uses `EventSource`; closes and reopens when user switches containers.
- Connection timeout: 10 min idle, then client reconnects automatically.

#### `POST /stdb/comments/{id}/status`
```json
{ "status": "approved" | "flagged" | "rejected" }
```
Auth: `Authorization: Bearer {google_id_token}`.

1. `google.oauth2.id_token.verify_oauth2_token(token, Request(), GOOGLE_CLIENT_ID)` — raises `ValueError` on invalid/expired.
2. Check `id_info['email'] == OWNER_EMAIL` — 403 otherwise.
3. `stdb_client.set_comment_status(id, status)` using `SPACETIME_TOKEN`.
4. Return `{"ok": true}`.

#### `DELETE /stdb/comments/{id}`
Same auth gate → `stdb_client.delete_comment(id)`.

#### `GET /healthz`
Returns `{"ok": true}`.

### Auth middleware

A single FastAPI dependency `require_owner(authorization: str = Header(...))`:
- Strips `Bearer ` prefix.
- Calls `verify_oauth2_token`.
- Checks email.
- Raises `HTTPException(403)` on any failure.

### Environment variables

```
PORT=3160
STDB_HTTP_URL=http://127.0.0.1:3100
STDB_MODULE=sastaspace
SPACETIME_TOKEN=<owner token>
GOOGLE_CLIENT_ID=867977197738-pdb93cs9rm2enujjfe13jsnd5jv67cqr.apps.googleusercontent.com
OWNER_EMAIL=mohitkhare582@gmail.com
ALLOWED_ORIGINS=https://admin.sastaspace.com
```

### CORS

`allow_origins=[ALLOWED_ORIGINS]` — only admin panel may call this service.

---

## Frontend changes summary

### New files
- `apps/admin/src/hooks/useStdb.ts` — shared STDB connection hook
- `apps/admin/src/hooks/usePoll.ts` — generic polling hook (`useInterval` + fetch)

### Changed files
- `apps/admin/src/lib/data.ts` — remove all mock data; keep only type definitions and `relTime`
- `apps/admin/src/components/panels/Comments.tsx` — wire to `useStdb` + write proxy fetch
- `apps/admin/src/components/panels/TypeWars.tsx` — wire to `useStdb` (typewars module)
- `apps/admin/src/components/panels/Server.tsx` — wire to `usePoll('/system', 3000)`
- `apps/admin/src/components/panels/Services.tsx` — wire to `usePoll('/containers', 15000)`
- `apps/admin/src/components/panels/Logs.tsx` — replace mock with `EventSource`
- `apps/admin/src/components/panels/Dashboard.tsx` — derives from live comments + containers
- `infra/admin/security_headers.conf` — add `https://api.sastaspace.com` to `connect-src`
- `apps/admin/next.config.mjs` — add `NEXT_PUBLIC_ADMIN_API_URL` and `NEXT_PUBLIC_STDB_URI`

### No changes
- Auth flow, Shell.tsx, routing, all other panels

---

## Infra changes

### docker-compose.yml — new service
```yaml
admin-api:
  build:
    context: ../services/admin-api
    dockerfile: Dockerfile
  image: sastaspace-admin-api:local
  container_name: sastaspace-admin-api
  restart: unless-stopped
  read_only: true
  tmpfs: [/tmp]
  cap_drop: [ALL]
  security_opt: ["no-new-privileges:true"]
  pids_limit: 256
  mem_limit: 256m
  user: "1000:1000"
  network_mode: host
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
  env_file:
    - ../services/admin-api/.env
  environment:
    - PORT=3160
    - STDB_HTTP_URL=http://127.0.0.1:3100
    - STDB_MODULE=sastaspace
    - ALLOWED_ORIGINS=https://admin.sastaspace.com
  depends_on:
    spacetime:
      condition: service_healthy
```

### Cloudflare tunnel
New ingress rule: `api.sastaspace.com → http://localhost:3160` (added via API, same as admin rule).

### CI/CD — new job in deploy.yml
```
admin-api:
  trigger: '^services/admin-api/'
  steps: ruff lint → pytest → docker build → rsync .env → docker compose up admin-api
```

---

## Testing

| Layer | What |
|-------|------|
| `test_system.py` | Mocks `psutil`; asserts response shape |
| `test_containers.py` | Mocks Docker SDK; asserts container list shape |
| `test_logs.py` | Mocks subprocess; asserts SSE line format |
| `test_stdb_proxy.py` | Mocks `verify_oauth2_token` + `SpacetimeClient`; tests 200/401/403 |

No E2E tests for admin-api (no Playwright). Frontend STDB wiring relies on STDB SDK's own test coverage.

---

## Implementation order

1. `services/admin-api/` — build and deploy the service first; smoke test endpoints from curl
2. `infra/` — Cloudflare tunnel rule + docker-compose entry
3. `apps/admin` hooks — `useStdb`, `usePoll`
4. Wire panels: Server → Services → Logs → Comments → TypeWars → Dashboard
5. CSP update + deploy admin frontend

---

## Out of scope

- Log search / filtering on the backend (done client-side in the existing Logs panel)
- Alerting / notifications when a container goes unhealthy
- Historical metrics storage (no time-series DB)
- TypeWars write actions from admin (read-only monitoring only)
