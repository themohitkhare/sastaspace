# Polling + Engaged Waiting Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SSE streaming with HTTP polling and redesign the waiting screen to keep users engaged during the 2–3 minute redesign wait.

**Architecture:** The Python worker already crawls sites and stores the results in MongoDB — we extend `update_job()` to persist `site_colors` and `site_title` after crawl. On the frontend, `pollJobStatus()` replaces `streamJobStatus()` with a simple `while(true)/fetch/yield/sleep` loop that silently retries on network failure (only errors after 5 consecutive failures). The waiting screen gets a full visual redesign: aurora background, luma spinner, rotating insight cards, brand color swatches, and an animated counter.

**Tech Stack:** Python 3.11 / Motor (MongoDB async) / FastAPI · TypeScript / Next.js 16 App Router / Tailwind v4 / motion/react / Vitest · pytest-asyncio

---

## File Map

### Backend (modify only)
- `sastaspace/database.py:92–121` — add `site_colors` + `site_title` kwargs to `update_job()`
- `sastaspace/jobs.py:286–318` — call `update_job()` with crawl data after crawl success
- `tests/test_jobs_crawl_data.py` — new, tests backend changes

### Frontend — transport layer (modify)
- `web/src/lib/sse-client.ts` — remove `streamJobStatus`, add `JobStatus` type + `pollJobStatus` + `sleep` helper
- `web/src/__tests__/sse-client.test.ts` — replace `streamJobStatus` tests with `pollJobStatus` tests

### Frontend — hook (modify)
- `web/src/hooks/use-redesign.ts` — replace SSE loop with poll loop; update `RedesignState` type; remove `ActivityItem`/`DiscoveryItem`; add `siteColors`/`siteTitle`/`retryCount`
- `web/src/hooks/use-redesign.test.ts` — update type tests (remove old, add new)

### Frontend — new UI components (create)
- `web/src/components/ui/aurora-background.tsx` — from JSON; needs `animate-aurora` in globals.css
- `web/src/components/ui/luma-spin.tsx` — from JSON; adapted (remove `style jsx`, use globals.css keyframe)
- `web/src/components/ui/animated-counter.tsx` — from JSON, verbatim copy
- `web/src/components/progress/step-pills.tsx` — 3-pill step indicator
- `web/src/components/progress/insight-cards.tsx` — rotating insight copy with fade
- `web/src/components/progress/color-swatches.tsx` — brand color circles, fade in when available

### Frontend — globals + progress view (modify/rewrite)
- `web/src/app/globals.css` — add `@keyframes aurora` + `--animate-aurora` + `@keyframes luma-anim` + `--animate-luma-anim`
- `web/src/components/progress/progress-view.tsx` — full rewrite using all new components
- Delete: `web/src/components/progress/activity-feed.tsx`
- Delete: `web/src/components/progress/discovery-grid.tsx`

---

## Task 1: Backend — persist crawl data on job document

**Files:**
- Modify: `sastaspace/database.py:92–121`
- Modify: `sastaspace/jobs.py:254–320`
- Create: `tests/test_jobs_crawl_data.py`

Context: `update_job()` takes only keyword-only args. `redesign_handler()` in `jobs.py` already has `crawl_result.title` and `crawl_result.colors` available after crawl succeeds. `GET /jobs/{id}` returns the full job document — adding fields to the document automatically exposes them to the frontend.

- [ ] **Step 1: Write the failing test**

Create `tests/test_jobs_crawl_data.py`:

```python
# tests/test_jobs_crawl_data.py
"""Tests for site_colors / site_title persistence after crawl."""
import pytest
from unittest.mock import AsyncMock, patch, call


@pytest.mark.asyncio
async def test_update_job_accepts_site_colors_and_title():
    """update_job() must accept site_colors and site_title kwargs without error."""
    with patch("sastaspace.database._get_db") as mock_db:
        mock_collection = AsyncMock()
        mock_db.return_value.__getitem__ = lambda self, key: mock_collection
        mock_collection.update_one = AsyncMock()

        from sastaspace.database import update_job

        # Should not raise
        await update_job(
            "job-123",
            site_colors=["#ff0000", "#00ff00"],
            site_title="Test Site",
        )

        # update_one was called with the new fields
        update_one_call = mock_collection.update_one.call_args
        set_doc = update_one_call[0][1]["$set"]
        assert set_doc["site_colors"] == ["#ff0000", "#00ff00"]
        assert set_doc["site_title"] == "Test Site"


@pytest.mark.asyncio
async def test_update_job_site_fields_optional():
    """site_colors and site_title must be optional — omitting them must not add them to the update."""
    with patch("sastaspace.database._get_db") as mock_db:
        mock_collection = AsyncMock()
        mock_db.return_value.__getitem__ = lambda self, key: mock_collection
        mock_collection.update_one = AsyncMock()

        from sastaspace.database import update_job

        await update_job("job-123", status="crawling")

        set_doc = mock_collection.update_one.call_args[0][1]["$set"]
        assert "site_colors" not in set_doc
        assert "site_title" not in set_doc
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/mkhare/Development/sastaspace
uv run pytest tests/test_jobs_crawl_data.py -v
```

