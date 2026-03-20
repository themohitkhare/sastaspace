import pytest
from fastapi.testclient import TestClient

from sastaspace.crawler import CrawlResult
from sastaspace.deployer import DeployResult


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
