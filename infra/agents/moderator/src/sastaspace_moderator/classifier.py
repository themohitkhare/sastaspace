"""Comment classifier wrapped in an Agno agent.

Default model: `gemma3:1b` (815MB, fits comfortably alongside other Ollama
models on taxila's 7900 XTX). LlamaGuard-3 was tried first but it's tuned
for "is this user trying to elicit harmful content from an LLM" semantics,
which lets through threats and spam aimed at a *human* reader. A small
generic model with an explicit one-word prompt classifies our use case
correctly (verified against benign/spam/threat samples).

The classifier is wrapped in an Agno Agent so future agents in the lab
share the same shape (model + instructions + run loop), even though for
v1 we only need yes/no.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Disable Agno's anonymous usage telemetry — comments are sensitive.
# Must be set before importing agno modules that read it at import time.
os.environ.setdefault("AGNO_TELEMETRY", "false")

from agno.agent import Agent  # noqa: E402
from agno.models.ollama import Ollama  # noqa: E402


@dataclass(frozen=True)
class Verdict:
    """Classifier output. `safe=True` means approve the comment."""

    safe: bool
    raw: str
    categories: tuple[str, ...] = field(default_factory=tuple)


CLASSIFIER_INSTRUCTIONS = (
    "You are a strict content safety classifier for a personal blog. "
    "Reply with exactly one word and nothing else: SAFE if the user comment "
    "is harmless, or UNSAFE if it contains any of: spam, advertising, "
    "promotional links, harassment, hate, threats, violence, doxxing, "
    "explicit sexual content, or illegal content. "
    "Do not explain. Do not add punctuation. One word only."
)


class LlamaGuardClassifier:
    """Agno-wrapped classifier. Name kept for backwards-compat with imports."""

    def __init__(
        self,
        model_id: str = "gemma3:1b",
        ollama_host: str = "http://localhost:11434",
    ) -> None:
        self._agent = Agent(
            model=Ollama(id=model_id, host=ollama_host),
            description="Content moderation classifier for sastaspace blog comments.",
            instructions=CLASSIFIER_INSTRUCTIONS,
            markdown=False,
        )

    def classify(self, body: str) -> Verdict:
        """Run the classifier on the given comment body."""
        response = self._agent.run(body)
        raw = (response.content or "").strip()
        return parse_verdict(raw)


def parse_verdict(raw: str) -> Verdict:
    """Extract a Verdict from the classifier's raw text output.

    Accepts: SAFE / UNSAFE (case-insensitive) — and also LlamaGuard-style
    `safe\\nS1,...` for backwards-compat if anyone swaps the model back.
    """
    if not raw:
        return Verdict(safe=False, raw="", categories=())

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    head = lines[0].lower().rstrip(".,!?")

    if head.startswith("safe"):
        return Verdict(safe=True, raw=raw, categories=())

    cats: tuple[str, ...] = ()
    if len(lines) >= 2:
        cats = tuple(c.strip().upper() for c in lines[1].split(",") if c.strip())
    return Verdict(safe=False, raw=raw, categories=cats)
