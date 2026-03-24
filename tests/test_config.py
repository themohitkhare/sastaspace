# tests/test_config.py
from sastaspace.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.server_port == 8080
    assert s.claude_model == "claude-sonnet-4-6-20250514"
    assert s.sites_dir.name == "sites"
    assert s.claude_code_api_url == "http://localhost:8000/v1"


def test_settings_override_port(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "9090")
    s = Settings()
    assert s.server_port == 9090


def test_settings_override_api_url(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_API_URL", "http://localhost:9000/v1")
    s = Settings()
    assert s.claude_code_api_url == "http://localhost:9000/v1"


def test_espocrm_defaults_disabled():
    s = Settings()
    assert s.espocrm_url == ""
    assert s.espocrm_api_key == ""
    assert s.espocrm_admin_key == ""
