# Loading Screen Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the static 3-bar loading screen into a live activity feed that shows the AI pipeline working in real-time, using job_id-based tracking for resilient reconnectable progress streaming.

**Architecture:** Task 0 refactors POST /redesign to return `{ job_id }` immediately and adds a `GET /jobs/{job_id}/stream` SSE endpoint — enabling page-refresh resilience and tab resilience. Phase A adds a `progress_callback` to the Agno pipeline (fired before each agent), threading through `redesigner.py` → `jobs.py` as `agent_activity` + `discovery` SSE events. Phase B streams the crawl screenshot and builds a before/after reveal component.

**Tech Stack:** FastAPI SSE + `sse-starlette`, Python `asyncio.run_coroutine_threadsafe`, React 19, `motion` (framer-motion), Tailwind v4, TypeScript discriminated unions.

---

## File Map

**Modified — Backend:**
- `sastaspace/server.py` — POST /redesign returns `{ job_id }` JSON; new `GET /jobs/{job_id}/stream` SSE endpoint
- `sastaspace/agents/pipeline.py` — add `progress_callback: ProgressCallback` param + `AGENT_MESSAGES` dict; `run_redesign_pipeline` returns `str`; `_run_normalizer` takes `(html, design_brief, settings)`
- `sastaspace/redesigner.py` — thread `progress_callback` through `agno_redesign`
- `sastaspace/jobs.py` — capture `get_running_loop()` before `to_thread`; build thread-safe callback; emit `discovery` + `screenshot` events

**Modified — Frontend:**
- `web/src/lib/sse-client.ts` — split into `submitRedesign(url, tier) → job_id` + `streamJobStatus(job_id)`
- `web/src/hooks/use-redesign.ts` — store `job_id` in URL on start; resume from URL on mount; handle `agent_activity`, `discovery`, `screenshot` events; `ActivityItem` includes `agent` field
- `web/src/components/progress/progress-view.tsx` — wire new subcomponents
- `web/src/components/progress/step-indicator.tsx` — shimmer pulse on active step

**Created — Frontend:**
- `web/src/components/progress/activity-feed.tsx` — animated live agent messages
- `web/src/components/progress/discovery-grid.tsx` — discovered site fact cards
- `web/src/components/progress/site-screenshot.tsx` — Phase B screenshot reveal

---

## Task 0: Job-ID Tracking — POST /redesign returns job_id, add stream endpoint

**Files:**
- Modify: `sastaspace/server.py`
- Modify: `web/src/lib/sse-client.ts`
- Modify: `web/src/hooks/use-redesign.ts`

Split the monolithic SSE POST into: a fast JSON POST that returns `job_id`, and a separate reconnectable GET stream.

- [ ] **Step 1: Write failing backend test**

Add `tests/test_job_stream.py`:

```python
# tests/test_job_stream.py
"""Tests for job_id-based tracking endpoints."""
from unittest.mock import AsyncMock, patch

import pytest

from sastaspace.database import create_job, JobStatus


async def test_redesign_returns_job_id(test_client):
    """POST /redesign returns { job_id } immediately when Redis available."""
    with patch("sastaspace.server.svc") as mock_svc:
        mock_svc.enqueue = AsyncMock(return_value="test-job-123")
        resp = test_client.post("/redesign", json={"url": "https://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-job-123"


async def test_job_stream_404_for_unknown_job(test_client):
    """GET /jobs/{job_id}/stream returns 404 when job not in DB."""
    with patch("sastaspace.server.svc") as mock_svc:
        mock_svc.subscribe_job = AsyncMock(return_value=iter([]))
        resp = test_client.get("/jobs/nonexistent-job/stream")
        assert resp.status_code == 404


async def test_job_stream_returns_cached_done_event(test_client):
    """GET /jobs/{job_id}/stream returns done event immediately if job already complete."""
    job_id = "done-job-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.2.3.4")
    from sastaspace.database import update_job
    await update_job(job_id, status=JobStatus.DONE.value, subdomain="example-com", progress=100)

    with patch("sastaspace.server.svc"):
        # TestClient will stream SSE; check it terminates cleanly
        with test_client.stream("GET", f"/jobs/{job_id}/stream") as r:
            assert r.status_code == 200
```

- [ ] **Step 2: Run to verify fails**

```bash
uv run pytest tests/test_job_stream.py -v
```
Expected: FAILED — no `/jobs/{job_id}/stream` endpoint

- [ ] **Step 3: Refactor POST /redesign in `server.py`**

