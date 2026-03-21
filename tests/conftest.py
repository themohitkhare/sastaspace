from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import sastaspace.database as db_module
from sastaspace.crawler import CrawlResult
from sastaspace.deployer import DeployResult


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Wire a fresh in-memory MongoDB mock for every test.

    Runs synchronously so it works for both sync TestClient tests and
    async pytest-asyncio tests. mongomock_motor is sync-under-async and
    works across any event loop.
    """
    client = AsyncMongoMockClient()
    mock_database = client["sastaspace_test"]
    monkeypatch.setattr(db_module, "_client", client)
    monkeypatch.setattr(db_module, "_db", mock_database)
    yield
    monkeypatch.setattr(db_module, "_client", None)
    monkeypatch.setattr(db_module, "_db", None)


@pytest.fixture
def tmp_sites(tmp_path):
    """Create a temporary sites directory."""
    sites = tmp_path / "sites"
    sites.mkdir()
    return sites


@pytest.fixture
def mock_crawl_result():
    """A successful CrawlResult for testing."""
    return CrawlResult(
        url="https://example.com",
        title="Example",
        meta_description="An example site",
        favicon_url="",
        html_source="<html><body>Hello</body></html>",
        screenshot_base64="",
        headings=["h1: Example"],
        navigation_links=[],
        text_content="Hello world",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )


@pytest.fixture
def mock_deploy_result(tmp_sites):
    """A successful DeployResult for testing."""
    return DeployResult(
        subdomain="example-com",
        index_path=tmp_sites / "example-com" / "index.html",
        sites_dir=tmp_sites,
    )


@pytest.fixture
def test_client(tmp_sites):
    """TestClient with a fresh app bound to tmp_sites."""
    from sastaspace.server import make_app

    app = make_app(tmp_sites)
    return TestClient(app)


@pytest.fixture
def redesign_client(tmp_sites, mock_crawl_result, mock_deploy_result):
    """TestClient with mocked pipeline functions for /redesign testing."""
    mock_html = "<html><body><p>Redesigned</p></body></html>"

    with (
        patch(
            "sastaspace.server.crawl",
            new_callable=AsyncMock,
            return_value=mock_crawl_result,
        ) as m_crawl,
        patch(
            "sastaspace.server.redesign",
            return_value=mock_html,
        ) as m_redesign,
        patch(
            "sastaspace.server.deploy",
            return_value=mock_deploy_result,
        ) as m_deploy,
    ):
        from sastaspace.server import make_app

        app = make_app(tmp_sites)
        client = TestClient(app)
        client._mock_crawl = m_crawl
        client._mock_redesign = m_redesign
        client._mock_deploy = m_deploy
        yield client
