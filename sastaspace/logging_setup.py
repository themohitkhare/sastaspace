# sastaspace/logging_setup.py
"""Centralised logging configuration.

Call ``configure_logging()`` once at startup (before any getLogger calls emit)
to set the root logger format.  When ``LOG_FORMAT=json`` (or Settings.log_format
== "json"), output is structured JSON suitable for Loki / CloudWatch / etc.
Otherwise plain text is used for local development.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(log_format: str = "text", level: int = logging.INFO) -> None:
    """Configure the root logger.

    Parameters
    ----------
    log_format:
        ``"json"`` for structured JSON lines, anything else for human-readable text.
    level:
        Root log level (default ``INFO``).
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers to avoid duplicate output
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if log_format == "json":
        from pythonjsonlogger.json import JsonFormatter

        formatter = JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s %(module)s %(funcName)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