When Redis (`svc`) is available, change the endpoint to return JSON instead of SSE:

```python
@app.post("/redesign")
async def redesign_endpoint(body: RedesignRequest, request: Request):
    ...
    if svc is not None:
        # Redis path: enqueue and return job_id immediately
        _redesign_requests_total.labels(status="started").inc()
        job_id = await svc.enqueue(url=body.url, client_ip=ip, tier=body.tier)
        return {"job_id": job_id}
    else:
        # Inline fallback: stream directly (unchanged)
        return EventSourceResponse(redesign_stream(body.url, body.tier))
```

- [ ] **Step 4: Add `GET /jobs/{job_id}/stream` endpoint**

```python
@app.get("/jobs/{job_id}/stream")
async def job_stream_endpoint(job_id: str):
    """SSE stream for a specific job. Reconnectable — safe to call multiple times."""
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # If already done/failed, emit terminal event immediately and close
    if job["status"] in (JobStatus.DONE.value, JobStatus.FAILED.value):
        async def _terminal():
            if job["status"] == JobStatus.DONE.value:
                payload = json.dumps({
                    "job_id": job_id,
                    "subdomain": job.get("subdomain", ""),
                    "url": job.get("url", ""),
                    "progress": 100,
                })
                yield ServerSentEvent(data=payload, event="done")
            else:
                payload = json.dumps({
                    "job_id": job_id,
                    "error": job.get("error", "Job failed"),
                })
                yield ServerSentEvent(data=payload, event="error")
        return EventSourceResponse(_terminal())

    if svc is None:
        raise HTTPException(status_code=503, detail="Job queue unavailable")

    return EventSourceResponse(redis_job_stream(job_id))
```

- [ ] **Step 5: Run backend tests**

```bash
uv run pytest tests/test_job_stream.py tests/test_server.py -v
```
Expected: all PASS (existing server tests may need `svc=None` to stay on inline path)

- [ ] **Step 6: Update frontend `sse-client.ts`**

Split the single `streamRedesign` function into two:

```typescript
// web/src/lib/sse-client.ts

export type SSEEvent = {
  event: string
  data: Record<string, unknown>
}

/** Submit a redesign request and return the job_id. */
export async function submitRedesign(
  url: string,
  tier: "standard" | "premium" = "standard",
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
  const data = await resp.json()
  // Redis path returns { job_id }, inline fallback returns SSE stream
  if (data.job_id) return data.job_id
  throw new Error("No job_id returned from server")
}

/** Stream status events for a job. Reconnectable — yields SSEEvent objects. */
export async function* streamJobStatus(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080"
  const resp = await fetch(`${backendUrl}/jobs/${jobId}/stream`, { signal })
  if (!resp.ok || !resp.body) throw new Error(`Stream failed: ${resp.status}`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let currentEvent = "message"

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() ?? ""

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        try {
          const data = JSON.parse(line.slice(5).trim())
          yield { event: currentEvent, data }
          currentEvent = "message"
        } catch {
          // skip malformed
        }
      }
    }
  }
}
```

- [ ] **Step 7: Update `use-redesign.ts` to use job_id + store in URL**

Replace the `streamRedesign` call with the two-step flow. On job start, push `?job=<job_id>` to the URL. On mount, check for existing `?job=` param and reconnect.

```typescript
// In useRedesign, replace the SSE submission logic:

const startRedesign = useCallback(async (url: string) => {
  setState({ status: "connecting", url })
  const controller = new AbortController()
  abortRef.current = controller

  try {
    // Step 1: submit and get job_id
    const jobId = await submitRedesign(url, "standard", controller.signal)

    // Persist in URL so refresh can resume
    const params = new URLSearchParams(window.location.search)
    params.set("job", jobId)
    window.history.replaceState(null, "", `?${params}`)

    setState({
      status: "progress",
      currentStep: "crawling",
      domain: extractDomain(url),
      steps: STEPS.map((s) => ({ ...s, value: 0, status: "pending" as const })),
      tier: "standard",
      activities: [],
      discoveryItems: [],
      screenshot: undefined,
      jobId,
    })

    // Step 2: stream status events
    for await (const event of streamJobStatus(jobId, controller.signal)) {
      handleSseEvent(event)  // existing dispatch logic
    }
  } catch (err) {
    if (controller.signal.aborted) return
    setState({ status: "error", message: "Connection failed", url })
  }
}, [])

// On mount: resume from URL if job_id present
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  const jobId = params.get("job")
  if (jobId) {
    // Poll DB for current status and resume stream
    resumeJob(jobId)
  }
}, [])
```

