"""
ZYE AI — Music Intelligence Errors
==================================

Structured error codes and exceptions for the ZYE Smart Music System.
Fully compliant with Section 48 of the Master Engineering Specification.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class MusicErrorCode(str, Enum):
    """Structured error codes for all music operations."""
    # Initialization and Device Errors
    MUSIC_INITIALIZATION_FAILED = "MUSIC_INITIALIZATION_FAILED"
    LOCAL_LIBRARY_EMPTY = "LOCAL_LIBRARY_EMPTY"
    TRACK_NOT_FOUND = "TRACK_NOT_FOUND"
    PLAYBACK_DEVICE_UNAVAILABLE = "PLAYBACK_DEVICE_UNAVAILABLE"
    PLAYBACK_FAILED = "PLAYBACK_FAILED"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_ACTIVATION_TIMEOUT = "DEVICE_ACTIVATION_TIMEOUT"

    # Playback Control Errors
    VOLUME_ADJUSTMENT_OUT_OF_BOUNDS = "VOLUME_ADJUSTMENT_OUT_OF_BOUNDS"
    SEEK_OUT_OF_BOUNDS = "SEEK_OUT_OF_BOUNDS"

    # Spotify Platform and Authentication Errors
    SPOTIFY_CONFIG_MISSING = "SPOTIFY_CONFIG_MISSING"
    SPOTIFY_CONFIG_CORRUPT = "SPOTIFY_CONFIG_CORRUPT"
    SPOTIFY_UNAUTHENTICATED = "SPOTIFY_UNAUTHENTICATED"
    SPOTIFY_TOKEN_EXPIRED = "SPOTIFY_TOKEN_EXPIRED"
    SPOTIFY_PREMIUM_REQUIRED = "SPOTIFY_PREMIUM_REQUIRED"
    SPOTIFY_NO_ACTIVE_DEVICE = "SPOTIFY_NO_ACTIVE_DEVICE"
    SPOTIFY_VOICE_NOT_AUTHORIZED = "SPOTIFY_VOICE_NOT_AUTHORIZED"
    SPOTIFY_MCP_PROCESS_CRASHED = "SPOTIFY_MCP_PROCESS_CRASHED"

    # Audio Ducking Errors
    DUCKING_FAILED = "DUCKING_FAILED"
    DUCKING_RESTORE_FAILED = "DUCKING_RESTORE_FAILED"

    # Network, Rate Limits, and Routing Errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    NETWORK_UNREACHABLE = "NETWORK_UNREACHABLE"
    INTENT_UNRECOGNIZED = "INTENT_UNRECOGNIZED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"

    # Validation and Argument Errors
    EMPTY_MUSIC_QUERY = "EMPTY_MUSIC_QUERY"
    MUSIC_QUERY_TOO_LONG = "MUSIC_QUERY_TOO_LONG"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    INVALID_RESULT_LIMIT = "INVALID_RESULT_LIMIT"
    NO_ELIGIBLE_TRACKS = "NO_ELIGIBLE_TRACKS"

    # Playback Verification Codes
    DEVICE_MISMATCH = "DEVICE_MISMATCH"
    TRACK_MISMATCH = "TRACK_MISMATCH"
    ACCEPTED_UNVERIFIED = "ACCEPTED_UNVERIFIED"
    PLAYBACK_VERIFIED = "PLAYBACK_VERIFIED"


class ZyeMusicError(Exception):
    """Base exception class for all music subsystem errors."""

    def __init__(
        self,
        code: MusicErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error for MCP and API consumers."""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class MusicAuthorizationError(ZyeMusicError):
    """Raised when an operation is prohibited by platform compliance rules."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class PlaybackDeviceError(ZyeMusicError):
    """Raised when a playback device is missing or unreachable."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.PLAYBACK_DEVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class SpotifyConfigurationError(ZyeMusicError):
    """Raised when Spotify credentials or configs are missing/invalid."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.SPOTIFY_CONFIG_MISSING,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class AudioDuckingError(ZyeMusicError):
    """Raised when audio ducking or restoration fails."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.DUCKING_FAILED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class TrackNotFoundError(ZyeMusicError):
    """Raised when a requested song or playlist cannot be located."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.TRACK_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class PlaybackExecutionError(ZyeMusicError):
    """Raised when playback command execution encounters a failure."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.PLAYBACK_FAILED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class MusicValidationError(ZyeMusicError, ValueError):
    """Raised when music request arguments or query syntax fail validation."""

    def __init__(
        self,
        message: str,
        code: MusicErrorCode = MusicErrorCode.EMPTY_MUSIC_QUERY,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, details=details)
