"""
Acceptance Test Suite: Publication Timestamp Validation Engine (Day 38 / Phase 3).
Tests 13-18 covering ISO 8601, RFC 2822, missing dates, corrupted formats, future dates, and freshness windows.
"""

from datetime import datetime, timezone
import unittest
from zye_realtime_tactical.news.timestamp_validator import TimestampValidator


class TestNewsTimestampValidator(unittest.TestCase):
    """Verifies strict timestamp parsing, UTC standardization, and freshness threshold gates."""

    def setUp(self) -> None:
        self.ref_epoch = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc).timestamp()

    def test_13_valid_iso_8601_utc_parsing(self):
        """Test 13: Standard ISO 8601 timestamps normalized strictly to UTC."""
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date="2026-11-22T08:30:00Z",
            freshness_window_hours=72.0,
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "VALID_UTC")
        self.assertEqual(iso_utc, "2026-11-22T08:30:00Z")
        self.assertFalse(is_stale)
        self.assertIsNotNone(epoch_ts)

    def test_14_rfc_2822_http_date_parsing(self):
        """Test 14: RFC 2822 / HTTP format dates parsed and converted to UTC."""
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date="Sun, 22 Nov 2026 06:15:00 GMT",
            freshness_window_hours=72.0,
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "VALID_UTC")
        self.assertEqual(iso_utc, "2026-11-22T06:15:00Z")
        self.assertFalse(is_stale)

    def test_15_missing_timestamp_disqualification(self):
        """Test 15: Articles missing timestamps return MISSING_TIMESTAMP and fail freshness."""
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date="",
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "MISSING_TIMESTAMP")
        self.assertIsNone(iso_utc)
        self.assertIsNone(epoch_ts)

        status_none, _, _, _ = TimestampValidator.validate_and_normalize(None, as_of_timestamp=self.ref_epoch)
        self.assertEqual(status_none, "MISSING_TIMESTAMP")

    def test_16_invalid_timestamp_format_rejected(self):
        """Test 16: Corrupted or unrecognizable date strings return INVALID_TIMESTAMP."""
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date="sometime last week or maybe earlier",
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "INVALID_TIMESTAMP")
        self.assertIsNone(iso_utc)

    def test_17_future_timestamp_disqualified(self):
        """Test 17: Dates set > 1 hour in the future return FUTURE_TIMESTAMP."""
        future_str = "2026-11-25T12:00:00Z"
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date=future_str,
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "FUTURE_TIMESTAMP")
        self.assertFalse(is_stale)
        self.assertIsNotNone(epoch_ts)

    def test_18_stale_article_beyond_freshness_window(self):
        """Test 18: Valid articles older than freshness_window_hours (e.g. 72h) return STALE with is_stale=True."""
        stale_str = "2026-11-15T12:00:00Z"  # 7 days old
        status, iso_utc, epoch_ts, is_stale = TimestampValidator.validate_and_normalize(
            raw_date=stale_str,
            freshness_window_hours=72.0,
            as_of_timestamp=self.ref_epoch,
        )
        self.assertEqual(status, "STALE")
        self.assertTrue(is_stale)
        self.assertIsNotNone(epoch_ts)


if __name__ == "__main__":
    unittest.main()
