"""
ZYE AI — Unit Tests: Music Authorization Engine
===============================================

Tests strict policy gating across:
- Mode A (Manual Spotify control via MCP / tools) -> ALLOWED
- Mode B (Local music voice control) -> ALLOWED
- Mode C (Spotify voice control) -> BLOCKED by default unless explicit permission granted
"""

import pytest
from zye_music.music_authorization import MusicAuthorization
from zye_music.music_errors import MusicAuthorizationError, MusicErrorCode
from zye_music.music_models import InputOrigin, ProviderType


def test_local_music_allowed_across_all_origins():
    auth = MusicAuthorization()
    for origin in (
        InputOrigin.VOICE,
        InputOrigin.MANUAL_TOOL,
        InputOrigin.ORCHESTRATOR,
        InputOrigin.SCRIPT,
        InputOrigin.API,
    ):
        allowed, reason, code = auth.is_authorized(ProviderType.LOCAL, origin, "play")
        assert allowed is True
        assert reason is None
        assert code is None


def test_mode_a_manual_spotify_control_allowed():
    auth = MusicAuthorization()
    for origin in (InputOrigin.MANUAL_TOOL, InputOrigin.ORCHESTRATOR, InputOrigin.SCRIPT, InputOrigin.API):
        allowed, reason, code = auth.is_authorized(ProviderType.SPOTIFY, origin, "play")
        assert allowed is True
        assert reason is None
        assert code is None


def test_mode_c_spotify_voice_blocked_by_default():
    auth = MusicAuthorization(allow_spotify_voice_experimental=False)
    allowed, reason, code = auth.is_authorized(ProviderType.SPOTIFY, InputOrigin.VOICE, "play")
    assert allowed is False
    assert code == MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED
    assert "Spotify voice control is currently restricted" in reason

    with pytest.raises(MusicAuthorizationError) as exc_info:
        auth.require_authorization(ProviderType.SPOTIFY, InputOrigin.VOICE, "play")
    assert exc_info.value.code == MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED


def test_mode_c_spotify_voice_with_explicit_permission():
    auth = MusicAuthorization(allow_spotify_voice_experimental=True)
    allowed, reason, code = auth.is_authorized(ProviderType.SPOTIFY, InputOrigin.VOICE, "play")
    assert allowed is True
    assert reason is None

    # Toggle permission off at runtime
    auth.set_spotify_voice_permission(False)
    allowed, reason, code = auth.is_authorized(ProviderType.SPOTIFY, InputOrigin.VOICE, "play")
    assert allowed is False

    # Toggle back on
    auth.set_spotify_voice_permission(True)
    allowed, reason, code = auth.is_authorized(ProviderType.SPOTIFY, InputOrigin.VOICE, "play")
    assert allowed is True
