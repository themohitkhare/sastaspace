from unittest.mock import MagicMock

from sastaspace_moderator.classifier import Verdict
from sastaspace_moderator.main import classify_safely, run_once
from sastaspace_moderator.stdb import PendingComment


def _fake_pending(n: int = 2) -> list[PendingComment]:
    return [
        PendingComment(id=i, post_slug="x", author_name="a", body=f"body {i}", created_at_micros=0)
        for i in range(1, n + 1)
    ]


def test_run_once_classifies_each_pending_and_sets_status():
    client = MagicMock()
    client.fetch_pending.return_value = _fake_pending(3)
    classifier = MagicMock()
    classifier.classify.side_effect = [
        Verdict(safe=True, raw="safe"),
        Verdict(safe=False, raw="unsafe\nS1", categories=("S1",)),
        Verdict(safe=True, raw="safe"),
    ]

    handled = run_once(client, classifier)

    assert handled == 3
    statuses = [call.args[1] for call in client.set_status.call_args_list]
    assert statuses == ["approved", "flagged", "approved"]


def test_classify_safely_fails_closed_on_classifier_exception():
    classifier = MagicMock()
    classifier.classify.side_effect = RuntimeError("boom")
    c = PendingComment(id=1, post_slug="x", author_name="a", body="b", created_at_micros=0)
    v = classify_safely(classifier, c)
    assert v.safe is False
    assert "ERROR" in v.categories


def test_run_once_with_no_pending_returns_zero():
    client = MagicMock()
    client.fetch_pending.return_value = []
    classifier = MagicMock()
    handled = run_once(client, classifier)
    assert handled == 0
    classifier.classify.assert_not_called()
    client.set_status.assert_not_called()
