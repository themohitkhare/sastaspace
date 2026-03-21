# Testing Patterns

**Analysis Date:** 2026-03-21

## Test Frameworks

### Frontend (TypeScript/React)

**Unit/Integration Runner:**
- Vitest — config: `web/vitest.config.ts`
- Environment: `jsdom`
- Globals enabled (`globals: true`) — no need to import `describe`/`it`/`expect` in test files
- Setup file: `web/vitest.setup.ts` — imports `@testing-library/jest-dom/vitest`
- Path alias `@/` available in tests (mirrors production config)
- E2E tests excluded from Vitest: `exclude: ['**/e2e/**']`

**E2E Runner:**
- Playwright — config: `web/playwright.config.ts`
- Browser: Chromium only (`Desktop Chrome` device profile)
- Sequential execution: `fullyParallel: false`, `workers: 1`
- `BASE_URL` env var controls target — defaults to `http://localhost:3000`
- Docker-aware: when `BASE_URL` is set, no `webServer` block is added (assumes app already running)

### Backend (Python)

**Runner:**
- pytest — config in `pyproject.toml` under `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async test functions run automatically without `@pytest.mark.asyncio`
- Test discovery: `tests/` directory

**Run Commands:**
```bash
# Frontend unit tests
cd web && npm run test              # Run all Vitest tests once
cd web && npm run test:coverage     # With coverage (vitest run --coverage)

# Frontend E2E tests
cd web && npm run test:e2e          # Playwright headless
cd web && npm run test:e2e:headed   # Playwright with browser visible

# Backend tests
uv run pytest tests/ -v            # Run all Python tests verbose
make test                          # Same via Makefile

# Full CI check (backend)
make ci                            # lint + test

# E2E in Docker (full stack)
docker compose --profile test up   # Runs tests service after frontend is healthy
```

## Test File Organization

**Frontend:**
- Unit/integration tests: `web/src/__tests__/` (separate directory, not co-located)
- Naming: `{subject}.test.ts` or `{subject}.test.tsx`
- E2E tests: `web/e2e/` directory
- E2E naming: `{feature}.spec.ts`

```
web/
├── src/
│   └── __tests__/
│       ├── contact-form.test.tsx      # Component test
│       ├── url-input-form.test.tsx    # Component test
│       ├── sse-client.test.ts         # Lib test
│       ├── url-utils.test.ts          # Lib test
│       └── api-contact.test.ts        # API route test
└── e2e/
    └── sastaspace.spec.ts             # Full E2E spec
```

**Backend:**
- Tests in `tests/` at project root (not inside `sastaspace/` package)
- Naming: `test_{module}.py` mirrors source module name
- Shared fixtures in `tests/conftest.py`

```
tests/
├── conftest.py           # Shared fixtures
├── test_server.py        # FastAPI route tests
├── test_crawler.py       # Crawler unit tests
├── test_deployer.py      # Deployer unit tests
├── test_redesigner.py    # Redesigner unit tests
├── test_config.py        # Settings tests
└── test_cli.py           # CLI tests
```

## Test Structure

**Frontend Vitest — suite organization:**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('ComponentName or functionName', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.stubEnv('ENV_VAR', 'value')
  })

  it('describes the expected behavior', () => {
    // arrange -> act -> assert
  })
})
```

**Frontend Playwright — test organization:**
```typescript
import { test, expect, type Page } from "@playwright/test";

// Helper functions defined at top of file
async function hasHorizontalScroll(page: Page): Promise<boolean> { ... }

// Section comments using ASCII art dividers
// --- 1. Section title --------------------------------------------------------
test.describe("Feature - context", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(BASE);
  });

  test("describes behavior", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /text/i })).toBeVisible();
  });
});
```

**Backend pytest — test organization:**
```python
# tests/test_module.py
from unittest.mock import AsyncMock, patch
import pytest

# Helper factory functions at top of file
def make_test_client(sites_dir: Path):
    from sastaspace.server import make_app
    app = make_app(sites_dir)
    return TestClient(app)

# --- Section separator comments ---

def test_function_name(tmp_path):
    # Arrange
    result = deploy(url="https://acme.com", html=HTML, sites_dir=tmp_path)
    # Assert
    assert result.subdomain == "acme-com"
```

## Mocking

**Frontend — Vitest mocking patterns:**

Third-party UI libraries mocked at module level to avoid rendering complexity:
```typescript
// Mock animation library
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}))

// Mock icon library
vi.mock('lucide-react', () => ({
  Loader2: () => <svg data-testid="loader-icon" />,
}))

// Mock CAPTCHA widget
vi.mock('@marsidev/react-turnstile', () => ({
  Turnstile: () => null,
}))
```

Environment variables mocked via `vi.stubEnv`:
```typescript
beforeEach(() => {
  vi.restoreAllMocks()
  vi.stubEnv('NEXT_PUBLIC_ENABLE_TURNSTILE', 'false')
  vi.stubEnv('RESEND_API_KEY', 'test-key')
})
```

External SDK mocked before import (critical ordering — mock must precede import of the module under test):
```typescript
// vi.mock hoisting means this executes before the import below
vi.mock('resend', () => ({
  Resend: function () {
    return { emails: { send: mockSend } }
  },
}))
import { POST } from '@/app/api/contact/route'
```

`fetch` mocked via `vi.spyOn` for network calls:
```typescript
vi.spyOn(globalThis, 'fetch').mockResolvedValue({
  ok: true,
  body: createSSEStream(chunks),
} as unknown as Response)
```

**Frontend — Playwright route interception:**
```typescript
await page.route("**/redesign", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body: sseBody,
  });
});
```

