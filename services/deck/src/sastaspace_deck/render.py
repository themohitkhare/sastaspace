"""Per-track audio rendering.

Single backend: ``musicgen`` via ``audiocraft`` (slow on CPU, fast on GPU).
Available only when the optional ``[musicgen]`` install is present and the
model has been downloaded; otherwise :func:`render_wav` raises
:class:`RenderUnavailableError` rather than synthesising a placeholder. The
old sine-wave placeholder was removed on 2026-04-27 — it produced
"default sounds" indistinguishable from actual generation in the UI, which
masked the fact that the model wasn't wired and confused users.

Returns raw 16-bit mono WAV bytes at 44.1 kHz.
"""

from __future__ import annotations

import logging

from .plan import PlannedTrack

log = logging.getLogger("sastaspace.deck.render")

SAMPLE_RATE = 44_100


class RenderUnavailableError(RuntimeError):
    """Raised when no real renderer is wired and the service can't produce audio.

    Surfaces as a 5xx from the FastAPI route so the frontend can show an
    honest error instead of a fake-audio download.
    """


def render_wav(track: PlannedTrack, *, prefer_musicgen: bool = False) -> bytes:
    """Render ``track`` to 16-bit mono WAV bytes via the musicgen backend.

    Raises :class:`RenderUnavailableError` if the backend can't render —
    callers should map that to a 503/500 response. We don't fall back to a
    placeholder; silently substituting a sine wave for real generation hid
    pipeline misconfiguration in the past.
    """
    if not prefer_musicgen:
        raise RenderUnavailableError(
            "deck render requires PREFER_MUSICGEN=1 — placeholder backend was removed",
        )
    return _musicgen_render(track)


def _musicgen_render(track: PlannedTrack) -> bytes:
    # Wire-up: load `facebook/musicgen-small` once at module level, run with
    # `track.musicgen_prompt`, encode at 44.1 kHz mono int16. Left as a stub
    # so the service can boot without torch installed; flip `prefer_musicgen`
    # to True once the optional install lands and the model is on disk. The
    # production path now lives in workers/src/agents/deck-agent.ts which
    # calls LocalAI directly — this FastAPI service is on the Phase 4
    # deletion list.
    raise RenderUnavailableError(
        "musicgen backend not enabled — install .[musicgen] and wire up,"
        " or use the STDB worker (services/deck is being removed in Phase 4)",
    )
