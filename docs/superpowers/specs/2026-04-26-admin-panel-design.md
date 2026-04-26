# admin.sastaspace.com — Design Spec

**Date:** 2026-04-26  
**Status:** Approved for implementation planning  
**Scope:** Standalone admin panel consolidating all sastaspace project management into one interface.

---

## Problem Statement

- `notes.sastaspace.com/admin/comments` is broken in production — `NEXT_PUBLIC_OWNER_EMAIL` is never passed to the notes CI build, so `isOwnerSignedIn()` always returns false.
- There is no single place to manage comments, monitor server health, check container status, or observe the TypeWars game state.
- As more projects ship, this gap will grow.

---

## Goals

- One URL (`admin.sastaspace.com`) for all owner-facing management tasks.
- Comment moderation, server metrics, container health, game state, and log viewing in one panel.
- Reuse existing auth infrastructure (magic-link via `auth.sastaspace.com`).
- Follow existing codebase patterns exactly (Next.js app + FastAPI service).

---

## Architecture

Two new additions to the monorepo:

### `apps/admin/`
- Next.js 16, static export (`output: 'export'`)
- Served by nginx at `127.0.0.1:3150`
- Routed via Cloudflare Tunnel: `admin.sastaspace.com` → `localhost:3150`
- Data sources:
  - **SpacetimeDB** (`wss://stdb.sastaspace.com`) via WebSocket subscription — comments, game state, projects, presence
  - **Metrics service** (`/api/*` proxied through the admin nginx config to `http://127.0.0.1:3160`) — system vitals, container health, logs. The admin `nginx.conf` strips the `/api` prefix and forwards to the metrics FastAPI service on the host loopback.

### `services/metrics/`
- FastAPI + uvicorn, same layout as `services/auth/`
- Port `3160`, `network_mode: host`
- Mounts `/var/run/docker.sock` (read-write, needed for restart)
- Provides: system vitals, container stats, log tailing, container restart

---

## Authentication

Reuses `auth.sastaspace.com` magic-link flow with a new callback URL.

**Flow:**
1. App loads → check `localStorage` key `sastaspace.auth.v1`
2. No session → Sign In screen with email input → POST to `auth.sastaspace.com/auth/request`
3. User clicks magic link → auth service redirects to `https://admin.sastaspace.com/auth/callback#token=...&email=...`
4. Admin app reads URL fragment, saves to localStorage, verifies `email === NEXT_PUBLIC_ADMIN_OWNER_EMAIL`
5. Wrong email → Access Denied screen (shows signed-in email, Sign Out button)
6. Correct email → admin UI renders

**Auth service change required:** add `ADMIN_CALLBACK=https://admin.sastaspace.com/auth/callback` env var and a new `/auth/verify` redirect path for it (or reuse existing callback mechanism with a query param to distinguish).

**Env vars for admin app (baked at build time):**
- `NEXT_PUBLIC_ADMIN_OWNER_EMAIL=mohitkhare582@gmail.com`
- `NEXT_PUBLIC_STDB_URI=wss://stdb.sastaspace.com`
- `NEXT_PUBLIC_STDB_MODULE=sastaspace`
- `NEXT_PUBLIC_METRICS_TOKEN={secret}` — bearer token for metrics service API

---

## Navigation & Shell Layout

### Left Sidebar (240px, collapsible to 56px icon-only)

**Top:** sastaspace brandmark + "admin" label

**Nav items** (icon + label, active state highlighted):
1. Dashboard
2. Comments — yellow badge showing pending+flagged count (hidden when 0)
3. Server
4. Services — red dot when any container is unhealthy
5. TypeWars
6. Logs

**Bottom:**
- Signed-in email (small, truncated)
- Sign Out button

### Top Bar (56px, sticky)
- Page title (updates per section)
- "Updated Xs ago" — time since last successful data fetch
- Manual refresh icon button

### Main Content
Full remaining height, scrollable, 24px padding.

---

## Routes

