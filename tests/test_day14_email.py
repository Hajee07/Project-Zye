"""
Unit tests for Day 14 Email Management Intelligence Engine.
Verifies triage prioritization, draft storage, recipient validation, and send safety.
"""

import os
import tempfile
import unittest
from pathlib import Path

from zye_personal_assistant.email_engine import EmailEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestDay14Email(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_em_test_")
        os.close(self._tmp_fd)
        sg = SafetyGateway(db_path=self._tmp_path)
        self.engine = EmailEngine(db_path=self._tmp_path, safety_gateway=sg)

    def tearDown(self):
        try:
            Path(self._tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_priority_classification_rules(self):
        self.assertEqual(self.engine.classify_email_priority("URGENT: Production outage", "Server down"), "CRITICAL")
        self.assertEqual(self.engine.classify_email_priority("Invoice for Review", "Please find attached invoice"), "HIGH")
        self.assertEqual(self.engine.classify_email_priority("Weekly Status Update", "Here is our weekly report"), "MEDIUM")
        self.assertEqual(self.engine.classify_email_priority("Monthly Newsletter", "Check out new marketing updates"), "LOW")

    def test_02_create_draft_stores_in_database(self):
        res = self.engine.create_draft(
            to_addr="partner@enterprise.com",
            subject="Collaboration Proposal",
            body="Looking forward to exploring synergies.",
            tone="Professional",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("draft_id", res)
        self.assertEqual(res["to_addr"], "partner@enterprise.com")

    def test_03_send_email_requires_explicit_confirmation(self):
        res = self.engine.send_email(
            to_addr="client@acme.com",
            subject="Contract Execution",
            body="Please see contract details.",
            confirmed=False,
        )
        self.assertEqual(res["status"], "CONFIRMATION_REQUIRED")
        self.assertIn("safety_audit", res)
        self.assertEqual(res["recipient"], "client@acme.com")

    def test_04_send_email_invalid_recipient_rejected(self):
        res = self.engine.send_email(
            to_addr="invalid-email-address",
            subject="Hello",
            body="Testing",
            confirmed=True,
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("Invalid recipient", res["message"])

    def test_05_attachment_validation(self):
        # Non-existent attachment
        res = self.engine.send_email(
            to_addr="valid@acme.com",
            subject="File",
            body="Test",
            confirmed=True,
            attachments=["/non/existent/invoice.pdf"],
        )
        self.assertEqual(res["status"], "ERROR")
        self.assertIn("Attachment file not found", res["message"])


if __name__ == "__main__":
    unittest.main()