Add `jobId` to the `progress` state variant:

```typescript
| {
    status: "progress"
    jobId: string        // NEW
    currentStep: string
    domain: string
    steps: StepState[]
    tier: "standard" | "premium"
    activities: ActivityItem[]
    discoveryItems: DiscoveryItem[]
    screenshot?: string
  }
```

- [ ] **Step 8: TypeScript check**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 9: Lint + commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
cd web && npx next lint
git add sastaspace/server.py web/src/lib/sse-client.ts web/src/hooks/use-redesign.ts tests/test_job_stream.py
git commit -m "feat: job_id-based tracking — POST /redesign returns job_id, add /jobs/{id}/stream SSE endpoint"
```

---

## Phase A — Agent Activity Stream + Discovery Feed

---

### Task 1: Add `progress_callback` to the Agno pipeline

**Files:**
- Modify: `sastaspace/agents/pipeline.py`

Note: `run_redesign_pipeline` returns `str`. `_run_normalizer` takes `(html, design_brief, settings)`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_pipeline_callback.py
"""Tests for pipeline progress callback."""
from unittest.mock import MagicMock, patch

from sastaspace.agents.pipeline import AGENT_MESSAGES, run_redesign_pipeline
from sastaspace.crawler import CrawlResult


def _crawl():
    return CrawlResult(
        url="https://example.com", title="Example", meta_description="",
        favicon_url="", html_source="<html></html>", screenshot_base64="",
        headings=[], navigation_links=[], text_content="Hello",
        images=[], colors=[], fonts=[], sections=[], error="",
    )


def test_progress_callback_called_for_each_agent():
    """progress_callback fires once per agent stage."""
    callback = MagicMock()
    mock_html = "<!DOCTYPE html><html><body>Test</body></html>"

    with (
        patch("sastaspace.agents.pipeline._run_crawl_analyst", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_design_strategist", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_copywriter", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_component_selector", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch("sastaspace.agents.pipeline._run_quality_reviewer",
              return_value=MagicMock(passed=True, overall_score=8, issues=[])),
        patch("sastaspace.agents.pipeline._run_normalizer", return_value=mock_html),
    ):
        from sastaspace.config import Settings
        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=callback)

    assert isinstance(result, str)   # returns str, not AgnoRedesignResult
    assert callback.call_count == 7
    event, data = callback.call_args_list[0][0]
    assert event == "agent_activity"
    assert "agent" in data and "message" in data and "step_progress" in data


def test_agent_messages_covers_all_agents():
    expected = {
        "crawl_analyst", "design_strategist", "copywriter",
        "component_selector", "html_generator", "quality_reviewer", "normalizer",
    }
    assert set(AGENT_MESSAGES.keys()) == expected


def test_progress_callback_none_is_safe():
    mock_html = "<!DOCTYPE html><html><body>Test</body></html>"
    with (
        patch("sastaspace.agents.pipeline._run_crawl_analyst", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_design_strategist", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_copywriter", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_component_selector", return_value=MagicMock()),
        patch("sastaspace.agents.pipeline._run_html_generator", return_value=mock_html),
        patch("sastaspace.agents.pipeline._run_quality_reviewer",
              return_value=MagicMock(passed=True, overall_score=8, issues=[])),
        patch("sastaspace.agents.pipeline._run_normalizer", return_value=mock_html),
    ):
        from sastaspace.config import Settings
        result = run_redesign_pipeline(_crawl(), Settings(), progress_callback=None)
    assert result == mock_html
```

- [ ] **Step 2: Run to verify fails**

```bash
uv run pytest tests/test_pipeline_callback.py -v
```
Expected: FAILED — `AGENT_MESSAGES` not importable

- [ ] **Step 3: Add `AGENT_MESSAGES` and `ProgressCallback` to `pipeline.py`**

After existing imports, add:

```python
from collections.abc import Callable

ProgressCallback = Callable[[str, dict], None] | None

AGENT_MESSAGES: dict[str, dict] = {
    "crawl_analyst":       {"message": "Analyzing your site's content and structure", "step_progress": 42},
    "design_strategist":   {"message": "Crafting your new design direction",           "step_progress": 50},
    "copywriter":          {"message": "Rewriting your copy for conversion",           "step_progress": 57},
    "component_selector":  {"message": "Selecting UI components for your industry",    "step_progress": 63},
    "html_generator":      {"message": "Building your new page",                       "step_progress": 68},
    "quality_reviewer":    {"message": "Reviewing design quality",                     "step_progress": 74},
    "normalizer":          {"message": "Finalizing your redesign",                     "step_progress": 78},
}
```

