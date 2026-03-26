# tests/test_agent_caller.py
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.swarm.agent_caller import AgentCaller, AgentCallError


class TestAgentCaller:
    def _make_caller(self):
        with patch(
            "sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude"
        ):
            return AgentCaller(default_model="claude-sonnet-4-6-20250514")

    def _mock_run(self, stdout: str, returncode: int = 0):
        return MagicMock(stdout=stdout, stderr="", returncode=returncode)

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_returns_parsed_json(self, _find, mock_run):
        mock_run.return_value = self._mock_run('{"site_type": "saas", "industry": "dev tools"}')
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        result = caller.call(
            role="site-classifier",
            system_prompt="Classify this site.",
            context={"url": "https://example.com"},
            timeout=60,
        )
        assert result["site_type"] == "saas"

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_extracts_json_from_markdown_fence(self, _find, mock_run):
        mock_run.return_value = self._mock_run(
            'Here is the result:\n```json\n{"site_type": "blog"}\n```'
        )
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        result = caller.call(role="site-classifier", system_prompt="Classify.", context={})
        assert result["site_type"] == "blog"

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_returns_raw_string(self, _find, mock_run):
        mock_run.return_value = self._mock_run("<!DOCTYPE html><html><body>Hello</body></html>")
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        result = caller.call_raw(role="builder", system_prompt="Build HTML.", context={})
        assert result.startswith("<!DOCTYPE html>")

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_with_model_override(self, _find, mock_run):
        mock_run.return_value = self._mock_run('{"ok": true}')
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        caller.call(
            role="builder",
            system_prompt="Build.",
            context={},
            model="claude-opus-4-6-20250514",
        )
        cmd = mock_run.call_args[0][0]
        assert "claude-opus-4-6-20250514" in cmd

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_raises_on_empty_response(self, _find, mock_run):
        mock_run.return_value = self._mock_run("")
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        with pytest.raises(AgentCallError, match="Empty response"):
            caller.call(role="test", system_prompt="Test.", context={})

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_raises_on_timeout(self, _find, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=60)
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        with pytest.raises(AgentCallError, match="timed out"):
            caller.call_raw(role="test", system_prompt="Test.", context={}, timeout=60)

    @patch("subprocess.run")
    @patch("sastaspace.swarm.agent_caller._find_claude_binary", return_value="/usr/bin/claude")
    def test_call_raises_on_nonzero_exit(self, _find, mock_run):
        mock_run.return_value = self._mock_run("", returncode=1)
        mock_run.return_value.stderr = "Some error"
        caller = AgentCaller(default_model="claude-sonnet-4-6-20250514")
        with pytest.raises(AgentCallError, match="CLI failed"):
            caller.call_raw(role="test", system_prompt="Test.", context={})
