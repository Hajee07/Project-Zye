"""
Telemetry Access Policy.
Validates stream identifiers, prevents namespace pollution, and controls stream resets.
"""

from __future__ import annotations

import re
from typing import Tuple

from zye_realtime_tactical.security.telemetry_resource_policy import TelemetryResourcePolicy

STREAM_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,64}$")


class TelemetrySecurityError(Exception):
    """Raised when an invalid, unauthorized, or malformed stream request is encountered."""
    pass


class TelemetryAccessPolicy:
    """Zero-trust policy enforcing stream authorization and naming hygiene."""

    @classmethod
    def validate_stream_name(cls, stream_name: str) -> Tuple[bool, str]:
        """Validates stream name length, character set, and absence of control chars."""
        if not stream_name or not isinstance(stream_name, str):
            return False, "Stream name must be a non-empty string."

        trimmed = stream_name.strip()
        if len(trimmed) > TelemetryResourcePolicy.MAX_STREAM_NAME_LENGTH:
            return False, f"Stream name exceeds maximum length of {TelemetryResourcePolicy.MAX_STREAM_NAME_LENGTH} characters."

        if not STREAM_NAME_REGEX.match(trimmed):
            return False, "Stream name contains invalid characters. Only alphanumeric, underscores, hyphens, and colons are permitted."

        return True, "Valid"