Change `run_redesign_pipeline` signature:

```python
def run_redesign_pipeline(
    crawl_result: CrawlResult,
    settings: Settings,
    progress_callback: ProgressCallback = None,
) -> str:
```

Inside the function body, add a local helper and call it before each agent:

```python
def _emit(agent_name: str) -> None:
    if progress_callback is None:
        return
    meta = AGENT_MESSAGES.get(agent_name, {"message": agent_name, "step_progress": 50})
    try:
        progress_callback("agent_activity", {
            "agent": agent_name,
            "message": meta["message"],
            "step_progress": meta["step_progress"],
        })
    except Exception:
        pass  # never let UI callback crash the pipeline

# Then before each _run_* call:
_emit("crawl_analyst")
site_analysis = _run_crawl_analyst(crawl_result, settings)

_emit("design_strategist")
design_brief = _run_design_strategist(site_analysis, crawl_result, settings)

_emit("copywriter")
copy_output = _run_copywriter(site_analysis, design_brief, crawl_result, settings)

_emit("component_selector")
component_selection = _run_component_selector(site_analysis, design_brief, settings)

_emit("html_generator")
html = _run_html_generator(...)  # keep existing args unchanged

_emit("quality_reviewer")
quality = _run_quality_reviewer(...)  # keep existing args unchanged

_emit("normalizer")
html = _run_normalizer(html, design_brief, settings)  # 3 args: html, design_brief, settings
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_pipeline_callback.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
git add sastaspace/agents/pipeline.py tests/test_pipeline_callback.py
git commit -m "feat(pipeline): add progress_callback for real-time agent activity streaming"
```

---

### Task 2: Thread callback through `agno_redesign` and `jobs.py`

**Files:**
- Modify: `sastaspace/redesigner.py`
- Modify: `sastaspace/jobs.py`

Critical: capture `get_running_loop()` **before** `to_thread`. Wrap callback in exception guard.

- [ ] **Step 1: Write failing test**

Add to `tests/test_pipeline_callback.py`:

```python
async def test_redesign_handler_emits_agent_activity(job_service, tmp_path):
    """redesign_handler publishes agent_activity events via the progress callback."""
    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

    job_id = "callback-test-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com", title="Example", meta_description="",
        favicon_url="", html_source="<html></html>", screenshot_base64="",
        headings=[], navigation_links=[], text_content="Hello",
        images=[], colors=[], fonts=[], sections=[], error="",
    )
    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    activity_events = []

    original_publish = job_service.publish_status
    async def capture(jid, event, data):
        if event == "agent_activity":
            activity_events.append(data)
        return await original_publish(jid, event, data)
    job_service.publish_status = capture

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler
        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(activity_events) >= 1
    assert all("agent" in e and "message" in e for e in activity_events)
```

- [ ] **Step 2: Run to verify fails**

```bash
uv run pytest tests/test_pipeline_callback.py::test_redesign_handler_emits_agent_activity -v
```

- [ ] **Step 3: Update `agno_redesign` in `redesigner.py`**

```python
from sastaspace.agents.pipeline import ProgressCallback

def agno_redesign(
    crawl_result: CrawlResult,
    settings,
    tier: str = "standard",
    progress_callback: "ProgressCallback" = None,
) -> str:
```

Pass it through to `run_redesign_pipeline`:

```python
result = run_redesign_pipeline(crawl_result, settings, progress_callback=progress_callback)
```

- [ ] **Step 4: Build thread-safe callback in `jobs.py`**

In `redesign_handler`, capture the loop **before** `to_thread`, then pass the callback:

```python
# Capture the running loop before entering the thread
loop = asyncio.get_running_loop()

def _on_agent_progress(event: str, data: dict) -> None:
    """Called synchronously from the pipeline thread — schedule publish on the event loop."""
    data["job_id"] = job_id
    try:
        asyncio.run_coroutine_threadsafe(
            job_service.publish_status(job_id, event, data),
            loop,
        )
    except Exception:
        pass  # never crash the pipeline thread over a UI event

html = await asyncio.to_thread(
    agno_redesign,
    crawl_result,
    settings,
    tier,
    _on_agent_progress,
)
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/test_pipeline_callback.py tests/test_jobs.py -v
```
Expected: all PASS

