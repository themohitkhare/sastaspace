# sastaspace/swarm/agent_caller.py
"""Thin wrapper around OpenAI client for focused per-agent calls."""

from __future__ import annotations

import json
import logging
import re
import time

from openai import OpenAI, RateLimitError

_logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


class AgentCallError(Exception):
    """Raised when an agent call fails."""


class AgentCaller:
    """Makes single-purpose calls to claude-code-api for individual agents."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000/v1",
        api_key: str = "claude-code",
        default_model: str = "claude-sonnet-4-6-20250514",
    ):
        self._client = OpenAI(base_url=api_url, api_key=api_key)
        self._default_model = default_model

    def call(
        self,
        role: str,
        system_prompt: str,
        context: dict | list | str,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> dict:
        """Call an agent and return parsed JSON response."""
        raw = self.call_raw(
            role=role,
            system_prompt=system_prompt,
            context=context,
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return self._parse_json(raw, role)

    def call_raw(
        self,
        role: str,
        system_prompt: str,
        context: dict | list | str,
        *,
        model: str | None = None,
        max_tokens: int = 16000,
        timeout: int = 120,
    ) -> str:
        """Call an agent and return raw string response (for HTML/code output).

        Retries up to 4 times with exponential backoff on rate limit (429) errors.
        """
        user_content = context if isinstance(context, str) else json.dumps(context)
        _logger.info("agent_call_start role=%s model=%s", role, model or self._default_model)

        delays = [0, 5, 15, 30]
        last_error: Exception | None = None

        for attempt, delay in enumerate(delays):
            if delay > 0:
                _logger.warning(
                    "agent_call_retry role=%s attempt=%d delay=%ds", role, attempt + 1, delay
                )
                time.sleep(delay)

            try:
                response = self._client.chat.completions.create(
                    model=model or self._default_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=max_tokens,
                    timeout=timeout,
                )

                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise AgentCallError(f"Empty response from agent '{role}'")

                _logger.info("agent_call_done role=%s chars=%d", role, len(content))
                return content

            except RateLimitError as e:
                last_error = e
                _logger.warning("agent_call_rate_limited role=%s attempt=%d", role, attempt + 1)
                continue

        raise AgentCallError(f"Agent '{role}' failed after {len(delays)} attempts: {last_error}")

    def _parse_json(self, raw: str, role: str) -> dict:
        """Extract JSON from raw response, handling markdown fences."""
        text = raw.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown fence
        match = _JSON_FENCE_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise AgentCallError(f"Agent '{role}' returned non-JSON response: {text[:200]}...")
