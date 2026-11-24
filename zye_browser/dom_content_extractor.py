"""
DOM Content Extraction Coordinator — Day 24.
Extracts visible text, applies security filters, detects prompt injections, and returns structured page snapshots.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.content_filter import ContentFilter
from zye_browser.dom_inspector import DOMInspector
from zye_browser.models import DOMPageSnapshot
from zye_browser.page_snapshot import PageSnapshotFormatter
from zye_browser.visible_text_cleaner import VisibleTextCleaner

logger = logging.getLogger("ZyeDOMExtractor")


class DOMContentExtractor:
    """Extracts, cleans, and structures visible DOM content from the active browser page."""

    DEFAULT_MAX_CHARS = 12000

    def __init__(
        self,
        session_manager: Optional[BrowserSessionManager] = None,
        inspector: Optional[DOMInspector] = None,
    ) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()
        self.inspector = inspector or DOMInspector(self.session_manager)

    async def extract_page_snapshot(
        self,
        max_chars: int = DEFAULT_MAX_CHARS,
        filter_criteria: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> DOMPageSnapshot:
        """
        Extract visible text and structure from active browser tab.
        Applies cleaning, injection neutralizing, character boundaries, and optional filtering.
        """
        page = await self.session_manager.get_active_page()
        url = page.url
        title = await page.title()

        # 1. Gather headings and metrics
        headings_raw = await self.inspector.get_headings()
        headings = [h["text"] for h in headings_raw]

        links = await self.inspector.get_links(max_links=50)
        interactive = await self.inspector.get_interactive_elements(max_elements=30)

        # 2. Extract visible innerText
        raw_text = await page.evaluate(
            """() => {
                // Remove invisible script and style elements from clone before extracting text
                return document.body ? document.body.innerText : '';
            }"""
        )

        # 3. Clean and sanitize
        cleaned_text, flags = VisibleTextCleaner.clean(raw_text, max_chars=max_chars)
        is_truncated = len(raw_text) > max_chars

        if flags > 0:
            logger.warning("DOM Content on '%s' had %d prompt injection signatures neutralized.", url, flags)

        # 4. Apply optional content filtering
        if filter_criteria:
            crit = filter_criteria.lower().strip()
            if "urgent" in crit:
                cleaned_text = ContentFilter.filter_urgent(cleaned_text)
            elif "action" in crit:
                cleaned_text = ContentFilter.filter_action_items(cleaned_text)
            elif "invoice" in crit or "finance" in crit:
                cleaned_text = ContentFilter.filter_finance_and_invoices(cleaned_text)
            elif "keyword" in crit and keywords:
                cleaned_text = ContentFilter.filter_by_keywords(cleaned_text, keywords)

        return PageSnapshotFormatter.create_snapshot(
            url=url,
            title=title,
            cleaned_text=cleaned_text,
            headings=headings,
            interactive_count=len(interactive),
            links_count=len(links),
            is_truncated=is_truncated,
        )