- [ ] **Step 6: Lint + commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
git add sastaspace/redesigner.py sastaspace/jobs.py tests/test_pipeline_callback.py
git commit -m "feat(jobs): thread progress_callback through agno_redesign with run_coroutine_threadsafe"
```

---

### Task 3: Emit `discovery` event after crawl

**Files:**
- Modify: `sastaspace/jobs.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_pipeline_callback.py`:

```python
async def test_redesign_handler_emits_discovery(job_service, tmp_path):
    """redesign_handler emits discovery event with real crawl data."""
    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

    job_id = "discovery-test-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com", title="Acme Corp", meta_description="We build things",
        favicon_url="", html_source="<html></html>", screenshot_base64="",
        headings=[], navigation_links=[], text_content="",
        images=[], colors=["#ff0000", "#0000ff"], fonts=["Inter"],
        sections=["hero", "footer"], error="",
    )
    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    discovery_events = []

    original_publish = job_service.publish_status
    async def capture(jid, event, data):
        if event == "discovery":
            discovery_events.append(data)
        return await original_publish(jid, event, data)
    job_service.publish_status = capture

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler
        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(discovery_events) == 1
    labels = [i["label"] for i in discovery_events[0]["items"]]
    assert "Title" in labels
    assert "Colors" in labels
```

- [ ] **Step 2: Run to verify fails**

```bash
uv run pytest tests/test_pipeline_callback.py::test_redesign_handler_emits_discovery -v
```

- [ ] **Step 3: Add discovery emit in `jobs.py`**

After the crawl success log, before the redesigning step:

```python
# Emit discovered site facts for the UI discovery grid
_discovery_items = []
if crawl_result.title:
    _discovery_items.append({"label": "Title", "value": crawl_result.title})
if crawl_result.colors:
    _discovery_items.append({"label": "Colors", "value": f"{len(crawl_result.colors)} detected"})
if crawl_result.sections:
    _discovery_items.append(
        {"label": "Sections", "value": f"{len(crawl_result.sections)} content sections"}
    )
if crawl_result.fonts:
    _discovery_items.append({"label": "Fonts", "value": crawl_result.fonts[0]})
if _discovery_items:
    await job_service.publish_status(
        job_id, "discovery", {"job_id": job_id, "items": _discovery_items}
    )
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest tests/test_pipeline_callback.py tests/test_jobs.py -v
```

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
git add sastaspace/jobs.py tests/test_pipeline_callback.py
git commit -m "feat(jobs): emit discovery event after crawl with real site data"
```

---

### Task 4: Handle new SSE events in the frontend hook

**Files:**
- Modify: `web/src/hooks/use-redesign.ts`

`ActivityItem` must include `agent` field for icon lookup. TypeScript narrowing must be explicit.

- [ ] **Step 1: Write failing test**

```typescript
// web/src/hooks/use-redesign.test.ts
import { describe, it, expect } from "vitest"
import type { ActivityItem, DiscoveryItem } from "@/hooks/use-redesign"

describe("use-redesign types", () => {
  it("ActivityItem has id, agent, message, timestamp", () => {
    const item: ActivityItem = {
      id: "1",
      agent: "design_strategist",
      message: "Crafting your design direction",
      timestamp: Date.now(),
    }
    expect(item.agent).toBe("design_strategist")
  })

  it("DiscoveryItem has label and value", () => {
    const item: DiscoveryItem = { label: "Colors", value: "4 detected" }
    expect(item.label).toBe("Colors")
  })
})
```

- [ ] **Step 2: Run to verify fails**

```bash
cd web && npx vitest run src/hooks/use-redesign.test.ts
```

- [ ] **Step 3: Export new types and extend progress state**

In `use-redesign.ts`:

```typescript
export type ActivityItem = {
  id: string
  agent: string      // e.g. "design_strategist"
  message: string
  timestamp: number
}

export type DiscoveryItem = {
  label: string
  value: string
}
```

Add to `progress` state variant:

```typescript
  | {
      status: "progress"
      jobId: string
      currentStep: string
      domain: string
      steps: StepState[]
      tier: "standard" | "premium"
      activities: ActivityItem[]
      discoveryItems: DiscoveryItem[]
      screenshot?: string
    }
```

Initialise in connecting → progress transition:

```typescript
activities: [],
discoveryItems: [],
screenshot: undefined,
```

Add event handlers (use explicit narrowing before setState):

