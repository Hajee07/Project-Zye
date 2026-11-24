"""
Google Drive Web Intelligence Adapter — Day 24.
Read-only extraction of Google Drive files, folders, search results, and metadata.
Zero file deletion, zero unauthorized document alterations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError, DriveLoginRequiredError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import GoogleDriveItemMetadata

logger = logging.getLogger("ZyeDriveAdapter")


class GoogleDriveAdapter:
    """Safe read-only adapter for interacting with Google Drive web interface."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def ensure_drive_view(self, page: Page) -> None:
        """Verify page is in Google Drive and user is authenticated."""
        url = page.url
        if "accounts.google.com/signin" in url or "accounts.google.com/ServiceLogin" in url:
            profile_id = self.session_manager._active_profile_id or "unknown"
            raise DriveLoginRequiredError(
                code="ERR_DRIVE_LOGIN_REQUIRED",
                message="Google Drive requires user authentication for this profile.",
                profile_id=profile_id,
                remediation="Log in to Google Drive in the opened browser window once to establish your session.",
            )

        if "drive.google.com" not in url:
            await page.goto("https://drive.google.com/drive/my-drive", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            if "accounts.google.com" in page.url:
                profile_id = self.session_manager._active_profile_id or "unknown"
                raise DriveLoginRequiredError(
                    code="ERR_DRIVE_LOGIN_REQUIRED",
                    message="Google Drive redirected to sign-in page. Please complete login in Chrome.",
                    profile_id=profile_id,
                )

    async def list_items(self, max_results: int = 15) -> List[GoogleDriveItemMetadata]:
        """List visible files and folders from Google Drive view."""
        page = await self.session_manager.get_active_page()
        await self.ensure_drive_view(page)

        try:
            items_raw: List[Dict[str, Any]] = await page.evaluate(
                """(limit) => {
                    const rows = document.querySelectorAll('div[role="row"], tr[role="row"], c-wiz[data-item-id]');
                    const results = [];
                    for (let i = 0; i < Math.min(rows.length, limit); i++) {
                        const row = rows[i];
                        const text = row.innerText.trim();
                        if (!text) continue;
                        
                        // Try finding item name element
                        const nameElem = row.querySelector('[data-target="doc-name"], div[data-column-type="NAME"]') || row.querySelector('div[aria-label]');
                        const name = nameElem ? (nameElem.getAttribute('aria-label') || nameElem.innerText.trim()) : text.split('\\n')[0];
                        
                        let itemType = 'file';
                        const lowerName = name.toLowerCase();
                        if (lowerName.includes('folder') || row.querySelector('svg[aria-label*="folder" i]')) {
                            itemType = 'folder';
                        } else if (lowerName.endsWith('.pdf')) {
                            itemType = 'pdf';
                        } else if (lowerName.endsWith('.xlsx') || lowerName.endsWith('.csv') || lowerName.includes('sheet')) {
                            itemType = 'sheet';
                        } else if (lowerName.endsWith('.docx') || lowerName.includes('doc')) {
                            itemType = 'doc';
                        } else if (lowerName.endsWith('.pptx') || lowerName.includes('presentation')) {
                            itemType = 'slide';
                        }
                        
                        results.push({
                            item_id: 'item_' + i,
                            name: name,
                            item_type: itemType,
                            owner: 'Me',
                            last_modified: '',
                            file_size: '',
                            url: window.location.href,
                            is_shared: false
                        });
                    }
                    return results;
                }""",
                max_results,
            )

            return [
                GoogleDriveItemMetadata(
                    item_id=it.get("item_id"),
                    name=it.get("name", "Unnamed Item"),
                    item_type=it.get("item_type", "file"),
                    owner=it.get("owner"),
                    last_modified=it.get("last_modified"),
                    file_size=it.get("file_size"),
                    url=it.get("url"),
                    is_shared=it.get("is_shared", False),
                )
                for it in items_raw
            ]

        except Exception as exc:
            logger.warning("Error evaluating Drive DOM elements: %s", exc)
            return []

    async def search_and_list(self, query: str, max_results: int = 15) -> List[GoogleDriveItemMetadata]:
        """Search Google Drive by query and return matching items."""
        page = await self.session_manager.get_active_page()
        await self.ensure_drive_view(page)

        search_url = f"https://drive.google.com/drive/search?q={quote_plus(query)}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        return await self.list_items(max_results=max_results)
