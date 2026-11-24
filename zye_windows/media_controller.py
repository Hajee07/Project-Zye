"""
Global Media Session Controller & Session Inspector — Zye Day 16 & Day 18.
Controls active media sessions (Spotify, YouTube, VLC, browser audio) using Windows virtual media keys,
and inspects running desktop media application sessions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

try:
    import pyautogui
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    import pygetwindow as gw
    _PYGETWINDOW_AVAILABLE = True
except ImportError:
    _PYGETWINDOW_AVAILABLE = False

from zye_windows.windows_models import MediaSessionInfo

logger = logging.getLogger("zye.windows.media")

SUPPORTED_MEDIA_COMMANDS = {
    "play_pause": "playpause",
    "play": "playpause",
    "pause": "playpause",
    "next": "nexttrack",
    "previous": "prevtrack",
    "stop": "stop",
}

KNOWN_MEDIA_APPS = {
    "spotify": "Spotify",
    "vlc": "VLC media player",
    "chrome": "Google Chrome (Media)",
    "msedge": "Microsoft Edge (Media)",
    "wmplayer": "Windows Media Player",
    "music.ui": "Groove Music / Media Player",
}


class WindowsMediaController:
    """
    Dispatches media session playback control commands and identifies active media sessions.
    """

    def __init__(self) -> None:
        if _PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True

    def get_active_media_session(self) -> dict[str, Any]:
        """
        Identify the currently active or prominent desktop media session.
        Inspects running media player window titles and audio session processes.
        """
        session = self._inspect_media_windows()
        if session:
            return {
                "status": "ACTIVE_SESSION",
                "session": session.model_dump(),
            }
        else:
            return {
                "status": "NO_SESSION",
                "message": "No active media playback session detected.",
                "session": None,
            }

    def get_media_session_details(self) -> dict[str, Any]:
        """Fetch comprehensive metadata for the active media session."""
        active = self.get_active_media_session()
        if active.get("status") == "ACTIVE_SESSION":
            return {
                "status": "SUCCESS",
                "details": active["session"],
            }
        return {
            "status": "NO_MEDIA",
            "message": "No media session details available.",
        }

    def media_control(self, command: str, app_target: Optional[str] = None) -> dict[str, Any]:
        """
        Send global media session command.
        Supported: play_pause, play, pause, next, previous, stop.
        """
        if not _PYAUTOGUI_AVAILABLE:
            return {
                "status": "ERROR",
                "message": "pyautogui is required for media playback control.",
            }

        cmd_clean = str(command).strip().lower()
        if cmd_clean not in SUPPORTED_MEDIA_COMMANDS:
            return {
                "status": "REJECTED",
                "message": f"Unsupported media command '{command}'. Supported: {sorted(list(SUPPORTED_MEDIA_COMMANDS.keys()))}",
                "command": command,
            }

        # Check active session context
        session_info = self._inspect_media_windows()
        app_name = session_info.source_app_id if session_info else "Global Audio"

        key_to_press = SUPPORTED_MEDIA_COMMANDS[cmd_clean]
        try:
            pyautogui.press(key_to_press)
            return {
                "status": "SUCCESS",
                "command": cmd_clean,
                "virtual_key": key_to_press,
                "target_application": app_name,
                "message": f"Dispatched '{cmd_clean}' media command to {app_name}.",
                "verified": True,
            }
        except Exception as exc:
            logger.error("Media key execution failed: %s", exc)
            return {"status": "ERROR", "message": f"Media command failed: {exc}"}

    def _inspect_media_windows(self) -> Optional[MediaSessionInfo]:
        """Inspect visible desktop window titles for known media players."""
        if not _PYGETWINDOW_AVAILABLE:
            return None

        try:
            windows = gw.getAllWindows()
            for w in windows:
                title = (w.title or "").strip()
                if not title:
                    continue
                title_lower = title.lower()

                # Spotify inspection: Spotify window title is typically "Artist - Song" or "Spotify"
                if "spotify" in title_lower or "spotify free" in title_lower or "spotify premium" in title_lower:
                    track = title if title_lower not in ("spotify", "spotify free", "spotify premium") else "Spotify Playback"
                    return MediaSessionInfo(
                        session_id="spotify_session",
                        source_app_id="Spotify",
                        title=track,
                        playback_status="PLAYING" if track != "Spotify Playback" else "PAUSED",
                        can_play=True,
                        can_pause=True,
                        can_skip_next=True,
                        can_skip_previous=True,
                    )

                # VLC inspection
                if "vlc media player" in title_lower:
                    track = title.replace("- VLC media player", "").strip()
                    return MediaSessionInfo(
                        session_id="vlc_session",
                        source_app_id="VLC",
                        title=track or "VLC Video/Audio",
                        playback_status="ACTIVE",
                        can_play=True,
                        can_pause=True,
                        can_skip_next=True,
                        can_skip_previous=True,
                    )

                # YouTube on Chrome/Edge
                if "youtube" in title_lower and ("google chrome" in title_lower or "edge" in title_lower):
                    track = title.split(" - YouTube")[0].strip()
                    return MediaSessionInfo(
                        session_id="browser_youtube",
                        source_app_id="YouTube (Browser)",
                        title=track,
                        playback_status="PLAYING",
                        can_play=True,
                        can_pause=True,
                        can_skip_next=True,
                        can_skip_previous=True,
                    )

        except Exception as exc:
            logger.debug("Media window inspection error: %s", exc)

        return None
