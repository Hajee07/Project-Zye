"""
Gemini Error Handler — Zye Multi-Project Gemini Intelligence Infrastructure v2.0 (Section 13).
Handles API status codes (400, 401, 403, 404, 429, 500, 503, TIMEOUT), enforces exponential
backoff with jitter, respects Retry-After, sanitizes error logs, and prevents rate-limit evasion.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from gemini_db import get_db_connection

logger = logging.getLogger("zye.gemini.error_handler")

# Status codes that may be retried safely
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422}


@dataclass
class ErrorHandlingResult:
    """Outcome of error evaluation and recovery plan."""
    status_code: int | None
    error_type: str
    sanitized_message: str
    retryable: bool
    retry_delay_seconds: float = 0.0
    action: str = "FAIL"  # RETRY, FAIL, PAUSE_PROJECT, AUTH_ALERT


class GeminiErrorHandler:
    """
    Evaluator and dispatcher for Gemini API exceptions and connection faults.
    """

    def __init__(
        self,
        db_path: str | None = None,
        max_retries: int = 3,
        base_backoff_seconds: float = 2.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        self._db_path = db_path
        self._max_retries = max_retries
        self._base_backoff = base_backoff_seconds
        self._max_backoff = max_backoff_seconds
        self._lock = threading.RLock()

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def parse_status_code(self, exc: Exception) -> int | None:
        """Extract HTTP status code from exception object or string."""
        if hasattr(exc, "status_code") and isinstance(exc.status_code, int):
            return exc.status_code
        if hasattr(exc, "code") and isinstance(exc.code, int):
            return exc.code

        # Regex scan message
        msg = str(exc)
        match = re.search(r"\b(400|401|403|404|429|500|502|503|504)\b", msg)
        if match:
            return int(match.group(1))

        if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower() or "rate limit" in msg.lower():
            return 429
        if "UNAUTHENTICATED" in msg or "invalid api key" in msg.lower():
            return 401
        if "PERMISSION_DENIED" in msg:
            return 403
        if "NOT_FOUND" in msg:
            return 404
        if "DEADLINE_EXCEEDED" in msg or "timed out" in msg.lower() or "timeout" in msg.lower():
            return 504
        if "UNAVAILABLE" in msg:
            return 503

        return None

    def extract_retry_after(self, exc: Exception) -> float:
        """Extract suggested retry delay in seconds if indicated in headers or text."""
        # Check attributes
        if hasattr(exc, "retry_after") and isinstance(exc.retry_after, (int, float)):
            return float(exc.retry_after)

        msg = str(exc)
        # Search for pattern: Retry-After: <seconds> or retry in <seconds>s
        match = re.search(r"(?:retry[-_]after|retry\s+in)\s*[:=]?\s*(\d+(?:\.\d+)?)", msg, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return 0.0

    def sanitize_message(self, message: str) -> str:
        """Strip raw API keys, credentials, and tokens from error strings."""
        if not message:
            return ""

        # Mask potential Gemini API keys (starts with AIza or AQ. or similar base64-like strings)
        cleaned = re.sub(r"(AIza[0-9A-Za-z-_]{35})", "************[REDACTED_API_KEY]", message)
        cleaned = re.sub(r"(AQ\.[0-9A-Za-z-_]{20,})", "************[REDACTED_API_KEY]", cleaned)
        cleaned = re.sub(r"(key=)[0-9A-Za-z-_]+", r"\1[REDACTED]", cleaned)
        cleaned = re.sub(r"(api_key['\":\s=]+)[0-9A-Za-z-_]+", r"\1[REDACTED]", cleaned, flags=re.IGNORECASE)
        return cleaned

    def calculate_backoff(self, retry_count: int, retry_after: float = 0.0) -> float:
        """Calculate exponential backoff with random jitter."""
        if retry_after > 0:
            # Jitter the Retry-After slightly (0 to 10%)
            jitter = random.uniform(0.0, max(0.5, retry_after * 0.1))
            return min(self._max_backoff, retry_after + jitter)

        backoff = self._base_backoff * (2 ** retry_count)
        jitter = random.uniform(0.1, max(0.5, backoff * 0.2))
        return min(self._max_backoff, backoff + jitter)

    def evaluate_error(
        self,
        exc: Exception,
        slot_id: int,
        retry_count: int = 0,
        request_id: str | None = None,
        project_id: str | None = None,
    ) -> ErrorHandlingResult:
        """
        Evaluate an exception from a Gemini API invocation and decide recovery strategy.
        Persists diagnostic telemetry to gemini_error_history.
        """
        code = self.parse_status_code(exc)
        raw_msg = str(exc)
        sanitized = self.sanitize_message(raw_msg)
        retry_after = self.extract_retry_after(exc)

        # Classify error type
        if code == 429:
            error_type = "RESOURCE_EXHAUSTED"
            retryable = (retry_count < self._max_retries)
            delay = self.calculate_backoff(retry_count, retry_after)
            action = "PAUSE_PROJECT" if not retryable else "RETRY"
        elif code in (401, 403):
            error_type = "AUTH_PERMISSION_ERROR"
            retryable = False
            delay = 0.0
            action = "AUTH_ALERT"
        elif code == 404:
            error_type = "MODEL_NOT_FOUND"
            retryable = False
            delay = 0.0
            action = "FAIL"
        elif code == 400:
            error_type = "INVALID_ARGUMENT"
            retryable = False
            delay = 0.0
            action = "FAIL"
        elif code in (500, 502, 503, 504):
            error_type = "SERVICE_UNAVAILABLE"
            retryable = (retry_count < self._max_retries)
            delay = self.calculate_backoff(retry_count, retry_after)
            action = "RETRY" if retryable else "FAIL"
        else:
            # Catch-all
            error_type = type(exc).__name__
            retryable = (retry_count < self._max_retries) and any(
                term in sanitized.lower() for term in ["timeout", "connection", "reset", "closed"]
            )
            delay = self.calculate_backoff(retry_count, retry_after) if retryable else 0.0
            action = "RETRY" if retryable else "FAIL"

        self.log_error_to_db(
            request_id=request_id,
            slot_id=slot_id,
            project_id=project_id,
            status_code=code,
            error_type=error_type,
            sanitized_message=sanitized,
            retry_count=retry_count,
            retry_after_seconds=delay,
        )

        return ErrorHandlingResult(
            status_code=code,
            error_type=error_type,
            sanitized_message=sanitized,
            retryable=retryable,
            retry_delay_seconds=delay,
            action=action,
        )

    def log_error_to_db(
        self,
        request_id: str | None,
        slot_id: int,
        project_id: str | None,
        status_code: int | None,
        error_type: str,
        sanitized_message: str,
        retry_count: int,
        retry_after_seconds: float,
    ) -> None:
        """Insert error record into gemini_error_history table."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = get_db_connection(self._db_path)
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO gemini_error_history
                        (request_id, slot_id, project_id, status_code, error_type, sanitized_message, retry_count, retry_after_seconds, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        request_id or "NONE",
                        slot_id,
                        project_id or f"zye-project-{slot_id:02d}",
                        status_code,
                        error_type,
                        sanitized_message[:1000],  # cap message length
                        retry_count,
                        retry_after_seconds,
                        now,
                    ))
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to log error to gemini_error_history: %s", exc)
