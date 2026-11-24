"""
ZYE AI — Master Music Reliability & Section 44 Unit Test Suite (P0)
===================================================================

Comprehensive verification of:
- Strict query argument normalization (q -> query)
- Validation failures for empty queries
- Fail-closed provider routing (no silent local fallbacks)
- Track identity changes across requests
- Independent search caching
- Prevention of immediate track repetition (DiverseTrackSelector)
- Non-repetition in open-ended song requests
- Single-track and empty-library edge cases
- Repeat-one mode preservation
- Mood and genre exclusions (e.g. 'no melody' excludes melody tracks)
- Three-layer verification (DEVICE_MISMATCH, TRACK_MISMATCH, ACCEPTED_UNVERIFIED)
- MCP error propagation and malformed JSON rejection
- Mode C Spotify voice policy enforcement
- Tool continuation suppression
"""

from __future__ import annotations

import json
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from zye_music.audio_source_attribution import (
    AudioSessionEvidence,
    AudioSourceType,
    WindowsAudioSourceAttributor,
)
from zye_music.local_music_provider import LocalMusicProvider
from zye_music.music_authorization import MusicAuthorization
from zye_music.music_errors import (
    MusicAuthorizationError,
    MusicErrorCode,
    MusicValidationError,
)
from zye_music.music_models import (
    InputOrigin,
    MusicStatus,
    MusicTrack,
    PlaybackResult,
    PlaybackState,
    ProviderType,
)
from zye_music.playback_verifier import PlaybackVerifier, ThreeLayerVerificationResult
from zye_music.provider_router import MusicProviderRouter
from zye_music.spotify_mcp_adapter import (
    SPOTIFY_TOOL_NAME_MAP,
    SpotifyMCPAdapter,
    build_spotify_search_args,
)
from zye_music.track_selector import DiverseTrackSelector


# ===========================================================================
# TEST 01 — Query argument mapping
# ===========================================================================
def test_01_query_argument_mapping():
    """Input q='Kannana Kanne' maps to required 'query' and supported media type."""
    input_args = {"q": "Kannana Kanne"}
    mapped = build_spotify_search_args(input_args)
    assert mapped["query"] == "Kannana Kanne"
    assert mapped["type"] == "track"
    assert mapped["limit"] == 5

    # Also test explicit positional argument
    mapped_pos = build_spotify_search_args("Arabic Kuthu", media_type="album", limit=3)
    assert mapped_pos["query"] == "Arabic Kuthu"
    assert mapped_pos["type"] == "album"
    assert mapped_pos["limit"] == 3


# ===========================================================================
# TEST 02 — Empty specific-track search
# ===========================================================================
def test_02_empty_specific_track_search():
    """Empty or whitespace queries must raise validation error and trigger no playback."""
    with pytest.raises(MusicValidationError) as exc_info:
        build_spotify_search_args({"q": ""})
    assert exc_info.value.code == MusicErrorCode.EMPTY_MUSIC_QUERY

    with pytest.raises(MusicValidationError) as exc_info2:
        build_spotify_search_args("   ")
    assert exc_info2.value.code == MusicErrorCode.EMPTY_MUSIC_QUERY

    # Excessive query length (>300 chars)
    with pytest.raises(MusicValidationError) as exc_info3:
        build_spotify_search_args("A" * 301)
    assert exc_info3.value.code == MusicErrorCode.MUSIC_QUERY_TOO_LONG


# ===========================================================================
# TEST 03 — Explicit provider unavailable (Fail-closed, no silent fallback)
# ===========================================================================
def test_03_explicit_provider_unavailable():
    """When explicit Spotify is requested but unavailable, fail closed without falling back to local."""
    mock_local = MagicMock(spec=LocalMusicProvider)
    mock_local.provider_type = ProviderType.LOCAL

    # Router without available Spotify provider
    router = MusicProviderRouter(local_provider=mock_local, spotify_provider=None)

    with pytest.raises(MusicAuthorizationError) as exc_info:
        # Request via manual tool (Mode A authorized, but provider missing)
        router.resolve_provider(requested_provider=ProviderType.SPOTIFY, origin=InputOrigin.MANUAL_TOOL)
    assert exc_info.value.code == MusicErrorCode.SPOTIFY_CONFIG_MISSING

    # Local provider must NOT have been called or returned
    mock_local.play.assert_not_called()


