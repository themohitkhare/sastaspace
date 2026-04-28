"""Unit tests for the local plan-drafting fallback."""

from sastaspace_deck.plan import draft_plan


def test_meditation_returns_calm_mood():
    plan = draft_plan("A meditation app for stressed professionals", 3)
    assert len(plan) == 3
    assert all(t.mood == "calm" for t in plan)


def test_game_returns_playful_mood():
    plan = draft_plan("A 2D pixel-art platformer", 3)
    assert len(plan) == 3
    assert all(t.mood == "playful" for t in plan)


def test_dark_keyword_overrides_domain_mood():
    plan = draft_plan("A 2D platformer set in a haunted candy factory", 3)
    assert all(t.mood == "dark" for t in plan)


def test_count_clamped_to_max_ten():
    plan = draft_plan("anything", 999)
    assert len(plan) == 10


def test_count_clamped_to_min_one():
    plan = draft_plan("anything", 0)
    assert len(plan) == 1


def test_pad_when_seeds_run_out():
    # The generic seed list is short; asking for 8 should trigger padding.
    plan = draft_plan("a tabletop game pamphlet", 8)
    assert len(plan) == 8


def test_musicgen_prompt_includes_track_metadata():
    plan = draft_plan("A meditation app", 1)
    p = plan[0].musicgen_prompt
    assert plan[0].mood in p
    assert plan[0].type in p
    assert f"{plan[0].length}s" in p
