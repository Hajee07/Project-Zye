"""
ZYE AI — Music Provider Interface
=================================

Abstract base protocol defining all operations supported by music backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

from zye_music.music_models import (
    MusicCapability,
    MusicTrack,
    PlaybackResult,
    PlaybackState,
    ProviderType,
)


class MusicProvider(ABC):
    """Abstract interface that every ZYE music backend must implement."""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """The provider type identifier (LOCAL, SPOTIFY, etc.)."""
        ...

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize backend resources (audio devices, MCP connections, etc.)."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources, stop audio, close child processes."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and ready to accept commands."""
        ...

    @abstractmethod
    def get_capabilities(self) -> Set[MusicCapability]:
        """Return the set of capabilities supported by this provider."""
        ...

    @abstractmethod
    def play(
        self,
        track_or_query: Optional[str] = None,
        context_uri: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> PlaybackResult:
        """Start or change playback."""
        ...

    @abstractmethod
    def pause(self, device_id: Optional[str] = None) -> PlaybackResult:
        """Pause current playback."""
        ...

    @abstractmethod
    def resume(self, device_id: Optional[str] = None) -> PlaybackResult:
        """Resume playback on active/specified device."""
        ...

    @abstractmethod
    def stop(self, device_id: Optional[str] = None) -> PlaybackResult:
        """Stop playback completely."""
        ...

    @abstractmethod
    def next_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        """Skip to the next track."""
        ...

    @abstractmethod
    def previous_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        """Return to the previous track."""
        ...

    @abstractmethod
    def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> PlaybackResult:
        """Set absolute playback volume (0 to 100)."""
        ...

    @abstractmethod
    def adjust_volume(self, adjustment: int, device_id: Optional[str] = None) -> PlaybackResult:
        """Adjust volume relatively (-100 to +100)."""
        ...

    @abstractmethod
    def seek(self, position_ms: int, device_id: Optional[str] = None) -> PlaybackResult:
        """Seek to position in milliseconds in current track."""
        ...

    @abstractmethod
    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> PlaybackResult:
        """Enable or disable shuffle mode."""
        ...

    @abstractmethod
    def set_repeat(self, state: str, device_id: Optional[str] = None) -> PlaybackResult:
        """Set repeat mode ('off', 'track', 'context')."""
        ...

    @abstractmethod
    def get_playback_state(self, device_id: Optional[str] = None) -> PlaybackState:
        """Get current playback state."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[MusicTrack]:
        """Search available library/catalog for matching tracks."""
        ...

    @abstractmethod
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Return list of playback devices available to this provider."""
        ...
