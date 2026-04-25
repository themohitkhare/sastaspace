from sastaspace_moderator.classifier import Verdict, parse_verdict


def test_safe_response_parses_as_safe():
    v = parse_verdict("safe")
    assert v.safe is True
    assert v.categories == ()


def test_unsafe_with_categories():
    v = parse_verdict("unsafe\nS1, S6")
    assert v.safe is False
    assert v.categories == ("S1", "S6")


def test_unsafe_without_categories():
    v = parse_verdict("unsafe")
    assert v.safe is False
    assert v.categories == ()


def test_empty_response_fails_closed():
    v = parse_verdict("")
    assert v.safe is False
    assert v.raw == ""


def test_garbage_response_fails_closed():
    v = parse_verdict("I think this is fine actually")
    assert v.safe is False


def test_safe_with_extra_whitespace():
    v = parse_verdict("  safe  \n\n")
    assert v.safe is True


def test_verdict_is_frozen():
    v = Verdict(safe=True, raw="safe")
    try:
        v.safe = False  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("Verdict should be frozen")
