import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _level_from_env() -> int:
    raw = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def _json_enabled() -> bool:
    raw = os.getenv("LOG_JSON", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": _utc_ts(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)

        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "costagent") -> logging.Logger:
    """Return a configured logger for operational logs (stdout)."""
    logger = logging.getLogger(name)
    if getattr(logger, "_costagent_configured", False):
        return logger

    logger.setLevel(_level_from_env())
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.setLevel(_level_from_env())
    if _json_enabled():
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)

    setattr(logger, "_costagent_configured", True)
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Log a structured operational event.

    This is separate from business Memory (SQLite). Use this for fine-grained
    lifecycle events and exceptions (stack traces live here).
    """
    logger.info(event, extra={"extra_fields": {"event": event, **fields}})

