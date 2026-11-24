"""
Publication Timestamp Validation & Freshness Engine (Day 38 / Phase 3).
Parses multi-format publication dates, standardizes to UTC, enforces freshness windows,
and detects future or missing timestamps.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional, Tuple


class TimestampValidator:
    """Rigorous parser and freshness validator for news publication timestamps."""

    @classmethod
    def validate_and_normalize(
        cls,
        raw_date: Optional[str],
        freshness_window_hours: float = 72.0,
        as_of_timestamp: Optional[float] = None,
    ) -> Tuple[str, Optional[str], Optional[float], bool]:
        """
        Parses and validates a publication date string.
        Returns:
            (status, iso_utc_string, epoch_seconds, is_stale)
        Status values:
            - VALID_UTC: Cleanly parsed and normalized
            - MISSING_TIMESTAMP: Date was None, blank, or unspecified
            - INVALID_TIMESTAMP: Unparseable date format
            - FUTURE_TIMESTAMP: Date is set in the future (> 1 hour ahead)
            - STALE: Date is valid but exceeds freshness_window_hours
        """
        now_epoch = as_of_timestamp if as_of_timestamp is not None else time.time()
        now_dt = datetime.fromtimestamp(now_epoch, tz=timezone.utc)

        if not raw_date or not isinstance(raw_date, str) or not raw_date.strip():
            return "MISSING_TIMESTAMP", None, None, False

        date_str = raw_date.strip()
        parsed_dt: Optional[datetime] = None

        # 1. Check relative date strings (e.g. "2 hours ago", "45 mins ago", "1 day ago")
        rel_match = re.match(r"^(\d+)\s+(min|minute|hour|day|week)s?\s+ago$", date_str, re.IGNORECASE)
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            seconds_offset = 0
            if unit.startswith("min"):
                seconds_offset = amount * 60
            elif unit.startswith("hour"):
                seconds_offset = amount * 3600
            elif unit.startswith("day"):
                seconds_offset = amount * 86400
            elif unit.startswith("week"):
                seconds_offset = amount * 604800
            epoch_val = now_epoch - seconds_offset
            parsed_dt = datetime.fromtimestamp(epoch_val, tz=timezone.utc)

        # 2. ISO 8601 Parsing (e.g. "2026-11-22T10:00:00Z" or "2026-11-22T15:30:00+05:30")
        if parsed_dt is None:
            try:
                # Replace trailing 'Z' with '+00:00' for standard fromisoformat
                iso_clean = date_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_clean)
                if dt.tzinfo is None:
                    parsed_dt = dt.replace(tzinfo=timezone.utc)
                else:
                    parsed_dt = dt.astimezone(timezone.utc)
            except Exception:
                pass

        # 3. RFC 2822 / HTTP Date Parsing (e.g. "Sun, 22 Nov 2026 10:00:00 GMT")
        if parsed_dt is None:
            try:
                dt = parsedate_to_datetime(date_str)
                if dt.tzinfo is None:
                    parsed_dt = dt.replace(tzinfo=timezone.utc)
                else:
                    parsed_dt = dt.astimezone(timezone.utc)
            except Exception:
                pass

        # 4. Common Standard Datetime Formats
        if parsed_dt is None:
            common_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d-%m-%Y %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
                "%b %d, %Y %H:%M",
                "%B %d, %Y",
            ]
            for fmt in common_formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    parsed_dt = dt.replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

        if parsed_dt is None:
            return "INVALID_TIMESTAMP", None, None, False

        epoch_val = parsed_dt.timestamp()
        iso_utc = parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 5. Future timestamp detection (allow up to 1-hour clock skew)
        if epoch_val > (now_epoch + 3600.0):
            return "FUTURE_TIMESTAMP", iso_utc, epoch_val, False

        # 6. Freshness window check
        age_hours = (now_epoch - epoch_val) / 3600.0
        if freshness_window_hours > 0 and age_hours > freshness_window_hours:
            return "STALE", iso_utc, epoch_val, True

        return "VALID_UTC", iso_utc, epoch_val, False

    @classmethod
    def parse_timestamp(
        cls,
        raw_date: Optional[str],
        as_of_epoch: Optional[float] = None,
    ) -> Tuple[bool, Optional[datetime]]:
        """Parses a date string and returns (is_valid, datetime_utc)."""
        status, iso_utc, epoch_val, _ = cls.validate_and_normalize(
            raw_date=raw_date,
            as_of_timestamp=as_of_epoch,
            freshness_window_hours=0.0,
        )
        if status in ("VALID_UTC", "STALE") and epoch_val is not None:
            return True, datetime.fromtimestamp(epoch_val, tz=timezone.utc)
        return False, None

    @classmethod
    def is_fresh(
        cls,
        dt: Optional[datetime],
        window_hours: float = 72.0,
        as_of_epoch: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """Checks if a datetime is within window_hours of reference epoch."""
        if dt is None:
            return False, 999999.0
        now_epoch = as_of_epoch if as_of_epoch is not None else time.time()
        age_hours = (now_epoch - dt.timestamp()) / 3600.0
        return (age_hours <= window_hours and age_hours >= -1.0), age_hours