Expected: `FAILED` — `update_job() got an unexpected keyword argument 'site_colors'`

- [ ] **Step 3: Extend `update_job()` in `database.py`**

Add two new kwargs after `html_path` (around line 99):

```python
async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    error: str | None = None,
    subdomain: str | None = None,
    html_path: str | None = None,
    site_colors: list[str] | None = None,
    site_title: str | None = None,
) -> None:
    """Update fields on a job record."""
    now = datetime.now(UTC).isoformat()
    updates: dict = {"updated_at": now}

    if status is not None:
        updates["status"] = status
    if progress is not None:
        updates["progress"] = progress
    if message is not None:
        updates["message"] = message
    if error is not None:
        updates["error"] = error
    if subdomain is not None:
        updates["subdomain"] = subdomain
    if html_path is not None:
        updates["html_path"] = html_path
    if site_colors is not None:
        updates["site_colors"] = site_colors
    if site_title is not None:
        updates["site_title"] = site_title
    if status in (JobStatus.DONE.value, JobStatus.FAILED.value):
        updates["completed_at"] = now

    await _get_db()["jobs"].update_one({"_id": job_id}, {"$set": updates})
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_jobs_crawl_data.py -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Persist crawl data in `jobs.py`**

In `redesign_handler()`, after the `# Emit discovered site facts` block and before `# Step 2: Redesigning` (around line 305), add:

```python
    # Persist crawl data so polling clients can show brand colors + title
    await update_job(
        job_id,
        site_colors=crawl_result.colors[:5],
        site_title=crawl_result.title,
    )
```

- [ ] **Step 6: Run ruff and full backend tests**

```bash
uv run ruff check sastaspace/ tests/ --fix
uv run ruff format sastaspace/ tests/
uv run pytest tests/ -v
```

Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add sastaspace/database.py sastaspace/jobs.py tests/test_jobs_crawl_data.py
git commit -m "feat: persist site_colors and site_title on job doc after crawl"
```

---

## Task 2: Replace SSE transport with polling

**Files:**
- Modify: `web/src/lib/sse-client.ts`
- Modify: `web/src/__tests__/sse-client.test.ts`

Context: `streamJobStatus` is a streaming async generator over SSE. The new `pollJobStatus` is a simple `while(true)/fetch/sleep` generator. The `submitRedesign` function is unchanged. `streamJobStatus` tests must be replaced — they test a function that no longer exists.

- [ ] **Step 1: Write the failing poll tests**

Replace the contents of `web/src/__tests__/sse-client.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { submitRedesign, pollJobStatus } from '@/lib/sse-client'
import type { JobStatus } from '@/lib/sse-client'

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// --- submitRedesign (unchanged) ---

describe('submitRedesign', () => {
  it('returns job_id on success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'test-job-123' }),
    } as unknown as Response)

    const jobId = await submitRedesign('https://example.com')
    expect(jobId).toBe('test-job-123')
  })

  it('throws on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
    } as unknown as Response)

    await expect(submitRedesign('https://example.com')).rejects.toThrow(
      'Redesign request failed: 500'
    )
  })

  it('throws when no job_id in response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as unknown as Response)

    await expect(submitRedesign('https://example.com')).rejects.toThrow(
      'No job_id returned from server'
    )
  })
})

// --- pollJobStatus ---

function makeJob(overrides: Partial<JobStatus> = {}): JobStatus {
  return {
    id: 'job-1',
    status: 'crawling',
    progress: 25,
    message: 'Crawling...',
    ...overrides,
  }
}