| URL | Screen |
|-----|--------|
| `/` | Dashboard |
| `/comments` | Comment moderation |
| `/server` | System metrics |
| `/services` | Container status |
| `/game` | TypeWars overview |
| `/logs` | Log viewer |
| `/auth/callback` | Auth redirect handler (no UI, just processes fragment) |

---

## Screen 1 — Dashboard (`/`)

Auto-refreshes every 30 seconds.

### Vital Cards (top row, 4 equal-width cards)

**Pending Comments**
- Value: count of comments with status `pending` or `flagged`
- Secondary: "X submitted in the last hour" (derived from `createdAt`)
- Colour: green if 0, yellow if >0
- Click → `/comments?status=pending`
- Source: SpacetimeDB SQL on `comment` table

**CPU**
- Value: current usage %
- Secondary: 10-point sparkline (last 5 minutes)
- Colour: green <50%, yellow 50–80%, red >80%
- Source: `GET /system`

**Memory**
- Value: "X.X / Y GB"
- Secondary: thin percentage bar
- Colour: green <70%, yellow 70–85%, red >85%
- Source: `GET /system`

**Services**
- Value: "6 / 6 healthy" or "5 / 6 healthy"
- Colour: green if all healthy, red if any not
- Click → `/services`
- Source: `GET /containers`

### Two-Column Section (below cards)

**Left — Recent Comments**
- Heading: "Recent comments"
- 5 most recent comments (any status), ordered by `created_at` desc
- Each row: status badge + author + post slug (linked) + first 60 chars of body + relative time
- "View all →" → `/comments`
- Source: SpacetimeDB

**Right — Service Status**
- Heading: "Services"
- All 6 containers, compact list
- Each row: coloured dot + display name + uptime string
- Click any → `/services`
- Source: `GET /containers`

---

## Screen 2 — Comments (`/comments`)

Real-time via SpacetimeDB WebSocket subscription (same `subscribeAdminComments` pattern as existing `admin.ts`).

### Filter Bar (sticky)

- **Status tabs:** All | Pending | Flagged | Approved | Rejected — each shows count in parens. Default: Pending.
- **Post filter:** dropdown — "All posts" | individual slugs derived from data
- **Search:** "Filter by content…" — client-side, filters on body text

### Comment Cards

One card per comment. Not a table — cards give room for full body text.

**Top line:** `[status badge] [author] · [post slug, linked] · [relative time, full datetime on hover]`

**Body:** full comment text, no truncation

**Action row:**
- **Approve** (green) — if status ≠ approved
- **Flag** (orange) — if status ≠ flagged
- **Reject** (grey) — if status ≠ rejected
- **Delete** (red, always) — triggers confirm modal

While action is in-flight: all buttons on that card disabled, spinner shown.

**Status badge colours:** pending=yellow, flagged=orange, approved=green, rejected=grey

### Delete Confirm Modal
- Title: "Delete this comment?"
- Body: author name + first 80 chars of comment body
- Buttons: Cancel (ghost) | Delete (red solid)

### Empty States
- Pending tab, 0 items: "Queue is clear. Nothing needs review."
- All tab, no data: "No comments submitted yet."
- Search, no matches: `No comments matching "${query}"`

---

## Screen 3 — Server (`/server`)

Polls `GET /system` every 15 seconds.

### Vital Cards (top row, 4 cards)

**CPU** — current %, colour-coded. Secondary: core count.

**Memory** — "X.X / Y GB". Percentage bar. Secondary: "Swap: X / Y MB". Colour-coded.

**Disk** — "X / Y GB". Percentage bar. Secondary: mount point. Colour-coded.

**GPU** — "X% utilisation". Secondary: "VRAM: X / Y MB" and "Temp: Z°C". Source: `rocm-smi`. If unavailable → "GPU data unavailable" in grey (no error state).

Colour thresholds: green=healthy, yellow=watch, red=act.
- CPU: <50% green, 50–80% yellow, >80% red
- Memory: <70% green, 70–85% yellow, >85% red
- Disk: <80% green, 80–90% yellow, >90% red

### Time-Series Charts (three stacked, full width)

