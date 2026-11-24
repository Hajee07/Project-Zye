"""
ZYE AI — Multilingual Music Intent Router
=========================================

Alexa-style natural language intent router supporting:
- Tamil (Unicode)
- Tanglish (Tamil written in Latin script)
- English

Extracts:
- Intent (PLAY, PAUSE, RESUME, STOP, NEXT, PREVIOUS, VOLUME, MUTE, SHUFFLE, REPEAT, NOW_PLAYING)
- Query / Track / Artist names
- Mood and contextual indicators
- Provider preferences ("spotify la", "local music", etc.)
"""

from __future__ import annotations

import re
from typing import Optional, Tuple
from zye_music.music_models import IntentResult, IntentType, ProviderType
from zye_music.music_preferences import MusicPreferences
from zye_music.music_search import normalize_tamil_text


class MusicIntentRouter:
    """Classifies natural language user voice input into structured music commands."""

    # Volume extraction regex
    VOLUME_PATTERN = re.compile(
        r"(?:volume|satham|sound|vol)\s*(?:to|ai|ah)?\s*(\d{1,3})(?:\s*%|\s*percent)?",
        re.IGNORECASE,
    )

    @classmethod
    def parse_intent(cls, text: str) -> IntentResult:
        """Parse natural language command into structured IntentResult."""
        if not text or not text.strip():
            return IntentResult(intent=IntentType.UNKNOWN, raw_text="")

        norm = normalize_tamil_text(text)

        # Detect provider preference
        provider_preference: Optional[ProviderType] = None
        if "spotify" in norm:
            provider_preference = ProviderType.SPOTIFY
        elif any(k in norm for k in ["local", "computer", "system", "file", "download"]):
            provider_preference = ProviderType.LOCAL

        # 1. Volume commands
        # Specific volume level
        vol_match = cls.VOLUME_PATTERN.search(norm)
        if vol_match:
            try:
                level = int(vol_match.group(1))
                return IntentResult(
                    intent=IntentType.VOLUME_SET,
                    volume_level=max(0, min(100, level)),
                    provider_preference=provider_preference,
                    raw_text=text,
                )
            except ValueError:
                pass

        # Volume Up
        if any(
            k in norm
            for k in [
                "volume up",
                "increase volume",
                "volume increase",
                "satham ethu",
                "satham koodu",
                "satham kootu",
                "satham koottu",
                "volume kootu",
                "raise volume",
                "louder",
                "sound increase",
                "satham athigam",
                "சத்தம் கூட்டு",
                "சத்தம் ஏத்து",
                "கூட்டு",
            ]
        ):
            return IntentResult(
                intent=IntentType.VOLUME_UP,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # Volume Down
        if any(
            k in norm
            for k in [
                "volume down",
                "decrease volume",
                "volume decrease",
                "satham kora",
                "satham korai",
                "volume korai",
                "lower volume",
                "softer",
                "sound decrease",
            ]
        ):
            return IntentResult(
                intent=IntentType.VOLUME_DOWN,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 2. Mute / Unmute
        if any(k in norm for k in ["unmute", "satham kudu", "sound on", "unmute pannu"]):
            return IntentResult(
                intent=IntentType.UNMUTE,
                provider_preference=provider_preference,
                raw_text=text,
            )

        if any(k in norm for k in ["mute", "pesama iru", "sound off", "silent", "mute pannu"]):
            return IntentResult(
                intent=IntentType.MUTE,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 3. Pause
        if any(
            k in norm
            for k in [
                "pause",
                "niruthu",
                "pause pannu",
                "paata pause",
                "hold on",
                "konjam nillu",
                "wait pannu",
            ]
        ):
            return IntentResult(
                intent=IntentType.PAUSE,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 4. Resume
        if any(
            k in norm
            for k in [
                "resume",
                "thodaru",
                "resume pannu",
                "continue",
                "marubadiyum podu",
                "தொடரு",
            ]
        ) or norm == "play pannu":
            return IntentResult(
                intent=IntentType.RESUME,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 5. Stop
        if any(
            k in norm
            for k in [
                "stop music",
                "stop song",
                "paata niruthu",
                "close music",
                "stop pannu",
                "niruthidu",
                "paatta stop pannu",
            ]
        ):
            return IntentResult(
                intent=IntentType.STOP,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 6. Next
        if any(
            k in norm
            for k in [
                "next song",
                "adutha paatu",
                "next track",
                "skip",
                "skip pannu",
                "adutha song",
                "next podu",
            ]
        ):
            return IntentResult(
                intent=IntentType.NEXT,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 7. Previous
        if any(
            k in norm
            for k in [
                "previous song",
                "munthaiya paatu",
                "prev song",
                "back track",
                "munnaadi paatu",
                "previous track",
                "back podu",
            ]
        ):
            return IntentResult(
                intent=IntentType.PREVIOUS,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 8. Shuffle
        if any(k in norm for k in ["shuffle on", "shuffle podu", "kalandhu podu", "shuffle songs"]):
            return IntentResult(
                intent=IntentType.SHUFFLE_ON,
                provider_preference=provider_preference,
                raw_text=text,
            )
        if any(k in norm for k in ["shuffle off", "turn off shuffle", "shuffle niruthu"]):
            return IntentResult(
                intent=IntentType.SHUFFLE_OFF,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 9. Repeat
        if any(k in norm for k in ["repeat this song", "repeat one", "idhaiye repeat", "marubadiyum idhaiye"]):
            return IntentResult(
                intent=IntentType.REPEAT_ONE,
                provider_preference=provider_preference,
                raw_text=text,
            )
        if any(k in norm for k in ["repeat all", "repeat playlist", "loop all"]):
            return IntentResult(
                intent=IntentType.REPEAT_ALL,
                provider_preference=provider_preference,
                raw_text=text,
            )
        if any(k in norm for k in ["repeat off", "stop repeat", "loop off"]):
            return IntentResult(
                intent=IntentType.REPEAT_OFF,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 10. Query / Now playing
        if any(
            k in norm
            for k in [
                "what song",
                "which song",
                "enna paatu",
                "now playing",
                "current song",
                "current track",
                "paatu peru enna",
                "yaaru paaduna",
            ]
        ):
            return IntentResult(
                intent=IntentType.NOW_PLAYING,
                provider_preference=provider_preference,
                raw_text=text,
            )

        # 11. Play command
        if any(
            k in norm
            for k in [
                "play",
                "podu",
                "vai",
                "paadu",
                "kelu",
                "paatu",
                "pattu",
                "song",
                "music",
                "melody",
                "பாட்டு",
                "போடு",
                "வை",
                "பாடு",
                "கேளு",
                "இசை",
            ]
        ):
            # Extract query after removing play phrases
            cleaned = cls._extract_song_query(norm)
            mood = MusicPreferences.detect_mood(norm)
            return IntentResult(
                intent=IntentType.PLAY,
                query=cleaned or None,
                mood=mood,
                provider_preference=provider_preference,
                raw_text=text,
            )

        return IntentResult(
            intent=IntentType.UNKNOWN,
            query=norm,
            provider_preference=provider_preference,
            raw_text=text,
        )

    @classmethod
    def _extract_song_query(cls, text: str) -> str:
        """Strip command carrier words and extract core song or artist name."""
        res = text.strip().rstrip(".")
        # Remove provider references
        res = re.sub(r"\b(?:on\s+spotify|spotify\s+la|in\s+spotify)\b", "", res)
        res = re.sub(r"\b(?:local(?:ly)?|from\s+local|system\s+la)\b", "", res)

        prefixes = [
            r"^(?:zye|hey zye|please|can you|could you)\s+",
            r"^(?:play|podu|vai|start|put)\s+",
            r"^(?:enna\s+paatu|oru\s+nalla\s+paatu|edhavadhu\s+paatu)\s+",
            r"^(?:edhavadhu|ethavadhu|oru|nalla|edhachum|ethachum)\s+",
            r"^(?:ஏதாச்சும்|ஏதாவது|எதாச்சும்|எதாவது|ஒரு|நல்ல|எனக்கு)\s*",
        ]
        suffixes = [
            r"\s+(?:podu|vai|paadungren|kelungren|play pannu|podunga)$",
            r"\s+(?:songs?|tracks?|paatu|pattu|paadu|hits)$",
            r"\s*(?:சாங்|சாங்க்|பாட்டு|பாடு|பாடுங்க|போடு|போடுங்க|வை|வைங்க|பாடல்|இசை)$",
        ]

        changed = True
        while changed:
            orig = res
            for p in prefixes:
                res = re.sub(p, "", res, flags=re.IGNORECASE).strip()
            for s in suffixes:
                res = re.sub(s, "", res, flags=re.IGNORECASE).strip()
            changed = (res != orig)

        return res.strip()