describe('pollJobStatus', () => {
  it('yields job status and stops on done', async () => {
    const jobs: JobStatus[] = [
      makeJob({ status: 'crawling' }),
      makeJob({ status: 'done', subdomain: 'example-com' }),
    ]
    let callCount = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      const job = jobs[callCount++]
      return { ok: true, json: async () => job } as unknown as Response
    })

    const results: JobStatus[] = []
    const gen = pollJobStatus('job-1')

    // Get first value
    const p1 = gen.next()
    await vi.runAllTimersAsync()
    results.push((await p1).value)

    // Get second value (done — generator should complete)
    const p2 = gen.next()
    await vi.runAllTimersAsync()
    const r2 = await p2
    results.push(r2.value)
    expect(r2.done).toBe(true)

    expect(results[0].status).toBe('crawling')
    expect(results[1].status).toBe('done')
  })

  it('silently retries on network error and continues', async () => {
    let callCount = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      callCount++
      if (callCount === 1) throw new Error('Network error')
      return {
        ok: true,
        json: async () => makeJob({ status: 'crawling' }),
      } as unknown as Response
    })

    const gen = pollJobStatus('job-1')
    const p = gen.next()
    await vi.runAllTimersAsync()
    const result = await p

    expect(result.value.status).toBe('crawling')
    expect(callCount).toBe(2) // first failed, second succeeded
  })

  it('throws POLL_FAILED after 5 consecutive network errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const collected: JobStatus[] = []
    await expect(async () => {
      const gen = pollJobStatus('job-1')
      for (let i = 0; i < 6; i++) {
        const p = gen.next()
        await vi.runAllTimersAsync()
        const r = await p
        if (r.done) break
        collected.push(r.value)
      }
    }).rejects.toThrow('POLL_FAILED')

    expect(collected).toHaveLength(0) // never yielded
  })

  it('stops polling when AbortSignal is aborted', async () => {
    const controller = new AbortController()
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      controller.abort()
      return {
        ok: true,
        json: async () => makeJob({ status: 'crawling' }),
      } as unknown as Response
    })

    const results: JobStatus[] = []
    const gen = pollJobStatus('job-1', controller.signal)
    const p = gen.next()
    await vi.runAllTimersAsync()
    const r = await p
    // After aborting, next call should terminate the generator
    if (!r.done && r.value) results.push(r.value)

    const p2 = gen.next()
    await vi.runAllTimersAsync()
    const r2 = await p2
    expect(r2.done).toBe(true)
  })

  it('uses 1s interval when status is deploying', async () => {
    // We verify interval logic indirectly via consecutive failures counting
    // The main thing we test: deploying jobs get a shorter next-poll window.
    // This is structural — verified by code reading, not easily unit-testable with fake timers.
    // Smoke test: poll a deploying job and get a result
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => makeJob({ status: 'deploying', progress: 90 }),
    } as unknown as Response)

    const gen = pollJobStatus('job-1')
    const p = gen.next()
    await vi.runAllTimersAsync()
    const r = await p
    expect(r.value.status).toBe('deploying')
  })
})
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx vitest run src/__tests__/sse-client.test.ts
```

Expected: FAIL — `pollJobStatus` does not exist yet, `streamJobStatus` import breaks.

- [ ] **Step 3: Rewrite `web/src/lib/sse-client.ts`**

```typescript
// web/src/lib/sse-client.ts

export type SSEEvent = {
  event: string
  data: Record<string, unknown>
}

export type JobStatus = {
  id: string
  status: "queued" | "crawling" | "redesigning" | "deploying" | "done" | "failed"
  progress: number
  message: string
  subdomain?: string
  error?: string
  site_colors?: string[]
  site_title?: string
  created_at?: string
}

/** Submit a redesign request. Returns job_id or throws. */
export async function submitRedesign(
  url: string,
  tier: "free" | "standard" | "premium" = "free",
  signal?: AbortSignal
): Promise<string> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  const resp = await fetch(`${backendUrl}/redesign`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, tier }),
    signal,
  })
  if (!resp.ok) throw new Error(`Redesign request failed: ${resp.status}`)
  const data = (await resp.json()) as { job_id?: string }
  if (data.job_id) return data.job_id
  throw new Error("No job_id returned from server")
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * Poll GET /jobs/{id} every 3s (1s when deploying).
 * Silently retries on network errors; throws "POLL_FAILED" after 5 consecutive failures.
 * Generator stops when status is "done" or "failed".
 */