60-minute window, 1-minute resolution, 60 data points stored in metrics service memory.

1. **CPU %** — line chart, Y-axis 0–100%
2. **Memory (GB)** — line chart, Y-axis 0 to total GB
3. **Network I/O** — two-series area chart, TX and RX in Mbps

Each chart shows "Updated Xs ago". All charts refresh together on manual refresh.

---

## Screen 4 — Services (`/services`)

Polls `GET /containers` every 15 seconds.

### Container Cards (grid: 3 cols wide, 2 medium, 1 narrow)

**Each card:**
- Header: display name + status badge
- Status badge: Running (green) | Unhealthy (red) | Stopped (grey) | Starting (yellow, pulse)
- Uptime: "Up 3h 42m" or "Stopped"
- Memory: "48 MB used"
- Image: secondary text
- Footer: **Logs →** button (→ `/logs?service={name}`) | **Restart** button (→ confirm modal)

**Container → Display name:**
| Container | Display |
|-----------|---------|
| `sastaspace-stdb` | SpacetimeDB |
| `sastaspace-auth` | Auth Service |
| `sastaspace-notes` | Notes |
| `sastaspace-landing` | Landing |
| `sastaspace-typewars` | TypeWars |
| `sastaspace-moderator` | Moderator |

### Restart Confirm Modal
- Title: "Restart {display name}?"
- Body: "The service will be briefly unavailable."
- Cancel | Restart (red)

### Error Banner
If metrics service unreachable → yellow top banner: "Metrics service unreachable — container data unavailable."

---

## Screen 5 — TypeWars (`/game`)

Real-time SpacetimeDB subscription on: `GlobalWar`, `Region`, `Player`, `BattleSession`, `Word` tables.

### War Status Banner (full width, coloured)
- Active war (green): "War active · started X hours ago · Y active battles"
  - Total damage dealt this war (sum across all regions)
- No active war (grey): "No active war."

### Three-Column Section

**Left — Legion Standings**
Table columns: Legion (colour-coded chip) | Regions held | Total damage dealt | Active players

Sorted by regions held desc. Legion names sourced from `apps/typewars/src/lib/legions.ts`.

**Middle — Region Map**
Grid of all seeded regions. Each cell:
- Region name
- Controlling legion — cell background tinted in that legion's colour
- HP bar (current / max)
- Contested: if 2+ legions dealt damage in the last tick → striped or glowing border

**Right — Live Activity Feed**
Last 20 game events, newest at top:
- Word submitted: "[Player] typed '[word]' in [Region] for X damage"
- Battle started/ended: "Battle started/ended in [Region]"
- Region captured: "[Region] captured by [Legion]"

### Active Battles Table (full width, below columns)
Columns: Player | Legion | Region | Session start (relative) | Words typed | Damage dealt
Empty state: "No active battles."

---

## Screen 6 — Logs (`/logs`)

Polls `GET /logs/{container}?tail=N` every 5 seconds.

### Two-Panel Layout

**Left panel (220px, fixed):**
- Heading: "Service"
- List of all 6 containers: coloured status dot + display name
- Active selection highlighted
- URL param: `/logs?service={container}` pre-selects (linked from Services screen)

**Right panel (fills remaining width):**

Toolbar:
- Service name as heading
- Lines selector: 50 | 200 | 500 — changing value re-fetches immediately
- Auto-scroll toggle (on by default)
- Filter input: "Filter lines…" — hides non-matching lines, highlights matches in yellow
- Clear button (clears displayed output only, does not affect actual logs)

Log output area:
- Monospace font, dark background, light text
- Each line: `[timestamp]  [content]`
- Line colours:
  - Contains ERROR → red
  - Contains WARN → yellow/amber
  - Contains DEBUG → dimmed grey
  - Otherwise → default
- Auto-scroll: scrolls to bottom on new lines when enabled
- When auto-scroll is off and new lines arrive → "↓ New lines" pill at bottom; clicking it scrolls down and re-enables auto-scroll

