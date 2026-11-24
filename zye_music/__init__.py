"""
ZYE AI — Smart Music Subsystem
==============================

Complete background music intelligence system integrating:
- Local audio playback (Mode B)
- Spotify Web API / MCP server (Mode A & Mode C)
- Multilingual Tamil, English, and Tanglish intent parsing
- Speech-aware audio ducking and restoration
- Policy-compliant authorization gate
"""

from zye_music.audio_ducking import AudioDucker
from zye_music.audio_lifecycle_adapter import AudioLifecycleAdapter
from zye_music.local_music_provider import LocalMusicProvider
from zye_music.music_authorization import MusicAuthorization
from zye_music.music_errors import (
    AudioDuckingError,
    MusicAuthorizationError,
    MusicErrorCode,
    PlaybackDeviceError,
    PlaybackExecutionError,
    SpotifyConfigurationError,
    TrackNotFoundError,
    ZyeMusicError,
)
from zye_music.music_intent_router import MusicIntentRouter
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
from zye_music.music_search import MusicSearchEngine, normalize_tamil_text
from zye_music.playback_verifier import PlaybackVerifier
from zye_music.provider_interface import MusicProvider
from zye_music.provider_router import MusicProviderRouter
from zye_music.spotify_mcp_adapter import SpotifyMCPAdapter
from zye_music.volume_manager import VolumeManager

__all__ = [
    "AudioDucker",
    "AudioLifecycleAdapter",
    "AudioDuckingError",
    "InputOrigin",
    "IntentResult",
    "IntentType",
    "LocalMusicProvider",
    "MusicAuthorization",
    "MusicAuthorizationError",
    "MusicCapability",
    "MusicErrorCode",
    "MusicIntentRouter",
    "MusicPreferences",
    "MusicProvider",
    "MusicProviderRouter",
    "MusicSearchEngine",
    "MusicStatus",
    "MusicTrack",
    "PlaybackAction",
    "PlaybackDeviceError",
    "PlaybackExecutionError",
    "PlaybackResult",
    "PlaybackState",
    "PlaybackVerifier",
    "ProviderType",
    "SpotifyConfigurationError",
    "SpotifyMCPAdapter",
    "TrackNotFoundError",
    "VolumeManager",
    "ZyeMusicError",
    "normalize_tamil_text",
]