```typescript
case "agent_activity": {
  if (state.status !== "progress") break
  const activity: ActivityItem = {
    id: `${Date.now()}-${Math.random()}`,
    agent: (event.data.agent as string) ?? "",
    message: (event.data.message as string) ?? "",
    timestamp: Date.now(),
  }
  setState((prev) => {
    if (prev.status !== "progress") return prev
    const updates: Partial<typeof prev> = {
      activities: [...prev.activities.slice(-9), activity],
    }
    if (event.data.step_progress) {
      updates.steps = prev.steps.map((s) =>
        s.name === "redesigning"
          ? { ...s, value: event.data.step_progress as number }
          : s
      )
    }
    return { ...prev, ...updates }
  })
  break
}

case "discovery": {
  setState((prev) => {
    if (prev.status !== "progress") return prev
    return { ...prev, discoveryItems: event.data.items as DiscoveryItem[] }
  })
  break
}

case "screenshot": {
  setState((prev) => {
    if (prev.status !== "progress") return prev
    return { ...prev, screenshot: event.data.screenshot_base64 as string }
  })
  break
}
```

- [ ] **Step 4: Run tests + TypeScript**

```bash
cd web && npx vitest run src/hooks/use-redesign.test.ts && npx tsc --noEmit
```
Expected: PASS, no type errors

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/use-redesign.ts web/src/hooks/use-redesign.test.ts
git commit -m "feat(frontend): add ActivityItem/DiscoveryItem state and new SSE event handlers"
```

---

### Task 5: Build `ActivityFeed` component

**Files:**
- Create: `web/src/components/progress/activity-feed.tsx`

Uses `item.agent` for icon lookup (not `item.message`).

- [ ] **Step 1: Create the component**

```tsx
// web/src/components/progress/activity-feed.tsx
"use client"

import { AnimatePresence, motion } from "motion/react"
import type { ActivityItem } from "@/hooks/use-redesign"

const AGENT_ICONS: Record<string, string> = {
  crawl_analyst:      "🔍",
  design_strategist:  "🎨",
  copywriter:         "✍️",
  component_selector: "🧩",
  html_generator:     "⚡",
  quality_reviewer:   "✓",
  normalizer:         "🔧",
}

