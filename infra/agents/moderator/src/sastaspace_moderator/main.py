"""Moderator entrypoint: poll → classify → set_status loop."""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from collections.abc import Iterator

from .classifier import LlamaGuardClassifier, Verdict
from .stdb import PendingComment, SpacetimeClient

log = logging.getLogger("sastaspace.moderator")


def env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        log.error("missing required env var: %s", name)
        sys.exit(2)
    return val


def run_once(
    client: SpacetimeClient, classifier: LlamaGuardClassifier, batch_size: int = 25
) -> int:
    """Process one batch of pending comments. Returns count handled."""
    pending = client.fetch_pending(limit=batch_size)
    for c in pending:
        verdict = classify_safely(classifier, c)
        new_status = "approved" if verdict.safe else "flagged"
        client.set_status(c.id, new_status)
        log.info(
            "comment %d (%s) %s%s",
            c.id,
            c.post_slug,
            new_status,
            f" categories={','.join(verdict.categories)}" if verdict.categories else "",
        )
    return len(pending)


def classify_safely(classifier: LlamaGuardClassifier, c: PendingComment) -> Verdict:
    """Wrap classifier call so a single bad row doesn't crash the loop.

    Fail-closed: any error → flagged. Owner can re-approve via the admin UI.
    """
    try:
        return classifier.classify(c.body)
    except Exception:  # noqa: BLE001
        log.exception("classifier failed for comment id=%d", c.id)
        return Verdict(safe=False, raw="<classifier-error>", categories=("ERROR",))


def loop(
    client: SpacetimeClient,
    classifier: LlamaGuardClassifier,
    sleep_seconds: float,
    until_stopped: Iterator[bool],
) -> None:
    for keep_going in until_stopped:
        if not keep_going:
            break
        try:
            n = run_once(client, classifier)
            if n == 0:
                time.sleep(sleep_seconds)
        except Exception:  # noqa: BLE001
            log.exception("moderator loop iteration failed; backing off")
            time.sleep(sleep_seconds * 2)


def forever() -> Iterator[bool]:
    """Default 'until' generator — runs until SIGINT/SIGTERM."""
    stop = False

    def _stop(*_a: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    while not stop:
        yield True
    yield False


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    base_url = env("STDB_HTTP_URL", "http://localhost:3100")
    database = env("STDB_MODULE", "sastaspace")
    owner_token = env("SPACETIME_TOKEN")
    ollama_host = env("OLLAMA_HOST", "http://localhost:11434")
    model = env("MODERATOR_MODEL", "gemma3:1b")
    sleep_seconds = float(env("POLL_SECONDS", "3"))

    log.info(
        "moderator starting: stdb=%s db=%s ollama=%s model=%s poll=%ss",
        base_url,
        database,
        ollama_host,
        model,
        sleep_seconds,
    )

    classifier = LlamaGuardClassifier(model_id=model, ollama_host=ollama_host)
    with SpacetimeClient(base_url, database, owner_token) as client:
        loop(client, classifier, sleep_seconds, forever())
    log.info("moderator stopped cleanly")


if __name__ == "__main__":
    main()
