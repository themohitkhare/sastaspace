# Testing Patterns

**Analysis Date:** 2026-03-21

## Test Framework

**Runner:**
- `pytest` 8.x
- Config: `pyproject.toml` `[tool.pytest.ini_options]`
- `asyncio_mode = "auto"` — all async tests run automatically without explicit `@pytest.mark.asyncio` decorator (though the decorator is still present in some tests)

**Async support:**
- `pytest-asyncio` 0.24.x

**HTTP testing:**
- `fastapi.testclient.TestClient` (synchronous HTTPX-based test client, no server startup)

**Run Commands:**
```bash
uv run pytest tests/ -v          # Run all tests with verbose output
make test                         # Same via Makefile
make ci                           # lint then test
```

No watch mode or coverage commands are configured. No `--cov` flags in Makefile.

## Test File Organization

**Location:** Separate `tests/` directory at project root — not co-located with source

**Naming:** `test_{module}.py` mirrors source module name exactly:
```
sastaspace/crawler.py     → tests/test_crawler.py
sastaspace/redesigner.py  → tests/test_redesigner.py
sastaspace/deployer.py    → tests/test_deployer.py
sastaspace/server.py      → tests/test_server.py
sastaspace/cli.py         → tests/test_cli.py
sastaspace/config.py      → tests/test_config.py
```

**`tests/__init__.py`:** Present but empty — makes `tests/` a package.

## Test Structure

**Suite Organization:**
```python
# tests/test_deployer.py

# --- derive_subdomain tests ---

def test_derive_subdomain_simple():
    assert derive_subdomain("https://acme.com") == "acme-com"

# --- deploy() tests ---

def test_deploy_creates_index_html(tmp_path):
    ...

# --- load_registry tests ---

def test_load_registry_returns_empty_list_when_missing(tmp_path):
    ...
```

Comment headers (`# --- name ---`) group tests by function under test within a single file.

**Naming:**
- `test_{what it does}` describing the expected behavior: `test_deploy_creates_index_html`, `test_crawl_handles_timeout_error`, `test_raises_on_missing_doctype`
- Names are complete sentences describing the assertion, not the code path

**Docstrings on tests:**
Used selectively on non-obvious tests to clarify intent:
```python
def test_raises_on_crawl_error():
    """redesign() raises before calling the API when CrawlResult.error is set."""
```

## Mocking

**Framework:** `unittest.mock` — `patch`, `MagicMock`, `AsyncMock`

**Import pattern:**
```python
from unittest.mock import AsyncMock, MagicMock, patch
```

**Async mocking (Playwright):**
Context managers and async methods are mocked by configuring `__aenter__` and `__aexit__` on the mock:
```python
with patch("sastaspace.crawler.async_playwright") as mock_pw:
    mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_pw.return_value)
    mock_pw.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_pw.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_context.new_page = AsyncMock(return_value=mock_page)
```

**OpenAI client mocking:**
A builder function creates a fully configured mock chain:
```python
def make_mock_client(response_text: str):
    mock_message = MagicMock()
    mock_message.content = response_text
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
    result = redesign(make_crawl_result())
```

**subprocess / side-effect mocking:**
`side_effect` is used to control stateful behavior across repeated calls:
```python
call_count = {"n": 0}

def mock_listening(port):
    call_count["n"] += 1
    return call_count["n"] > 2

with patch("sastaspace.server._is_port_listening", side_effect=mock_listening):
    ...
```

**`patch` scope:** All patches use `with patch(...)` context managers scoped to individual test functions. No module-level patches.

**Multi-patch pattern (Python 3.10+ parenthesized `with`):**
```python
with (
    patch("sastaspace.cli.crawl", mock_crawl),
    patch("sastaspace.cli.redesign", mock_redesign),
    patch("sastaspace.cli.ensure_running", mock_ensure),
    patch("sastaspace.cli.webbrowser.open"),
):
    result = runner.invoke(...)
```

**What is mocked:**
- External I/O: Playwright browser launch, OpenAI API client, subprocess spawning, `webbrowser.open`, `time.sleep`, `time.time`
- Dependencies at their import sites in the module under test (e.g., `"sastaspace.redesigner.OpenAI"` not `"openai.OpenAI"`)