interface ActivityFeedProps {
  activities: ActivityItem[]
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (activities.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5 w-full max-w-sm">
      <AnimatePresence mode="popLayout" initial={false}>
        {[...activities].reverse().slice(0, 5).map((item) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <span className="text-base leading-none w-5 text-center">
              {AGENT_ICONS[item.agent] ?? "→"}
            </span>
            <span>{item.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd web && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/progress/activity-feed.tsx
git commit -m "feat(frontend): ActivityFeed component with per-agent icons and animated entries"
```

---

### Task 6: Build `DiscoveryGrid` component

**Files:**
- Create: `web/src/components/progress/discovery-grid.tsx`

- [ ] **Step 1: Create the component**

```tsx
// web/src/components/progress/discovery-grid.tsx
"use client"

import { motion } from "motion/react"
import type { DiscoveryItem } from "@/hooks/use-redesign"

interface DiscoveryGridProps {
  items: DiscoveryItem[]
}

export function DiscoveryGrid({ items }: DiscoveryGridProps) {
  if (items.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="grid grid-cols-2 gap-2 w-full max-w-sm"
    >
      {items.map((item, i) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.08, duration: 0.3 }}
          className="rounded-lg border border-border/50 bg-muted/30 px-3 py-2"
        >
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className="text-sm font-medium text-foreground truncate">{item.value}</p>
        </motion.div>
      ))}
    </motion.div>
  )
}
```

- [ ] **Step 2: TypeScript check + commit**

```bash
cd web && npx tsc --noEmit
git add web/src/components/progress/discovery-grid.tsx
git commit -m "feat(frontend): DiscoveryGrid component for crawl result cards"
```

---

### Task 7: Shimmer pulse on active step indicator

**Files:**
- Modify: `web/src/components/progress/step-indicator.tsx`

- [ ] **Step 1: Update active step bar**

Import `motion` at the top: `import { motion } from "motion/react"`

Replace the progress bar render for `status === "active"`:

```tsx
{step.status === "active" ? (
  <div className="relative flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
    {/* Filled portion */}
    <motion.div
      className="absolute inset-y-0 left-0 rounded-full bg-foreground/80"
      style={{ width: `${step.value}%` }}
      animate={{ opacity: [0.7, 1, 0.7] }}
      transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
    />
    {/* Shimmer sweep — never looks frozen */}
    <motion.div
      className="absolute inset-y-0 w-16 bg-gradient-to-r from-transparent via-white/20 to-transparent"
      animate={{ x: ["-4rem", "100%"] }}
      transition={{ duration: 2.5, repeat: Infinity, ease: "linear", repeatDelay: 0.5 }}
    />
  </div>
) : (
  <Progress value={step.value} className="flex-1 h-1.5" />
)}
```

- [ ] **Step 2: TypeScript check + commit**

```bash
cd web && npx tsc --noEmit
git add web/src/components/progress/step-indicator.tsx
git commit -m "feat(frontend): shimmer pulse animation on active step bar"
```

---

### Task 8: Wire everything into `progress-view.tsx`

**Files:**
- Modify: `web/src/components/progress/progress-view.tsx`

- [ ] **Step 1: Update imports and layout**

Add imports:

```tsx
import { ActivityFeed } from "@/components/progress/activity-feed"
import { DiscoveryGrid } from "@/components/progress/discovery-grid"
```

In the progress state render, add in order:

```tsx
{/* Time expectation — shown immediately, reframes wait as quality signal */}
<p className="text-xs text-muted-foreground text-center">
  AI redesigns typically take 2–3 minutes. Real work happening here.
</p>

{/* Discovery grid — appears after crawl completes */}
<DiscoveryGrid items={state.discoveryItems} />

{/* Step indicators (existing) */}
{state.steps.map((step) => <StepIndicator key={step.name} step={step} />)}

{/* Live agent activity feed */}
<ActivityFeed activities={state.activities} />
```

Verify `state.discoveryItems` and `state.activities` are accessible — they are on `progress` state after Task 4.

- [ ] **Step 2: TypeScript check + all frontend tests**

```bash
cd web && npx tsc --noEmit && npx vitest run && npx next lint
```

- [ ] **Step 3: Run backend tests too**

```bash
uv run pytest tests/ -q
```

- [ ] **Step 4: Commit + push (Phase A complete)**

```bash
git add web/src/components/progress/progress-view.tsx
git commit -m "feat(frontend): wire ActivityFeed, DiscoveryGrid, time expectation into progress view"
git push origin main
```

**Phase A verification after deploy:**
1. Submit a URL on sastaspace.com
2. Within 10s: discovery grid appears with site title, colors, sections
3. During AI step: activity messages appear one by one with icons
4. Step bar shimmers continuously — never frozen
5. Page refresh: `?job=<id>` in URL reconnects to stream

---

## Phase B — Before/After Screenshot Teaser

---

### Task 9: Emit screenshot event from backend

**Files:**
- Modify: `sastaspace/jobs.py`

Guard against large screenshots (>500KB base64 ≈ 375KB raw) before emitting.

- [ ] **Step 1: Write failing test**

Add to `tests/test_pipeline_callback.py`:

```python
async def test_redesign_handler_emits_screenshot(job_service, tmp_path):
    """Emits screenshot event when screenshot is present and not too large."""
    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

    job_id = "screenshot-test-1"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com", title="Example", meta_description="",
        favicon_url="", html_source="<html></html>",
        screenshot_base64="iVBORw0KGgo=",  # small fake base64
        headings=[], navigation_links=[], text_content="",
        images=[], colors=[], fonts=[], sections=[], error="",
    )
    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    screenshot_events = []

    original_publish = job_service.publish_status
    async def capture(jid, event, data):
        if event == "screenshot":
            screenshot_events.append(data)
        return await original_publish(jid, event, data)
    job_service.publish_status = capture

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler
        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(screenshot_events) == 1
    assert screenshot_events[0]["screenshot_base64"] == "iVBORw0KGgo="


async def test_redesign_handler_skips_large_screenshot(job_service, tmp_path):
    """Does not emit screenshot if base64 exceeds 500KB."""
    from sastaspace.crawler import CrawlResult
    from sastaspace.database import create_job
    from sastaspace.deployer import DeployResult

    job_id = "screenshot-test-2"
    await create_job(job_id=job_id, url="https://example.com", client_ip="1.1.1.1")

    crawl_result = CrawlResult(
        url="https://example.com", title="Example", meta_description="",
        favicon_url="", html_source="<html></html>",
        screenshot_base64="A" * (500_001),  # 500KB+ — too large
        headings=[], navigation_links=[], text_content="",
        images=[], colors=[], fonts=[], sections=[], error="",
    )
    deploy_result = DeployResult(
        subdomain="example-com",
        index_path=tmp_path / "example-com" / "index.html",
        sites_dir=tmp_path,
    )
    mock_html = "<!DOCTYPE html><html><body>Done</body></html>"
    screenshot_events = []

