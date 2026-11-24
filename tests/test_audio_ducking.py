"""
ZYE AI — Unit Tests: Audio Ducking Engine
=========================================

Verifies speech-aware audio ducking:
- Volume reduction down to ducked depth percentage
- Smooth restoration
- Depth tracking reference counts
- Force unduck behavior
"""

from zye_music.audio_ducking import AudioDucker


def test_audio_ducking_and_restoration():
    volume_state = [80]

    def set_vol(v: int):
        volume_state[0] = v

    def get_vol():
        return volume_state[0]

    ducker = AudioDucker(
        set_volume_fn=set_vol,
        get_volume_fn=get_vol,
        ducked_volume_percentage=20,
        ramp_duration_ms=0,
    )

    assert ducker.is_ducked is False
    assert get_vol() == 80

    # Duck volume
    res_duck = ducker.duck_sync()
    assert res_duck is True
    assert ducker.is_ducked is True
    assert get_vol() == 20

    # Second duck call increments depth count but remains at ducked volume
    ducker.duck_sync()
    assert ducker._duck_depth_count == 2
    assert get_vol() == 20

    # First unduck decrements depth count, still ducked
    ducker.unduck_sync(force=False)
    assert ducker.is_ducked is True
    assert ducker._duck_depth_count == 1

    # Second unduck restores original volume
    ducker.unduck_sync(force=False)
    assert ducker.is_ducked is False
    assert get_vol() == 80


def test_audio_ducking_force_unduck():
    volume_state = [75]

    def set_vol(v: int):
        volume_state[0] = v

    def get_vol():
        return volume_state[0]

    ducker = AudioDucker(
        set_volume_fn=set_vol,
        get_volume_fn=get_vol,
        ducked_volume_percentage=15,
        ramp_duration_ms=0,
    )

    ducker.duck_sync()
    ducker.duck_sync()
    assert ducker._duck_depth_count == 2
    assert get_vol() == 15

    # Force unduck immediately resets and restores volume
    ducker.unduck_sync(force=True)
    assert ducker.is_ducked is False
    assert ducker._duck_depth_count == 0
    assert get_vol() == 75