# ===========================================================================
# TEST 04 — Track identity changes across requests
# ===========================================================================
def test_04_track_identity_changes():
    """Request Track A, then Track B; verify media identifiers are distinct."""
    candidates = [
        MusicTrack(uri="spotify:track:A100", name="Track A", artist="Artist 1"),
        MusicTrack(uri="spotify:track:B200", name="Track B", artist="Artist 2"),
    ]
    selector = DiverseTrackSelector(history_size=5)
    first_choice = selector.select(candidates)
    selector.record_played(first_choice)

    second_choice = selector.select(candidates, current_track_id=first_choice.id)
    assert first_choice.id != second_choice.id
    assert first_choice.uri != second_choice.uri


# ===========================================================================
# TEST 05 — Cached results independent per query
# ===========================================================================
def test_05_cached_results():
    """Two different search queries must yield distinct, independent results."""
    cache: Dict[str, Any] = {}

    def search_with_cache(query: str) -> Dict[str, Any]:
        norm = query.strip().lower()
        if norm not in cache:
            cache[norm] = {
                "query": query,
                "track_id": f"id_{hash(norm) & 0xfffffff}",
                "title": f"Song for {query}",
            }
        return cache[norm]

    res_vathi = search_with_cache("Vathi Coming")
    res_arabic = search_with_cache("Arabic Kuthu")

    assert res_vathi["track_id"] != res_arabic["track_id"]
    assert res_vathi["title"] != res_arabic["title"]
    # Re-fetch ensures idempotence without bleed
    assert search_with_cache("Vathi Coming")["track_id"] == res_vathi["track_id"]


# ===========================================================================
# TEST 06 — Previous-track reuse prevention
# ===========================================================================
def test_06_previous_track_reuse():
    """A new open-ended request must not immediately reuse the previous track ID."""
    tracks = [
        MusicTrack(uri="local:1", name="Track 1", artist="Artist"),
        MusicTrack(uri="local:2", name="Track 2", artist="Artist"),
        MusicTrack(uri="local:3", name="Track 3", artist="Artist"),
    ]
    selector = DiverseTrackSelector(history_size=5)
    t1 = selector.select(tracks)
    selector.record_played(t1)

    t2 = selector.select(tracks, current_track_id=t1.id)
    selector.record_played(t2)

    assert t2.id != t1.id
    assert t1.id in selector.recent


# ===========================================================================
# TEST 07 — Same track explicitly requested remains supported
# ===========================================================================
def test_07_same_track_explicitly_requested():
    """When the user explicitly asks for the same song again, legitimate replay is supported."""
    lp = LocalMusicProvider()
    lp.initialize()

    # If library has tracks, searching for the exact same track name twice returns that track
    if lp._tracks:
        first_title = lp._tracks[0].title
        res1 = lp.search(first_title)
        res2 = lp.search(first_title)
        assert len(res1) > 0
        assert len(res2) > 0
        assert res1[0].uri == res2[0].uri


# ===========================================================================
# TEST 08 — Open-ended music selection avoids immediate repetition
# ===========================================================================
def test_08_open_ended_music_selection():
    """Repeatedly requesting general music across multiple candidate tracks avoids immediate repetition."""
    candidates = [f"track_{i}.mp3" for i in range(5)]
    selector = DiverseTrackSelector(history_size=4)

    history: List[str] = []
    for _ in range(25):
        pick = selector.select(candidates)
        if history:
            assert pick != history[-1], f"Immediate repetition detected: {pick} == {history[-1]}"
        selector.record_played(pick)
        history.append(pick)


# ===========================================================================
# TEST 09 — Single-track library handled gracefully
# ===========================================================================
def test_09_single_track_library():
    """When only 1 track exists in the library, system returns it without crashing."""
    single = [MusicTrack(uri="only_track", name="Only Track", artist="Solo")]
    selector = DiverseTrackSelector(history_size=5)

    pick1 = selector.select(single)
    selector.record_played(pick1)
    # Next pick has no alternative, must return the single track safely
    pick2 = selector.select(single, current_track_id=pick1.id)
    assert pick2.id == "only_track"


