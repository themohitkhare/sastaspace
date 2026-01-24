"""Centralized logging configuration for structured JSON output."""
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Outputs logs as JSON for Loki parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "backend",
            "module": record.module,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        if record.levelno >= logging.ERROR and record.exc_info is None:
            log_data["stack"] = traceback.format_stack()
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    json_formatter = JSONFormatter()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)  # stdout for Docker
    console_handler.setLevel(log_level)
    console_handler.setFormatter(json_formatter)
    
    root_logger.addHandler(console_handler)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger(__name__).info(
        "Logging configured", extra={"extra_fields": {"component": "logging_config"}}
    )
