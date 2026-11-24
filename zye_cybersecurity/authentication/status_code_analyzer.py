"""
ZYE AI — Windows NTSTATUS Authentication Status Code Analyzer (Day 40).
Provides documented mappings for Windows Status and SubStatus NTSTATUS failure codes,
deciphering failure reasons (invalid password, user not found, account locked).
"""

from __future__ import annotations

import re
from typing import Dict, NamedTuple, Optional, Tuple


class StatusCodeInfo(NamedTuple):
    code: str
    symbol: str
    description: str


# Documented Windows NTSTATUS Logon Failure Codes:
# https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-4625
NTSTATUS_FAILURE_CODES: Dict[str, Tuple[str, str]] = {
    "0xC0000064": (
        "STATUS_NO_SUCH_USER",
        "User name does not exist. The specified user account is not recognized.",
    ),
    "0xC000006A": (
        "STATUS_WRONG_PASSWORD",
        "Incorrect password. The user name is valid but the password provided was wrong.",
    ),
    "0xC000006D": (
        "STATUS_LOGON_FAILURE",
        "Generic logon failure. Indicates that the attempted logon is invalid (often paired with a specific SubStatus).",
    ),
    "0xC0000234": (
        "STATUS_ACCOUNT_LOCKED_OUT",
        "User account has been locked out because the number of failed attempts exceeded policy.",
    ),
    "0xC0000072": (
        "STATUS_ACCOUNT_DISABLED",
        "User account is disabled. An attempt was made to log in using a disabled account.",
    ),
    "0xC000015B": (
        "STATUS_LOGON_TYPE_NOT_GRANTED",
        "The user has not been granted the requested logon type at this computer (e.g. no Allow log on through Remote Desktop).",
    ),
    "0xC0000193": (
        "STATUS_ACCOUNT_EXPIRED",
        "The user account has expired and is no longer valid.",
    ),
    "0xC0000224": (
        "STATUS_PASSWORD_MUST_CHANGE",
        "User must change password at next logon.",
    ),
    "0xC000006E": (
        "STATUS_ACCOUNT_RESTRICTION",
        "Account restriction (e.g. user cannot log on during these hours or from this computer).",
    ),
    "0xC0000070": (
        "STATUS_INVALID_WORKSTATION",
        "Workstation restriction. The user is not authorized to log on from this workstation.",
    ),
    "0xC0000071": (
        "STATUS_PASSWORD_EXPIRED",
        "The user account password has expired.",
    ),
    "0xC0000022": (
        "STATUS_ACCESS_DENIED",
        "Access denied. An internal authorization check failed.",
    ),
    "0xC0000133": (
        "STATUS_TIME_DIFFERENCE_AT_DC",
        "Clocks between the client and the domain controller are out of synchronization.",
    ),
}


class StatusCodeAnalyzer:
    """Deciphers and explains hexadecimal NTSTATUS and SubStatus failure codes."""

    @staticmethod
    def normalize_hex_code(code: Optional[str]) -> Optional[str]:
        """Normalize hex string to standard uppercase format (e.g. '0xc000006a' -> '0xC000006A')."""
        if not code or not isinstance(code, str):
            return None
        cleaned = code.strip()
        if cleaned in ("-", "", "%%0"):
            return None
        if cleaned.lower().startswith("0x"):
            return "0x" + cleaned[2:].upper()
        # Handle bare hex
        if re.match(r"^[0-9a-fA-F]{8}$", cleaned):
            return "0x" + cleaned.upper()
        return cleaned

    @classmethod
    def get_status_info(cls, status_hex: Optional[str]) -> StatusCodeInfo:
        """
        Return StatusCodeInfo(code, symbol, description).
        Can be accessed as named tuple (.symbol, .description) or unpacked as 2-tuple.
        """
        norm = cls.normalize_hex_code(status_hex)
        if not norm:
            return StatusCodeInfo(
                code="UNKNOWN",
                symbol="UNKNOWN_STATUS_CODE",
                description="Status code not provided.",
            )

        if norm in NTSTATUS_FAILURE_CODES:
            symbol, desc = NTSTATUS_FAILURE_CODES[norm]
            return StatusCodeInfo(code=norm, symbol=symbol, description=desc)

        return StatusCodeInfo(
            code=norm,
            symbol="STATUS_UNKNOWN_FAILURE",
            description=f"Unknown or unmapped Windows NTSTATUS failure code: {norm}.",
        )

    @classmethod
    def is_bad_password(cls, status_hex: Optional[str]) -> bool:
        """Check if status corresponds to wrong password."""
        norm = cls.normalize_hex_code(status_hex)
        return norm == "0xC000006A"

    @classmethod
    def is_account_not_found(cls, status_hex: Optional[str]) -> bool:
        """Check if status corresponds to non-existent account."""
        norm = cls.normalize_hex_code(status_hex)
        return norm == "0xC0000064"

    @classmethod
    def is_account_locked(cls, status_hex: Optional[str]) -> bool:
        """Check if status corresponds to locked account."""
        norm = cls.normalize_hex_code(status_hex)
        return norm == "0xC0000234"

    @classmethod
    def determine_failure_reason(cls, status: Optional[str], sub_status: Optional[str]) -> str:
        """
        Determine human-readable root cause explanation.
        SubStatus takes precedence over generic Status (0xC000006D).
        """
        effective = sub_status if sub_status and sub_status != "0x0" else status
        info = cls.get_status_info(effective)
        return info.description
