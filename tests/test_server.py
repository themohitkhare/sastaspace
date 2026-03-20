# tests/test_server.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

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
    from sastaspace.server import make_app

    app = make_app(sites_dir)
    return TestClient(app)


def test_root_returns_html_listing(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "acme-com" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_root_shows_link_to_site(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/")
    assert "https://acme.com" in resp.text or "acme-com" in resp.text


def test_site_route_serves_index_html(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/acme-com/")
    assert resp.status_code == 200
    assert "<h1>Acme</h1>" in resp.text


def test_site_route_without_trailing_slash(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/acme-com/", follow_redirects=True)
    assert resp.status_code == 200


def test_unknown_site_returns_404(tmp_path):
    sites = make_test_sites(tmp_path)
    client = make_test_client(sites)

    resp = client.get("/nonexistent/")
    assert resp.status_code == 404


def test_root_with_empty_registry(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()
    client = make_test_client(sites)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "No sites" in resp.text


# --- ensure_running() tests ---


def test_ensure_running_returns_port_when_already_listening(tmp_path):
    sites = tmp_path / "sites"
    sites.mkdir()
    (sites / ".server_port").write_text("8080")

    with patch("sastaspace.server._is_port_listening", return_value=True):
        from sastaspace.server import ensure_running

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
        from sastaspace.server import ensure_running

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
        from sastaspace.server import ensure_running

        port = ensure_running(sites, preferred_port=8080)

    assert port == 8081