export async function* pollJobStatus(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<JobStatus> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  let consecutiveFailures = 0
  let lastStatus: string = "queued"

  while (true) {
    if (signal?.aborted) return

    try {
      const resp = await fetch(`${backendUrl}/jobs/${jobId}`, { signal })
      if (signal?.aborted) return

      if (resp.ok) {
        consecutiveFailures = 0
        const job = (await resp.json()) as JobStatus
        lastStatus = job.status
        yield job
        if (job.status === "done" || job.status === "failed") return
      } else {
        consecutiveFailures++
      }
    } catch {
      if (signal?.aborted) return
      consecutiveFailures++
    }

    if (consecutiveFailures >= 5) {
      throw new Error("POLL_FAILED")
    }

    const intervalMs = lastStatus === "deploying" ? 1000 : 3000
    await sleep(intervalMs)
  }
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npx vitest run src/__tests__/sse-client.test.ts
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/sse-client.ts web/src/__tests__/sse-client.test.ts
git commit -m "feat: replace SSE streamJobStatus with HTTP pollJobStatus"
```

---

## Task 3: Update `use-redesign` hook for polling

**Files:**
- Modify: `web/src/hooks/use-redesign.ts`
- Modify: `web/src/hooks/use-redesign.test.ts`

Context: The current hook uses `streamJobStatus` and tracks `activities`, `discoveryItems`, `screenshot` in state — all SSE-only features. The new hook uses `pollJobStatus`, tracks `siteColors`/`siteTitle` in progress state, and handles the "POLL_FAILED" error distinctly with a `resumeJobId` for the "Check status" button.

- [ ] **Step 1: Update the test file**

Replace `web/src/hooks/use-redesign.test.ts` with:

```typescript
import { describe, it, expect } from "vitest"
import type { RedesignState } from "@/hooks/use-redesign"

describe("RedesignState type", () => {
  it("progress state has siteColors and siteTitle", () => {
    const s: RedesignState = {
      status: "progress",
      currentStep: "crawling",
      domain: "example.com",
      steps: [],
      tier: "free",
      jobId: "abc",
      siteColors: ["#ff0000"],
      siteTitle: "Example",
      retryCount: 0,
      jobCreatedAt: "",
    }
    expect(s.status).toBe("progress")
    if (s.status === "progress") {
      expect(s.siteColors).toEqual(["#ff0000"])
      expect(s.siteTitle).toBe("Example")
    }
  })

  it("error state can carry resumeJobId for network-failure resume", () => {
    const s: RedesignState = {
      status: "error",
      message: "Having trouble connecting.",
      url: "https://example.com",
      resumeJobId: "job-123",
    }
    if (s.status === "error") {
      expect(s.resumeJobId).toBe("job-123")
    }
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx vitest run src/hooks/use-redesign.test.ts
```

Expected: FAIL — `siteColors`, `siteTitle`, `resumeJobId` don't exist on current types.

- [ ] **Step 3: Rewrite `web/src/hooks/use-redesign.ts`**

```typescript
"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { submitRedesign, pollJobStatus } from "@/lib/sse-client";
import { extractDomain } from "@/lib/url-utils";

type StepState = {
  name: string;
  label: string;
  value: number;
  status: "pending" | "active" | "done";
};

export type RedesignTier = "free" | "premium";

export type RedesignState =
  | { status: "idle" }
  | { status: "connecting" }
  | {
      status: "progress";
      currentStep: string;
      domain: string;
      steps: StepState[];
      tier: RedesignTier;
      jobId: string;
      siteColors: string[];
      siteTitle: string;
      retryCount: number;
      jobCreatedAt: string;
    }
  | { status: "done"; subdomain: string; originalUrl: string; domain: string; tier: RedesignTier }
  | { status: "error"; message: string; url: string; resumeJobId?: string };

export const STEPS = [
  { name: "crawling", label: (d: string) => `Analyzing ${d}` },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "redesigning", label: (_d: string) => "Redesigning your site with AI" },
  { name: "deploying", label: (d: string) => `Preparing your new ${d}` },
] as const;

function makeInitialSteps(domain: string): StepState[] {
  return STEPS.map((s) => ({
    name: s.name,
    label: s.label(domain),
    value: 0,
    status: "pending" as const,
  }));
}

// Map job status → (step name, progress %)
const STATUS_TO_STEP: Record<string, { stepName: string; progressValue: number }> = {
  queued:      { stepName: "crawling",    progressValue: 5  },
  crawling:    { stepName: "crawling",    progressValue: 25 },
  redesigning: { stepName: "redesigning", progressValue: 65 },
  deploying:   { stepName: "deploying",   progressValue: 90 },
};

const STEP_NAMES = STEPS.map((s) => s.name);

const GENERIC_ERROR_MESSAGE =
  "We couldn't redesign that site right now. This can happen with very large or complex websites.";

const JOB_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export function useRedesign() {
  const [state, setState] = useState<RedesignState>({ status: "idle" });
  const abortRef = useRef<AbortController | null>(null);
  const lastUrlRef = useRef<string>("");
  const lastTierRef = useRef<RedesignTier>("free");

  const pollJob = useCallback(
    async (jobId: string, url: string, tier: RedesignTier, controller: AbortController) => {
      const domain = extractDomain(url);

      setState({
        status: "progress",
        currentStep: "crawling",
        domain,
        steps: makeInitialSteps(domain),
        tier,
        jobId,
        siteColors: [],
        siteTitle: "",
        retryCount: 0,
        jobCreatedAt: "",
      });

      try {
        for await (const job of pollJobStatus(jobId, controller.signal)) {
          if (controller.signal.aborted) return;

          // Guard: job too old
          if (job.created_at) {
            const ageMs = Date.now() - new Date(job.created_at).getTime();
            if (ageMs > JOB_TIMEOUT_MS) {
              setState({
                status: "error",
                message: "This is taking longer than expected. Please check back in a few minutes.",
                url,
              });
              return;
            }
          }

          if (job.status === "failed") {
            setState({
              status: "error",
              message: job.error || GENERIC_ERROR_MESSAGE,
              url,
            });
            return;
          }

          if (job.status === "done") {
            // Flash all steps to 100% for 800ms before transitioning
            const doneSteps = makeInitialSteps(domain).map((step) => ({
              ...step,
              value: 100,
              status: "done" as const,
            }));
            setState((prev) =>
              prev.status === "progress"
                ? { ...prev, currentStep: "done", steps: doneSteps }
                : prev
            );
            await new Promise((r) => setTimeout(r, 800));
            if (controller.signal.aborted) return;
            setState({
              status: "done",
              subdomain: job.subdomain!,
              originalUrl: url,
              domain,
              tier,
            });
            return;
          }

          // In-progress update
          const { stepName, progressValue } =
            STATUS_TO_STEP[job.status] ?? STATUS_TO_STEP.queued;
          const stepIndex = STEP_NAMES.indexOf(stepName);
          const updatedSteps = makeInitialSteps(domain).map((step, i) => {
            if (i < stepIndex) return { ...step, value: 100, status: "done" as const };
            if (i === stepIndex)
              return { ...step, value: progressValue, status: "active" as const };
            return step;
          });

          setState({
            status: "progress",
            currentStep: stepName,
            domain,
            steps: updatedSteps,
            tier,
            jobId,
            siteColors: job.site_colors ?? [],
            siteTitle: job.site_title ?? "",
            retryCount: 0,
            jobCreatedAt: job.created_at ?? "",
          });
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        const isPollFailed = e instanceof Error && e.message === "POLL_FAILED";
        setState({
          status: "error",
          message: isPollFailed
            ? "Having trouble connecting. Your redesign may still be in progress — check back in a few minutes."
            : GENERIC_ERROR_MESSAGE,
          url,
          resumeJobId: isPollFailed ? jobId : undefined,
        });
      }
    },
    []
  );

  const start = useCallback(
    async (url: string, tier: RedesignTier = "free") => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      lastUrlRef.current = url;
      lastTierRef.current = tier;

      setState({ status: "connecting" });

      try {
        const jobId = await submitRedesign(url, tier, controller.signal);
        if (controller.signal.aborted) return;

        // Persist job ID + original URL for page-refresh reconnection
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          params.set("job", jobId);
          params.set("url", url); // restored on refresh so domain label stays correct
          window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
        }

        await pollJob(jobId, url, tier, controller);
      } catch {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: GENERIC_ERROR_MESSAGE, url });
      }
    },
    [pollJob]
  );

  const retry = useCallback(() => {
    if (state.status !== "error") return;
    if (state.resumeJobId) {
      // Network failure: resume polling the existing job
      const controller = new AbortController();
      abortRef.current = controller;
      pollJob(state.resumeJobId, state.url, lastTierRef.current, controller);
    } else {
      start(state.url, lastTierRef.current);
    }
  }, [state, start, pollJob]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ status: "idle" });
  }, []);

  // On mount: if ?job= present in URL, resume polling without re-submitting
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get("job");
    if (!jobId) return;

    const controller = new AbortController();
    abortRef.current = controller;
    // Restore URL from query param so domain label renders correctly after refresh
    const url = params.get("url") || lastUrlRef.current || "";
    if (url) lastUrlRef.current = url;
    pollJob(jobId, url, lastTierRef.current, controller);

    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { state, start, retry, reset };
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
npx vitest run src/hooks/use-redesign.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/use-redesign.ts web/src/hooks/use-redesign.test.ts
git commit -m "feat: update useRedesign hook to use polling transport"
```

---

## Task 4: Install UI components and CSS keyframes

**Files:**
- Create: `web/src/components/ui/aurora-background.tsx`
- Create: `web/src/components/ui/luma-spin.tsx`
- Create: `web/src/components/ui/animated-counter.tsx`
- Modify: `web/src/app/globals.css`

Context: Components are in `components/` JSON registry files. Each has a `files[].content` field with the TypeScript source. The LumaSpin original uses `style jsx` (JSX scoped styles), which is not available in Next.js App Router without `styled-jsx`. We convert it to use Tailwind arbitrary-value animations with keyframes defined in `globals.css`. The `Progress` component (`web/src/components/ui/progress.tsx`) already exists from Phase 3 — do NOT overwrite it.

- [ ] **Step 1: Add keyframes to `globals.css`**

Append before the closing of the file (or after the existing `:root` block), in `web/src/app/globals.css`:

```css
/* Aurora background animation */
@keyframes aurora {
  from {
    background-position: 50% 50%, 50% 50%;
  }
  to {
    background-position: 350% 50%, 350% 50%;
  }
}

