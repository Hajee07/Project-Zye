"""
DOM Inspection and Query Engine — Day 24.
Queries headings, interactive elements, tables, and structured elements from the active document.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

from zye_browser.browser_session_manager import BrowserSessionManager

logger = logging.getLogger("ZyeDOMInspector")


class DOMInspector:
    """Inspects visible elements and structured data within the active web page."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def get_headings(self) -> List[Dict[str, str]]:
        """Extract all visible H1, H2, and H3 headings in document order."""
        page = await self.session_manager.get_active_page()
        headings = await page.evaluate(
            """() => {
                const results = [];
                const tags = document.querySelectorAll('h1, h2, h3');
                tags.forEach(h => {
                    const text = h.innerText.trim();
                    if (text && h.offsetParent !== null) {
                        results.push({ tag: h.tagName.toLowerCase(), text: text });
                    }
                });
                return results;
            }"""
        )
        return headings

    async def get_links(self, max_links: int = 50) -> List[Dict[str, str]]:
        """Extract visible links with text and valid hrefs."""
        page = await self.session_manager.get_active_page()
        links = await page.evaluate(
            """(limit) => {
                const results = [];
                const anchors = document.querySelectorAll('a[href]');
                for (let i = 0; i < anchors.length && results.length < limit; i++) {
                    const a = anchors[i];
                    const text = a.innerText.trim();
                    const href = a.href;
                    if (text && href && !href.startsWith('javascript:') && a.offsetParent !== null) {
                        results.push({ text: text, href: href });
                    }
                }
                return results;
            }""",
            max_links,
        )
        return links

    async def get_interactive_elements(self, max_elements: int = 40) -> List[Dict[str, Any]]:
        """List visible buttons, inputs, and clickable elements."""
        page = await self.session_manager.get_active_page()
        elements = await page.evaluate(
            """(limit) => {
                const results = [];
                const items = document.querySelectorAll('button, input, textarea, select, [role="button"]');
                for (let i = 0; i < items.length && results.length < limit; i++) {
                    const el = items[i];
                    if (el.offsetParent !== null) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || null,
                            name: el.name || null,
                            id: el.id || null,
                            aria_label: el.getAttribute('aria-label') || null,
                            text: el.innerText ? el.innerText.trim().substring(0, 50) : null,
                            placeholder: el.placeholder || null
                        });
                    }
                }
                return results;
            }""",
            max_elements,
        )
        return elements

    async def extract_tables(self) -> List[List[List[str]]]:
        """Extract visible HTML table data as 2D arrays."""
        page = await self.session_manager.get_active_page()
        tables = await page.evaluate(
            """() => {
                const tablesData = [];
                const tableElems = document.querySelectorAll('table');
                tableElems.forEach(table => {
                    const rows = [];
                    table.querySelectorAll('tr').forEach(tr => {
                        const row = [];
                        tr.querySelectorAll('th, td').forEach(cell => {
                            row.push(cell.innerText.trim());
                        });
                        if (row.length > 0) rows.push(row);
                    });
                    if (rows.length > 0) tablesData.push(rows);
                });
                return tablesData;
            }"""
        )
        return tables
