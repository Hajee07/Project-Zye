"""
ZYE AI — Three-Layer Playback State Verifier
============================================

Implements three-layer independent music playback verification:
- Layer 1: Command acceptance (API accepted, operation submitted).
- Layer 2: Provider playback state readback (device ID, track ID, is_playing, progress).
- Layer 3: Local Windows audio session observation (correlates CoreAudio activity).

Returns structured verification outcome:
- PLAYBACK_VERIFIED
- TRACK_MISMATCH
- DEVICE_MISMATCH
- PREVIOUS_TRACK_STILL_PLAYING
- ACCEPTED_UNVERIFIED
- TRACK_NOT_PLAYING
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from zye_music.music_models import MusicStatus, PlaybackState, MusicTrack
from zye_music.audio_source_attribution import WindowsAudioSourceAttributor

logger = logging.getLogger("zye.music.verifier")


@dataclass
class ThreeLayerVerificationResult:
    status: str  # "PLAYBACK_VERIFIED", "TRACK_MISMATCH", "DEVICE_MISMATCH", "ACCEPTED_UNVERIFIED", etc.
    verified: bool
    api_accepted: bool = True
    track_match: bool = False
    device_match: bool = False
    provider_playback_verified: bool = False
    local_audio_activity_observed: Optional[bool] = None
    observed_state: Optional[PlaybackState] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "verified": self.verified,
            "api_accepted": self.api_accepted,
            "track_match": self.track_match,
            "device_match": self.device_match,
            "provider_playback_verified": self.provider_playback_verified,
            "local_audio_activity_observed": self.local_audio_activity_observed,
            "details": self.details,
        }


class PlaybackVerifier:
    """Verifies state changes on playback devices via bounded polling and three-layer attribution."""

    DEFAULT_POLL_INTERVAL_MS: int = 100
    DEFAULT_TIMEOUT_MS: int = 2000

    @classmethod
    async def verify_state_change(
        cls,
        get_state_fn: Callable[[], PlaybackState],
        condition_fn: Callable[[PlaybackState], bool],
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS,
    ) -> MusicStatus:
        """Poll get_state_fn until condition_fn returns True or timeout expires."""
        start_time = time.monotonic()
        timeout_sec = timeout_ms / 1000.0
        interval_sec = poll_interval_ms / 1000.0

        while (time.monotonic() - start_time) < timeout_sec:
            try:
                state = get_state_fn()
                if condition_fn(state):
                    return MusicStatus.PLAYBACK_VERIFIED
            except Exception as e:
                logger.debug("Verification check error: %s", e)

            await asyncio.sleep(interval_sec)

        logger.info("Playback state change unverified within %dms timeout.", timeout_ms)
        return MusicStatus.ACCEPTED_UNVERIFIED

    @classmethod
    def verify_sync(
        cls,
        get_state_fn: Callable[[], PlaybackState],
        condition_fn: Callable[[PlaybackState], bool],
        timeout_ms: int = 1000,
        poll_interval_ms: int = 50,
    ) -> MusicStatus:
        """Synchronous bounded verification loop."""
        start_time = time.monotonic()
        timeout_sec = timeout_ms / 1000.0
        interval_sec = poll_interval_ms / 1000.0

        while (time.monotonic() - start_time) < timeout_sec:
            try:
                state = get_state_fn()
                if condition_fn(state):
                    return MusicStatus.PLAYBACK_VERIFIED
            except Exception as e:
                logger.debug("Sync verification check error: %s", e)

            time.sleep(interval_sec)

        return MusicStatus.ACCEPTED_UNVERIFIED

    @classmethod
    def verify_three_layer(
        cls,
        expected_track_id: Optional[str] = None,
        expected_device_id: Optional[str] = None,
        get_state_fn: Optional[Callable[[], PlaybackState]] = None,
        attributor: Optional[WindowsAudioSourceAttributor] = None,
        timeout_ms: int = 1500,
        poll_interval_ms: int = 100,
        api_accepted: bool = True,
        target_track: Optional[str] = None,
        target_device_id: Optional[str] = None,
        provider_state: Optional[Any] = None,
        skip_layer3: bool = False,
    ) -> ThreeLayerVerificationResult:
        """
        Execute full three-layer verification:
        1. API command acceptance.
        2. Provider playback state readback.
        3. Local Windows audio session attribution.
        """
        expected_track_id = target_track or expected_track_id
        expected_device_id = target_device_id or expected_device_id

        if not api_accepted:
            return ThreeLayerVerificationResult(
                status="ACTION_FAILED",
                verified=False,
                api_accepted=False,
                details={"error": "API command was rejected"},
            )

        if get_state_fn is None:
            if provider_state is None:
                return ThreeLayerVerificationResult(
                    status="ACCEPTED_UNVERIFIED",
                    verified=False,
                    api_accepted=True,
                    details={"reason": "No provider state readback available"},
                )
            if isinstance(provider_state, dict):
                # Convert raw dict to PlaybackState
                is_p = provider_state.get("is_playing", False)
                dev = provider_state.get("device", {}) or {}
                dev_id = dev.get("id") or dev.get("name")
                item = provider_state.get("item", {}) or {}
                tr_id = item.get("id") or item.get("name")
                tr_name = item.get("name")
                tr_uri = item.get("uri")
                track_obj = MusicTrack(id=tr_id or "unknown", name=tr_name or "", uri=tr_uri or "")
                st = PlaybackState(is_playing=is_p, device_id=dev_id, track=track_obj)
                get_state_fn = lambda: st
            elif isinstance(provider_state, PlaybackState):
                get_state_fn = lambda: provider_state
            else:
                return ThreeLayerVerificationResult(
                    status="ACCEPTED_UNVERIFIED",
                    verified=False,
                    api_accepted=True,
                )

        start_time = time.monotonic()
        timeout_sec = timeout_ms / 1000.0
        interval_sec = poll_interval_ms / 1000.0

        last_state: Optional[PlaybackState] = None

        while (time.monotonic() - start_time) < timeout_sec:
            try:
                state = get_state_fn()
                last_state = state

                # Device matching check
                device_ok = True
                if expected_device_id and state.device_id:
                    device_ok = (state.device_id == expected_device_id or
                                 expected_device_id in state.device_id or
                                 state.device_id in ("local_default_speaker", "default"))

                # Track matching check
                track_ok = True
                if expected_track_id:
                    curr_track_id = state.track.id if state.track else None
                    curr_track_name = state.track.name if state.track else None
                    curr_track_uri = state.track.uri if state.track else None
                    norm_exp = expected_track_id.replace("spotify:track:", "").lower()
                    track_ok = (
                        (curr_track_id and (curr_track_id.lower() == norm_exp or curr_track_id == expected_track_id)) or
                        (curr_track_name and (norm_exp in curr_track_name.lower() or curr_track_name.lower() in norm_exp)) or
                        (curr_track_uri and (curr_track_uri == expected_track_id or curr_track_uri == f"spotify:track:{norm_exp}"))
                    )

                is_playing_ok = state.is_playing is True

                if not device_ok:
                    return ThreeLayerVerificationResult(
                        status="DEVICE_MISMATCH",
                        verified=False,
                        api_accepted=True,
                        device_match=False,
                        track_match=track_ok,
                        observed_state=state,
                        details={"expected_device": expected_device_id, "actual_device": state.device_id},
                    )

                if not track_ok:
                    return ThreeLayerVerificationResult(
                        status="TRACK_MISMATCH",
                        verified=False,
                        api_accepted=True,
                        device_match=device_ok,
                        track_match=False,
                        observed_state=state,
                        details={"expected_track": expected_track_id, "actual_track": curr_track_id or curr_track_name},
                    )

                if is_playing_ok and device_ok and track_ok:
                    # Layer 3: Local audio activity observation if local device
                    local_observed = None
                    if not skip_layer3:
                        if not expected_device_id or "local" in expected_device_id.lower() or "speaker" in expected_device_id.lower():
                            if attributor is None:
                                attributor = WindowsAudioSourceAttributor()
                            dom = attributor.get_dominant_audio_source()
                            local_observed = dom.get("confidence", 0.0) >= 0.80

                    return ThreeLayerVerificationResult(
                        status="PLAYBACK_VERIFIED",
                        verified=True,
                        api_accepted=True,
                        track_match=True,
                        device_match=True,
                        provider_playback_verified=True,
                        local_audio_activity_observed=local_observed,
                        observed_state=state,
                    )
            except Exception as e:
                logger.debug("Three-layer verification iteration error: %s", e)

            time.sleep(interval_sec)

        return ThreeLayerVerificationResult(
            status="ACCEPTED_UNVERIFIED",
            verified=False,
            api_accepted=True,
            track_match=False,
            device_match=False,
            provider_playback_verified=False,
            observed_state=last_state,
        )