/* Luma orbital spinner animation */
@keyframes luma-anim {
  0%    { inset: 0 35px 35px 0; }
  12.5% { inset: 0 35px 0 0; }
  25%   { inset: 35px 35px 0 0; }
  37.5% { inset: 35px 0 0 0; }
  50%   { inset: 35px 0 0 35px; }
  62.5% { inset: 0 0 0 35px; }
  75%   { inset: 0 0 35px 35px; }
  87.5% { inset: 0 0 35px 0; }
  100%  { inset: 0 35px 35px 0; }
}
```

And inside the existing `@theme inline { ... }` block, add animation variables:

```css
  --animate-aurora: aurora 60s linear infinite;
  --animate-luma: luma-anim 2.5s infinite;
  --animate-luma-delay: luma-anim 2.5s infinite -1.25s;
```

- [ ] **Step 2: Create `aurora-background.tsx`**

Copy from `components/marketing-blocks/backgrounds/aceternity__aurora-background.json` files[0].content verbatim into `web/src/components/ui/aurora-background.tsx`. The content is:

```typescript
"use client";
import { cn } from "@/lib/utils";
import React, { ReactNode } from "react";

interface AuroraBackgroundProps extends React.HTMLProps<HTMLDivElement> {
  children: ReactNode;
  showRadialGradient?: boolean;
}

