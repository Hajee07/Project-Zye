"""
Audit Logging & Intelligence History — Zye Day 13.
Logs structured JSON events for Negative Brain Audits, Mission Transitions,
Autonomous Watchdog Scans, and Emergency Reflexes with automatic secret redaction.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
from datetime import datetime, timezone
from typing import Any

from zye_guard import redact_secrets

LOGS_DIR = pathlib.Path.cwd() / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def _get_rotating_logger(name: str, log_filename: str) -> logging.Logger:
    """Create or retrieve a rotating file logger for intelligence audit streams."""
    logger = logging.getLogger(f"zye.audit.{name}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        log_path = LOGS_DIR / log_filename
        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


_audit_logger = _get_rotating_logger("negative_brain", "zye_negative_audit.log")
_mission_logger = _get_rotating_logger("missions", "zye_mission_history.log")
_watchdog_logger = _get_rotating_logger("watchdog", "zye_autonomous_watchdog.log")
_reflex_logger = _get_rotating_logger("emergency", "zye_emergency_reflex.log")


def log_negative_audit(report: dict[str, Any]) -> None:
    """Log structured negative pre-mortem audit event with redacted secrets."""
    try:
        raw_json = json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "NEGATIVE_AUDIT",
            "report": report,
        })
        redacted = redact_secrets(raw_json)
        _audit_logger.info(redacted)
    except Exception as exc:
        logging.getLogger("zye.intelligence").warning("Failed to log negative audit: %s", exc)


def log_mission_transition(from_mission: str, to_mission: str, reason: str) -> None:
    """Log mission profile transition event."""
    try:
        raw_json = json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "MISSION_TRANSITION",
            "from_mission": from_mission,
            "to_mission": to_mission,
            "reason": reason,
        })
        redacted = redact_secrets(raw_json)
        _mission_logger.info(redacted)
    except Exception as exc:
        logging.getLogger("zye.intelligence").warning("Failed to log mission transition: %s", exc)


def log_watchdog_event(event: dict[str, Any]) -> None:
    """Log autonomous watchdog scan and problem detection event."""
    try:
        raw_json = json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "WATCHDOG_SCAN",
            "data": event,
        })
        redacted = redact_secrets(raw_json)
        _watchdog_logger.info(redacted)
    except Exception as exc:
        logging.getLogger("zye.intelligence").warning("Failed to log watchdog event: %s", exc)


def log_emergency_reflex(reflex_result: dict[str, Any]) -> None:
    """Log emergency reflex execution event."""
    try:
        raw_json = json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "EMERGENCY_REFLEX",
            "result": reflex_result,
        })
        redacted = redact_secrets(raw_json)
        _reflex_logger.info(redacted)
    except Exception as exc:
        logging.getLogger("zye.intelligence").warning("Failed to log emergency reflex: %s", exc)
