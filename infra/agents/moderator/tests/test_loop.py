"""Cover the run-once-N-times loop driver."""

from unittest.mock import MagicMock

from sastaspace_moderator.classifier import Verdict
from sastaspace_moderator.main import loop
from sastaspace_moderator.stdb import PendingComment


def _ticks(n: int):
    """Yield True n times then False — simulates SIGINT after n iterations."""
    for _ in range(n):
        yield True
    yield False


def test_loop_processes_each_tick_until_stopped(monkeypatch):
    monkeypatch.setattr("sastaspace_moderator.main.time.sleep", lambda _s: None)
    client = MagicMock()
    client.fetch_pending.side_effect = [
        [PendingComment(id=1, post_slug="x", author_name="a", body="b", created_at_micros=0)],
        [],
        [PendingComment(id=2, post_slug="x", author_name="a", body="b", created_at_micros=0)],
    ]
    classifier = MagicMock()
    classifier.classify.return_value = Verdict(safe=True, raw="safe")

    loop(client, classifier, sleep_seconds=0.0, until_stopped=_ticks(3))

    assert client.fetch_pending.call_count == 3
    assert client.set_status.call_count == 2  # only the non-empty ticks


def test_loop_swallows_exceptions_and_continues(monkeypatch):
    monkeypatch.setattr("sastaspace_moderator.main.time.sleep", lambda _s: None)
    client = MagicMock()
    client.fetch_pending.side_effect = [RuntimeError("transient"), []]
    classifier = MagicMock()

    loop(client, classifier, sleep_seconds=0.0, until_stopped=_ticks(2))

    # Loop survived the first failure and ran the second iteration.
    assert client.fetch_pending.call_count == 2
