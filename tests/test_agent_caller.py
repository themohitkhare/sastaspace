# tests/test_agent_caller.py
from unittest.mock import MagicMock, patch

import pytest

from sastaspace.swarm.agent_caller import AgentCaller, AgentCallError


class TestAgentCaller:
    def _make_caller(self):
        return AgentCaller(
            api_url="http://localhost:8000/v1",
            api_key="test-key",
            default_model="claude-sonnet-4-6-20250514",
        )

    def _mock_response(self, content: str):
        choice = MagicMock()
        choice.message.content = content
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_returns_parsed_json(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            '{"site_type": "saas", "industry": "dev tools"}'
        )
        caller = self._make_caller()
        result = caller.call(
            role="site-classifier",
            system_prompt="Classify this site.",
            context={"url": "https://example.com"},
            timeout=60,
        )
        assert result["site_type"] == "saas"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_extracts_json_from_markdown_fence(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            'Here is the result:\n```json\n{"site_type": "blog"}\n```'
        )
        caller = self._make_caller()
        result = caller.call(role="site-classifier", system_prompt="Classify.", context={})
        assert result["site_type"] == "blog"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_returns_raw_string_when_not_json(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response(
            "<!DOCTYPE html><html><body>Hello</body></html>"
        )
        caller = self._make_caller()
        result = caller.call_raw(role="builder", system_prompt="Build HTML.", context={})
        assert result.startswith("<!DOCTYPE html>")

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_with_model_override(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response('{"ok": true}')
        caller = self._make_caller()
        caller.call(
            role="builder",
            system_prompt="Build.",
            context={},
            model="claude-opus-4-6-20250514",
        )
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-opus-4-6-20250514"

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_raises_on_empty_response(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response("")
        caller = self._make_caller()
        with pytest.raises(AgentCallError, match="Empty response"):
            caller.call(role="test", system_prompt="Test.", context={})

    @patch("sastaspace.swarm.agent_caller.OpenAI")
    def test_call_with_max_tokens(self, mock_openai_cls):
        client = MagicMock()
        mock_openai_cls.return_value = client
        client.chat.completions.create.return_value = self._mock_response('{"ok": true}')
        caller = self._make_caller()
        caller.call(role="test", system_prompt="Test.", context={}, max_tokens=5000)
        call_kwargs = client.chat.completions.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == 5000
