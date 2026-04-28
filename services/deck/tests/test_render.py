"""Render-layer tests — placeholder backend was removed; render_wav now
raises RenderUnavailableError unless musicgen is wired."""

import pytest

from sastaspace_deck.plan import PlannedTrack
from sastaspace_deck.render import RenderUnavailableError, render_wav


def _track(**kwargs) -> PlannedTrack:
    base = dict(
        name="Test", type="background", length=2, desc="", tempo="60bpm",
        instruments="pad", mood="calm",
    )
    base.update(kwargs)
    return PlannedTrack(**base)


def test_render_without_musicgen_raises():
    """Default path — no PREFER_MUSICGEN — must fail loudly, not synth a sine."""
    with pytest.raises(RenderUnavailableError):
        render_wav(_track(type="background", length=1))


def test_render_with_musicgen_flag_but_no_install_raises():
    """PREFER_MUSICGEN=1 but musicgen not wired up still raises (no silent fallback)."""
    with pytest.raises(RenderUnavailableError):
        render_wav(_track(type="loop", length=2), prefer_musicgen=True)
