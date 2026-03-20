# tests/test_config.py
import pytest

from sastaspace.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-ant-test"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    s = Settings()
    assert s.server_port == 8080
    assert s.claude_model == "claude-sonnet-4-20250514"
    assert s.sites_dir.name == "sites"


def test_settings_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(Exception):
        Settings()


def test_settings_override_port(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("SERVER_PORT", "9090")
    s = Settings()
    assert s.server_port == 9090
