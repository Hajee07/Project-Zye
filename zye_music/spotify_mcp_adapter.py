"""
ZYE AI — Spotify MCP Server Adapter
===================================

Python bridge communicating with the TypeScript Spotify MCP Server over stdio.
Passes configuration via SPOTIFY_CONFIG_PATH, translates JSON-RPC tool calls,
and maps responses to structured ZYE Music models.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from typing import Any, Dict, List, Optional, Set

from zye_music.music_errors import (
    MusicErrorCode,
    MusicValidationError,
    PlaybackExecutionError,
    SpotifyConfigurationError,
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
from zye_music.provider_interface import MusicProvider

logger = logging.getLogger("zye.music.spotify_adapter")

from typing import Literal

SearchType = Literal[
    "track",
    "album",
    "artist",
    "playlist",
    "episode",
    "show",
]


def build_spotify_search_args(
    query: str | dict[str, Any],
    media_type: SearchType = "track",
    limit: int = 5,
) -> dict[str, Any]:
    """Strictly validates and builds Spotify search arguments conforming to platform specifications."""
    if isinstance(query, dict):
        d = query
        raw_q = d.get("query") if "query" in d else d.get("q", "")
        media_type = d.get("type") or d.get("media_type") or media_type
        limit = d.get("limit", limit)
        query = raw_q

    if not isinstance(query, str):
        raise MusicValidationError(
            "Query must be a string",
            code=MusicErrorCode.EMPTY_MUSIC_QUERY,
        )

    query = query.strip()

    if not query:
        raise MusicValidationError(
            "Query cannot be empty or whitespace",
            code=MusicErrorCode.EMPTY_MUSIC_QUERY,
        )

    if len(query) > 300:
        raise MusicValidationError(
            "Query exceeds maximum 300 characters",
            code=MusicErrorCode.MUSIC_QUERY_TOO_LONG,
        )

    supported = {
        "track",
        "album",
        "artist",
        "playlist",
        "episode",
        "show",
    }

    if media_type not in supported:
        raise MusicValidationError(
            f"Unsupported media type '{media_type}'",
            code=MusicErrorCode.UNSUPPORTED_MEDIA_TYPE,
        )

    if type(limit) is not int:
        raise MusicValidationError(
            "Limit must be an integer",
            code=MusicErrorCode.INVALID_RESULT_LIMIT,
        )

    if not 1 <= limit <= 10:
        raise MusicValidationError(
            "Limit must be between 1 and 10",
            code=MusicErrorCode.INVALID_RESULT_LIMIT,
        )

    return {
        "query": query,
        "type": media_type,
        "limit": limit,
    }


SPOTIFY_TOOL_NAME_MAP: dict[str, str] = {
    "spotify_search": "searchSpotify",
    "search": "searchSpotify",
    "searchSpotify": "searchSpotify",
    "spotify_play_music": "playMusic",
    "play_music": "playMusic",
    "playMusic": "playMusic",
    "spotify_pause_playback": "pausePlayback",
    "pause_playback": "pausePlayback",
    "pausePlayback": "pausePlayback",
    "spotify_resume_playback": "resumePlayback",
    "resume_playback": "resumePlayback",
    "resumePlayback": "resumePlayback",
    "spotify_skip_to_next": "skipToNext",
    "skip_to_next": "skipToNext",
    "skipToNext": "skipToNext",
    "spotify_skip_to_previous": "skipToPrevious",
    "skip_to_previous": "skipToPrevious",
    "skipToPrevious": "skipToPrevious",
    "spotify_set_volume": "setVolume",
    "set_volume": "setVolume",
    "setVolume": "setVolume",
    "spotify_adjust_volume": "adjustVolume",
    "adjust_volume": "adjustVolume",
    "adjustVolume": "adjustVolume",
    "spotify_seek_playback": "seekPlayback",
    "seek_playback": "seekPlayback",
    "seekPlayback": "seekPlayback",
    "spotify_set_shuffle": "setShuffle",
    "set_shuffle": "setShuffle",
    "setShuffle": "setShuffle",
    "spotify_set_repeat": "setRepeat",
    "set_repeat": "setRepeat",
    "setRepeat": "setRepeat",
    "spotify_get_now_playing": "getNowPlaying",
    "get_now_playing": "getNowPlaying",
    "getNowPlaying": "getNowPlaying",
    "spotify_get_available_devices": "getAvailableDevices",
    "get_available_devices": "getAvailableDevices",
    "getAvailableDevices": "getAvailableDevices",
    "spotify_transfer_playback": "transferPlayback",
    "transfer_playback": "transferPlayback",
    "transferPlayback": "transferPlayback",
}


class SpotifyMCPAdapter(MusicProvider):
    """Subprocess adapter managing Spotify MCP server communication via stdio JSON-RPC."""

    def __init__(
        self,
        mcp_script_path: str = r"d:\Zye\external_mcp\spotify-mcp-server\build\index.js",
        config_path: str = r"C:\ZyeSecrets\spotify-config.json",
        node_executable: str = "node",
    ) -> None:
        self.mcp_script_path = mcp_script_path
        self.config_path = config_path
        self.node_executable = node_executable
        self._process: Optional[subprocess.Popen[str]] = None
        self._lock = threading.RLock()
        self._request_id: int = 1
        self._is_initialized: bool = False

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.SPOTIFY

    def initialize(self) -> bool:
        """Verify configuration and start MCP child process."""
        with self._lock:
            if self._is_initialized and self._process and self._process.poll() is None:
                return True

            if not os.path.exists(self.config_path):
                logger.warning(
                    "Spotify config missing at %s. Spotify provider unavailable until configured.",
                    self.config_path,
                )
                return False

            if not os.path.exists(self.mcp_script_path):
                logger.error("Spotify MCP build missing at %s.", self.mcp_script_path)
                return False

            try:
                env = os.environ.copy()
                env["SPOTIFY_CONFIG_PATH"] = self.config_path

                self._process = subprocess.Popen(
                    [self.node_executable, self.mcp_script_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    env=env,
                )
                self._is_initialized = True
                logger.info("Spotify MCP adapter process spawned (PID: %d)", self._process.pid)
                return True
            except Exception as e:
                logger.error("Failed to spawn Spotify MCP process: %s", e)
                self._is_initialized = False
                return False

    def shutdown(self) -> None:
        """Gracefully terminate MCP process."""
        with self._lock:
            if self._process:
                try:
                    if self._process.stdin:
                        self._process.stdin.close()
                    self._process.terminate()
                    self._process.wait(timeout=2.0)
                except Exception:
                    self._process.kill()
                finally:
                    self._process = None
            self._is_initialized = False

    def is_available(self) -> bool:
        with self._lock:
            if not self._is_initialized or not self._process:
                return False
            return self._process.poll() is None

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
            MusicCapability.TRANSFER,
            MusicCapability.LIBRARY,
        }

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC tools/call request to the MCP server with strict name mapping and argument validation."""
        mapped_name = SPOTIFY_TOOL_NAME_MAP.get(name, name)
        args = dict(arguments or {})

        # Normalize and validate arguments
        if mapped_name == "searchSpotify":
            if "q" in args and "query" not in args:
                args["query"] = args.pop("q")
            q_val = str(args.get("query", "")).strip()
            if not q_val:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": "EMPTY_MUSIC_QUERY: Query parameter is required and cannot be empty"}],
                }
            if "type" not in args:
                args["type"] = "track"
        elif mapped_name == "playMusic":
            if "track_or_query" in args and "uri" not in args and "uris" not in args:
                tq = str(args.pop("track_or_query")).strip()
                if tq.startswith("spotify:track:") or tq.startswith("http"):
                    args["uris"] = [tq]

        with self._lock:
            if not self.is_available():
                if not self.initialize():
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": "Spotify MCP server is not available"}],
                    }

            req_id = self._request_id
            self._request_id += 1

            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {
                    "name": mapped_name,
                    "arguments": args,
                },
            }

            try:
                line = json.dumps(payload) + "\n"
                if not self._process or not self._process.stdin or not self._process.stdout:
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": "Subprocess IO pipe not available"}],
                    }

                self._process.stdin.write(line)
                self._process.stdin.flush()

                resp_line = self._process.stdout.readline()
                if not resp_line:
                    logger.error("Spotify MCP process exited unexpectedly or closed pipe.")
                    return {
                        "isError": True,
                        "content": [{"type": "text", "text": "Spotify MCP server returned empty response"}],
                    }

                resp_json = json.loads(resp_line.strip())
                return resp_json.get("result", resp_json)
            except Exception as e:
                logger.error("Error communicating with Spotify MCP server: %s", e)
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error communicating with Spotify MCP server: {e}"}],
                }

    def play(
        self,
        track_or_query: Optional[str] = None,
        context_uri: Optional[str] = None,
        device_id: Optional[str] = None,
        track_uri: Optional[str] = None,
        uri: Optional[str] = None,
        query: Optional[str] = None,
    ) -> PlaybackResult:
        track_or_query = track_uri or uri or query or track_or_query
        args: Dict[str, Any] = {}
        if track_or_query:
            if track_or_query.startswith("spotify:track:") or track_or_query.startswith("http"):
                args["uris"] = [track_or_query]
            else:
                # Search and play
                tracks = self.search(track_or_query, limit=1)
                if tracks:
                    args["uris"] = [tracks[0].uri]
                else:
                    return PlaybackResult(
                        success=False,
                        status=MusicStatus.TRACK_NOT_FOUND,
                        message=f"No Spotify tracks found matching '{track_or_query}'",
                        action=PlaybackAction.PLAY,
                        error_code=MusicErrorCode.TRACK_NOT_FOUND,
                    )
        if context_uri:
            args["contextUri"] = context_uri
        if device_id:
            args["deviceId"] = device_id

        res = self.call_tool("playMusic", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.PLAY)

    def pause(self, device_id: Optional[str] = None) -> PlaybackResult:
        args = {"deviceId": device_id} if device_id else {}
        res = self.call_tool("pausePlayback", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.PAUSE)

    def resume(self, device_id: Optional[str] = None) -> PlaybackResult:
        args = {"deviceId": device_id} if device_id else {}
        res = self.call_tool("resumePlayback", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.RESUME)

    def stop(self, device_id: Optional[str] = None) -> PlaybackResult:
        return self.pause(device_id)

    def next_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        args = {"deviceId": device_id} if device_id else {}
        res = self.call_tool("skipToNext", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.NEXT)

    def previous_track(self, device_id: Optional[str] = None) -> PlaybackResult:
        args = {"deviceId": device_id} if device_id else {}
        res = self.call_tool("skipToPrevious", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.PREVIOUS)

    def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> PlaybackResult:
        args: Dict[str, Any] = {"volumePercent": volume_percent}
        if device_id:
            args["deviceId"] = device_id
        res = self.call_tool("setVolume", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.VOLUME)

    def adjust_volume(self, adjustment: int, device_id: Optional[str] = None) -> PlaybackResult:
        args: Dict[str, Any] = {"adjustment": adjustment}
        if device_id:
            args["deviceId"] = device_id
        res = self.call_tool("adjustVolume", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.VOLUME)

    def seek(self, position_ms: int, device_id: Optional[str] = None) -> PlaybackResult:
        args: Dict[str, Any] = {"positionMs": position_ms}
        if device_id:
            args["deviceId"] = device_id
        res = self.call_tool("seekPlayback", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.SEEK)

    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> PlaybackResult:
        args: Dict[str, Any] = {"state": state}
        if device_id:
            args["deviceId"] = device_id
        res = self.call_tool("setShuffle", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.SHUFFLE)

    def set_repeat(self, state: str, device_id: Optional[str] = None) -> PlaybackResult:
        args: Dict[str, Any] = {"state": state}
        if device_id:
            args["deviceId"] = device_id
        res = self.call_tool("setRepeat", args)
        return self._mcp_result_to_playback_result(res, PlaybackAction.REPEAT)

    def get_playback_state(self, device_id: Optional[str] = None) -> PlaybackState:
        res = self.call_tool("getNowPlaying", {})
        text = self._extract_text(res)
        is_playing = "Playing" in text
        return PlaybackState(
            is_playing=is_playing,
            provider=ProviderType.SPOTIFY,
            device_id=device_id,
        )

    def search(self, query: str, limit: int = 10) -> List[MusicTrack]:
        try:
            norm_args = build_spotify_search_args(query, media_type="track", limit=min(limit, 10))
        except ValueError as ve:
            logger.warning("Invalid Spotify search arguments: %s", ve)
            return []

        res = self.call_tool("searchSpotify", norm_args)
        if res.get("isError"):
            logger.warning("Spotify search failed: %s", self._extract_text(res))
            return []

        # Check for structured JSON content first (Section 18)
        content_items = res.get("content", [])
        for item in content_items:
            text = item.get("text", "")
            if text.startswith("{") and "SEARCH_COMPLETED" in text:
                try:
                    payload = json.loads(text)
                    items = payload.get("items", [])
                    tracks: List[MusicTrack] = []
                    for t_item in items:
                        t_id = str(t_item.get("id") or "")
                        tracks.append(MusicTrack(
                            id=t_id,
                            name=t_item.get("title", ""),
                            artist=", ".join(t_item.get("artists", [])) or "Spotify Artist",
                            album=t_item.get("album"),
                            duration_seconds=round((t_item.get("duration_ms") or 0) / 1000.0, 1),
                            provider=ProviderType.SPOTIFY,
                            uri=t_item.get("uri") or f"spotify:track:{t_id}",
                        ))
                    if tracks:
                        return tracks[:limit]
                except Exception as pe:
                    logger.debug("Failed parsing structured search JSON: %s", pe)

        # Fallback to human-readable text parsing
        text = self._extract_text(res)
        tracks_fallback: List[MusicTrack] = []
        for line in text.split("\n"):
            line = line.strip()
            if line and " - ID: " in line:
                try:
                    parts = line.split(" - ID: ")
                    track_info = parts[0]
                    track_id = parts[1].strip()
                    title = track_info
                    artist = "Spotify Artist"
                    if " by " in track_info:
                        title_part, artist_part = track_info.split(" by ", 1)
                        title = title_part.strip().strip('"')
                        if " [" in artist_part:
                            artist_part = artist_part.split(" [")[0]
                        if " (" in artist_part:
                            artist_part = artist_part.split(" (")[0]
                        artist = artist_part.strip()
                    tracks_fallback.append(
                        MusicTrack(
                            id=track_id,
                            uri=f"spotify:track:{track_id}",
                            name=title,
                            artist=artist,
                            provider=ProviderType.SPOTIFY,
                        )
                    )
                except Exception:
                    pass
        return tracks_fallback[:limit]

    def get_available_devices(self) -> List[Dict[str, Any]]:
        res = self.call_tool("getAvailableDevices", {})
        text = self._extract_text(res)
        devices: List[Dict[str, Any]] = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                devices.append({"name": line[2:].strip(), "is_active": "active" in line.lower()})
        return devices

    def _extract_text(self, mcp_res: Dict[str, Any]) -> str:
        content = mcp_res.get("content", [])
        if isinstance(content, list):
            return "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
        return str(mcp_res)

    def _mcp_result_to_playback_result(
        self,
        mcp_res: Dict[str, Any],
        action: PlaybackAction,
    ) -> PlaybackResult:
        is_error = mcp_res.get("isError", False)
        text = self._extract_text(mcp_res)

        if is_error:
            error_code = MusicErrorCode.PLAYBACK_FAILED
            status = MusicStatus.ACTION_FAILED
            if "No active device" in text:
                error_code = MusicErrorCode.SPOTIFY_NO_ACTIVE_DEVICE
                status = MusicStatus.NO_ACTIVE_DEVICE
            elif "authentication" in text.lower() or "unauthorized" in text.lower():
                error_code = MusicErrorCode.SPOTIFY_UNAUTHENTICATED
                status = MusicStatus.AUTHENTICATION_REQUIRED
            elif "premium" in text.lower():
                error_code = MusicErrorCode.SPOTIFY_PREMIUM_REQUIRED
                status = MusicStatus.PREMIUM_REQUIRED

            return PlaybackResult(
                success=False,
                status=status,
                message=text or "Spotify operation failed",
                action=action,
                error_code=error_code,
            )

        return PlaybackResult(
            success=True,
            status=MusicStatus.PLAYBACK_VERIFIED,
            message=text or "Operation succeeded",
            action=action,
        )
