# tests/test_cli.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from sastaspace.cli import main

SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Hi</h1></body></html>"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sites_dir(tmp_path):
    d = tmp_path / "sites"
    d.mkdir()
    return d


def make_mock_crawl_result(url="https://acme.com"):
    from sastaspace.crawler import CrawlResult

    return CrawlResult(
        url=url,
        title="Acme",
        meta_description="",
        favicon_url="",
        html_source="<html></html>",
        screenshot_base64="abc",
        headings=[],
        navigation_links=[],
        text_content="Hello",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="",
    )


# --- list command ---


def test_list_empty(runner, sites_dir):
    result = runner.invoke(main, ["list", "--sites-dir", str(sites_dir)])
    assert result.exit_code == 0
    assert "No sites" in result.output or result.output.strip()


def test_list_shows_deployed_sites(runner, sites_dir):
    (sites_dir / "acme-com").mkdir()
    registry = [
        {
            "subdomain": "acme-com",
            "original_url": "https://acme.com",
            "timestamp": "2026-01-01T00:00:00Z",
            "status": "deployed",
        }
    ]
    (sites_dir / "_registry.json").write_text(json.dumps(registry))

    result = runner.invoke(main, ["list", "--sites-dir", str(sites_dir)])
    assert result.exit_code == 0
    assert "acme-com" in result.output


# --- remove command ---


def test_remove_existing_site(runner, sites_dir):
    (sites_dir / "acme-com").mkdir()
    registry = [
        {
            "subdomain": "acme-com",
            "original_url": "https://acme.com",
            "timestamp": "T",
            "status": "deployed",
        }
    ]
    (sites_dir / "_registry.json").write_text(json.dumps(registry))

    result = runner.invoke(main, ["remove", "acme-com", "--sites-dir", str(sites_dir)], input="y\n")
    assert result.exit_code == 0
    assert not (sites_dir / "acme-com").exists()


def test_remove_nonexistent_site(runner, sites_dir):
    result = runner.invoke(main, ["remove", "ghost", "--sites-dir", str(sites_dir)], input="y\n")
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "ghost" in result.output


def test_open_command(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with (
        patch("sastaspace.cli.ensure_running", return_value=8080),
        patch("sastaspace.cli.webbrowser.open") as mock_open,
    ):
        result = runner.invoke(main, ["open", "acme-com", "--sites-dir", str(sites_dir)])

    assert result.exit_code == 0
    mock_open.assert_called_once()
    assert "acme-com" in mock_open.call_args[0][0]


def test_serve_command_calls_subprocess(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with patch("sastaspace.cli.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(main, ["serve", "--sites-dir", str(sites_dir)])

    assert mock_run.called
    cmd = " ".join(mock_run.call_args[0][0])
    assert "uvicorn" in cmd


# --- redesign command ---


def test_redesign_full_pipeline(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_crawl = AsyncMock(return_value=make_mock_crawl_result())
    mock_redesign = MagicMock(return_value=SAMPLE_HTML)
    mock_ensure = MagicMock(return_value=8080)

    with (
        patch("sastaspace.cli.crawl", mock_crawl),
        patch("sastaspace.cli.redesign", mock_redesign),
        patch("sastaspace.cli.ensure_running", mock_ensure),
        patch("sastaspace.cli.webbrowser.open"),
    ):
        result = runner.invoke(
            main,
            ["redesign", "https://acme.com", "--sites-dir", str(sites_dir), "--no-open"],
        )

    assert result.exit_code == 0, result.output
    assert (sites_dir / "acme-com" / "index.html").exists()


def test_redesign_shows_error_on_crawl_failure(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    from sastaspace.crawler import CrawlResult

    failed_result = CrawlResult(
        url="https://bad.com",
        title="",
        meta_description="",
        favicon_url="",
        html_source="",
        screenshot_base64="",
        headings=[],
        navigation_links=[],
        text_content="",
        images=[],
        colors=[],
        fonts=[],
        sections=[],
        error="Could not connect",
    )
    mock_crawl = AsyncMock(return_value=failed_result)

    with patch("sastaspace.cli.crawl", mock_crawl):
        result = runner.invoke(
            main,
            ["redesign", "https://bad.com", "--sites-dir", str(sites_dir)],
        )

    assert result.exit_code != 0
    assert "Could not connect" in result.output


def test_redesign_custom_subdomain(runner, sites_dir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_crawl = AsyncMock(return_value=make_mock_crawl_result())
    mock_redesign = MagicMock(return_value=SAMPLE_HTML)
    mock_ensure = MagicMock(return_value=8080)

    with (
        patch("sastaspace.cli.crawl", mock_crawl),
        patch("sastaspace.cli.redesign", mock_redesign),
        patch("sastaspace.cli.ensure_running", mock_ensure),
        patch("sastaspace.cli.webbrowser.open"),
    ):
        result = runner.invoke(
            main,
            [
                "redesign",
                "https://acme.com",
                "-s",
                "myacme",
                "--sites-dir",
                str(sites_dir),
                "--no-open",
            ],
        )

    assert result.exit_code == 0, result.output
    assert (sites_dir / "myacme" / "index.html").exists()