    original_publish = job_service.publish_status
    async def capture(jid, event, data):
        if event == "screenshot":
            screenshot_events.append(data)
        return await original_publish(jid, event, data)
    job_service.publish_status = capture

    with (
        patch("sastaspace.crawler.crawl", new_callable=AsyncMock, return_value=crawl_result),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.deployer.deploy", return_value=deploy_result),
    ):
        from sastaspace.jobs import redesign_handler
        await redesign_handler(job_id, "https://example.com", "standard", job_service)

    assert len(screenshot_events) == 0  # skipped — too large
```

- [ ] **Step 2: Run to verify fails**

```bash
uv run pytest tests/test_pipeline_callback.py::test_redesign_handler_emits_screenshot tests/test_pipeline_callback.py::test_redesign_handler_skips_large_screenshot -v
```

- [ ] **Step 3: Add screenshot emit with size guard in `jobs.py`**

After the discovery emit:

```python
# Emit screenshot for before/after reveal — skip if too large for SSE
_MAX_SCREENSHOT_B64 = 500_000  # ~375KB raw PNG
if (
    crawl_result.screenshot_base64
    and len(crawl_result.screenshot_base64) <= _MAX_SCREENSHOT_B64
):
    await job_service.publish_status(
        job_id,
        "screenshot",
        {"job_id": job_id, "screenshot_base64": crawl_result.screenshot_base64},
    )
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest tests/test_pipeline_callback.py tests/test_jobs.py -v
```

- [ ] **Step 5: Lint + commit**

```bash
uv run ruff check sastaspace/ tests/ && uv run ruff format sastaspace/ tests/
git add sastaspace/jobs.py tests/test_pipeline_callback.py
git commit -m "feat(jobs): emit screenshot event after crawl with 500KB size guard"
```

---

### Task 10: Build `SiteScreenshot` component

**Files:**
- Create: `web/src/components/progress/site-screenshot.tsx`

- [ ] **Step 1: Create the component**

```tsx
// web/src/components/progress/site-screenshot.tsx
"use client"

import { motion } from "motion/react"

interface SiteScreenshotProps {
  screenshotBase64: string
  domain: string
}

export function SiteScreenshot({ screenshotBase64, domain }: SiteScreenshotProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative w-full max-w-sm rounded-xl overflow-hidden border border-border/50 shadow-lg"
    >
      <img
        src={`data:image/png;base64,${screenshotBase64}`}
        alt={`Current ${domain} website`}
        className="w-full object-cover object-top"
        style={{ filter: "saturate(0.3) brightness(0.85)", maxHeight: "200px" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
        <span className="text-xs text-white/80 font-medium">{domain} — before</span>
        <motion.span
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-xs text-white/60"
        >
          transforming…
        </motion.span>
      </div>
    </motion.div>
  )
}
```

- [ ] **Step 2: TypeScript check + commit**

```bash
cd web && npx tsc --noEmit
git add web/src/components/progress/site-screenshot.tsx
git commit -m "feat(frontend): SiteScreenshot component — desaturated before-state with overlay"
```

---

### Task 11: Wire screenshot into progress view

**Files:**
- Modify: `web/src/components/progress/progress-view.tsx`

- [ ] **Step 1: Add import and render**

```tsx
import { SiteScreenshot } from "@/components/progress/site-screenshot"
```

Between the time expectation text and the discovery grid:

```tsx
{state.screenshot && (
  <SiteScreenshot screenshotBase64={state.screenshot} domain={state.domain} />
)}
```

- [ ] **Step 2: Full check + push**

```bash
cd web && npx tsc --noEmit && npx vitest run && npx next lint
uv run pytest tests/ -q
git add web/src/components/progress/progress-view.tsx
git commit -m "feat(frontend): show current site screenshot during redesign wait (Phase B)"
git push origin main
```

---

## End-to-End Verification

After CI deploys:

| Time | User sees |
|---|---|
| 0s | Form submitted, `?job=<id>` appears in URL |
| ~4s | Crawl done — screenshot appears (desaturated, "transforming…") |
| ~8s | Discovery grid fades in: Title, Colors, Sections, Fonts |
| ~10s | "🔍 Analyzing your site's content" appears in feed |
| ~30s | "🎨 Crafting your new design direction" |
| ~90s | "✍️ Rewriting your copy for conversion" |
| … | Each agent announces itself; step bar shimmers throughout |
| ~3min | "done" event — auto-navigate to result |
| Refresh | `?job=<id>` in URL reconnects to stream, resumes from current state |
