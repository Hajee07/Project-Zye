"""
Page Snapshot Formatter — Day 24.
Packages cleaned DOM content, metadata, and structural headers into a standardized AI-ready snapshot.
"""

from __future__ import annotations

import datetime
from typing import List, Optional
from zye_browser.models import DOMPageSnapshot


class PageSnapshotFormatter:
    """Formats page content and structural metadata into standardized DOMPageSnapshot objects."""

    @classmethod
    def create_snapshot(
        cls,
        url: str,
        title: str,
        cleaned_text: str,
        headings: Optional[List[str]] = None,
        interactive_count: int = 0,
        links_count: int = 0,
        is_truncated: bool = False,
    ) -> DOMPageSnapshot:
        """Construct DOMPageSnapshot model."""
        return DOMPageSnapshot(
            url=url,
            title=title,
            extracted_at=datetime.datetime.now().isoformat(),
            character_count=len(cleaned_text),
            truncated=is_truncated,
            headings=headings or [],
            content_text=cleaned_text,
            interactive_elements_count=interactive_count,
            links_count=links_count,
        )

    @classmethod
    def to_formatted_text(cls, snapshot: DOMPageSnapshot) -> str:
        """Generate human and AI-readable text representation."""
        headings_str = " | ".join(snapshot.headings[:10]) if snapshot.headings else "None"
        header = [
            "=== ZYE WEB INTELLIGENCE SNAPSHOT ===",
            f"URL: {snapshot.url}",
            f"TITLE: {snapshot.title}",
            f"TIMESTAMP: {snapshot.extracted_at}",
            f"HEADINGS: {headings_str}",
            f"INTERACTIVE ELEMENTS: {snapshot.interactive_elements_count} | LINKS: {snapshot.links_count}",
            "=====================================",
            "",
            snapshot.content_text,
        ]
        return "\n".join(header)
