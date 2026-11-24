"""
Structured Error Taxonomy for Microsoft Outlook Automation — Zye Day 23.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from zye_office.errors import ZyeOfficeError


class OutlookAutomationError(ZyeOfficeError):
    def __init__(
        self,
        message: str,
        error_code: str = "OUTLOOK_AUTOMATION_ERROR",
        remediation: str = "Ensure Microsoft Outlook is installed, running, and logged in.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            code=error_code,
            message=message,
            app_name="outlook",
            remediation=remediation,
            details=details,
        )


class OutlookNotInstalledError(OutlookAutomationError):
    def __init__(self, message: str = "Microsoft Outlook is not installed or registered.") -> None:
        super().__init__(message=message, error_code="OUTLOOK_NOT_INSTALLED", remediation="Install Microsoft Office with Outlook.")


class OutlookCOMUnavailableError(OutlookAutomationError):
    def __init__(self, message: str = "Failed to establish COM connection to Outlook.Application.") -> None:
        super().__init__(message=message, error_code="OUTLOOK_COM_UNAVAILABLE", remediation="Launch Microsoft Outlook desktop application.")


class OutlookProfileUnavailableError(OutlookAutomationError):
    def __init__(self, message: str = "No configured Outlook MAPI profile or default mailbox found.") -> None:
        super().__init__(message=message, error_code="OUTLOOK_PROFILE_UNAVAILABLE", remediation="Configure an email account in Microsoft Outlook.")


class OutlookMessageNotFoundError(OutlookAutomationError):
    def __init__(self, message_id: str) -> None:
        super().__init__(
            message=f"Message '{message_id}' was not found in Outlook store.",
            error_code="OUTLOOK_MESSAGE_NOT_FOUND",
            remediation="Verify message EntryID or search criteria.",
            details={"message_id": message_id},
        )


class OutlookSendConfirmationError(OutlookAutomationError):
    def __init__(self, message: str = "Sending email requires explicit user authorization (confirmed=True).") -> None:
        super().__init__(
            message=message,
            error_code="OUTLOOK_SEND_CONFIRMATION_REQUIRED",
            remediation="Review recipients, subject, and attachments, then pass confirmed=True to powerpoint_or_outlook_send.",
        )


class OutlookSecurityError(OutlookAutomationError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            error_code="OUTLOOK_SECURITY_BLOCKED",
            remediation="Operation was blocked due to untrusted attachment or unauthorized mailbox action.",
        )