Empty state (no service selected): "Select a service on the left to view its logs."

---

## New Service — `services/metrics/`

### File Structure
```
services/metrics/
  src/sastaspace_metrics/
    __init__.py
    main.py       — FastAPI app, routes, auth middleware
    system.py     — reads /proc/meminfo, /proc/stat, df output, rocm-smi
    docker.py     — Docker SDK wrapper: container info, logs, restart
  tests/
    test_main.py
    test_system.py
    test_docker.py
  Dockerfile
  pyproject.toml
```

### Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/healthz` | None | Health check |
| GET | `/system` | Bearer | Current CPU, mem, swap, disk, GPU |
| GET | `/system/history` | Bearer | Last 60 data points (1/min) for charts |
| GET | `/containers` | Bearer | All containers: status, uptime, mem |
| GET | `/logs/{container}?tail=100` | Bearer | Last N log lines |
| POST | `/containers/{container}/restart` | Bearer | Restart a container |

### Auth
All routes except `/healthz` require `Authorization: Bearer {ADMIN_TOKEN}`. Token is an env var set at deploy time, same pattern as `E2E_TEST_SECRET` in the auth service.

### System metrics sources
- CPU: `/proc/stat` — compute % from idle/total across ticks
- Memory: `/proc/meminfo` — MemTotal, MemAvailable, SwapTotal, SwapFree
- Disk: `shutil.disk_usage('/')` — total, used, free
- GPU: subprocess call to `rocm-smi --showuse --showmeminfo vram --showtemp --json` — if command fails, return `null` for GPU fields

### Docker access
Uses the `docker` Python SDK, socket at `/var/run/docker.sock`. Mounted read-write (needed for restart).

History buffer: a module-level deque of max 60 entries, appended once per minute via a background task started in the FastAPI lifespan. Resets on restart — acceptable.

### Deployment config additions

**`infra/docker-compose.yml`:**
```yaml
admin:
  image: nginx:1.29-alpine
  container_name: sastaspace-admin
  ports:
    - "127.0.0.1:3150:80"
  volumes:
    - ./admin/out:/usr/share/nginx/html:ro
    - ./admin/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - ./landing/security_headers.conf:/etc/nginx/conf.d/security_headers.conf:ro
  # same cap_drop, security_opt, etc. as other nginx services

metrics:
  build:
    context: ../services/metrics
    dockerfile: Dockerfile
  image: sastaspace-metrics:local
  container_name: sastaspace-metrics
  restart: unless-stopped
  network_mode: host   # shares host network; binds directly to 127.0.0.1:3160
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  env_file:
    - ../services/metrics/.env
  environment:
    - PORT=3160
```

Note: `network_mode: host` means `ports:` is ignored — the service binds directly to the host loopback at port 3160. No port mapping needed.

**Cloudflare Tunnel:** add ingress `admin.sastaspace.com` → `localhost:3150`

**`deploy.yml` additions:**
- Change detection: `^(apps/admin|infra/admin/)` for admin app; `^services/metrics/` for metrics service
- Two new jobs: `admin` and `metrics` — modelled after the existing `auth` job
- `TYPEWARS_OUT_DIR`-style var: `ADMIN_OUT_DIR=/home/mkhare/sastaspace/infra/admin/out`

**Auth service change:** new `ADMIN_CALLBACK` env var; the `/auth/verify` endpoint redirects to it when a query param `app=admin` is present (or a dedicated route — implementation detail for the plan stage).

---

## What's Broken Today (Root Cause)

`NEXT_PUBLIC_OWNER_EMAIL` is baked at Next.js build time. It is never set in the notes CI job, so it compiles to `undefined`. `isOwnerSignedIn()` returns false for every user. Moving admin to its own app with correctly set env vars fixes this cleanly without touching the notes app.

---

## Out of Scope (v1)

- Bulk comment actions (select all, approve all) — add later
- Push notifications for new pending comments — add later
- Admin audit log (who did what when) — add later
- Multi-owner support — not needed
- Mobile layout — desktop-first; basic responsiveness only
