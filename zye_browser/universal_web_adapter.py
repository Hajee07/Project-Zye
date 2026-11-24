"""
Universal Web Adapter — Day 24.
Generic website interaction, main article extraction, and navigation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

from zye_browser.browser_session_manager import BrowserSessionManager

logger = logging.getLogger("ZyeUniversalWebAdapter")


class UniversalWebAdapter:
    """Handles arbitrary web pages, extracting article content and structural elements."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def get_main_content(self) -> Dict[str, Any]:
        """Extract primary article or content text from the active page."""
        page = await self.session_manager.get_active_page()

        data = await page.evaluate(
            """() => {
                // Try finding common article/main containers
                const mainSelectors = ['article', 'main', '#content', '.content', '.main-content', '#main'];
                let mainElem = null;
                for (const sel of mainSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 100) {
                        mainElem = el;
                        break;
                    }
                }
                
                const target = mainElem || document.body;
                
                // Headings
                const headings = Array.from(target.querySelectorAll('h1, h2, h3'))
                    .map(h => h.innerText.trim())
                    .filter(t => t.length > 0);
                    
                // Clean visible text
                const text = target.innerText.trim();
                
                return {
                    url: window.location.href,
                    title: document.title,
                    headings: headings.slice(0, 15),
                    text: text.substring(0, 15000),
                    char_count: text.length
                };
            }"""
        )

        return data
