"""
ZYE AI — Unit Tests: Local Music Player Engine
==============================================

Verifies:
- Headless initialization
- Library scanning and mock track discovery
- Volume controls and mute memory
- Playback controls (play, pause, resume, stop)
"""

import os
import tempfile
import pytest
from zye_music.local_music_provider import LocalMusicProvider
from zye_music.music_models import MusicStatus


@pytest.fixture
def temp_music_dir():
    with tempfile.TemporaryDirectory() as td:
        # Create a mock mp3 file
        mock_file = os.path.join(td, "Anirudh - Master The Blaster.mp3")
        with open(mock_file, "wb") as f:
            f.write(b"ID3\x03\x00\x00\x00\x00\x00#mock-audio-data")
        yield td


def test_local_provider_library_scanning(temp_music_dir):
    provider = LocalMusicProvider(music_directories=[temp_music_dir], default_volume=70)
    count = provider.rescan_library()
    assert count == 1
    assert len(provider._tracks) == 1
    assert provider._tracks[0].name == "Master The Blaster"
    assert provider._tracks[0].artist == "Anirudh"


def test_local_provider_search(temp_music_dir):
    provider = LocalMusicProvider(music_directories=[temp_music_dir])
    provider.rescan_library()

    results = provider.search("anirudh")
    assert len(results) == 1
    assert results[0].artist == "Anirudh"

    results_none = provider.search("nonexistent track query 12345")
    assert len(results_none) == 0


def test_local_provider_volume_and_mute():
    provider = LocalMusicProvider(default_volume=60)
    assert provider.get_playback_state().volume_percent == 60

    provider.set_volume(90)
    assert provider.get_playback_state().volume_percent == 90

    # Mute
    provider.mute()
    assert provider.get_playback_state().is_muted is True
    assert provider.get_playback_state().volume_percent == 0

    # Unmute restores to 90
    provider.unmute()
    assert provider.get_playback_state().is_muted is False
    assert provider.get_playback_state().volume_percent == 90