**Backend — Python mocking patterns:**

`unittest.mock.patch` as context manager (parenthesized for multi-patch):
```python
with (
    patch("sastaspace.server.crawl", new_callable=AsyncMock, return_value=mock_crawl_result) as m_crawl,
    patch("sastaspace.server.redesign", return_value=mock_html) as m_redesign,
    patch("sastaspace.server.deploy", return_value=mock_deploy_result) as m_deploy,
):
    app = make_app(tmp_sites)
    client = TestClient(app)
```

Mock page object factory for Playwright browser pages:
```python
def make_mock_page(title="Test Site", ...):
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)
    page.content = AsyncMock(return_value=html)
    return page
```

## Fixtures and Factories

**Backend — pytest fixtures in `tests/conftest.py`:**
```python
@pytest.fixture
def tmp_sites(tmp_path):
    """Create a temporary sites directory."""
    sites = tmp_path / "sites"
    sites.mkdir()
    return sites

@pytest.fixture
def mock_crawl_result():
    """A successful CrawlResult for testing."""
    return CrawlResult(url="https://example.com", ...)

@pytest.fixture
def redesign_client(tmp_sites, mock_crawl_result, mock_deploy_result):
    """TestClient with mocked pipeline functions for /redesign testing."""
    # Patches crawl/redesign/deploy and yields a TestClient
    ...
    yield client
```

**Frontend — helper factories are local to each test file (no shared fixtures):**
```typescript
// API route tests: inline request factory
function makeRequest(body: Record<string, unknown>): NextRequest {
  return new NextRequest('http://localhost:3000/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// SSE tests: stream factory
function createSSEStream(chunks: string[]): ReadableStream<Uint8Array> { ... }

// E2E tests: SSE payload builder
function buildSSE(events: Array<{ event: string; data: Record<string, unknown> }>): string { ... }
```

`tmp_path` pytest built-in fixture used universally for filesystem isolation — no custom temp directory logic.

## Coverage

**Requirements:** No enforced coverage threshold detected.

**View Coverage:**
```bash
cd web && npm run test:coverage    # Vitest HTML/text coverage report
```

## Test Types

**Unit Tests (Vitest / pytest):**
- Scope: individual functions and pure logic
- `web/src/__tests__/url-utils.test.ts` — tests `validateUrl` and `extractDomain` with no mocking
- `web/src/__tests__/sse-client.test.ts` — tests SSE stream parsing with mocked `fetch`
- `tests/test_deployer.py` — tests `derive_subdomain` and `deploy()` with real `tmp_path` filesystem
- `tests/test_crawler.py` — tests internal extraction helpers with real `BeautifulSoup` objects

**Integration Tests (Vitest / pytest TestClient):**
- Scope: component rendering + behavior, or API route with mocked external services
- `web/src/__tests__/contact-form.test.tsx` — renders `ContactForm`, fires DOM events, asserts output
- `web/src/__tests__/api-contact.test.ts` — calls Next.js Route Handler directly via `NextRequest`
- `tests/test_server.py` — calls FastAPI routes via `TestClient` with real filesystem via `tmp_path`

**E2E Tests (Playwright):**
- Scope: full browser against running application stack
- File: `web/e2e/sastaspace.spec.ts`
- Sections covered: landing page desktop (1280px), landing page mobile (375px), result page structure, contact form presence/fields/layout, contact form client-side validation, contact form mobile (375px), API routes via `request` fixture, iframe recursion detection, landing-to-progress transition, SSE progress flow with mocked backend
- Runs against `http://localhost:3000` locally or `http://frontend:3000` in Docker network

## Common Patterns

**Async Testing (Vitest):**
```typescript
it('yields parsed SSE events', async () => {
  // mock fetch before calling async generator
  const events = []
  for await (const event of streamRedesign('https://test.com', 'http://localhost:8080')) {
    events.push(event)
  }
  expect(events[0].event).toBe('crawling')
})
```

**Async Testing (pytest with asyncio_mode = "auto"):**
```python
# No decorator needed — asyncio_mode = "auto" handles it
async def test_crawl_returns_result():
    result = await crawl("https://example.com")
    assert result.url == "https://example.com"
```

**Error/Status Testing (API routes):**
```typescript
it('returns 400 when name is missing', async () => {
  const req = makeRequest({ name: '', email: 'test@test.com', message: 'Hello', ... })
  const res = await POST(req)
  expect(res.status).toBe(400)
  const data = await res.json()
  expect(data.error).toBe('All fields are required')
})
```

**Responsive/Layout Testing (Playwright):**
```typescript
// Always set viewport explicitly before navigation
await page.setViewportSize({ width: 375, height: 812 });
// Check element dimensions
const box = await btn.boundingBox();
expect(box!.height).toBeGreaterThanOrEqual(44);
```

**What to Mock:**
- Third-party UI widgets that fail in jsdom: animations (`motion/react`), CAPTCHA (`@marsidev/react-turnstile`)
- External network calls: `fetch`, `Resend` email SDK
- Playwright/Chromium browser when testing crawler logic in Python
- Pipeline dependencies in FastAPI route tests: `crawl`, `redesign`, `deploy`

**What NOT to Mock:**
- Pure utility functions (`validateUrl`, `extractDomain`, `derive_subdomain`) — use real inputs
- Filesystem operations — use `tmp_path` for real isolation
- FastAPI request/response cycle — use `TestClient` directly
- DOM and React rendering — use `@testing-library/react` with real jsdom
- BeautifulSoup HTML parsing — use real HTML strings in Python unit tests