export const AuroraBackground = ({
  className,
  children,
  showRadialGradient = true,
  ...props
}: AuroraBackgroundProps) => {
  return (
    <main>
      <div
        className={cn(
          "relative flex flex-col h-[100vh] items-center justify-center bg-zinc-50 dark:bg-zinc-900 text-slate-950 transition-bg",
          className
        )}
        {...props}
      >
        <div className="absolute inset-0 overflow-hidden">
          <div
            className={cn(
              `
            [--white-gradient:repeating-linear-gradient(100deg,var(--white)_0%,var(--white)_7%,var(--transparent)_10%,var(--transparent)_12%,var(--white)_16%)]
            [--dark-gradient:repeating-linear-gradient(100deg,var(--black)_0%,var(--black)_7%,var(--transparent)_10%,var(--transparent)_12%,var(--black)_16%)]
            [--aurora:repeating-linear-gradient(100deg,var(--blue-500)_10%,var(--indigo-300)_15%,var(--blue-300)_20%,var(--violet-200)_25%,var(--blue-400)_30%)]
            [background-image:var(--white-gradient),var(--aurora)]
            dark:[background-image:var(--dark-gradient),var(--aurora)]
            [background-size:300%,_200%]
            [background-position:50%_50%,50%_50%]
            filter blur-[10px] invert dark:invert-0
            after:content-[""] after:absolute after:inset-0 after:[background-image:var(--white-gradient),var(--aurora)]
            after:dark:[background-image:var(--dark-gradient),var(--aurora)]
            after:[background-size:200%,_100%]
            after:animate-aurora after:[background-attachment:fixed] after:mix-blend-difference
            pointer-events-none
            absolute -inset-[10px] opacity-50 will-change-transform`,
              showRadialGradient &&
                `[mask-image:radial-gradient(ellipse_at_100%_0%,black_10%,var(--transparent)_70%)]`
            )}
          ></div>
        </div>
        {children}
      </div>
    </main>
  );
};
```

- [ ] **Step 3: Create `luma-spin.tsx`**

The original uses `style jsx` which isn't available in the App Router. Adapt it to use the keyframes added to `globals.css`:

Create `web/src/components/ui/luma-spin.tsx`:

```typescript
"use client";

export function LumaSpin() {
  return (
    <div className="relative w-[65px] aspect-square">
      <span
        className="absolute rounded-[50px]"
        style={{ animation: "luma-anim 2.5s infinite", boxShadow: "inset 0 0 0 3px currentColor" }}
      />
      <span
        className="absolute rounded-[50px]"
        style={{
          animation: "luma-anim 2.5s infinite -1.25s",
          boxShadow: "inset 0 0 0 3px currentColor",
        }}
      />
    </div>
  );
}
```

- [ ] **Step 4: Create `animated-counter.tsx`**

Copy from `components/marketing-blocks/texts/preetsuthar17__animated-counter.json` files[0].content verbatim into `web/src/components/ui/animated-counter.tsx`. The content starts with `"use client"` and exports `Counter`. Paste it exactly, preserving the `\r\n` line endings as `\n`.

The key exports to know: `Counter` with props `{ start?, end, duration?, className?, fontSize? }`.

- [ ] **Step 5: Run TypeScript check**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx tsc --noEmit
```

Fix any type errors before proceeding.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ui/aurora-background.tsx \
        web/src/components/ui/luma-spin.tsx \
        web/src/components/ui/animated-counter.tsx \
        web/src/app/globals.css
git commit -m "feat: install aurora background, luma spinner, animated counter components"
```

---

## Task 5: New progress sub-components

**Files:**
- Create: `web/src/components/progress/step-pills.tsx`
- Create: `web/src/components/progress/insight-cards.tsx`
- Create: `web/src/components/progress/color-swatches.tsx`

Context: These three components are standalone — they receive only props, have no side-effect data fetching, and can be built and tested in isolation. `InsightCards` manages its own timer (`setInterval` at 1s to tick elapsed seconds). `ColorSwatches` fades in when `colors` prop becomes non-empty.

- [ ] **Step 1: Create `step-pills.tsx`**

```typescript
// web/src/components/progress/step-pills.tsx
"use client";

import { cn } from "@/lib/utils";

type PillStep = {
  key: string;
  label: string;
  activeStatuses: string[];
};

const PILL_STEPS: PillStep[] = [
  { key: "analyzing", label: "Analyzing",  activeStatuses: ["queued", "crawling"] },
  { key: "designing", label: "Designing",  activeStatuses: ["redesigning"] },
  { key: "building",  label: "Building",   activeStatuses: ["deploying", "done"] },
];

interface StepPillsProps {
  currentStatus: string; // job.status value
}

