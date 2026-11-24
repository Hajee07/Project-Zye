"""
ZYE AI — Unit Tests: Music Intent Router
========================================

Verifies Alexa-style natural language intent classification for:
- English
- Tamil (Unicode)
- Tanglish (Tamil in Latin script)
"""

from zye_music.music_intent_router import MusicIntentRouter
from zye_music.music_models import IntentType, ProviderType


def test_play_intents_multilingual():
    # English
    r1 = MusicIntentRouter.parse_intent("play Master the Blaster")
    assert r1.intent == IntentType.PLAY
    assert "master the blaster" in r1.query.lower()

    # Tanglish
    r2 = MusicIntentRouter.parse_intent("anirudh song podu")
    assert r2.intent == IntentType.PLAY
    assert "anirudh" in r2.query.lower()

    r3 = MusicIntentRouter.parse_intent("oru nalla melody paatu vai")
    assert r3.intent == IntentType.PLAY
    assert "melody" in (r3.query or "").lower()

    # Tamil Unicode
    r4 = MusicIntentRouter.parse_intent("பாட்டு போடு")
    assert r4.intent == IntentType.PLAY


def test_pause_and_resume_intents():
    assert MusicIntentRouter.parse_intent("pause music").intent == IntentType.PAUSE
    assert MusicIntentRouter.parse_intent("paata niruthu").intent == IntentType.PAUSE
    assert MusicIntentRouter.parse_intent("konjam hold on pannu").intent == IntentType.PAUSE

    assert MusicIntentRouter.parse_intent("resume music").intent == IntentType.RESUME
    assert MusicIntentRouter.parse_intent("thodaru").intent == IntentType.RESUME
    assert MusicIntentRouter.parse_intent("marubadiyum podu").intent == IntentType.RESUME


def test_skip_and_navigation_intents():
    assert MusicIntentRouter.parse_intent("next song").intent == IntentType.NEXT
    assert MusicIntentRouter.parse_intent("adutha paatu").intent == IntentType.NEXT
    assert MusicIntentRouter.parse_intent("skip pannu").intent == IntentType.NEXT

    assert MusicIntentRouter.parse_intent("previous song").intent == IntentType.PREVIOUS
    assert MusicIntentRouter.parse_intent("munthaiya paatu").intent == IntentType.PREVIOUS


def test_volume_and_mute_intents():
    # Specific volume
    r_vol = MusicIntentRouter.parse_intent("set volume to 65 percent")
    assert r_vol.intent == IntentType.VOLUME_SET
    assert r_vol.volume_level == 65

    # Volume up
    assert MusicIntentRouter.parse_intent("volume up").intent == IntentType.VOLUME_UP
    assert MusicIntentRouter.parse_intent("satham kootu").intent == IntentType.VOLUME_UP

    # Volume down
    assert MusicIntentRouter.parse_intent("volume down").intent == IntentType.VOLUME_DOWN
    assert MusicIntentRouter.parse_intent("satham kora").intent == IntentType.VOLUME_DOWN

    # Mute & Unmute
    assert MusicIntentRouter.parse_intent("mute pannu").intent == IntentType.MUTE
    assert MusicIntentRouter.parse_intent("pesama iru").intent == IntentType.MUTE
    assert MusicIntentRouter.parse_intent("unmute pannu").intent == IntentType.UNMUTE


def test_provider_preference_detection():
    r_spot = MusicIntentRouter.parse_intent("spotify la ar rahman song podu")
    assert r_spot.intent == IntentType.PLAY
    assert r_spot.provider_preference == ProviderType.SPOTIFY

    r_local = MusicIntentRouter.parse_intent("system la irukura local song podu")
    assert r_local.intent == IntentType.PLAY
    assert r_local.provider_preference == ProviderType.LOCAL


def test_now_playing_intents():
    assert MusicIntentRouter.parse_intent("what song is playing").intent == IntentType.NOW_PLAYING
    assert MusicIntentRouter.parse_intent("enna paatu idhu").intent == IntentType.NOW_PLAYING