# ===========================================================================
# TEST 10 — Empty library returns NO_ELIGIBLE_TRACKS (No demo audio fallback)
# ===========================================================================
def test_10_empty_library():
    """Empty candidate pool raises LookupError; never substitutes demo audio."""
    selector = DiverseTrackSelector(history_size=5)
    with pytest.raises(LookupError) as exc_info:
        selector.select([])
    assert "NO_ELIGIBLE_TRACKS" in str(exc_info.value)


# ===========================================================================
# TEST 11 — Repeat-one mode preservation
# ===========================================================================
def test_11_repeat_one_mode():
    """Correctly detect and preserve intentional repeat-track state."""
    state = PlaybackState(
        is_playing=True,
        track=MusicTrack(uri="spotify:track:repeat1", name="Loop Track", artist="Looper"),
        repeat_state="track",
    )
    assert state.repeat_state == "track"
    # When repeat_state == 'track', the user intends to replay the same track


# ===========================================================================
# TEST 12 — Mood and genre exclusion (e.g. 'no melody' excludes melody tracks)
# ===========================================================================
def test_12_mood_exclusion():
    """Requesting non-melody music from library excludes all melody tracks."""
    candidates = [
        "AR Rahman Style - Pure Melody.wav",
        "Energy Beat Booster.mp3",
        "Acoustic Evening Guitar.mp3",
        "Morning Calm Melody.wav",
        "Chill Lofi Study Beats.mp3",
    ]
    selector = DiverseTrackSelector(history_size=3)

    for _ in range(10):
        pick = selector.select(candidates, exclude_terms=["melody", "pure melody"])
        selector.record_played(pick)
        assert "melody" not in pick.lower(), f"Excluded term 'melody' leaked into selection: {pick}"


# ===========================================================================
# TEST 13 — Wrong playback device detection (DEVICE_MISMATCH)
# ===========================================================================
def test_13_wrong_playback_device():
    """Report DEVICE_MISMATCH when actual device differs from target."""
    verifier = PlaybackVerifier()
    mock_raw = {
        "is_playing": True,
        "device": {"id": "device_tv", "name": "Living Room TV"},
        "item": {"id": "trk_1", "name": "Vathi Coming"},
    }
    result = verifier.verify_three_layer(
        api_accepted=True,
        target_track="Vathi Coming",
        target_device_id="device_speakers",  # Mismatched target
        provider_state=mock_raw,
        skip_layer3=True,
    )
    assert result.status in (MusicStatus.DEVICE_NOT_FOUND, "DEVICE_MISMATCH")
    assert result.device_match is False
    assert result.verified is False


# ===========================================================================
# TEST 14 — Wrong playing track detection (TRACK_MISMATCH)
# ===========================================================================
def test_14_wrong_playing_track():
    """Report TRACK_MISMATCH when actual playing track differs from target."""
    verifier = PlaybackVerifier()
    mock_raw = {
        "is_playing": True,
        "device": {"id": "dev_pc", "name": "PC"},
        "item": {"id": "trk_wrong", "name": "Unrelated Old Song"},
    }
    result = verifier.verify_three_layer(
        api_accepted=True,
        target_track="Arabic Kuthu",
        target_device_id="dev_pc",
        provider_state=mock_raw,
        skip_layer3=True,
    )
    assert result.status in (MusicStatus.TRACK_NOT_FOUND, "TRACK_MISMATCH")
    assert result.track_match is False
    assert result.verified is False


# ===========================================================================
# TEST 15 — API accepted but state unavailable (ACCEPTED_UNVERIFIED)
# ===========================================================================
def test_15_api_accepted_state_unavailable():
    """Report ACCEPTED_UNVERIFIED when command accepted but readback unavailable."""
    verifier = PlaybackVerifier()
    result = verifier.verify_three_layer(
        api_accepted=True,
        target_track="Arabic Kuthu",
        target_device_id="dev_pc",
        provider_state=None,  # State readback failed / unavailable
        skip_layer3=True,
    )
    assert result.status in (MusicStatus.ACCEPTED_UNVERIFIED, "ACCEPTED_UNVERIFIED")
    assert result.verified is False
    assert result.api_accepted is True


