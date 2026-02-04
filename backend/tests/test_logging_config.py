"""Tests for logging configuration."""

import logging
import sys

from app.core.logging_config import JSONFormatter


class TestJSONFormatter:
    """Test JSONFormatter output."""

    def test_format_includes_exception_when_exc_info_set(self):
        """Format adds exception key when record has exc_info."""
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.makeLogRecord(
                {
                    "name": "test",
                    "pathname": "",
                    "lineno": 0,
                    "msg": "error occurred",
                    "args": (),
                    "levelname": "ERROR",
                    "levelno": logging.ERROR,
                    "exc_info": sys.exc_info(),
                }
            )
            out = formatter.format(record)
        assert "exception" in out
        assert "test error" in out or "ValueError" in out

    def test_format_includes_stack_for_error_without_exc_info(self):
        """Format adds stack key for ERROR level when exc_info is None."""
        formatter = JSONFormatter()
        record = logging.makeLogRecord(
            {
                "name": "test",
                "pathname": "",
                "lineno": 0,
                "msg": "error",
                "args": (),
                "levelname": "ERROR",
                "levelno": logging.ERROR,
                "exc_info": None,
            }
        )
        out = formatter.format(record)
        assert "stack" in out
