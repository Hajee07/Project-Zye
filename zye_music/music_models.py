"""
ZYE AI — Music Intelligence Models
==================================

Data structures, enums, and representations for the ZYE Smart Music System.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from zye_music.music_errors import MusicErrorCode


class ProviderType(str, Enum):
    """Music provider backend."""
    LOCAL = "local"
    SPOTIFY = "spotify"
    SYSTEM = "system"


class InputOrigin(str, Enum):
    """Origin of the music request (used for strict policy gating)."""
    VOICE = "voice"
    MANUAL_TOOL = "manual_tool"
    ORCHESTRATOR = "orchestrator"
    SCRIPT = "script"
    API = "api"


class MusicCapability(str, Enum):
    """Capabilities supported by a provider."""
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK = "seek"
    VOLUME = "volume"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
    SEARCH = "search"
    QUEUE = "queue"
    TRANSFER = "transfer"
    LIBRARY = "library"


class MusicStatus(str, Enum):
    """Status returned by verified playback operations."""
    PLAYBACK_VERIFIED = "PLAYBACK_VERIFIED"
    ACCEPTED_UNVERIFIED = "ACCEPTED_UNVERIFIED"
    NO_ACTIVE_DEVICE = "NO_ACTIVE_DEVICE"
    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    PREMIUM_REQUIRED = "PREMIUM_REQUIRED"
    TRACK_NOT_FOUND = "TRACK_NOT_FOUND"
    ACTION_FAILED = "ACTION_FAILED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class PlaybackAction(str, Enum):
    """Actions performed on player."""
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    SEEK = "seek"
    VOLUME = "volume"
    MUTE = "mute"
    UNMUTE = "unmute"
    SHUFFLE = "shuffle"
    REPEAT = "repeat"
    STATUS = "status"


@dataclass
class MusicTrack:
    """Represents an individual musical track."""
    uri: str
    name: str
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    source: ProviderType = ProviderType.LOCAL
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    title: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self.uri
        if not self.title:
            self.title = self.name

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlaybackState:
    """Represents current playback state of a device/provider."""
    is_playing: bool = False
    track: Optional[MusicTrack] = None
    progress_ms: int = 0
    volume_percent: int = 100
    is_muted: bool = False
    shuffle_state: bool = False
    repeat_state: str = "off"  # "off", "track", "context"
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    provider: ProviderType = ProviderType.LOCAL

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.track:
            d["track"] = self.track.to_dict()
        return d


@dataclass
class PlaybackResult:
    """Unified result returned by all playback and provider operations."""
    success: bool
    status: MusicStatus
    message: str
    action: Optional[PlaybackAction] = None
    track: Optional[MusicTrack] = None
    state: Optional[PlaybackState] = None
    error_code: Optional[MusicErrorCode] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "success": self.success,
            "status": self.status.value if isinstance(self.status, MusicStatus) else str(self.status),
            "message": self.message,
            "action": self.action.value if self.action else None,
            "error_code": self.error_code.value if self.error_code else None,
            "details": self.details,
        }
        if self.track:
            d["track"] = self.track.to_dict()
        if self.state:
            d["state"] = self.state.to_dict()
        return d


class IntentType(str, Enum):
    """Categorized user intent for music voice/text commands."""
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT = "next"
    PREVIOUS = "previous"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_SET = "volume_set"
    MUTE = "mute"
    UNMUTE = "unmute"
    SHUFFLE_ON = "shuffle_on"
    SHUFFLE_OFF = "shuffle_off"
    REPEAT_ONE = "repeat_one"
    REPEAT_ALL = "repeat_all"
    REPEAT_OFF = "repeat_off"
    NOW_PLAYING = "now_playing"
    SEARCH = "search"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Parsed result from natural language / voice input."""
    intent: IntentType
    query: Optional[str] = None
    volume_level: Optional[int] = None
    artist: Optional[str] = None
    track: Optional[str] = None
    mood: Optional[str] = None
    time_of_day: Optional[str] = None
    provider_preference: Optional[ProviderType] = None
    raw_text: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "query": self.query,
            "volume_level": self.volume_level,
            "artist": self.artist,
            "track": self.track,
            "mood": self.mood,
            "time_of_day": self.time_of_day,
            "provider_preference": self.provider_preference.value if self.provider_preference else None,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
        }