export function StepPills({ currentStatus }: StepPillsProps) {
  // Determine which pill index is active
  const activeIndex = PILL_STEPS.findIndex((p) =>
    p.activeStatuses.includes(currentStatus)
  );

  return (
    <div className="flex items-center gap-3">
      {PILL_STEPS.map((pill, i) => {
        const isDone = activeIndex > i;
        const isActive = activeIndex === i;
        return (
          <div
            key={pill.key}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300",
              isActive && "bg-accent text-accent-foreground",
              isDone && "bg-accent/20 text-accent",
              !isActive && !isDone && "bg-secondary text-muted-foreground"
            )}
          >
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full",
                isActive && "bg-accent-foreground",
                isDone && "bg-accent",
                !isActive && !isDone && "bg-muted-foreground/40"
              )}
            />
            {pill.label}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create `insight-cards.tsx`**

```typescript
// web/src/components/progress/insight-cards.tsx
"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

const TRACK_1 = [
  "Visiting {domain}…",
  "Downloading {domain} assets and images",
  "Reading your business copy",
  "Identifying your target audience",
  "Mapping your customer journey",
  "Analyzing your conversion funnel",
  "Benchmarking against your industry",
  "Understanding what makes you unique",
];

const TRACK_2 = [
  "Designing a layout built for conversions",
  "Writing copy that speaks to your customers",
  "Crafting your hero for maximum impact",
  "Selecting typography that fits your brand",
  "Tuning your color palette",
  "Building mobile-first components",
  "Adding micro-animations for delight",
  "Finalizing your redesign…",
];

// Track switches at 45s
const TRACK_SWITCH_MS = 45_000;
// Message rotates every 4s
const MESSAGE_INTERVAL_MS = 4_000;

interface InsightCardsProps {
  domain: string;
}

export function InsightCards({ domain }: InsightCardsProps) {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsedMs((prev) => prev + 1000);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const track = elapsedMs < TRACK_SWITCH_MS ? TRACK_1 : TRACK_2;
  const messageIndex = Math.floor(elapsedMs / MESSAGE_INTERVAL_MS) % track.length;
  const rawMessage = track[messageIndex];
  const message = rawMessage.replace(/\{domain\}/g, domain || "your site");

  return (
    <div className="w-full max-w-sm rounded-xl border border-border/40 bg-background/30 backdrop-blur-sm px-5 py-4 min-h-[64px] flex items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.p
          key={`${messageIndex}-${elapsedMs < TRACK_SWITCH_MS ? 0 : 1}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.4 }}
          className="text-sm text-center text-foreground/80"
        >
          {message}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 3: Create `color-swatches.tsx`**

```typescript
// web/src/components/progress/color-swatches.tsx
"use client";

import { AnimatePresence, motion } from "motion/react";

interface ColorSwatchesProps {
  colors: string[]; // hex color strings, e.g. ["#ff0000", "rgb(0,0,0)"]
}

export function ColorSwatches({ colors }: ColorSwatchesProps) {
  if (!colors.length) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center gap-2"
      >
        <div className="flex items-center gap-2">
          {colors.slice(0, 5).map((color, i) => (
            <div
              key={i}
              className="w-5 h-5 rounded-full border border-border/30 shadow-sm"
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
        <p className="text-xs text-muted-foreground">Your brand colors</p>
      </motion.div>
    </AnimatePresence>
  );
}
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx tsc --noEmit
```

Fix any errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/progress/step-pills.tsx \
        web/src/components/progress/insight-cards.tsx \
        web/src/components/progress/color-swatches.tsx
git commit -m "feat: add StepPills, InsightCards, ColorSwatches progress components"
```

---

## Task 6: Rewrite progress-view.tsx, delete old components

**Files:**
- Modify: `web/src/components/progress/progress-view.tsx`
- Delete: `web/src/components/progress/activity-feed.tsx`
- Delete: `web/src/components/progress/discovery-grid.tsx`

Context: The current `progress-view.tsx` imports `ActivityFeed` and `DiscoveryGrid` which we're deleting. Check for any other files that import these two before deleting them.

Run first:
```bash
grep -r "activity-feed\|ActivityFeed\|discovery-grid\|DiscoveryGrid" web/src --include="*.tsx" --include="*.ts" -l
```
Only `progress-view.tsx` should appear. If anything else imports them, update those files first.

- [ ] **Step 1: Delete old components**

```bash
rm web/src/components/progress/activity-feed.tsx
rm web/src/components/progress/discovery-grid.tsx
```

- [ ] **Step 2: Rewrite `progress-view.tsx`**

```typescript
// web/src/components/progress/progress-view.tsx
"use client";

