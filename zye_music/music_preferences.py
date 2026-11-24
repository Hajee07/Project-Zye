"""
ZYE AI — Music Mood and Preference Intelligence
===============================================

Handles mood mapping (Section 30) and time-of-day awareness (Section 31).
Provides smart contextual queries for music requests without explicit song titles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from zye_music.music_search import normalize_tamil_text


# Mood keywords mapping (Tamil, English, Tanglish) -> canonical mood and search query keywords
MOOD_MAPPINGS: Dict[str, Dict[str, List[str]]] = {
    "focus": {
        "keywords": ["focus", "study", "concentration", "work", "coding", "padikka", "vela panna", "mind relax"],
        "queries": ["instrumental", "classical", "lofi", "ambient", "meditation"],
    },
    "relax": {
        "keywords": ["relax", "chill", "peaceful", "calm", "soothing", "nimmathi", "amaithi", "slow"],
        "queries": ["melody", "acoustic", "slow melody", "piano", "peaceful"],
    },
    "workout": {
        "keywords": ["workout", "gym", "exercise", "energy", "energetic", "motivation", "power", "running"],
        "queries": ["fast beat", "energetic", "gym workout", "edm", "kuthu"],
    },
    "melancholy": {
        "keywords": ["sad", "pain", "crying", "heartbreak", "sogam", "kavalai", "feelings", "aloneness"],
        "queries": ["sad melody", "emotional", "slow song", "breakup melody"],
    },
    "party": {
        "keywords": ["party", "dance", "celebration", "kuthu", "dappankuthu", "fun", "marana mass", "thara local"],
        "queries": ["kuthu songs", "dance hits", "folk dance", "party remix", "mass beat"],
    },
    "sleep": {
        "keywords": ["sleep", "night", "bedtime", "sleeping", "thoonga", "thookam", "lullaby", "thaalaattu"],
        "queries": ["lullaby", "soft flute", "deep sleep", "gentle rain", "slow instrumental"],
    },
    "romantic": {
        "keywords": ["love", "romance", "romantic", "kadhal", "crush", "couple", "feel"],
        "queries": ["love melody", "romantic songs", "duet songs", "heartfelt melody"],
    },
}


class MusicPreferences:
    """Resolves contextual music suggestions from moods and time-of-day."""

    @staticmethod
    def detect_mood(text: str) -> Optional[str]:
        """Detect mood category from input text."""
        normalized = normalize_tamil_text(text)
        for mood, info in MOOD_MAPPINGS.items():
            for kw in info["keywords"]:
                if kw in normalized:
                    return mood
        return None

    @staticmethod
    def get_time_of_day(now: Optional[datetime] = None) -> str:
        """Categorize current time of day."""
        dt = now or datetime.now()
        hour = dt.hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    @classmethod
    def get_contextual_query(cls, mood: Optional[str] = None, text: Optional[str] = None) -> str:
        """Derive a smart search query based on mood and time-of-day."""
        detected_mood = mood or (cls.detect_mood(text) if text else None)

        if detected_mood and detected_mood in MOOD_MAPPINGS:
            queries = MOOD_MAPPINGS[detected_mood]["queries"]
            return queries[0] if queries else detected_mood

        # Fallback to diverse time-of-day recommendation
        time_slot = cls.get_time_of_day()
        if time_slot == "morning":
            return "acoustic breeze"
        elif time_slot == "afternoon":
            return "focus instrumental"
        elif time_slot == "evening":
            return "chill lofi vibe"
        else:
            return "peaceful flute meditation"
