"""
Unit tests for GeminiKeyManager — 7-slot credential management, masking, and health tracking.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from gemini_key_manager import GeminiKeyManager, KeySlot, mask_credential, TOTAL_KEY_SLOTS


class TestGeminiKeyManager(unittest.TestCase):
    def setUp(self):
        self.km = GeminiKeyManager(db_path=":memory:", auto_load=False)

    def test_01_seven_slots_initialized(self):
        self.assertEqual(len(self.km.slots), 7)
        for i in range(1, TOTAL_KEY_SLOTS + 1):
            slot = self.km.get_slot(i)
            self.assertIsNotNone(slot)
            self.assertEqual(slot.slot_id, i)
            self.assertEqual(slot.account_alias, f"ACCOUNT_{i:02d}")
            self.assertEqual(slot.project_alias, f"PROJECT_{i:02d}")

    def test_02_mask_credential_hides_secrets(self):
        raw_key = "AIzaSyDummySecretKey1234567890ABCD"
        masked = mask_credential(raw_key)
        self.assertNotIn("AIzaSy", masked)
        self.assertNotIn("DummySecretKey", masked)
        self.assertTrue(masked.endswith("ABCD"))
        self.assertTrue(masked.startswith("************"))

    def test_03_mask_credential_empty_or_none(self):
        self.assertEqual(mask_credential(None), "NOT_CONFIGURED")
        self.assertEqual(mask_credential(""), "NOT_CONFIGURED")
        self.assertEqual(mask_credential("   "), "NOT_CONFIGURED")

    def test_04_get_slot_by_aliases(self):
        slot_by_int = self.km.get_slot(3)
        slot_by_acc = self.km.get_slot("ACCOUNT_03")
        slot_by_proj = self.km.get_slot("PROJECT_03")
        self.assertEqual(slot_by_int, slot_by_acc)
        self.assertEqual(slot_by_int, slot_by_proj)

    def test_05_auth_failed_marks_degraded(self):
        self.km.mark_auth_failed(2)
        slot = self.km.get_slot(2)
        self.assertEqual(slot.auth_status, "AUTH_FAILED")
        self.assertIn(slot.key_health, ["DEGRADED", "UNAVAILABLE"])

    def test_06_record_usage_increments_counters(self):
        slot = self.km.get_slot(1)
        init_reqs = slot.total_requests
        self.km.record_usage(1, input_tokens=100, output_tokens=50, thinking_tokens=20, success=True)
        self.assertEqual(slot.total_requests, init_reqs + 1)
        self.assertEqual(slot.successful_requests, 1)
        self.assertEqual(slot.total_input_tokens, 100)
        self.assertEqual(slot.total_output_tokens, 50)
        self.assertEqual(slot.total_thinking_tokens, 20)

    def test_07_rate_limited_marks_slot(self):
        self.km.mark_rate_limited(4)
        slot = self.km.get_slot(4)
        self.assertEqual(slot.auth_status, "RATE_LIMITED")

    def test_08_get_client_returns_none_if_disabled(self):
        slot = self.km.get_slot(5)
        slot.enabled = False
        client = self.km.get_client(5)
        self.assertIsNone(client)

    def test_09_database_sync(self):
        self.km.sync_to_database()
        summary = self.km.get_masked_admin_summary()
        self.assertEqual(len(summary), 7)
        self.assertIn("masked_key", summary[0])


if __name__ == "__main__":
    unittest.main()
