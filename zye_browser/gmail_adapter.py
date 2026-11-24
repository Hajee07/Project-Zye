"""
Gmail Web Intelligence Adapter — Day 24.
Read-only extraction of Gmail threads, emails, snippets, and headers via DOM inspection.
Zero credential extraction, zero email sending, zero email deletion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from playwright.async_api import Page

from zye_browser.browser_errors import BrowserAutomationError, GmailLoginRequiredError
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.models import GmailEmailDetail, GmailEmailSummary

logger = logging.getLogger("ZyeGmailAdapter")


class GmailAdapter:
    """Safe read-only adapter for interacting with Gmail web interface."""

    def __init__(self, session_manager: Optional[BrowserSessionManager] = None) -> None:
        self.session_manager = session_manager or BrowserSessionManager.get_instance()

    async def ensure_gmail_view(self, page: Page) -> None:
        """Verify page is in Gmail and user is logged in."""
        url = page.url
        if "accounts.google.com/signin" in url or "accounts.google.com/ServiceLogin" in url:
            profile_id = self.session_manager._active_profile_id or "unknown"
            raise GmailLoginRequiredError(
                code="ERR_GMAIL_LOGIN_REQUIRED",
                message="Gmail requires manual user login for this profile.",
                profile_id=profile_id,
                remediation="Log in to your Google Account once in the opened Chrome window. The session will persist automatically.",
            )

        if "mail.google.com" not in url:
            await page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Check again after navigation
            if "accounts.google.com" in page.url:
                profile_id = self.session_manager._active_profile_id or "unknown"
                raise GmailLoginRequiredError(
                    code="ERR_GMAIL_LOGIN_REQUIRED",
                    message="Gmail redirected to sign-in page. Please complete login in the browser window.",
                    profile_id=profile_id,
                )

    async def list_threads(self, max_results: int = 10, label: Optional[str] = None) -> List[GmailEmailSummary]:
        """
        List visible email threads from inbox or specified label.
        Extracts sender, subject, date, snippet, unread state.
        """
        page = await self.session_manager.get_active_page()
        await self.ensure_gmail_view(page)

        if label:
            clean_label = label.strip().lower()
            target_url = f"https://mail.google.com/mail/u/0/#{clean_label}"
            if page.url != target_url:
                await page.goto(target_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

        # Gmail renders email rows in table `table.F.cf.zt tr` or `tr.zA`
        # We extract threads using robust DOM query
        try:
            threads_data: List[Dict[str, Any]] = await page.evaluate(
                """(limit) => {
                    const rows = document.querySelectorAll('tr.zA');
                    const results = [];
                    for (let i = 0; i < Math.min(rows.length, limit); i++) {
                        const row = rows[i];
                        const isUnread = row.classList.contains('zE');
                        
                        // Sender
                        const senderElem = row.querySelector('.yX.xY .yP, .yX.xY .zF') || row.querySelector('.yW span');
                        const sender = senderElem ? senderElem.innerText.trim() : 'Unknown';
                        
                        // Subject & snippet
                        const subjectElem = row.querySelector('.y6 .bog span') || row.querySelector('.y6');
                        const subject = subjectElem ? subjectElem.innerText.trim() : '(No Subject)';
                        
                        const snippetElem = row.querySelector('.y2');
                        const snippet = snippetElem ? snippetElem.innerText.trim().replace(/^[-–—\\s]+/, '') : '';
                        
                        // Date
                        const dateElem = row.querySelector('.xW.xY span, .y5 span');
                        const dateSnippet = dateElem ? (dateElem.getAttribute('title') || dateElem.innerText.trim()) : '';
                        
                        // Starred
                        const starElem = row.querySelector('.apU.xS');
                        const isStarred = starElem ? starElem.getAttribute('aria-label') === 'Starred' : false;
                        
                        // Attachment
                        const attachmentElem = row.querySelector('.brd');
                        const hasAttachments = !!attachmentElem;
                        
                        results.push({
                            thread_id: 'thread_' + i,
                            sender: sender,
                            subject: subject,
                            snippet: snippet,
                            date_snippet: dateSnippet,
                            is_unread: isUnread,
                            is_starred: isStarred,
                            has_attachments: hasAttachments
                        });
                    }
                    return results;
                }""",
                max_results,
            )

            summaries: List[GmailEmailSummary] = [
                GmailEmailSummary(
                    thread_id=t.get("thread_id", f"idx_{idx}"),
                    sender=t.get("sender", "Unknown"),
                    subject=t.get("subject", "(No Subject)"),
                    date_snippet=t.get("date_snippet", ""),
                    snippet=t.get("snippet", ""),
                    is_unread=t.get("is_unread", False),
                    is_starred=t.get("is_starred", False),
                    has_attachments=t.get("has_attachments", False),
                )
                for idx, t in enumerate(threads_data)
            ]

            return summaries

        except Exception as exc:
            logger.warning("Error evaluating Gmail DOM table: %s", exc)
            return []

    async def open_thread_by_index(self, index: int) -> GmailEmailDetail:
        """Click on the nth thread in the list and read its full content."""
        page = await self.session_manager.get_active_page()
        await self.ensure_gmail_view(page)

        row_locator = page.locator("tr.zA").nth(index)
        count = await row_locator.count()
        if count == 0:
            raise BrowserAutomationError(
                code="ERR_GMAIL_THREAD_NOT_FOUND",
                message=f"No email thread found at index {index}.",
            )

        await row_locator.click()
        await page.wait_for_timeout(2000)

        # Extract thread content
        detail = await page.evaluate(
            """() => {
                const subjectElem = document.querySelector('h2.hP');
                const subject = subjectElem ? subjectElem.innerText.trim() : '';
                
                const senderElem = document.querySelector('.gD');
                const sender = senderElem ? (senderElem.getAttribute('email') || senderElem.innerText.trim()) : '';
                
                const dateElem = document.querySelector('.g3');
                const date = dateElem ? (dateElem.getAttribute('title') || dateElem.innerText.trim()) : '';
                
                // Visible body containers
                const bodyElems = document.querySelectorAll('.a3s.aiL, .ii.gt');
                let bodyText = '';
                bodyElems.forEach(el => {
                    bodyText += el.innerText.trim() + '\\n\\n';
                });
                
                // Attachments
                const attachElems = document.querySelectorAll('.aZo .aV3');
                const attachments = [];
                attachElems.forEach(el => {
                    attachments.push(el.innerText.trim());
                });
                
                return {
                    subject: subject,
                    sender: sender,
                    date: date,
                    body_text: bodyText.trim().substring(0, 12000),
                    attachments: attachments
                };
            }"""
        )

        return GmailEmailDetail(
            thread_id=f"thread_{index}",
            subject=detail.get("subject", "(No Subject)"),
            sender=detail.get("sender", "Unknown"),
            recipients=[],
            date=detail.get("date", ""),
            body_text=detail.get("body_text", ""),
            attachments=detail.get("attachments", []),
            labels=[],
            message_count=1,
        )

    async def search_and_list(self, query: str, max_results: int = 10) -> List[GmailEmailSummary]:
        """Search Gmail with query and return matching thread summaries."""
        page = await self.session_manager.get_active_page()
        await self.ensure_gmail_view(page)

        search_url = f"https://mail.google.com/mail/u/0/#search/{quote_plus(query)}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        return await self.list_threads(max_results=max_results)
