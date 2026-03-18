"""Focused tests for SASTA_EVENTS deck metadata and category coverage."""

from app.modules.sastadice.events.events_data import SASTA_EVENTS


def test_deck_size_and_basic_structure():
    """Deck should have 35 events with core fields."""
    assert len(SASTA_EVENTS) == 35

    for event in SASTA_EVENTS:
        assert "name" in event
        assert "desc" in event
        assert "type" in event
        assert "value" in event
        assert "category" in event


def test_event_categories_present():
    """All high-level event categories from the GDD should be present."""
    categories = {e["category"] for e in SASTA_EVENTS}
    # Cash gain/loss, movement, targeting, and global chaos
    assert "CASH_GAIN" in categories
    assert "CASH_LOSS" in categories
    assert "MOVEMENT" in categories
    assert "TARGETING" in categories
    assert "GLOBAL_CHAOS" in categories


def test_at_least_one_card_per_category():
    """Ensure there is at least one card per category."""
    by_category: dict[str, int] = {}
    for event in SASTA_EVENTS:
        by_category[event["category"]] = by_category.get(event["category"], 0) + 1

    assert by_category.get("CASH_GAIN", 0) >= 1
    assert by_category.get("CASH_LOSS", 0) >= 1
    assert by_category.get("MOVEMENT", 0) >= 1
    assert by_category.get("TARGETING", 0) >= 1
    assert by_category.get("GLOBAL_CHAOS", 0) >= 1