**What is NOT mocked:**
- Filesystem operations — all file I/O runs against `tmp_path` (pytest's real temp directory fixture)
- Pure logic functions: `derive_subdomain()`, `_clean_html()`, `_validate_html()`
- `Settings` defaults (tested directly, with `monkeypatch.setenv` for overrides)

## Fixtures and Factories

**Pytest built-in fixtures used:**
- `tmp_path` — real temporary directory, used in `test_deployer.py`, `test_server.py`, `test_cli.py`
- `monkeypatch` — used in `test_config.py` and `test_cli.py` for env var overrides

**Local fixtures defined in `test_cli.py`:**
```python
@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def sites_dir(tmp_path):
    d = tmp_path / "sites"
    d.mkdir()
    return d
```

**Builder functions (not fixtures):**
Module-level helper functions construct test data objects and are called directly:
```python
# tests/test_crawler.py
def make_mock_page(title="Test Site", meta_desc="A test site", html="...", screenshot_bytes=b"..."):
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)
    ...
    return page

# tests/test_redesigner.py
def make_crawl_result(url="https://acme.com", title="Acme", screenshot_b64=None):
    return CrawlResult(url=url, title=title, ...)

def make_mock_client(response_text: str):
    ...

# tests/test_server.py
def make_test_sites(tmp_path: Path) -> Path:
    ...

def make_test_client(sites_dir: Path):
    from sastaspace.server import make_app
    app = make_app(sites_dir)
    return TestClient(app)
```

**Constants in test files:**
```python
SAMPLE_HTML = "<!DOCTYPE html><html><body>hi</body></html>"
FAKE_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20).decode()
```

## Coverage

**Requirements:** None enforced — no `--cov` flag, no minimum threshold configured

**View Coverage:**
```bash
uv run pytest tests/ --cov=sastaspace --cov-report=term-missing
```
(Not configured in Makefile; must be run manually)

## Test Types

**Unit Tests:**
- Pure function tests with no mocking: `test_deployer.py` (all `derive_subdomain`, `load_registry` tests), `test_config.py`, `test_redesigner.py` HTML cleaning/validation tests
- Scope: single function, single behavior per test

**Integration Tests:**
- CLI pipeline tests in `test_cli.py` that invoke `Click` commands end-to-end via `CliRunner`, with only external I/O mocked
- FastAPI route tests in `test_server.py` using `TestClient` against a real `make_app()` instance with real `tmp_path` filesystem

**Async Tests:**
- `test_crawler.py` tests for `crawl()` are `async def` with `@pytest.mark.asyncio`; pytest-asyncio runs them via `asyncio_mode = "auto"`

**E2E Tests:** Not present — no real network calls or browser automation in tests

## Common Patterns

**Async test:**
```python
@pytest.mark.asyncio
async def test_crawl_returns_crawl_result():
    """crawl() should return a CrawlResult with title and screenshot populated."""
    mock_page = make_mock_page(title="Acme Inc", html="<html><body><h1>Acme</h1></body></html>")

    with patch("sastaspace.crawler.async_playwright") as mock_pw:
        ...
        result = await crawl("https://acme.com")

    assert isinstance(result, CrawlResult)
    assert result.error == ""
```

**Exception testing:**
```python
def test_raises_on_empty_response():
    mock_client = make_mock_client("")

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="empty"):
            redesign(make_crawl_result())
```

**Verifying a mock was NOT called:**
```python
def test_raises_on_crawl_error():
    bad_result = make_crawl_result()
    bad_result.error = "Timeout"

    mock_client = make_mock_client("")
    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        with pytest.raises(RedesignError, match="crawl failed"):
            redesign(bad_result)

    mock_client.chat.completions.create.assert_not_called()
```

**Inspecting call arguments:**
```python
def test_client_called_with_image_when_screenshot_present():
    mock_client = make_mock_client(SAMPLE_HTML)

    with patch("sastaspace.redesigner.OpenAI", return_value=mock_client):
        redesign(make_crawl_result(screenshot_b64=FAKE_PNG_B64))

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][-1]["content"]
    image_blocks = [c for c in user_content if c.get("type") == "image_url"]
    assert len(image_blocks) == 1
```

**Filesystem-based test with `tmp_path`:**
```python
def test_deploy_creates_index_html(tmp_path):
    result = deploy(url="https://acme.com", html=SAMPLE_HTML, sites_dir=tmp_path)
    index = tmp_path / result.subdomain / "index.html"
    assert index.exists()
    assert index.read_text() == SAMPLE_HTML
```

**`monkeypatch.setenv` for config overrides:**
```python
def test_settings_override_port(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "9090")
    s = Settings()
    assert s.server_port == 9090
```

---

*Testing analysis: 2026-03-21*
