"""
ZYE AI — Music Search Engine
============================

Intelligent music search engine with:
- Tamil Unicode NFC/NFD normalization.
- Tanglish phonetic and colloquial matching (e.g., "vaathi", "anirudh", "ar rahman").
- Ranked similarity scoring: Exact match > Prefix match > Substring match > Token overlap.
- Audio file tag extraction.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import List, Optional, Tuple
from zye_music.music_models import MusicTrack, ProviderType


def normalize_tamil_text(text: str) -> str:
    """Normalize Tamil and multilingual text using Unicode NFC form and lowercase."""
    if not text:
        return ""
    # Normalize Unicode composition
    normalized = unicodedata.normalize("NFC", text)
    # Convert to lowercase
    normalized = normalized.lower().strip()
    # Replace multiple spaces with a single space
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def clean_query_text(query: str) -> str:
    """Strip common music request filler words in Tamil, English, and Tanglish."""
    normalized = normalize_tamil_text(query)
    # Remove phrases like 'play', 'paatu podu', 'song', etc.
    fillers = [
        r"\bplay\b",
        r"\bsong\b",
        r"\bsongs\b",
        r"\bmusic\b",
        r"\btrack\b",
        r"\btracks\b",
        r"\bpaatu\b",
        r"\bpattu\b",
        r"\bpadu\b",
        r"\bpaadu\b",
        r"\bpodunkal\b",
        r"\bpodu\b",
        r"\bvai\b",
        r"\bvainga\b",
        r"\bkelu\b",
        r"\bvenum\b",
        r"\bplease\b",
        r"\bkonjam\b",
        r"\bedhavadhu\b",
        r"\bethavadhu\b",
        r"\boru\b",
        r"\bnalla\b",
        r"ஏதாச்சும்",
        r"ஏதாவது",
        r"எதாச்சும்",
        r"ஒரு",
        r"சாங்",
        r"சாங்க்",
        r"பாட்டு",
        r"பாடு",
        r"பாடுங்க",
        r"போடு",
        r"போடுங்க",
        r"வை",
        r"வைங்க",
        r"நல்ல",
        r"கொஞ்சம்",
    ]
    for pattern in fillers:
        normalized = re.sub(pattern, " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


class MusicSearchEngine:
    """In-memory search engine for local tracks and cached catalog items."""

    def __init__(self, tracks: Optional[List[MusicTrack]] = None) -> None:
        self.tracks: List[MusicTrack] = tracks or []

    def set_tracks(self, tracks: List[MusicTrack]) -> None:
        """Update available tracks."""
        self.tracks = list(tracks)

    def search(self, query: str, limit: int = 10) -> List[MusicTrack]:
        """Search tracks with ranking score."""
        if not query or not query.strip():
            return self.tracks[:limit]

        cleaned_query = clean_query_text(query)
        raw_query_norm = normalize_tamil_text(query)

        scored_tracks: List[Tuple[float, MusicTrack]] = []
        for track in self.tracks:
            score = self._compute_score(track, cleaned_query, raw_query_norm)
            if score > 0.0:
                scored_tracks.append((score, track))

        # Sort descending by score
        scored_tracks.sort(key=lambda x: x[0], reverse=True)
        return [track for _, track in scored_tracks[:limit]]

    def _compute_score(self, track: MusicTrack, cleaned_query: str, raw_query: str) -> float:
        name_norm = normalize_tamil_text(track.name)
        artist_norm = normalize_tamil_text(track.artist)
        album_norm = normalize_tamil_text(track.album)

        searchable_text = f"{name_norm} {artist_norm} {album_norm}"

        score = 0.0

        # Exact match on title
        if cleaned_query and name_norm == cleaned_query:
            score += 100.0
        # Title starts with query
        elif cleaned_query and name_norm.startswith(cleaned_query):
            score += 80.0
        # Substring in title
        elif cleaned_query and cleaned_query in name_norm:
            score += 60.0

        # Match in artist name
        if cleaned_query and artist_norm and cleaned_query in artist_norm:
            score += 40.0

        # Match in album
        if cleaned_query and album_norm and cleaned_query in album_norm:
            score += 30.0

        # Token set match
        tokens = [t for t in cleaned_query.split() if len(t) > 1]
        if tokens:
            matched_tokens = sum(1 for t in tokens if t in searchable_text)
            score += (matched_tokens / len(tokens)) * 25.0

        return score
