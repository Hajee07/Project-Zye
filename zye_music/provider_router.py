"""
ZYE AI — Music Provider Router
==============================

Coordinates provider selection between LocalMusicProvider (Mode B)
and SpotifyMCPAdapter (Mode A & Mode C), enforcing platform compliance
and audio ducking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from zye_music.audio_ducking import AudioDucker
from zye_music.music_authorization import MusicAuthorization
from zye_music.music_errors import (
    MusicErrorCode,
    MusicAuthorizationError,
)
from zye_music.music_models import (
    InputOrigin,
    IntentResult,
    IntentType,
    MusicCapability,
    MusicStatus,
    MusicTrack,
    PlaybackAction,
    PlaybackResult,
    PlaybackState,
    ProviderType,
)
from zye_music.music_preferences import MusicPreferences
from zye_music.provider_interface import MusicProvider

logger = logging.getLogger("zye.music.router")


class MusicProviderRouter:
    """Routes playback commands to appropriate music backend with policy gating."""

    def __init__(
        self,
        local_provider: Optional[MusicProvider] = None,
        spotify_provider: Optional[MusicProvider] = None,
        authorization: Optional[MusicAuthorization] = None,
        ducker: Optional[AudioDucker] = None,
        default_provider: ProviderType = ProviderType.LOCAL,
    ) -> None:
        if local_provider is None:
            from zye_music.local_music_provider import LocalMusicProvider
            local_provider = LocalMusicProvider()
        self.local_provider = local_provider
        self.spotify_provider = spotify_provider
        self.authorization = authorization or MusicAuthorization()
        self._auth = self.authorization
        self.ducker = ducker
        self.default_provider = default_provider

    def resolve_provider(
        self,
        requested_provider: Optional[ProviderType] = None,
        origin: InputOrigin = InputOrigin.VOICE,
        preferred: Optional[ProviderType] = None,
    ) -> MusicProvider:
        """Select backend based on user request, policy, and availability."""
        req = preferred if preferred is not None else requested_provider
        # 1. If explicit Spotify requested
        if req == ProviderType.SPOTIFY:
            # Policy verification
            allowed, reason, code = self.authorization.is_authorized(
                ProviderType.SPOTIFY, origin, "resolve_provider"
            )
            if not allowed:
                raise MusicAuthorizationError(
                    message=reason or "Spotify voice control is not authorized.",
                    code=code or MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED,
                    details={"provider": "spotify", "origin": origin.value},
                )
            if self.spotify_provider and self.spotify_provider.is_available():
                return self.spotify_provider
            raise MusicAuthorizationError(
                message="Spotify provider is not available or configured.",
                code=MusicErrorCode.SPOTIFY_CONFIG_MISSING,
            )

        # 2. If explicit Local requested
        if req == ProviderType.LOCAL:
            return self.local_provider

        # 3. Default resolution:
        # For voice commands, default to local music provider for zero-friction playback
        if origin == InputOrigin.VOICE:
            return self.local_provider

        # For manual tools or orchestrator, use configured default
        if self.default_provider == ProviderType.SPOTIFY:
            if self.spotify_provider and self.spotify_provider.is_available():
                return self.spotify_provider
            raise MusicAuthorizationError(
                message="Spotify provider is not available or configured.",
                code=MusicErrorCode.SPOTIFY_CONFIG_MISSING,
            )

        return self.local_provider

    def resolve_provider_type(
        self,
        requested_provider: Optional[ProviderType] = None,
        origin: InputOrigin = InputOrigin.VOICE,
        preferred: Optional[ProviderType] = None,
    ) -> ProviderType:
        """Resolve and return the ProviderType enum directly."""
        prov = self.resolve_provider(requested_provider=requested_provider, origin=origin, preferred=preferred)
        return getattr(prov, "provider_type", ProviderType.LOCAL)

    def execute_intent(
        self,
        intent_res: IntentResult,
        origin: InputOrigin = InputOrigin.VOICE,
    ) -> PlaybackResult:
        """Execute a parsed intent across the resolved provider."""
        try:
            provider = self.resolve_provider(intent_res.provider_preference, origin=origin)
        except MusicAuthorizationError as e:
            return PlaybackResult(
                success=False,
                status=MusicStatus.NOT_AUTHORIZED,
                message=e.message,
                error_code=e.code,
                details=e.details,
            )

        intent = intent_res.intent

        if intent == IntentType.PLAY:
            query = intent_res.query
            if not query and intent_res.mood:
                query = MusicPreferences.get_contextual_query(intent_res.mood)
            return provider.play(query)

        elif intent == IntentType.PAUSE:
            return provider.pause()

        elif intent == IntentType.RESUME:
            return provider.resume()

        elif intent == IntentType.STOP:
            return provider.stop()

        elif intent == IntentType.NEXT:
            return provider.next_track()

        elif intent == IntentType.PREVIOUS:
            return provider.previous_track()

        elif intent == IntentType.VOLUME_SET:
            level = intent_res.volume_level if intent_res.volume_level is not None else 80
            return provider.set_volume(level)

        elif intent == IntentType.VOLUME_UP:
            return provider.adjust_volume(+10)

        elif intent == IntentType.VOLUME_DOWN:
            return provider.adjust_volume(-10)

        elif intent == IntentType.MUTE:
            if hasattr(provider, "mute"):
                return provider.mute()
            return provider.set_volume(0)

        elif intent == IntentType.UNMUTE:
            if hasattr(provider, "unmute"):
                return provider.unmute()
            return provider.set_volume(80)

        elif intent == IntentType.SHUFFLE_ON:
            return provider.set_shuffle(True)

        elif intent == IntentType.SHUFFLE_OFF:
            return provider.set_shuffle(False)

        elif intent == IntentType.REPEAT_ONE:
            return provider.set_repeat("track")

        elif intent == IntentType.REPEAT_ALL:
            return provider.set_repeat("all")

        elif intent == IntentType.REPEAT_OFF:
            return provider.set_repeat("off")

        elif intent == IntentType.NOW_PLAYING:
            state = provider.get_playback_state()
            if state.is_playing and state.track:
                msg = f"Now playing '{state.track.name}' by {state.track.artist}"
            elif state.is_playing:
                msg = "Music is currently playing."
            else:
                msg = "No music is currently playing."
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=msg,
                action=PlaybackAction.STATUS,
                state=state,
            )

        return PlaybackResult(
            success=False,
            status=MusicStatus.ACTION_FAILED,
            message="Unrecognized music command",
            error_code=MusicErrorCode.INTENT_UNRECOGNIZED,
        )
