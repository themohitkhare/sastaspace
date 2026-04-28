"""Audio planner agent — Agno + Ollama (gemma3:1b).

Wraps the same model the moderator uses (already deployed on the prod box's
Ollama instance) in an Agno Agent that turns a project description into a
list of :class:`~sastaspace_deck.plan.PlannedTrack` records.

Why Agno instead of a raw `httpx.post(/api/generate)`:
- Matches infra/agents/moderator/src/sastaspace_moderator/classifier.py — one
  pattern for every "small AI helper" in the lab so they share retry, system
  prompt, and run-loop semantics.
- Cheaper to evolve later (swap the model, add tools, add a follow-up agent
  for instrument suggestion) without rewriting the call site.

The agent is intentionally fail-soft: any parse or runtime error raises
``AgentPlanError``, which :func:`~sastaspace_deck.plan.draft_plan` catches and
falls back to the deterministic local seed list.
"""

from __future__ import annotations

import json
import logging
import os

# Disable Agno's anonymous usage telemetry — we don't ship project briefs to
# third parties. Must be set before importing agno modules that read it at
# import time (matches the moderator's pattern).
os.environ.setdefault("AGNO_TELEMETRY", "false")

from agno.agent import Agent  # noqa: E402
from agno.models.ollama import Ollama  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from .plan import PlannedTrack  # noqa: E402

log = logging.getLogger("sastaspace.deck.agent")


# Hardened instructions: tells the model exactly what JSON to emit and forbids
# every common gemma3:1b drift (markdown fences, prose explanations, extra
# keys). Small models follow short, blunt rules better than long ones.
PLANNER_INSTRUCTIONS = """You are a music director for a small audio-asset tool.

Given a project description and a target track count, output a JSON array of
exactly that many tracks. Each track is an object with these exact keys:

- name        (string, short title, sentence case)
- type        (one of: background, loop, one-shot, intro, outro, transition, sting, jingle)
- length      (integer seconds, 1..180)
- desc        (string, one-sentence usage hint)
- tempo       (one of: 60bpm, 90bpm, 120bpm, free)
- instruments (string, comma-separated, e.g. "soft pads, gentle bell, no percussion")
- mood        (one of: calm, focused, playful, cinematic, dark, upbeat, warm, tense, dreamy, nostalgic)

Pick a mood that matches the project. Pick types that cover the project's
real audio needs (e.g. an app needs a notification, a game needs combat
music). Keep durations realistic — notifications are 2s, beds are 30-60s.

Output ONLY the JSON array. No prose, no markdown, no code fences, no
explanations. Start with `[` and end with `]`.
"""


class AgentPlanError(RuntimeError):
    """Raised when the agent run fails or its output can't be parsed."""


class _AgentTrack(BaseModel):
    """Strict shape used to validate one element of the agent's JSON array."""

    name: str = Field(..., min_length=1, max_length=80)
    type: str = Field(..., max_length=24)
    length: int = Field(..., ge=1, le=180)
    desc: str = Field(default="", max_length=240)
    tempo: str = Field(default="90bpm", max_length=24)
    instruments: str = Field(default="", max_length=240)
    mood: str = Field(default="focused", max_length=24)


class AudioPlannerAgent:
    """Agno-wrapped planner. One instance per process is fine."""

    def __init__(
        self,
        *,
        model_id: str = "gemma3:1b",
        ollama_host: str = "http://localhost:11434",
    ) -> None:
        self._agent = Agent(
            model=Ollama(id=model_id, host=ollama_host),
            description="Music director for sastaspace deck — turns project briefs into track plans.",
            instructions=PLANNER_INSTRUCTIONS,
            markdown=False,
        )

    def plan(self, description: str, count: int) -> list[PlannedTrack]:
        """Run the agent and return ``count`` parsed tracks.

        Raises :class:`AgentPlanError` on any failure (network, parse, empty
        result). The caller should fall back to a deterministic plan rather
        than surface the error.
        """
        prompt = (
            f"project description:\n{description}\n\n"
            f"track count: {count}\n\n"
            "Return the JSON array now."
        )
        try:
            response = self._agent.run(prompt)
        except Exception as exc:  # noqa: BLE001 — agno wraps many transport errors
            raise AgentPlanError(f"agent run failed: {exc}") from exc
        raw = (response.content or "").strip()
        return _parse_tracks(raw, count)


def _parse_tracks(raw: str, count: int) -> list[PlannedTrack]:
    """Parse the agent's text into validated tracks.

    Tolerates the most common gemma3:1b drift — wrapping the array in a
    ```json fence — but anything beyond that fails fast so the caller can
    fall back to the deterministic plan.
    """
    if not raw:
        raise AgentPlanError("empty agent response")
    text = raw
    if text.startswith("```"):
        # ```json\n...\n``` or ```\n...\n```
        parts = text.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentPlanError(f"agent output not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise AgentPlanError("agent output was not a JSON array")

    out: list[PlannedTrack] = []
    for row in data[:count]:
        if not isinstance(row, dict):
            continue
        try:
            t = _AgentTrack(**row)
        except (ValidationError, TypeError) as exc:
            log.debug("dropping unparseable track row: %s", exc)
            continue
        out.append(
            PlannedTrack(
                name=t.name,
                type=t.type,
                length=t.length,
                desc=t.desc,
                tempo=t.tempo,
                instruments=t.instruments,
                mood=t.mood,
            )
        )
    if not out:
        raise AgentPlanError("no parseable tracks in agent output")
    return out
