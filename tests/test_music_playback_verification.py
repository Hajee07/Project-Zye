"""
ZYE AI — Unit Tests: Playback Verifier
======================================

Verifies bounded polling playback verification:
- Returns PLAYBACK_VERIFIED when state change is detected within bounds
- Returns ACCEPTED_UNVERIFIED when state check exceeds bounded timeout
"""

from zye_music.music_models import MusicStatus, PlaybackState
from zye_music.playback_verifier import PlaybackVerifier


def test_playback_verifier_success():
    call_count = [0]

    def get_state():
        call_count[0] += 1
        return PlaybackState(is_playing=(call_count[0] >= 2))

    status = PlaybackVerifier.verify_sync(
        get_state_fn=get_state,
        condition_fn=lambda s: s.is_playing is True,
        timeout_ms=200,
        poll_interval_ms=10,
    )
    assert status == MusicStatus.PLAYBACK_VERIFIED


def test_playback_verifier_timeout_fallback():
    # Never transitions to is_playing=True
    state = PlaybackState(is_playing=False)

    status = PlaybackVerifier.verify_sync(
        get_state_fn=lambda: state,
        condition_fn=lambda s: s.is_playing is True,
        timeout_ms=50,
        poll_interval_ms=10,
    )
    assert status == MusicStatus.ACCEPTED_UNVERIFIED
