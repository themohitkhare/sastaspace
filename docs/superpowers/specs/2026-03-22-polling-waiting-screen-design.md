# Polling + Engaged Waiting Screen Design

**Date:** 2026-03-22
**Status:** Approved

---

## Problem

The current SSE streaming transport causes false error screens. When a network blip interrupts the stream during a 2–3 minute job, the frontend catches the exception and shows "Something went wrong" — even though the worker is still running and will complete successfully. Users give up and leave.

Root cause: any exception in the SSE `for await` loop sets `status: "error"` with no retry logic.

---

## Goal

Replace SSE streaming with HTTP polling so that network interruptions are invisible to the user. Redesign the waiting screen to keep users engaged during the 2–3 minute wait using timer-driven copy and components from `@components/`.

---

## Architecture

### Transport: SSE → Polling

**Remove:** `streamJobStatus()` in `web/src/lib/sse-client.ts`
**Add:** `pollJobStatus(jobId, signal?) → AsyncGenerator<JobStatus>` — polls `GET /jobs/{id}` every 3s

**Error handling change (the core fix):**
- Before: any exception → `status: "error"` screen
- After: network error → silent retry next poll. Error screen only on:
  1. `job.status === "failed"` (worker explicitly failed)
  2. 5 consecutive unreachable polls (backend truly down)
  3. Job age > 15 minutes (stuck guard)

**Poll interval:**
- `queued / crawling / redesigning`: every 3s
- `deploying`: every 1s (near done, faster feedback)
- `done / failed`: stop polling

**URL persistence:** After `POST /redesign` returns `{ job_id }`, `use-redesign.ts` calls `router.replace(\`?job=\${jobId}\`)` client-side before starting the poll loop. On mount, if `?job=` query param is already present (e.g. user refreshed), skip the `POST` and start polling immediately with the existing job ID.

### Backend: Enrich Job Status with Crawl Data

Store `site_colors: list[str]` and `site_title: str` on the job document after crawl completes. Worker already has this data — just needs `update_job()` to persist it.

`GET /jobs/{id}` already returns the full job document. No new endpoint needed. Frontend reads `job.site_colors` once available (after ~10–25s) and renders color swatches.

---

## Frontend Changes

### `web/src/lib/sse-client.ts`
- Remove `streamJobStatus()`
- Add `pollJobStatus(jobId, signal?): AsyncGenerator<JobStatus>` using a `while(true) { fetch; yield; sleep }` loop — **not** `setInterval`. The implementation polls `GET /jobs/{id}`, yields the result, then awaits `sleep(intervalMs)` before the next iteration. Loop exits when `signal?.aborted` is true, or status is `done`/`failed`.
- `JobStatus` type: `{ id, status, progress, message, subdomain?, error?, site_colors?, site_title? }`

### `web/src/hooks/use-redesign.ts`
- Replace `for await (const event of streamJobStatus(...))` with `for await (const status of pollJobStatus(...))`
- Map `job.status` → progress state:
  - `queued` → step: `crawling`, progress: 5%
  - `crawling` → step: `crawling`, progress: 25%
  - `redesigning` → step: `redesigning`, progress: 65%
  - `deploying` → step: `deploying`, progress: 90%
  - `done` → transition to done state, navigate to `/{subdomain}`
  - `failed` → set error state with `job.error`
- Store `siteColors` and `siteTitle` from job in progress state
- Retry counter: increment on network error, reset on success. Show error only at 5

### `web/src/components/progress/progress-view.tsx`
Full redesign. See UI section below.

### `sastaspace/jobs.py`
- After crawl completes, call `update_job(job_id, site_colors=result.colors[:5], site_title=result.title)`

---

## UI Design

### Layout (full-screen, centered)

```
┌──────────────[aurora background]──────────────┐
│  ████████████░░░░░░░  [linear progress bar]   │
│                                                │
│           [luma-spin orbital spinner]          │
│                                                │
│      Redesigning mrbrownbakery.com             │
│      [domain in accent, subtitle muted]        │
│                                                │
│  ● Analyzing  ●● Designing  ○ Building        │
│  [3 step pills, active = filled accent]        │
│                                                │
│  ╭──────────────────────────────────────╮     │
│  │  Analyzing your conversion funnel…   │     │
│  │  [rotates every 4s, fade transition] │     │
│  ╰──────────────────────────────────────╯     │
│                                                │
│    ■ ■ ■ ■ ■   [color swatches, fade in]      │
│    [visible once site_colors available]        │
│                                                │
│       12,847 redesigns completed               │
│       [animated counter, increments on mount]  │
└────────────────────────────────────────────────┘
```

### Components from `@components/`

