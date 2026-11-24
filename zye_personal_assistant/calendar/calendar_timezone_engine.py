"""
Timezone Engine for Zye Smart Calendar (Day 28).
Provides robust, offline-capable timezone conversions, normalization, and DST handling using Python standard zoneinfo.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import zoneinfo

logger = logging.getLogger("zye.personal_assistant.timezone")

DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_configured_timezone(override_tz: Optional[str] = None) -> str:
    """Return validated IANA timezone name."""
    if override_tz and validate_timezone(override_tz):
        return override_tz.strip()
    return DEFAULT_TIMEZONE


def validate_timezone(tz_name: str) -> bool:
    """Check if the timezone name is recognized by the system IANA database."""
    if not tz_name or not isinstance(tz_name, str):
        return False
    try:
        zoneinfo.ZoneInfo(tz_name.strip())
        return True
    except Exception:
        return False


def get_zone_info(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """Get ZoneInfo object, falling back safely to DEFAULT_TIMEZONE or UTC."""
    name = get_configured_timezone(tz_name)
    try:
        return zoneinfo.ZoneInfo(name)
    except Exception:
        return zoneinfo.ZoneInfo("UTC")


def convert_local_to_utc(dt: datetime, fallback_tz: str = DEFAULT_TIMEZONE) -> Tuple[int, datetime]:
    """
    Convert a datetime to UTC epoch milliseconds and aware UTC datetime.
    If datetime is naive, assign fallback timezone.
    """
    if dt.tzinfo is None:
        tz = get_zone_info(fallback_tz)
        dt = dt.replace(tzinfo=tz)

    utc_dt = dt.astimezone(timezone.utc)
    epoch_ms = int(utc_dt.timestamp() * 1000)
    return epoch_ms, utc_dt


def convert_utc_to_local(epoch_ms: int, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """Convert UTC epoch milliseconds to a local timezone-aware datetime."""
    tz = get_zone_info(tz_name)
    utc_dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    return utc_dt.astimezone(tz)


def parse_datetime_iso(iso_str: str, fallback_tz: str = DEFAULT_TIMEZONE) -> Tuple[datetime, int, str]:
    """
    Parse an ISO string into:
      1. Timezone-aware local datetime
      2. UTC epoch milliseconds
      3. Normalized ISO string with timezone offset
    """
    clean = iso_str.strip()
    if not clean:
        raise ValueError("Datetime string cannot be empty.")

    try:
        dt = datetime.fromisoformat(clean)
    except Exception as exc:
        raise ValueError(f"Failed to parse datetime '{clean}': {exc}")

    if dt.tzinfo is None:
        tz = get_zone_info(fallback_tz)
        dt = dt.replace(tzinfo=tz)

    epoch_ms, _ = convert_local_to_utc(dt, fallback_tz)
    return dt, epoch_ms, dt.isoformat()


def get_current_local_datetime(tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """Return the current local time in the specified timezone."""
    tz = get_zone_info(tz_name)
    return datetime.now(tz)


def format_event_time(dt: datetime, tz_name: Optional[str] = None) -> str:
    """Format datetime into a clear human-readable string for voice/display."""
    target_tz = get_zone_info(tz_name) if tz_name else dt.tzinfo
    if target_tz and dt.tzinfo != target_tz:
        dt = dt.astimezone(target_tz)

    return dt.strftime("%A, %b %d, %Y at %I:%M %p")
