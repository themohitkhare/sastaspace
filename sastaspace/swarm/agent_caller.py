# sastaspace/swarm/agent_caller.py
"""Call Claude Code CLI directly for per-agent calls — no API gateway needed."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess

_logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


class AgentCallError(Exception):
    """Raised when an agent call fails."""


def _find_claude_binary() -> str:
    """Locate the claude CLI binary."""
    path = shutil.which("claude")
    if path:
        return path
    # Common install locations
    for candidate in ["/usr/bin/claude", "/usr/local/bin/claude"]:
        import os

        if os.path.isfile(candidate):
            return candidate
    raise AgentCallError("Claude CLI not found — install via https://claude.ai/install.sh")


class AgentCaller:
    """Makes single-purpose calls to Claude Code CLI for individual agents.

    Uses `claude -p <prompt> --output-format text --model <model>` subprocess calls.
    No API gateway, no rate limits — uses the host's Claude Max subscription directly.
    """

    def __init__(
        self,
        api_url: str = "",  # Kept for backward compat but unused
        api_key: str = "",  # Kept for backward compat but unused
        default_model: str = "claude-sonnet-4-6-20250514",
    ):
        self._claude_bin = _find_claude_binary()
        self._default_model = default_model
        _logger.info("AgentCaller using CLI at %s", self._claude_bin)

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
        timeout: int = 300,
    ) -> str:
        """Call Claude CLI and return raw text response.

        Uses `claude -p` (print mode) which sends a single prompt and exits.
        """
        user_content = context if isinstance(context, str) else json.dumps(context)
        resolved_model = model or self._default_model
        _logger.info("agent_call_start role=%s model=%s via=cli", role, resolved_model)

        # Build the combined prompt (system + user)
        full_prompt = f"{system_prompt}\n\n---\n\n{user_content}"

        cmd = [
            self._claude_bin,
            "-p",
            full_prompt,
            "--output-format",
            "text",
            "--model",
            resolved_model,
            "--max-turns",
            "1",
            "--dangerously-skip-permissions",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=None,  # Inherit parent environment (Claude auth)
            )
        except subprocess.TimeoutExpired:
            raise AgentCallError(f"Agent '{role}' timed out after {timeout}s")

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "no stderr"
            stdout = result.stdout.strip()[:500] if result.stdout else "no stdout"
            _logger.error(
                "agent_call_failed role=%s rc=%d stderr=%s stdout=%s",
                role,
                result.returncode,
                stderr,
                stdout,
            )
            msg = f"Agent '{role}' CLI failed (rc={result.returncode})"
            raise AgentCallError(f"{msg}: stderr={stderr} stdout={stdout}")

        content = result.stdout.strip()
        if not content:
            raise AgentCallError(f"Empty response from agent '{role}'")

        if len(content) < 200:
            _logger.warning(
                "agent_call_short_response role=%s chars=%d content=%s",
                role,
                len(content),
                content[:200],
            )

        _logger.info("agent_call_done role=%s chars=%d", role, len(content))
        return content

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
