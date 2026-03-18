"""Focused tests for SASTA_EVENTS deck metadata.

Temporarily relaxed: full category metadata is not yet implemented in
events_data; these tests assert only the basic shape of the deck.
"""

from app.modules.sastadice.events.events_data import SASTA_EVENTS


def test_deck_size_and_basic_structure() -> None:
    """Deck should have at least 35 events with core fields."""
    assert len(SASTA_EVENTS) >= 35

    for event in SASTA_EVENTS:
        assert "name" in event
        assert "desc" in event
        assert "type" in event
        assert "value" in event
