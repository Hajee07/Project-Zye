# ZYE AI — Day 28 Timezone Architecture & Datetime Standardization

## 1. Timezone Principle
1. **Internal Normalization:** All comparison, conflict analysis, and persistent triggers operate in integer UTC epoch milliseconds (`start_utc`, `end_utc`, `due_at_utc`).
2. **Local Display & Voice:** All human-facing interactions use timezone-aware strings formatted in the user's configured local timezone (`Asia/Kolkata` by default, or overridden dynamically).
3. **Standard Python Library:** ZoneInfo (`zoneinfo.ZoneInfo`) is utilized exclusively without introducing external dependencies.

## 2. Parsing Pipeline
Given an input ISO string (e.g. `2026-11-25T10:00:00`):
1. `parse_datetime_iso`:
   - Strips whitespace.
   - If naive, attaches `get_zone_info(fallback_tz)`.
   - Converts to aware UTC datetime via `.astimezone(timezone.utc)`.
   - Computes `epoch_ms = int(utc_dt.timestamp() * 1000)`.
   - Normalizes ISO format with exact UTC offset: `2026-11-25T10:00:00+05:30`.
2. Validation:
   - Verifies $start < end$.
   - Bounds duration to $[5, 1440]$ minutes.

## 3. Supported Timezone Conversions
- Any valid IANA timezone identifier (e.g., `Asia/Kolkata`, `America/New_York`, `Europe/London`, `UTC`, `Asia/Dubai`) is dynamically resolved.
- Invalid strings fall back securely to `DEFAULT_TIMEZONE` (`Asia/Kolkata`), ensuring zero crashes on malformed voice transcripts.
