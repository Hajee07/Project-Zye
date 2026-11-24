"""
ZYE AI — Unit Tests: Music Provider Router
==========================================

Verifies provider routing, default provider resolution,
intent execution, and authorization boundary enforcement.
"""

from unittest.mock import MagicMock
from zye_music.music_authorization import MusicAuthorization
from zye_music.music_models import (
    InputOrigin,
    IntentResult,
    IntentType,
    MusicStatus,
    PlaybackResult,
    PlaybackState,
    ProviderType,
)
from zye_music.provider_router import MusicProviderRouter


def test_provider_resolution_voice_defaults_to_local():
    mock_local = MagicMock()
    mock_spotify = MagicMock()
    mock_spotify.is_available.return_value = True

    router = MusicProviderRouter(
        local_provider=mock_local,
        spotify_provider=mock_spotify,
        authorization=MusicAuthorization(),
    )

    resolved = router.resolve_provider(requested_provider=None, origin=InputOrigin.VOICE)
    assert resolved == mock_local


def test_provider_resolution_spotify_voice_denied_by_policy():
    mock_local = MagicMock()
    mock_spotify = MagicMock()
    mock_spotify.is_available.return_value = True

    router = MusicProviderRouter(
        local_provider=mock_local,
        spotify_provider=mock_spotify,
        authorization=MusicAuthorization(allow_spotify_voice_experimental=False),
    )

    # When user asks for Spotify via voice, execution returns NOT_AUTHORIZED result
    intent = IntentResult(intent=IntentType.PLAY, query="test song", provider_preference=ProviderType.SPOTIFY)
    result = router.execute_intent(intent, origin=InputOrigin.VOICE)
    assert result.success is False
    assert result.status == MusicStatus.NOT_AUTHORIZED
    assert "restricted" in result.message.lower()


def test_intent_execution_local_commands():
    mock_local = MagicMock()
    mock_local.play.return_value = PlaybackResult(
        success=True, status=MusicStatus.PLAYBACK_VERIFIED, message="Playing test"
    )
    mock_local.pause.return_value = PlaybackResult(
        success=True, status=MusicStatus.PLAYBACK_VERIFIED, message="Paused"
    )
    mock_local.get_playback_state.return_value = PlaybackState(is_playing=True)

    router = MusicProviderRouter(
        local_provider=mock_local,
        authorization=MusicAuthorization(),
    )

    # Play
    r1 = router.execute_intent(IntentResult(intent=IntentType.PLAY, query="Aradhya"), origin=InputOrigin.VOICE)
    assert r1.success is True
    mock_local.play.assert_called_with("Aradhya")

    # Pause
    r2 = router.execute_intent(IntentResult(intent=IntentType.PAUSE), origin=InputOrigin.VOICE)
    assert r2.success is True
    mock_local.pause.assert_called_once()
