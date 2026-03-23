# tests/test_server.py
import asyncio
import json
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from sastaspace.config import Settings
from sastaspace.crawler import CrawlResult
from sastaspace.server import _is_port_listening, ensure_running, make_app

SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Acme</h1></body></html>"


def make_test_sites(tmp_path: Path) -> Path:
    """Create a minimal sites/ directory for testing."""
    sites = tmp_path / "sites"
    sites.mkdir()

    (sites / "acme-com").mkdir()
    (sites / "acme-com" / "index.html").write_text(SAMPLE_HTML)

    registry = [
        {
            "subdomain": "acme-com",
            "original_url": "https://acme.com",
            "timestamp": "2026-01-01T00:00:00Z",
            "status": "deployed",
        },
    ]
    (sites / "_registry.json").write_text(json.dumps(registry))

    return sites


def make_test_client(sites_dir: Path):
    app = make_app(sites_dir)
    return TestClient(app)


def test_root_returns_html_listing(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/", timeout=10)
    assert resp.status_code == 200
    assert "acme-com" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_root_shows_link_to_site(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/", timeout=10)
    assert resp.status_code == 200
    assert "https://acme.com" in resp.text or "acme-com" in resp.text


def test_site_route_serves_index_html(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/acme-com/", timeout=10)
    assert resp.status_code == 200
    assert "<h1>Acme</h1>" in resp.text


def test_site_route_without_trailing_slash(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/acme-com/", follow_redirects=True, timeout=10)
    assert resp.status_code == 200


def test_unknown_site_returns_404(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/nonexistent/", timeout=10)
    assert resp.status_code == 404


def test_root_with_empty_registry(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()
    client = make_test_client(sites)

    resp = client.get("/", timeout=10)
    assert resp.status_code == 200
    assert "No sites" in resp.text


# --- ensure_running() tests ---


def test_ensure_running_returns_port_when_already_listening(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()
    (sites / ".server_port").write_text("8080")

    with patch("sastaspace.server._is_port_listening", return_value=True):
        port = ensure_running(sites, preferred_port=8080)

    assert port == 8080


def test_ensure_running_spawns_subprocess_when_not_listening(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()

    call_count = {"n": 0}

    def mock_listening(port):
        call_count["n"] += 1
        return call_count["n"] > 2

    mock_popen = MagicMock()

    with (
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen", return_value=mock_popen) as mock_popen_cls,
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", side_effect=[0.0, 0.5, 1.0, 10.0]),
    ):
        port = ensure_running(sites, preferred_port=8080)

    assert mock_popen_cls.called
    port_file = sites / ".server_port"
    assert port_file.exists()
    assert int(port_file.read_text()) == port


def test_ensure_running_tries_next_port_when_in_use(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()

    def mock_listening(port):
        # Port 8080 is in use, 8081 is free
        return port == 8080

    with (
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen"),
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", side_effect=[0.0, 0.1, 10.0]),
    ):
        port = ensure_running(sites, preferred_port=8080)

    assert port == 8081


# --- Config tests ---


def test_config_cors_origins_default():
    """Settings() has cors_origins == ["http://localhost:3000"]."""
    s = Settings()
    assert s.cors_origins == ["http://localhost:3000"]


def test_config_rate_limit_defaults():
    """Settings() has rate_limit_max == 3, rate_limit_window_seconds == 3600."""
    s = Settings()
    assert s.rate_limit_max == 3
    assert s.rate_limit_window_seconds == 3600


def test_config_cors_origins_from_env(monkeypatch):
    """CORS_ORIGINS="http://a.com,http://b.com" parses to list of 2."""
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com")
    s = Settings()
    assert s.cors_origins == ["http://a.com", "http://b.com"]


# --- CORS tests ---


def test_cors_allows_configured_origin(test_client):
    """OPTIONS preflight from http://localhost:3000 returns access-control-allow-origin header."""
    resp = test_client.options(
        "/redesign",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
        timeout=10,
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin(test_client):
    """OPTIONS preflight from http://evil.com does NOT return ACAO matching evil.com."""
    resp = test_client.options(
        "/redesign",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
        timeout=10,
    )
    assert resp.headers.get("access-control-allow-origin") != "http://evil.com"


# --- /redesign endpoint tests (Plan 01-02) ---


def parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into list of {event, data} dicts."""
    events = []
    current: dict = {}
    for line in text.split("\n"):
        if line.startswith("event:"):
            current["event"] = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            raw = line.split(":", 1)[1].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def test_redesign_sse_stream(redesign_client):
    """POST /redesign with valid URL returns 200 with text/event-stream."""
    resp = redesign_client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


def test_sse_event_names(redesign_client):
    """SSE stream contains events crawling, redesigning, deploying, done in order."""
    resp = redesign_client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    event_names = [e["event"] for e in events if "event" in e]
    assert "crawling" in event_names
    assert "redesigning" in event_names
    assert "deploying" in event_names
    assert "done" in event_names
    # Verify order
    idx_c = event_names.index("crawling")
    idx_r = event_names.index("redesigning")
    idx_dp = event_names.index("deploying")
    idx_d = event_names.index("done")
    assert idx_c < idx_r < idx_dp < idx_d


def test_sse_done_event_payload(redesign_client):
    """done event data has job_id, message, progress=100, url, subdomain."""
    resp = redesign_client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1
    data = done_events[0]["data"]
    assert "job_id" in data
    assert data["progress"] == 100
    assert data["subdomain"] == "example-com"
    assert data["url"] == "/example-com/"


def test_to_thread_wrapping(tmp_sites, mock_crawl_result, mock_deploy_result):
    """agno_redesign() and deploy() are called; crawl() is awaited directly."""
    mock_html = "<html><body><p>OK</p></body></html>"
    with (
        patch(
            "sastaspace.routes.sse.crawl",
            new_callable=AsyncMock,
            return_value=mock_crawl_result,
        ) as m_crawl,
        patch(
            "sastaspace.redesigner.agno_redesign",
            return_value=mock_html,
        ) as m_redesign,
        patch(
            "sastaspace.server.deploy",
            return_value=mock_deploy_result,
        ) as m_deploy,
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        resp = client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
        assert resp.status_code == 200

        m_crawl.assert_called_once_with("https://example.com")
        m_redesign.assert_called_once()
        m_deploy.assert_called_once()


def test_concurrency_cap(tmp_sites, mock_crawl_result, mock_deploy_result):
    """Second request while first is running returns 429."""
    block = threading.Event()
    proceed = threading.Event()

    original_crawl_result = mock_crawl_result

    async def slow_crawl(url):
        proceed.set()
        # Block in a thread-safe way
        await asyncio.get_event_loop().run_in_executor(None, block.wait, 5)
        return original_crawl_result

    mock_html = "<html><body>OK</body></html>"
    with (
        patch("sastaspace.routes.sse.crawl", side_effect=slow_crawl),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch(
            "sastaspace.server.deploy",
            return_value=mock_deploy_result,
        ),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)

        results: dict = {}

        def first_request():
            results["first"] = client.post(
                "/redesign", json={"url": "https://example.com"}, timeout=10
            )

        t = threading.Thread(target=first_request)
        t.start()
        proceed.wait(timeout=5)

        # Second request should get 429
        resp = client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
        assert resp.status_code == 429
        assert "already in progress" in resp.json()["error"]

        block.set()
        t.join(timeout=5)


def test_rate_limit(tmp_sites, mock_crawl_result, mock_deploy_result):
    """4th request from same non-localhost IP returns 429 with retry_after."""
    mock_html = "<html><body>OK</body></html>"
    with (
        patch(
            "sastaspace.routes.sse.crawl",
            new_callable=AsyncMock,
            return_value=mock_crawl_result,
        ),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch(
            "sastaspace.server.deploy",
            return_value=mock_deploy_result,
        ),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        headers = {"X-Forwarded-For": "1.2.3.4"}

        # First 3 requests should succeed
        for i in range(3):
            resp = client.post(
                "/redesign",
                json={"url": "https://example.com"},
                headers=headers,
                timeout=10,
            )
            assert resp.status_code == 200, f"Request {i + 1} should succeed"

        # 4th request should be rate limited
        resp = client.post(
            "/redesign",
            json={"url": "https://example.com"},
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 429
        data = resp.json()
        assert "Rate limit exceeded" in data["error"]
        assert "retry_after" in data


def test_rate_limit_localhost_exempt(tmp_sites, mock_crawl_result, mock_deploy_result):
    """Requests from 127.0.0.1 bypass rate limiting."""
    mock_html = "<html><body>OK</body></html>"
    with (
        patch(
            "sastaspace.routes.sse.crawl",
            new_callable=AsyncMock,
            return_value=mock_crawl_result,
        ),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch(
            "sastaspace.server.deploy",
            return_value=mock_deploy_result,
        ),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        # TestClient reports host as "testclient", so use header
        headers = {"X-Forwarded-For": "127.0.0.1"}

        # Make 5 requests -- all should succeed (localhost exempt)
        for i in range(5):
            resp = client.post(
                "/redesign",
                json={"url": "https://example.com"},
                headers=headers,
                timeout=10,
            )
            assert resp.status_code == 200, f"Request {i + 1} should succeed (localhost exempt)"


def test_error_crawl_failure(tmp_sites):
    """crawl error emits error SSE event with user-facing message."""
    failed_crawl = CrawlResult(
        url="https://example.com",
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        error="timeout",
    )
    with patch(
        "sastaspace.routes.sse.crawl",
        new_callable=AsyncMock,
        return_value=failed_crawl,
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        resp = client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) >= 1
        assert "Could not reach that website" in error_events[0]["data"]["error"]


def test_error_redesign_failure(tmp_sites, mock_crawl_result):
    """redesign exception emits error SSE event."""
    with (
        patch(
            "sastaspace.routes.sse.crawl",
            new_callable=AsyncMock,
            return_value=mock_crawl_result,
        ),
        patch(
            "sastaspace.redesigner.agno_redesign",
            side_effect=Exception("API down"),
        ),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        resp = client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) >= 1
        assert "Redesign service unavailable" in error_events[0]["data"]["error"]


# --- get_client_ip coverage ---


def test_get_client_ip_cf_connecting_ip(tmp_sites, mock_crawl_result, mock_deploy_result):
    """Line 57: get_client_ip returns cf-connecting-ip header."""
    mock_html = "<html><body>OK</body></html>"
    with (
        patch(
            "sastaspace.routes.sse.crawl", new_callable=AsyncMock, return_value=mock_crawl_result
        ),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.server.deploy", return_value=mock_deploy_result),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)
        # cf-connecting-ip should be used; since it's a non-localhost IP, rate limiting applies
        resp = client.post(
            "/redesign",
            json={"url": "https://example.com"},
            headers={"cf-connecting-ip": "5.6.7.8"},
            timeout=10,
        )
        assert resp.status_code == 200


def test_get_client_ip_unknown_no_client(tmp_sites, mock_crawl_result, mock_deploy_result):
    """Line 63: get_client_ip returns 'unknown' when request.client is None."""
    mock_html = "<html><body>OK</body></html>"
    with (
        patch(
            "sastaspace.routes.sse.crawl", new_callable=AsyncMock, return_value=mock_crawl_result
        ),
        patch("sastaspace.redesigner.agno_redesign", return_value=mock_html),
        patch("sastaspace.server.deploy", return_value=mock_deploy_result),
    ):
        app = make_app(tmp_sites)
        client = TestClient(app)

        # Patch Request.client to return None to hit the "unknown" branch
        with patch(
            "starlette.requests.Request.client",
            new_callable=lambda: property(lambda self: None),
        ):
            resp = client.post("/redesign", json={"url": "https://example.com"}, timeout=10)
            assert resp.status_code == 200


# --- index route registry decode error ---


def test_index_with_corrupt_registry(tmp_path):
    """Lines 186-187: index route handles registry JSON decode error."""
    sites = tmp_path / "sites"
    sites.mkdir()
    (sites / "_registry.json").write_text("not json {{{")
    client = make_test_client(sites)
    resp = client.get("/", timeout=10)
    assert resp.status_code == 200
    assert "No sites" in resp.text


# --- serve_site_asset route ---


def test_serve_site_asset_existing_file(tmp_path):
    """Lines 249-250: serve_site_asset returns existing asset file."""
    sites = make_test_sites(tmp_path)
    (sites / "acme-com" / "style.css").write_text("body { color: red; }")
    client = make_test_client(sites)
    resp = client.get("/acme-com/style.css", timeout=10)
    assert resp.status_code == 200
    assert "color: red" in resp.text


def test_serve_site_asset_fallback_index(tmp_path):
    """Lines 253-254: serve_site_asset falls back to index.html for unknown paths."""
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)
    resp = client.get("/acme-com/some/nested/path", timeout=10)
    assert resp.status_code == 200
    assert "<h1>Acme</h1>" in resp.text


def test_serve_site_asset_404(tmp_path):
    """Line 255: serve_site_asset returns 404 when no index.html exists."""
    sites = tmp_path / "sites"
    sites.mkdir()
    (sites / "ghost").mkdir()
    # No index.html in ghost/
    client = make_test_client(sites)
    resp = client.get("/ghost/some-file.js", timeout=10)
    assert resp.status_code == 404


# --- _is_port_listening ---


def test_is_port_listening_false():
    """Lines 261-263: _is_port_listening reports unused port as not listening."""
    # Use a very unlikely port
    assert _is_port_listening(19999) is False


# --- ensure_running port_file ValueError/OSError ---


def test_ensure_running_port_file_value_error(tmp_path):
    """Lines 281-282: ensure_running handles ValueError from corrupt port file."""
    sites = tmp_path / "sites"
    sites.mkdir()
    (sites / ".server_port").write_text("not-a-number")

    call_count = {"n": 0}

    def mock_listening(port):
        call_count["n"] += 1
        return call_count["n"] > 2

    with (
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen", return_value=MagicMock()),
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", side_effect=[0.0, 0.5, 1.0, 10.0]),
    ):
        port = ensure_running(sites, preferred_port=8080)

    assert isinstance(port, int)


def test_ensure_running_port_file_os_error(tmp_path):
    """Lines 281-282: ensure_running handles OSError from port file."""
    sites = tmp_path / "sites"
    sites.mkdir()
    # Create a valid port file that will raise OSError when read
    port_file = sites / ".server_port"
    port_file.write_text("8080")

    call_count = {"n": 0}

    def mock_listening(port):
        call_count["n"] += 1
        return call_count["n"] > 2

    original_read_text = Path.read_text

    def patched_read_text(self, *args, **kwargs):
        if self.name == ".server_port":
            raise OSError("disk error")
        return original_read_text(self, *args, **kwargs)

    with (
        patch.object(Path, "read_text", patched_read_text),
        patch("sastaspace.server._is_port_listening", side_effect=mock_listening),
        patch("sastaspace.server.subprocess.Popen", return_value=MagicMock()),
        patch("sastaspace.server.time.sleep"),
        patch("sastaspace.server.time.time", side_effect=[0.0, 0.5, 1.0, 10.0]),
    ):
        port = ensure_running(sites, preferred_port=8080)

    assert isinstance(port, int)