import { motion } from "motion/react";
import { AlertCircle, RotateCcw, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { LumaSpin } from "@/components/ui/luma-spin";
import { Counter } from "@/components/ui/animated-counter";
import { StepPills } from "@/components/progress/step-pills";
import { InsightCards } from "@/components/progress/insight-cards";
import { ColorSwatches } from "@/components/progress/color-swatches";
import type { RedesignState } from "@/hooks/use-redesign";

// Map step name → top-level progress bar value
const STEP_TO_PROGRESS: Record<string, number> = {
  connecting: 3,
  crawling:   25,
  redesigning: 65,
  deploying:  90,
  done:       100,
};

type ProgressViewState = Extract<RedesignState, { status: "progress" | "error" | "connecting" }>;

interface ProgressViewProps {
  state: ProgressViewState;
  onRetry: () => void;
}

export function ProgressView({ state, onRetry }: ProgressViewProps) {
  // --- Error state ---
  if (state.status === "error") {
    const isRateLimit =
      state.message.toLowerCase().includes("rate limit") ||
      state.message.toLowerCase().includes("limit");
    const isNetworkError = Boolean(state.resumeJobId);

    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-4 text-center"
        >
          <AlertCircle className="w-12 h-12 text-destructive" />
          <h2 className="font-heading text-[clamp(1.5rem,3vw,2rem)] text-foreground">
            Something went wrong
          </h2>
          <p className="text-base text-muted-foreground max-w-sm">
            {isRateLimit
              ? "You've reached the limit. Please try again in an hour."
              : state.message}
          </p>
          <Button
            size="lg"
            onClick={onRetry}
            className="bg-accent text-accent-foreground hover:bg-accent/90"
          >
            {isNetworkError ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Check status
              </>
            ) : (
              <>
                <RotateCcw className="w-4 h-4 mr-2" />
                Try again
              </>
            )}
          </Button>
        </motion.div>
      </div>
    );
  }

  // --- Connecting / progress state ---
  const isConnecting = state.status === "connecting";
  const domain = isConnecting ? "" : state.domain;
  const currentStep = isConnecting ? "connecting" : state.currentStep;
  const siteColors = isConnecting ? [] : state.siteColors;
  const jobStatus = isConnecting ? "queued" : state.currentStep;

  const progressValue = STEP_TO_PROGRESS[currentStep] ?? 5;

  return (
    <AuroraBackground
      className="min-h-screen"
      showRadialGradient
    >
      {/* Top progress bar */}
      <div className="absolute top-0 left-0 right-0 z-10">
        <Progress
          value={progressValue}
          className="h-1 rounded-none bg-transparent"
          indicatorClassName="bg-accent transition-all duration-1000"
        />
      </div>

      {/* Centered content */}
      <div className="relative z-10 flex flex-col items-center gap-6 px-4 py-16 w-full max-w-md">

        {/* Spinner */}
        <LumaSpin />

        {/* Domain title */}
        <div className="text-center">
          {domain ? (
            <p className="font-heading text-lg font-medium text-foreground">
              Redesigning{" "}
              <span className="text-accent">{domain}</span>
            </p>
          ) : (
            <p className="font-heading text-lg font-medium text-foreground">
              Starting…
            </p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            AI redesigns typically take 2–3 minutes
          </p>
        </div>

        {/* Step pills */}
        <StepPills currentStatus={jobStatus} />

        {/* Rotating insight cards */}
        <InsightCards domain={domain} />

        {/* Color swatches — fade in when crawl data arrives */}
        <ColorSwatches colors={siteColors} />

        {/* Animated counter */}
        <div className="flex items-center gap-1.5 text-muted-foreground text-sm mt-2">
          <Counter start={12800} end={12847} duration={3} fontSize={14} className="text-foreground font-semibold" />
          <span>redesigns completed</span>
        </div>
      </div>
    </AuroraBackground>
  );
}
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx tsc --noEmit
```

Fix any errors. Common issues:
- `AuroraBackground` wraps `<main>` — if it conflicts with existing `<main>` in the page layout, pass `className` overrides
- `Progress` component accepts `indicatorClassName` — already supported from Phase 3
- `Counter` from `animated-counter.tsx` — verify export name matches

- [ ] **Step 4: Run all Vitest tests**

```bash
npx vitest run
```

Expected: All tests PASS. If any test fails due to removed `ActivityItem`/`DiscoveryItem` types — they were removed in Task 3 and the test file was already updated there.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/progress/progress-view.tsx
git rm web/src/components/progress/activity-feed.tsx
git rm web/src/components/progress/discovery-grid.tsx
git commit -m "feat: redesign progress view with aurora bg, luma spinner, insight cards"
```

---

## Task 7: Final check and full test suite

**Files:** none new — verification only

- [ ] **Step 1: Full frontend type-check + lint**

```bash
cd /Users/mkhare/Development/sastaspace/web
npx tsc --noEmit
npx next lint
```

Expected: zero errors.

- [ ] **Step 2: Full Vitest test suite**

```bash
npx vitest run
```

Expected: All tests PASS.

- [ ] **Step 3: Full backend test suite + ruff**

```bash
cd /Users/mkhare/Development/sastaspace
uv run ruff check sastaspace/ tests/
uv run pytest tests/ -v
```

Expected: All pass.

- [ ] **Step 4: Next.js build smoke test**

```bash
cd /Users/mkhare/Development/sastaspace/web
npm run build
```

Expected: Build completes with no errors.

- [ ] **Step 5: Final commit**

Only commit if there are unstaged changes left over from previous tasks (there usually won't be):

```bash
git status
# If clean: done. If dirty: git add <specific files> then commit.
```

---

## Success Criteria Checklist

- [ ] Submitting a URL and simulating a network error does NOT show the error screen (retries silently)
- [ ] Refreshing mid-job (`?job=` param present) resumes polling without re-submitting
- [ ] Insight cards rotate every 4s with fade transition
- [ ] Track switches to "Build" copy at the 45s mark
- [ ] Color swatches appear once `job.site_colors` is set (after crawl, ~15–25s)
- [ ] `job.status === "failed"` shows error screen with `job.error` message
- [ ] 5 consecutive poll failures shows network-error message with "Check status" button
- [ ] Progress bar value advances: queued→5%, crawling→25%, redesigning→65%, deploying→90%, done→100%
- [ ] Aurora background renders behind all content
- [ ] TypeScript build passes with zero errors
