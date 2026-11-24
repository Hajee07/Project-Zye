"""
Day 29 Test Suite: Email Management Engine
Verifies IMAP unread triage, deterministic priority scoring, draft creation,
audit logging, and two-stage Negative Pre-Mortem SMTP sending confirmation.
"""

import email
import email.message
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zye_personal_assistant.database import init_assistant_database, get_db_connection
from zye_personal_assistant.email_engine import EmailEngine
from zye_personal_assistant.safety_gateway import SafetyGateway


class TestEmailManagement(unittest.TestCase):
    def setUp(self):
        self._tmp_fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite", prefix="zye_test_email_")
        os.close(self._tmp_fd)
        self.db_path = Path(self._tmp_path)
        init_assistant_database(self.db_path)
        self.safety = SafetyGateway(db_path=self.db_path)
        self.engine = EmailEngine(db_path=self.db_path, safety_gateway=self.safety)

    def tearDown(self):
        try:
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_01_fetch_unread_emails_config_required(self):
        """When credentials are not set, engine safely reports CONFIG_REQUIRED without crashing."""
        with patch.dict(os.environ, {}, clear=True):
            res = self.engine.fetch_unread_emails()
            self.assertEqual(res["status"], "CONFIG_REQUIRED")
            self.assertIn("not configured", res["message"].lower())

    def test_02_send_email_config_required(self):
        """When credentials are not set, send_email safely reports CONFIG_REQUIRED."""
        with patch.dict(os.environ, {}, clear=True):
            res = self.engine.send_email(to_addr="test@example.com", subject="Test", body="Hello")
            self.assertEqual(res["status"], "CONFIG_REQUIRED")

    def test_03_create_draft(self):
        """Drafts must be safely stored in the database without network calls."""
        res = self.engine.create_draft(
            to_addr="colleague@example.com",
            subject="Project Update",
            body="Here is the status report for today.",
            priority="HIGH",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["action"], "DRAFT_CREATED")
        self.assertGreater(res["draft_id"], 0)

        conn = get_db_connection(self.db_path)
        try:
            row = conn.execute("SELECT * FROM email_drafts WHERE id = ?;", (res["draft_id"],)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["to_addr"], "colleague@example.com")
            self.assertEqual(row["subject"], "Project Update")
            self.assertEqual(row["priority"], "HIGH")
        finally:
            conn.close()

    def test_04_create_draft_missing_fields(self):
        """Draft creation with empty recipient or subject returns validation error."""
        res1 = self.engine.create_draft(to_addr="", subject="Sub", body="Body")
        self.assertEqual(res1["status"], "ERROR")
        self.assertIn("recipient", res1["message"].lower())

        res2 = self.engine.create_draft(to_addr="a@b.com", subject="", body="Body")
        self.assertEqual(res2["status"], "ERROR")
        self.assertIn("subject", res2["message"].lower())

    def test_05_fetch_unread_with_mock_imap(self):
        """Verifies IMAP fetching, BODY.PEEK[] usage, and deterministic priority triage."""
        env_vars = {
            "ZYE_EMAIL_ADDRESS": "zye_test@example.com",
            "ZYE_EMAIL_APP_PASSWORD": "testpass123",
        }
        with patch.dict(os.environ, env_vars):
            msg1 = email.message.EmailMessage()
            msg1["Subject"] = "URGENT: Server Production Outage"
            msg1["From"] = "boss@enterprise.com"
            msg1.set_content("The primary API server is down, please address immediately!")

            msg2 = email.message.EmailMessage()
            msg2["Subject"] = "Weekly Newsletter #42"
            msg2["From"] = "news@digest.com"
            msg2.set_content("Here are this week's top software engineering updates.")

            mock_mail = MagicMock()
            mock_mail.search.return_value = ("OK", [b"1 2"])

            def mock_fetch(msg_id, spec):
                self.assertIn("BODY.PEEK", spec)
                if msg_id == b"1":
                    return ("OK", [(b"1 (RFC822 {100})", msg1.as_bytes())])
                return ("OK", [(b"2 (RFC822 {100})", msg2.as_bytes())])

            mock_mail.fetch.side_effect = mock_fetch

            with patch("imaplib.IMAP4_SSL") as mock_imap_cls:
                mock_imap_cls.return_value = mock_mail
                mock_mail.login.return_value = ("OK", [b"Success"])
                mock_mail.select.return_value = ("OK", [b"10"])

                result = self.engine.fetch_unread_emails(limit=5)
                self.assertEqual(result["status"], "SUCCESS")
                self.assertEqual(result["unread_count"], 2)
                emails = result["emails"]

                urgent = next(e for e in emails if "Outage" in e["subject"])
                self.assertEqual(urgent["priority"], "CRITICAL")

                newsletter = next(e for e in emails if "Newsletter" in e["subject"])
                self.assertEqual(newsletter["priority"], "LOW")

    def test_06_send_email_gating_and_dispatch(self):
        """Two-stage email send verification with Negative Brain gating."""
        env_vars = {
            "ZYE_EMAIL_ADDRESS": "zye_test@example.com",
            "ZYE_EMAIL_APP_PASSWORD": "testpass123",
        }
        with patch.dict(os.environ, env_vars):
            # Step 1: Unconfirmed request
            stage1 = self.engine.send_email(
                to_addr="partner@example.com",
                subject="Important Contract",
                body="Attached is the signed document.",
                confirmed=False,
            )
            self.assertEqual(stage1["status"], "APPROVAL_REQUIRED")
            self.assertIn("confirmation_id", stage1)
            token = stage1["confirmation_id"]
            self.assertTrue(bool(token))

            # Step 2: Confirm using token
            mock_smtp = MagicMock()
            with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
                mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
                mock_smtp.login.return_value = (235, b"Auth successful")
                mock_smtp.send_message.return_value = {}

                stage2 = self.engine.send_email(
                    to_addr="partner@example.com",
                    subject="Important Contract",
                    body="Attached is the signed document.",
                    confirmation_id=token,
                )
                self.assertEqual(stage2["status"], "SMTP_ACCEPTED")
                self.assertEqual(stage2["recipient"], "partner@example.com")
                mock_smtp.send_message.assert_called_once()

            # Verify SQLite email_action_history record
            conn = get_db_connection(self.db_path)
            try:
                row = conn.execute("SELECT * FROM email_action_history WHERE to_addr = ?;", ("partner@example.com",)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["status"], "SENT")
            finally:
                conn.close()

    def test_07_send_email_failure_handling(self):
        """SMTP server failure returns SEND_FAILED without crashing."""
        env_vars = {
            "ZYE_EMAIL_ADDRESS": "zye_test@example.com",
            "ZYE_EMAIL_APP_PASSWORD": "testpass123",
        }
        with patch.dict(os.environ, env_vars):
            with patch("smtplib.SMTP_SSL") as mock_smtp_cls:
                mock_smtp_cls.side_effect = ConnectionRefusedError("SMTP Connection Refused")
                res = self.engine.send_email(
                    to_addr="test@example.com",
                    subject="Crash Test",
                    body="Should fail safely",
                    confirmed=True,
                )
                self.assertEqual(res["status"], "SEND_FAILED")
                self.assertIn("SMTP Connection Refused", res["message"])


if __name__ == "__main__":
    unittest.main()
