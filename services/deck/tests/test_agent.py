"""Tests for the Agno planner agent.

We don't stand up a real Ollama in tests. Instead we exercise the parser
directly and inject a mock-shaped agent into ``draft_plan`` to validate
the integration seam.
"""

from unittest.mock import MagicMock

import pytest

from sastaspace_deck.agent import AgentPlanError, AudioPlannerAgent, _parse_tracks
from sastaspace_deck.plan import draft_plan


def test_parse_clean_json_array():
    raw = (
        "["
        '{"name":"Bed","type":"background","length":60,"desc":"main bed",'
        '"tempo":"60bpm","instruments":"pad","mood":"calm"}'
        "]"
    )
    out = _parse_tracks(raw, 1)
    assert len(out) == 1
    assert out[0].name == "Bed"
    assert out[0].length == 60


def test_parse_strips_json_code_fence():
    raw = (
        "```json\n"
        "[{\"name\":\"X\",\"type\":\"loop\",\"length\":10,\"desc\":\"\","
        "\"tempo\":\"90bpm\",\"instruments\":\"\",\"mood\":\"calm\"}]\n"
        "```"
    )
    out = _parse_tracks(raw, 1)
    assert len(out) == 1
    assert out[0].name == "X"


def test_parse_strips_unlabeled_fence():
    raw = (
        "```\n"
        "[{\"name\":\"X\",\"type\":\"loop\",\"length\":10,\"desc\":\"\","
        "\"tempo\":\"90bpm\",\"instruments\":\"\",\"mood\":\"calm\"}]\n"
        "```"
    )
    out = _parse_tracks(raw, 1)
    assert len(out) == 1


def test_parse_caps_at_count():
    rows = ", ".join(
        '{"name":"T' + str(i) + '","type":"loop","length":5,"desc":"","tempo":"90bpm","instruments":"","mood":"calm"}'
        for i in range(10)
    )
    out = _parse_tracks(f"[{rows}]", 3)
    assert len(out) == 3
    assert [t.name for t in out] == ["T0", "T1", "T2"]


def test_parse_drops_invalid_rows_keeps_valid():
    raw = (
        "["
        '{"name":"Good","type":"loop","length":5,"desc":"","tempo":"90bpm","instruments":"","mood":"calm"},'
        '{"length":"not-an-int"},'
        '"this is a string not an object"'
        "]"
    )
    out = _parse_tracks(raw, 5)
    assert len(out) == 1
    assert out[0].name == "Good"


def test_parse_rejects_empty_response():
    with pytest.raises(AgentPlanError):
        _parse_tracks("", 3)


def test_parse_rejects_non_json():
    with pytest.raises(AgentPlanError):
        _parse_tracks("not json at all", 3)


def test_parse_rejects_non_array():
    with pytest.raises(AgentPlanError):
        _parse_tracks('{"hi":"there"}', 3)


def test_parse_rejects_when_all_rows_invalid():
    with pytest.raises(AgentPlanError):
        _parse_tracks('[{"only":"junk"}, {"more":"junk"}]', 3)


def test_draft_plan_uses_agent_when_provided():
    fake_agent = MagicMock()
    fake_agent.plan.return_value = _parse_tracks(
        '[{"name":"From Agent","type":"background","length":30,"desc":"d","tempo":"60bpm","instruments":"pad","mood":"calm"}]',
        1,
    )
    out = draft_plan("anything", 1, agent=fake_agent)
    assert len(out) == 1
    assert out[0].name == "From Agent"
    fake_agent.plan.assert_called_once()


def test_draft_plan_falls_back_when_agent_raises():
    fake_agent = MagicMock()
    fake_agent.plan.side_effect = AgentPlanError("boom")
    # falls back to local draft for a meditation prompt → calm mood
    out = draft_plan("A meditation app", 3, agent=fake_agent)
    assert len(out) == 3
    assert all(t.mood == "calm" for t in out)


def test_audio_planner_agent_constructs_without_ollama_running():
    # Just confirms the import + constructor path works in CI without an
    # Ollama instance — the actual run() call would fail and is covered by
    # the fallback path in test_draft_plan_falls_back_when_agent_raises.
    a = AudioPlannerAgent(model_id="gemma3:1b", ollama_host="http://127.0.0.1:11434")
    assert a is not None
