"""Structured logging for Synzept."""

import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import get_settings


class StructuredFormatter(logging.Formatter):
    """JSON logs in production; readable text in development."""

    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        message = record.getMessage()

        if settings.log_json:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": message,
            }
            for key in (
                "request_id",
                "method",
                "path",
                "status",
                "duration_ms",
                "provider",
                "intent",
                "operation",
                "hit_count",
                "selected",
                "filtered_low_score",
                "filtered_untrusted",
                "tokens",
                "event",
                "surface",
                "retry_attempt",
                "fallback_provider",
                "error_code",
                "user_id",
                "conversation_id",
                "query",
            ):
                if hasattr(record, key):
                    from app.core.reliability import sanitize_log_value

                    payload[key] = sanitize_log_value(getattr(record, key))
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload, default=str)

        base = f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} | {record.levelname} | {record.name} | {message}"
        extras = []
        for key in ("request_id", "duration_ms", "path", "operation", "status", "provider"):
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")
        if extras:
            base += " | " + " ".join(extras)
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