| Component | Source file | Usage |
|-----------|-------------|-------|
| Aurora background | `marketing-blocks/backgrounds/aceternity__aurora-background.json` | Full-screen background |
| Luma spinner | `ui-components/spinner-loaders/theritikk__luma-spin.json` | Center spinner |
| Linear progress | `ui-components/spinner-loaders/sean0205__progress.json` | Top progress bar |
| Animated counter | `marketing-blocks/texts/preetsuthar17__animated-counter.json` | "X redesigns" stat (cosmetic — seeded at 12,847, increments locally on mount; no backend endpoint) |

### Insight Card Copy

Two tracks, 8 messages each, cycle every 4s with fade transition. Domain name interpolated into early messages.

**Track 1 — Analysis (shown during `crawling` / early `redesigning`):**
1. "Visiting {domain}…"
2. "Downloading {domain} assets and images"
3. "Reading your business copy"
4. "Identifying your target audience"
5. "Mapping your customer journey"
6. "Analyzing your conversion funnel"
7. "Benchmarking against your industry"
8. "Understanding what makes you unique"

**Track 2 — Build (shown during `redesigning` / `deploying`):**
1. "Designing a layout built for conversions"
2. "Writing copy that speaks to your customers"
3. "Crafting your hero for maximum impact"
4. "Selecting typography that fits your brand"
5. "Tuning your color palette"
6. "Building mobile-first components"
7. "Adding micro-animations for delight"
8. "Finalizing your redesign…"

Track switches automatically at the 45s mark (timer-driven, not API-driven).

### Color Swatches
- Rendered once `job.site_colors` is non-empty (after crawl)
- 4–5 swatches, small circles, fade in with `motion.div`
- Label: "Your brand colors" in muted text

### Step Indicators
3 pills: Analyzing · Designing · Building
Map from `job.status`:
- `queued/crawling` → Analyzing active
- `redesigning` → Designing active
- `deploying/done` → Building active

---

## Error States

**Network retry (silent):** Spinner keeps spinning. No visible change. Retry next poll.

**`job.status === "failed"`:** Show error screen with `job.error` message. Same design as current error state.

**5 consecutive network failures:** Show error: "Having trouble connecting. Your redesign may still be in progress — check back in a few minutes." Include a "Check status" button that does one manual poll.

**Job age > 15 min:** Show: "This is taking longer than expected. Please check back in a few minutes." (No email feature — the previous copy mentioning email was removed to avoid misleading users.)

---

## Files Changed

### Backend (Python)
- `sastaspace/jobs.py` — store `site_colors` + `site_title` after crawl

### Frontend (TypeScript)
- `web/src/lib/sse-client.ts` — replace `streamJobStatus` with `pollJobStatus`
- `web/src/hooks/use-redesign.ts` — replace SSE loop with poll loop; add retry counter; add `siteColors`/`siteTitle` to progress state
- `web/src/components/progress/progress-view.tsx` — full redesign with new layout
- `web/src/components/progress/insight-cards.tsx` — new component (rotating copy)
- `web/src/components/progress/color-swatches.tsx` — new component (brand colors)
- `web/src/components/progress/step-pills.tsx` — replaces current step-indicator (simpler 3-step version)
- Delete: `web/src/components/progress/activity-feed.tsx` — no longer needed (was SSE-driven)
- Delete: `web/src/components/progress/discovery-grid.tsx` — replaced by color-swatches

### Components to install from `@components/`
Each JSON file has a `files[].content` field containing the TypeScript source. Copy that content to the `target` path shown in the JSON (e.g., `components/ui/aurora-background.tsx`). Do **not** use `shadcn add` — these are direct file copies.

- `components/marketing-blocks/backgrounds/aceternity__aurora-background.json` → `web/src/components/ui/aurora-background.tsx`
- `components/ui-components/spinner-loaders/theritikk__luma-spin.json` → `web/src/components/ui/luma-spin.tsx`
- `components/ui-components/spinner-loaders/sean0205__progress.json` → `web/src/components/ui/progress.tsx` (already exists from Phase 3 — check before overwriting)
- `components/marketing-blocks/texts/preetsuthar17__animated-counter.json` → `web/src/components/ui/animated-counter.tsx`

---

## What We're NOT Changing

- `POST /redesign` endpoint — unchanged
- `GET /jobs/{id}` endpoint — unchanged (just adding 2 fields to response)
- `GET /jobs/{id}/stream` — keep for now, just unused by frontend
- Result page (`/[subdomain]`) — unchanged
- Backend pipeline — unchanged
- Worker job processing — unchanged except persisting 2 extra fields

---

## Success Criteria

1. Submitting a URL and experiencing a network blip does NOT show the error screen
2. Refreshing mid-job resumes polling automatically via `?job=` param
3. Insight cards rotate every 4s with smooth fade
4. Color swatches appear after crawl completes (~15–25s)
5. `job.status === "failed"` correctly shows error with specific message
6. Progress bar advances through 3 steps tied to job status
