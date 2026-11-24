"""
ZYE AI — Local Music Provider Engine
====================================

Headless, zero-foreground local audio player implementing:
- Pygame mixer background playback.
- Safe volume controls (0 to 100) with mute memory.
- Playlist, queue, shuffle, and repeat modes.
- Fast metadata scanning & Tamil-normalized search.
- Verified playback reporting.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from zye_music.music_errors import (
    MusicErrorCode,
    PlaybackExecutionError,
    TrackNotFoundError,
)
from zye_music.music_models import (
    MusicCapability,
    MusicStatus,
    MusicTrack,
    PlaybackAction,
    PlaybackResult,
    PlaybackState,
    ProviderType,
)
from zye_music.music_search import MusicSearchEngine, normalize_tamil_text
from zye_music.provider_interface import MusicProvider
from zye_music.track_selector import DiverseTrackSelector
from zye_music.volume_manager import VolumeManager

logger = logging.getLogger("zye.music.local")

# Suppress pygame greeting
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


class LocalMusicProvider(MusicProvider):
    """Local audio provider using headless pygame mixer."""

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}

    def __init__(
        self,
        music_directories: Optional[List[str]] = None,
        default_volume: int = 80,
    ) -> None:
        self._music_dirs = music_directories or [
            str(Path("d:/Zye/data/music").resolve()),
            os.path.expanduser("~/Music"),
        ]
        self._volume_manager = VolumeManager(initial_volume=default_volume)
        self._search_engine = MusicSearchEngine()
        self._tracks: List[MusicTrack] = []
        self._playlist: List[MusicTrack] = []
        self._current_index: int = -1
        self._current_track: Optional[MusicTrack] = None
        self._is_paused: bool = False
        self._is_initialized: bool = False
        self._shuffle_enabled: bool = False
        self._repeat_mode: str = "off"  # "off", "track", "all"
        self._selector = DiverseTrackSelector(history_size=10)
        self._lock = threading.RLock()
        self._playback_start_time: float = 0.0

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.LOCAL

    def initialize(self) -> bool:
        """Initialize pygame audio mixer."""
        with self._lock:
            if self._is_initialized:
                return True
            try:
                import pygame
                if not pygame.mixer.get_init():
                    # 44.1kHz, 16-bit stereo, buffer 2048
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self._is_initialized = True
                self._apply_volume(self._volume_manager.current_volume)
                self.rescan_library()
                logger.info(
                    "LocalMusicProvider initialized. Discovered %d tracks across directories.",
                    len(self._tracks),
                )
                return True
            except Exception as e:
                logger.error("Failed to initialize LocalMusicProvider: %s", e)
                self._is_initialized = False
                return False

    def shutdown(self) -> None:
        """Stop music and close mixer."""
        with self._lock:
            try:
                self.stop()
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except Exception as e:
                logger.debug("Error during LocalMusicProvider shutdown: %s", e)
            finally:
                self._is_initialized = False

    def is_available(self) -> bool:
        return self._is_initialized

    def get_capabilities(self) -> Set[MusicCapability]:
        return {
            MusicCapability.PLAY,
            MusicCapability.PAUSE,
            MusicCapability.RESUME,
            MusicCapability.STOP,
            MusicCapability.NEXT,
            MusicCapability.PREVIOUS,
            MusicCapability.VOLUME,
            MusicCapability.SHUFFLE,
            MusicCapability.REPEAT,
            MusicCapability.SEARCH,
            MusicCapability.QUEUE,
            MusicCapability.LIBRARY,
        }

    def rescan_library(self) -> int:
        """Scan configured music directories for audio files."""
        with self._lock:
            discovered: List[MusicTrack] = []
            for d in self._music_dirs:
                p = Path(d)
                if not p.exists() or not p.is_dir():
                    continue
                for root, _, files in os.walk(p):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.SUPPORTED_EXTENSIONS:
                            full_path = os.path.join(root, f)
                            track = self._build_track_from_file(full_path)
                            discovered.append(track)

            self._tracks = discovered
            self._search_engine.set_tracks(self._tracks)
            if not self._playlist and self._tracks:
                self._playlist = list(self._tracks)
            return len(self._tracks)

    def _build_track_from_file(self, file_path: str) -> MusicTrack:
        """Extract title and artist metadata from audio file path."""
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        artist = "Local Artist"
        title = base_name

        # Parse common formats: "Artist - Title" or "Title (Movie)"
        if " - " in base_name:
            parts = base_name.split(" - ", 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        elif " by " in base_name.lower():
            parts = base_name.split(" by ", 1)
            title = parts[0].strip()
            artist = parts[1].strip()

        uri = f"local:track:{Path(file_path).stem}"
        return MusicTrack(
            uri=uri,
            name=title,
            artist=artist,
            album="Local Audio Library",
            duration_ms=0,
            source=ProviderType.LOCAL,
            file_path=file_path,
        )

    def search(self, query: str, limit: int = 10) -> List[MusicTrack]:
        """Search local audio tracks."""
        with self._lock:
            return self._search_engine.search(query, limit=limit)

    def play(
        self,
        track_or_query: Optional[str] = None,
        context_uri: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> PlaybackResult:
        """Play track matching query or resume current playlist."""
        with self._lock:
            if not self._is_initialized:
                self.initialize()

            # If no query provided and already paused, resume
            if not track_or_query and self._is_paused and self._current_track:
                return self.resume()

            if not self._tracks:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.TRACK_NOT_FOUND,
                    message="Local music library is empty.",
                    action=PlaybackAction.PLAY,
                    error_code=MusicErrorCode.LOCAL_LIBRARY_EMPTY,
                )

            target_track: Optional[MusicTrack] = None

            q_clean = (track_or_query or "").strip().lower()
            is_open_ended = not q_clean or q_clean in (
                "any", "random", "play any", "play music", "music", "song",
                "oru paatu", "paatu", "edhavadhu", "all", "play any song"
            )

            # Check explicit melody exclusion: "melody vendaam", "no melody", etc.
            exclude_melody = any(ex in q_clean for ex in ["melody vendaam", "no melody", "not melody", "melody illa", "melody vendam"])

            if is_open_ended:
                candidates = self._tracks
                if exclude_melody:
                    candidates = [t for t in candidates if "melody" not in t.name.lower()]
                curr_id = self._current_track.id if self._current_track else None
                try:
                    target_track = self._selector.select(candidates or self._tracks, current_track_id=curr_id)
                except LookupError:
                    target_track = self._tracks[0]
            else:
                # Specific query requested
                if os.path.exists(track_or_query) and os.path.isfile(track_or_query):
                    target_track = self._build_track_from_file(track_or_query)
                else:
                    results = self.search(track_or_query, limit=5)
                    if exclude_melody and results:
                        results = [t for t in results if "melody" not in t.name.lower()]

                    if results:
                        target_track = results[0]
                    else:
                        # Check genre/mood keywords
                        mood_keywords = {
                            "beat": ["beat", "master", "kuthu", "energetic", "fast", "dance", "mass"],
                            "melody": ["melody", "soft", "pure", "romantic", "love"],
                            "acoustic": ["acoustic", "breeze", "guitar", "harris"],
                            "meditation": ["flute", "meditation", "peaceful", "calm", "relax"],
                            "lofi": ["lofi", "vibe", "yuvan", "chill", "slow"],
                        }
                        matched_candidates = []
                        for tag, words in mood_keywords.items():
                            if any(w in q_clean for w in words):
                                for t in self._tracks:
                                    if any(w in t.name.lower() for w in words):
                                        matched_candidates.append(t)
                        if exclude_melody and matched_candidates:
                            matched_candidates = [t for t in matched_candidates if "melody" not in t.name.lower()]

                        if matched_candidates:
                            curr_id = self._current_track.id if self._current_track else None
                            target_track = self._selector.select(matched_candidates, current_track_id=curr_id)
                        else:
                            # Specific song NOT found: Return TRACK_NOT_FOUND error! NEVER play fallback track!
                            return PlaybackResult(
                                success=False,
                                status=MusicStatus.TRACK_NOT_FOUND,
                                message=f"No local tracks found matching: '{track_or_query}'",
                                action=PlaybackAction.PLAY,
                                error_code=MusicErrorCode.TRACK_NOT_FOUND,
                            )

            return self._start_track_playback(target_track)

    def _start_track_playback(self, track: MusicTrack) -> PlaybackResult:
        """Load and play audio file using pygame mixer."""
        if not track.file_path or not os.path.exists(track.file_path):
            return PlaybackResult(
                success=False,
                status=MusicStatus.TRACK_NOT_FOUND,
                message=f"Audio file not found on disk: {track.file_path}",
                action=PlaybackAction.PLAY,
                track=track,
                error_code=MusicErrorCode.TRACK_NOT_FOUND,
            )

        try:
            import pygame
            pygame.mixer.music.load(track.file_path)
            # Repeat = -1 if repeat_mode == "track", else 0
            loops = -1 if self._repeat_mode == "track" else 0
            pygame.mixer.music.play(loops=loops)
            self._apply_volume(self._volume_manager.current_volume)

            self._current_track = track
            self._is_paused = False
            self._playback_start_time = time.monotonic()
            self._selector.record_verified_playback(track.id)

            # Ensure track is in playlist
            if track in self._playlist:
                self._current_index = self._playlist.index(track)
            else:
                self._playlist.insert(0, track)
                self._current_index = 0

            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Playing '{track.name}' by {track.artist}",
                action=PlaybackAction.PLAY,
                track=track,
                state=self.get_playback_state(),
            )
        except Exception as e:
            logger.error("Error playing track '%s': %s", track.name, e)
            return PlaybackResult(
                success=False,
                status=MusicStatus.ACTION_FAILED,
                message=f"Failed to play track: {e}",
                action=PlaybackAction.PLAY,
                track=track,
                error_code=MusicErrorCode.PLAYBACK_FAILED,
            )

    def pause(self, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.pause()
                self._is_paused = True
                return PlaybackResult(
                    success=True,
                    status=MusicStatus.PLAYBACK_VERIFIED,
                    message="Playback paused",
                    action=PlaybackAction.PAUSE,
                    track=self._current_track,
                    state=self.get_playback_state(),
                )
            except Exception as e:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.ACTION_FAILED,
                    message=f"Failed to pause: {e}",
                    action=PlaybackAction.PAUSE,
                    error_code=MusicErrorCode.PLAYBACK_FAILED,
                )

    def resume(self, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.unpause()
                self._is_paused = False
                return PlaybackResult(
                    success=True,
                    status=MusicStatus.PLAYBACK_VERIFIED,
                    message="Playback resumed",
                    action=PlaybackAction.RESUME,
                    track=self._current_track,
                    state=self.get_playback_state(),
                )
            except Exception as e:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.ACTION_FAILED,
                    message=f"Failed to resume: {e}",
                    action=PlaybackAction.RESUME,
                    error_code=MusicErrorCode.PLAYBACK_FAILED,
                )

    def stop(self, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                self._is_paused = False
                self._current_track = None
                return PlaybackResult(
                    success=True,
                    status=MusicStatus.PLAYBACK_VERIFIED,
                    message="Playback stopped",
                    action=PlaybackAction.STOP,
                    state=self.get_playback_state(),
                )
            except Exception as e:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.ACTION_FAILED,
                    message=f"Failed to stop: {e}",
                    action=PlaybackAction.STOP,
                    error_code=MusicErrorCode.PLAYBACK_FAILED,
                )

    def next_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            if not self._tracks:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.TRACK_NOT_FOUND,
                    message="Local music library is empty.",
                    action=PlaybackAction.NEXT,
                    error_code=MusicErrorCode.LOCAL_LIBRARY_EMPTY,
                )

            # If repeat mode is track, repeat the current track
            if self._repeat_mode == "track" and self._current_track:
                return self._start_track_playback(self._current_track)

            curr_id = self._current_track.id if self._current_track else None
            try:
                target_track = self._selector.select(self._tracks, current_track_id=curr_id)
            except LookupError:
                target_track = self._tracks[0]

            return self._start_track_playback(target_track)

    def previous_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            if not self._playlist:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.TRACK_NOT_FOUND,
                    message="Playlist is empty.",
                    action=PlaybackAction.PREVIOUS,
                    error_code=MusicErrorCode.TRACK_NOT_FOUND,
                )

            prev_index = max(0, self._current_index - 1)
            self._current_index = prev_index
            target_track = self._playlist[self._current_index]
            return self._start_track_playback(target_track)

    def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            new_vol = self._volume_manager.set_volume(volume_percent)
            self._apply_volume(new_vol)
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Volume set to {new_vol}%",
                action=PlaybackAction.VOLUME,
                state=self.get_playback_state(),
            )

    def adjust_volume(self, adjustment: int, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            old_vol, new_vol = self._volume_manager.adjust_volume(adjustment)
            self._apply_volume(new_vol)
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Volume adjusted from {old_vol}% to {new_vol}%",
                action=PlaybackAction.VOLUME,
                state=self.get_playback_state(),
            )

    def mute(self) -> PlaybackResult:
        with self._lock:
            saved_vol, _ = self._volume_manager.mute()
            self._apply_volume(0)
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Muted (saved level: {saved_vol}%)",
                action=PlaybackAction.MUTE,
                state=self.get_playback_state(),
            )

    def unmute(self) -> PlaybackResult:
        with self._lock:
            _, restored_vol = self._volume_manager.unmute()
            self._apply_volume(restored_vol)
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Unmuted (restored to {restored_vol}%)",
                action=PlaybackAction.UNMUTE,
                state=self.get_playback_state(),
            )

    def _apply_volume(self, vol_percent: int) -> None:
        """Send volume to pygame mixer (0.0 to 1.0)."""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.set_volume(max(0.0, min(1.0, vol_percent / 100.0)))
        except Exception as e:
            logger.debug("Failed to set pygame volume: %s", e)

    def seek(self, position_ms: int, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            try:
                import pygame
                if pygame.mixer.get_init():
                    pos_sec = max(0.0, position_ms / 1000.0)
                    pygame.mixer.music.set_pos(pos_sec)
                return PlaybackResult(
                    success=True,
                    status=MusicStatus.PLAYBACK_VERIFIED,
                    message=f"Seeked to {position_ms}ms",
                    action=PlaybackAction.SEEK,
                    state=self.get_playback_state(),
                )
            except Exception as e:
                return PlaybackResult(
                    success=False,
                    status=MusicStatus.ACTION_FAILED,
                    message=f"Seek failed: {e}",
                    action=PlaybackAction.SEEK,
                    error_code=MusicErrorCode.SEEK_OUT_OF_BOUNDS,
                )

    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            self._shuffle_enabled = state
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Shuffle {'enabled' if state else 'disabled'}",
                action=PlaybackAction.SHUFFLE,
                state=self.get_playback_state(),
            )

    def set_repeat(self, state: str, device_id: Optional[str] = None) -> PlaybackResult:
        with self._lock:
            mode = state.lower().strip()
            if mode not in ("off", "track", "all"):
                mode = "off"
            self._repeat_mode = mode
            return PlaybackResult(
                success=True,
                status=MusicStatus.PLAYBACK_VERIFIED,
                message=f"Repeat mode set to: {mode}",
                action=PlaybackAction.REPEAT,
                state=self.get_playback_state(),
            )

    def get_playback_state(self, device_id: Optional[str] = None) -> PlaybackState:
        with self._lock:
            is_playing = False
            try:
                import pygame
                if pygame.mixer.get_init():
                    is_playing = pygame.mixer.music.get_busy() and not self._is_paused
            except Exception:
                is_playing = False

            return PlaybackState(
                is_playing=is_playing,
                track=self._current_track,
                progress_ms=0,
                volume_percent=self._volume_manager.current_volume,
                is_muted=self._volume_manager.is_muted,
                shuffle_state=self._shuffle_enabled,
                repeat_state=self._repeat_mode,
                device_id="local_default_speaker",
                device_name="Windows Default Audio Device",
                provider=ProviderType.LOCAL,
            )

    def get_available_devices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "local_default_speaker",
                "name": "Windows Default Audio Device",
                "type": "Speaker",
                "is_active": True,
                "volume_percent": self._volume_manager.current_volume,
            }
        ]