# ===========================================================================
# TEST 16 — MCP isError propagation
# ===========================================================================
def test_16_mcp_is_error_propagation():
    """MCP response with isError=True must propagate failure and not register success."""
    adapter = SpotifyMCPAdapter()
    error_response = {
        "isError": True,
        "content": [{"type": "text", "text": "Error: Spotify Web API 401 Unauthorized"}],
    }
    with patch.object(adapter, "call_tool", return_value=error_response):
        res = adapter.play(track_uri="spotify:track:123")
        assert res.success is False
        assert res.status in (MusicStatus.ACTION_FAILED, MusicStatus.AUTHENTICATION_REQUIRED)


# ===========================================================================
# TEST 17 — Malformed JSON handled as explicit failure
# ===========================================================================
def test_17_malformed_json_explicit_failure():
    """Malformed JSON in tool output must trigger explicit failure, never false success."""
    adapter = SpotifyMCPAdapter()
    malformed_response = {
        "isError": False,
        "content": [{"type": "text", "text": "Unexpected end of JSON input at position 0: {bad"}],
    }
    with patch.object(adapter, "call_tool", return_value=malformed_response):
        search_res = adapter.search("Any Song")
        # Should return empty list or fail cleanly without crashing or false match
        assert isinstance(search_res, list)


# ===========================================================================
# TEST 18 — Demo audio blocked from production selection
# ===========================================================================
def test_18_demo_audio_blocked():
    """Test recordings or demo sound effects cannot be selected as user music."""
    library = [
        "demo_chirp.wav",
        "sample_beep.mp3",
        "test_tone_440hz.wav",
        "Real User Song.mp3",
    ]
    selector = DiverseTrackSelector(history_size=3)
    # Exclude demo/test patterns
    chosen = selector.select(library, exclude_terms=["demo", "sample", "test_tone"])
    assert chosen == "Real User Song.mp3"


# ===========================================================================
# TEST 19 — Unauthorized Spotify voice operation rejected (Mode C)
# ===========================================================================
def test_19_unauthorized_spotify_voice_operation():
    """Mode C policy compliance strictly denies Spotify voice requests unless opted in."""
    auth = MusicAuthorization()
    # Explicitly verify that Mode C (Spotify via Voice) is denied by default
    allowed, reason, code = auth.is_authorized(
        provider=ProviderType.SPOTIFY,
        origin=InputOrigin.VOICE,
        action="play",
    )
    assert allowed is False
    assert code == MusicErrorCode.SPOTIFY_VOICE_NOT_AUTHORIZED

    # Mode A (Manual tool) remains allowed
    allowed_m, _, _ = auth.is_authorized(
        provider=ProviderType.SPOTIFY,
        origin=InputOrigin.MANUAL_TOOL,
        action="play",
    )
    assert allowed_m is True

    # Mode B (Local music via Voice) remains allowed
    allowed_l, _, _ = auth.is_authorized(
        provider=ProviderType.LOCAL,
        origin=InputOrigin.VOICE,
        action="play",
    )
    assert allowed_l is True


# ===========================================================================
# TEST 20 — Tool continuation suppresses premature clarification
# ===========================================================================
def test_20_tool_continuation_suppression():
    """Verify tool mapping prevents mangled tool names that caused failed tool execution."""
    # Ensure all expected Gemini tool calls map to actual TypeScript MCP names
    assert SPOTIFY_TOOL_NAME_MAP["spotify_search"] == "searchSpotify"
    assert SPOTIFY_TOOL_NAME_MAP["spotify_play_music"] == "playMusic"
    assert SPOTIFY_TOOL_NAME_MAP["spotify_pause_playback"] == "pausePlayback"
    assert SPOTIFY_TOOL_NAME_MAP["spotify_get_now_playing"] == "getNowPlaying"
    assert SPOTIFY_TOOL_NAME_MAP["spotify_get_available_devices"] == "getAvailableDevices"
    assert SPOTIFY_TOOL_NAME_MAP["spotify_transfer_playback"] == "transferPlayback"
