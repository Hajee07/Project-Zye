"""
ZYE AI — Diverse Track Selector
===============================

Advanced non-repeating track selector implementing:
- Current-track exclusion for open-ended selection.
- Recent-track history bounding (default maxlen=10).
- Relax history oldest-first when all eligible tracks were played recently.
- Explicit repeat request preservation.
- Non-repeating deterministic selection without resetting RNG seed per call.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from typing import Any, List, Optional
from zye_music.music_models import MusicTrack

logger = logging.getLogger("zye.music.selector")


class DiverseTrackSelector:
    """Selects varied tracks from an authorized candidate collection without immediate repeats."""

    def __init__(
        self,
        history_size: int = 10,
        rng: Optional[random.Random] = None,
    ) -> None:
        if history_size < 1:
            raise ValueError("INVALID_HISTORY_SIZE: History size must be at least 1")

        self.history_size = history_size
        self.recent: deque[str] = deque(maxlen=history_size)
        self.rng = rng or random.Random()

    def select(
        self,
        candidates: List[MusicTrack] | List[str],
        current_track_id: Optional[str] = None,
        mood_filter: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
    ) -> Any:
        """
        Select a track from candidates, avoiding current_track_id, excluded terms, and recently played tracks.
        """
        if not candidates:
            raise LookupError("NO_ELIGIBLE_TRACKS: No candidate tracks provided")

        is_str_list = isinstance(candidates[0], str)
        if is_str_list:
            converted = [MusicTrack(uri=c, name=c, artist="Local Artist") for c in candidates]  # type: ignore
        else:
            converted = list(candidates)  # type: ignore

        # Apply exclusion filter (e.g. 'melody', 'ambient')
        if exclude_terms:
            lower_terms = [t.lower() for t in exclude_terms if t]
            filtered = [
                t for t in converted
                if not any(lt in (t.name or "").lower() or lt in (t.title or "").lower() or lt in t.id.lower() for lt in lower_terms)
            ]
            if filtered:
                converted = filtered
            else:
                logger.warning("All tracks excluded by terms %s; using full candidate pool", exclude_terms)

        # Apply mood filter if present
        if mood_filter:
            mf = mood_filter.lower()
            filtered = [
                t for t in converted
                if mf in (t.name or "").lower() or mf in (t.title or "").lower() or mf in t.id.lower()
            ]
            if filtered:
                converted = filtered

        unique = {track.id: track for track in converted if track.id}

        if not unique:
            raise LookupError("NO_ELIGIBLE_TRACKS: No candidate tracks with valid identifiers")

        tracks = list(unique.values())

        # Exclude currently playing track if alternative exists
        alternatives = [track for track in tracks if track.id != current_track_id]
        pool = alternatives or tracks

        # Prioritize tracks not in recent playback history
        fresh = [track for track in pool if track.id not in self.recent]

        if fresh:
            chosen = self.rng.choice(fresh)
            logger.debug("DiverseTrackSelector picked fresh candidate: '%s' (%s)", chosen.name, chosen.id)
            return chosen.id if is_str_list else chosen

        # All alternatives have been played recently. Relax history oldest-first.
        for old_id in self.recent:
            eligible = [track for track in pool if track.id == old_id]
            if eligible:
                chosen = self.rng.choice(eligible)
                logger.debug("DiverseTrackSelector relaxed oldest-first candidate: '%s' (%s)", chosen.name, chosen.id)
                return chosen.id if is_str_list else chosen

        chosen = self.rng.choice(pool)
        return chosen.id if is_str_list else chosen

    select_track = select

    def record_played(self, track: str | MusicTrack) -> None:
        """Record played track in recent history."""
        track_id = track.id if isinstance(track, MusicTrack) else str(track)
        self.record_verified_playback(track_id)

    def record_verified_playback(self, track_id: str) -> None:
        """Record verified playback of track to prevent immediate repetition."""
        if not track_id:
            return
        if track_id in self.recent:
            self.recent.remove(track_id)
        self.recent.append(track_id)
        logger.debug("Recorded track '%s' in recent history (depth=%d)", track_id, len(self.recent))

    def clear_history(self) -> None:
        """Clear playback history."""
        self.recent.clear()
