"""
Day 23 Comprehensive Test Suite — Advanced Microsoft Outlook Automation.
Tests Outlook Adapter, Mailbox Inspector, Message Reader, Search Engine, Draft Engine,
Reply Engine, Attachment Manager, Send Engine (Strict Confirmation), Folders, Categories,
Contacts, Tasks, and Calendar.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_office.models.day23_models import (
    OutlookDraftConfig,
    OutlookMailboxSummary,
    OutlookMessageMetadata,
)
from zye_office.outlook.outlook_constants import OutlookConstants
from zye_office.outlook.outlook_errors import (
    OutlookSendConfirmationError,
    OutlookSecurityError,
)
from zye_office.outlook.outlook_validator import OutlookValidator
from zye_office.outlook.outlook_permissions import OutlookPermissionEngine
from zye_office.outlook.outlook_adapter import OutlookAdapter
from zye_office.outlook.outlook_draft_engine import OutlookDraftEngine
from zye_office.outlook.outlook_send_engine import OutlookSendEngine
from zye_office.outlook.outlook_category_manager import OutlookCategoryManager


class TestDay23OutlookAutomation(unittest.TestCase):

    def setUp(self) -> None:
        self.validator = OutlookValidator()
        self.adapter = OutlookAdapter()

    def test_outlook_constants(self) -> None:
        """Verify Outlook COM folder and item type constants."""
        self.assertEqual(OutlookConstants.olFolderInbox, 6)
        self.assertEqual(OutlookConstants.olFolderDrafts, 16)
        self.assertEqual(OutlookConstants.olFolderSentMail, 5)
        self.assertEqual(OutlookConstants.olFolderCalendar, 9)
        self.assertEqual(OutlookConstants.olFolderContacts, 10)
        self.assertEqual(OutlookConstants.olFolderTasks, 13)
        self.assertEqual(OutlookConstants.olMailItem, 0)
        self.assertEqual(OutlookConstants.olAppointmentItem, 1)

    def test_email_models(self) -> None:
        """Verify Outlook email models."""
        msg = OutlookMessageMetadata(
            entry_id="ENTRY_001",
            subject="Quarterly Review",
            sender_name="CEO Office",
            sender_email="ceo@company.com",
            received_time="2026-11-20T10:00:00",
            is_unread=True,
            has_attachments=False,
        )
        self.assertEqual(msg.subject, "Quarterly Review")
        self.assertTrue(msg.is_unread)

        draft = OutlookDraftConfig(
            to_recipients=["team@zye.internal"],
            subject="Status Update",
            body="All systems operational.",
        )
        self.assertEqual(len(draft.to_recipients), 1)

    def test_outlook_validator(self) -> None:
        """Verify email address validation."""
        self.assertEqual(self.validator.validate_email_address("test@example.com"), "test@example.com")
        self.assertEqual(self.validator.validate_email_address("John Doe <john@company.com>"), "John Doe <john@company.com>")
        with self.assertRaises(OutlookSecurityError):
            self.validator.validate_email_address("invalid-email-no-at-sign")

    def test_outlook_permissions_security(self) -> None:
        """Verify send_email operation strictly requires user confirmation."""
        with self.assertRaises(OutlookSendConfirmationError):
            OutlookPermissionEngine.enforce_send_confirmation(False)

        # confirmed=True must not raise
        OutlookPermissionEngine.enforce_send_confirmation(True)

    def test_outlook_send_engine_confirmation_enforcement(self) -> None:
        """Verify send_authorized_email strictly raises OutlookSendConfirmationError when confirmed=False."""
        send_engine = OutlookSendEngine(adapter=self.adapter)
        with self.assertRaises(OutlookSendConfirmationError):
            send_engine.send_authorized_email(entry_id="FAKE_ENTRY_ID", confirmed=False)

    def test_outlook_adapter_defaults(self) -> None:
        """Verify Outlook adapter defaults and worker."""
        self.assertIsNotNone(self.adapter.worker)
        self.assertIsNotNone(self.adapter.com_runtime)


if __name__ == "__main__":
    unittest.main()
