"""
Validation & Constraint Enforcement for Microsoft Outlook Automation — Zye Day 23.
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Optional
from zye_office.outlook.outlook_errors import OutlookSecurityError

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".vbs", ".ps1", ".scr", ".js", ".hta", ".pif"}


class OutlookValidator:
    """Validates email addresses, attachments, and recipients."""

    @staticmethod
    def validate_email_address(email: str) -> str:
        clean = email.strip()
        # Accept name <email> or raw email
        match = re.search(r"[\w\.-]+@[\w\.-]+", clean)
        if not match:
            raise OutlookSecurityError(f"Invalid email address format: '{email}'")
        return clean

    @staticmethod
    def validate_attachment(file_path: str, max_size_bytes: int = 25 * 1024 * 1024) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in DANGEROUS_EXTENSIONS:
            raise OutlookSecurityError(f"Blocked executable attachment with dangerous extension '{ext}'.")

        size = os.path.getsize(file_path)
        if size > max_size_bytes:
            raise OutlookSecurityError(f"Attachment exceeds maximum allowed size of {max_size_bytes / (1024*1024)}MB.")

        return os.path.abspath(file_path)
