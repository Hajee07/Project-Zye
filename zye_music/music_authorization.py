"""
ZYE AI — Music Platform Authorization Engine
============================================

Enforces strict compliance with Spotify Developer Policy, Section 03/04/10/44
of the Master Engineering Specification.

Modes:
- Mode A: Manual Spotify Control (via MCP tools, explicit GUI/text orchestrator) -> ALLOWED.
- Mode B: Local Music Voice Control (via Gemini Live/voice loop) -> ALLOWED.
- Mode C: Spotify Voice Control -> BLOCKED unless explicit platform authorization
          and verified compliance permissions are established.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from zye_music.music_errors import MusicErrorCode, MusicAuthorizationError
from zye_music.music_models import InputOrigin, ProviderType

logger = logging.getLogger("zye.music.authorization")


class MusicAuthorization:
    """Policy engine governing access to music backends and origin enforcement."""

    def __init__(self, allow_spotify_voice_experimental: bool = False) -> None:
        self.allow_spotify_voice_experimental = allow_spotify_voice_experimental
        self._explicit_spotify_voice_permission: bool = allow_spotify_voice_experimental

    def set_spotify_voice_permission(self, granted: bool) -> None:
        """Allow explicit runtime authorization for Spotify voice operations."""
        self._explicit_spotify_voice_permission = granted
        logger.info("Spotify voice authorization set to: %s", granted)

    def is_authorized(
        self,
        provider: ProviderType,
        origin: InputOrigin,
        action: str = "play",
    ) -> Tuple[bool, Optional[str], Optional[MusicErrorCode]]:
        """
        Evaluate if the requested provider operation is permitted for the given input origin.

        Returns:
            Tuple of (is_allowed, denial_reason_or_none, error_code_or_none)
        """
        # Local music provider: Always allowed across all origins (Voice, Manual, Script, etc.)
        if provider == ProviderType.LOCAL:
            return True, None, None

        # System audio controls (mute, system volume): Always allowed
        if provider == ProviderType.SYSTEM:
            return True, None, None

        # Spotify Provider:
        if provider == ProviderType.SPOTIFY:
            # Mode A: Non-voice execution (manual tools, orchestrator scripts, API calls)
            if origin in (InputOrigin.MANUAL_TOOL, InputOrigin.ORCHESTRATOR, InputOrigin.SCRIPT, InputOrigin.API):
                return True, None, None

            # Mode C: Voice-origin control
            if origin == InputOrigin.VOICE:
                if self._explicit_spotify_voice_permission:
                    logger.debug("Spotify voice request authorized via explicit permission override.")
                    return True, None, None

                denial_message = (
                    "Spotify voice control is currently restricted under Spotify Platform Policy "
                    "in Development Mode. Mode A (manual Spotify MCP tool execution) and "
                    "Mode B (Local Music playback with full voice control) are fully operational. "
                    "To play music by voice, ask Zye to play from your local library, or explicitly "
                    "grant Spotify voice authorization in zye_config.toml."
                )
                logger.warning(
                    "Blocked Spotify request from VOICE origin: action=%s. Mode C compliance enforced.",
                    action,
                )
                return False, denial_message, MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED

        return True, None, None

    def require_authorization(
        self,
        provider: ProviderType,
        origin: InputOrigin,
        action: str = "play",
    ) -> None:
        """Raise MusicAuthorizationError if operation is not permitted."""
        allowed, reason, code = self.is_authorized(provider, origin, action)
        if not allowed:
            raise MusicAuthorizationError(
                message=reason or "Operation not authorized",
                code=code or MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED,
                details={"provider": provider.value, "origin": origin.value, "action": action},
            )
