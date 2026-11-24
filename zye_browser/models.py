"""
Pydantic Data Models for Zye Browser Intelligence & Profile Management — Day 24.
Comprehensive schemas for profiles, tabs, sessions, web apps, DOM snapshots, and summaries.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BrowserProfileMetadata(BaseModel):
    """Metadata describing a Zye-managed or discovered persistent browser profile."""

    profile_id: str = Field(..., description="Unique profile identifier (e.g. personal, work, profile_1)")
    display_name: str = Field(..., description="User-friendly display name (e.g. Personal Gmail, Office Work)")
    email: Optional[str] = Field(None, description="Primary email account associated with profile if known")
    account_type: str = Field("google", description="Account category: google, work, personal, custom")
    user_data_dir: str = Field(..., description="Absolute path to persistent profile user data directory")
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    last_used_at: Optional[str] = Field(None, description="ISO timestamp of last launch")
    is_active: bool = Field(False, description="Whether this profile is currently running in a Playwright session")
    is_locked: bool = Field(False, description="Whether this profile directory has an active lockfile/process")
    aliases: List[str] = Field(default_factory=list, description="English aliases (e.g. ['office', 'job', 'corp'])")
    tamil_aliases: List[str] = Field(default_factory=list, description="Tamil/Tanglish aliases (e.g. ['வேலை', 'ஆபீஸ்', 'officela'])")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    notes: Optional[str] = Field(None, description="Optional notes or description")


class DiscoveredChromeProfile(BaseModel):
    """Metadata extracted safely from host Chrome's Local State file without reading credentials."""

    chrome_profile_dir: str = Field(..., description="Directory name under Chrome User Data (e.g. Default, Profile 13)")
    name: str = Field(..., description="Profile name stored in Chrome preferences")
    email: Optional[str] = Field(None, description="Email associated with Chrome sync if present")
    gaia_name: Optional[str] = Field(None, description="Google Account display name if present")
    avatar_icon: Optional[str] = Field(None, description="Chrome avatar icon identifier")
    is_ephemeral: bool = Field(False, description="Whether Chrome marks profile as ephemeral")
    raw_data_path: Optional[str] = Field(None, description="Path to Chrome profile folder")


class BrowserAccountSelection(BaseModel):
    """Result of an account disambiguation / resolution request."""

    matched: bool = Field(..., description="True if a single unique profile was resolved")
    profile: Optional[BrowserProfileMetadata] = Field(None, description="Matched profile if matched=True")
    candidates: List[BrowserProfileMetadata] = Field(default_factory=list, description="Candidate profiles if ambiguous")
    match_strategy: str = Field("none", description="Strategy used: exact_id, email, alias, tamil_alias, fuzzy, interactive")
    confidence: float = Field(1.0, description="Match confidence score (0.0 to 1.0)")
    selection_prompt: Optional[str] = Field(None, description="Bilingual disambiguation prompt in Tamil and English if ambiguous")


class BrowserTabMetadata(BaseModel):
    """Metadata describing an open browser tab."""

    tab_id: int = Field(..., description="Zero-based or unique tab index")
    url: str = Field(..., description="Current URL of the tab")
    title: str = Field(..., description="Current document title")
    is_active: bool = Field(False, description="True if tab is the active foreground page")
    loading_status: str = Field("complete", description="Page load state: loading, domcontentloaded, complete")
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


class BrowserSessionStatus(BaseModel):
    """Runtime status of the Zye browser automation session."""

    is_running: bool = Field(False, description="Whether browser context is currently open")
    active_profile_id: Optional[str] = Field(None, description="ID of currently active profile")
    active_profile_name: Optional[str] = Field(None, description="Display name of active profile")
    chrome_version: Optional[str] = Field(None, description="Reported Chrome/Chromium version")
    headless: bool = Field(False, description="Whether browser is running headless")
    tabs_count: int = Field(0, description="Number of currently open tabs")
    active_tab: Optional[BrowserTabMetadata] = Field(None, description="Currently focused tab")
    user_data_dir: Optional[str] = Field(None, description="Directory path of active session")
    uptime_seconds: float = Field(0.0, description="Session elapsed time in seconds")
    last_activity_at: Optional[str] = Field(None, description="ISO timestamp of last browser interaction")


class GmailEmailSummary(BaseModel):
    """Summary of an email thread extracted from Gmail web view."""

    thread_id: str = Field(..., description="Unique thread or DOM identifier")
    message_id: Optional[str] = Field(None, description="Message ID if extractable")
    sender: str = Field(..., description="Sender name or email snippet")
    subject: str = Field(..., description="Email subject line")
    date_snippet: str = Field(..., description="Visible date snippet (e.g. 10:45 AM, Nov 20)")
    snippet: str = Field(..., description="Visible body preview snippet")
    is_unread: bool = Field(False, description="True if thread is marked unread")
    is_starred: bool = Field(False, description="True if thread is starred")
    has_attachments: bool = Field(False, description="True if attachment icon is present")
    labels: List[str] = Field(default_factory=list, description="Applied labels (e.g. Inbox, Important, Work)")


class GmailEmailDetail(BaseModel):
    """Detailed view of an opened Gmail thread/message."""

    thread_id: str = Field(..., description="Thread identifier")
    subject: str = Field(..., description="Email subject")
    sender: str = Field(..., description="Sender address/name")
    recipients: List[str] = Field(default_factory=list, description="Recipient addresses")
    date: str = Field(..., description="Full date/time string")
    body_text: str = Field(..., description="Extracted visible body text (cleaned and bounded)")
    attachments: List[str] = Field(default_factory=list, description="Attachment file names")
    labels: List[str] = Field(default_factory=list, description="Thread labels")
    message_count: int = Field(1, description="Number of messages in thread")


class GoogleDriveItemMetadata(BaseModel):
    """Metadata describing a file or folder in Google Drive web view."""

    item_id: Optional[str] = Field(None, description="DOM or item identifier")
    name: str = Field(..., description="File or folder display name")
    item_type: str = Field("file", description="file, folder, doc, sheet, slide, pdf, image, other")
    owner: Optional[str] = Field(None, description="Item owner name")
    last_modified: Optional[str] = Field(None, description="Last modified date string")
    file_size: Optional[str] = Field(None, description="File size string if visible")
    url: Optional[str] = Field(None, description="Direct URL or anchor link if visible")
    is_shared: bool = Field(False, description="Whether item is marked shared")


class DOMPageSnapshot(BaseModel):
    """Structured extraction of visible page content within bounds."""

    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Page Title")
    extracted_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    character_count: int = Field(..., description="Number of extracted characters")
    truncated: bool = Field(False, description="True if content exceeded character limit")
    headings: List[str] = Field(default_factory=list, description="H1-H3 headings found on page")
    content_text: str = Field(..., description="Cleaned visible text")
    interactive_elements_count: int = Field(0, description="Count of visible buttons/inputs/links")
    links_count: int = Field(0, description="Count of visible hyperlinks")


class WebSearchResult(BaseModel):
    """Structured result of in-app or web search."""

    query: str = Field(..., description="Search query executed")
    target_app: str = Field(..., description="Target web application or 'web_search'")
    total_results_found: int = Field(0, description="Number of items found")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="List of matched item summaries")
    snapshot_preview: Optional[str] = Field(None, description="Brief preview of search results")


class WebInteractionResult(BaseModel):
    """Result of safe DOM interaction (click, fill, navigate, etc.)."""

    success: bool = Field(..., description="True if action completed without error")
    action: str = Field(..., description="Action name: click, fill, navigate, select, switch_tab, scroll")
    target_selector_or_text: Optional[str] = Field(None, description="Target selector, aria label, or text")
    message: str = Field(..., description="Human-readable result summary")
    url_after_action: Optional[str] = Field(None, description="URL after action execution")
    title_after_action: Optional[str] = Field(None, description="Title after action execution")
    requires_confirmation: bool = Field(False, description="True if blocked pending user confirmation")


class GeminiWebSummary(BaseModel):
    """AI-synthesized structured intelligence from page or thread content."""

    summary: str = Field(..., description="Concise summary in English or requested language")
    key_points: List[str] = Field(default_factory=list, description="Bullet points of key information")
    action_items: List[str] = Field(default_factory=list, description="Action items or next steps identified")
    urgency_level: str = Field("normal", description="low, normal, high, critical")
    due_dates: List[str] = Field(default_factory=list, description="Extracted deadlines or due dates")
    amounts_or_finances: List[str] = Field(default_factory=list, description="Extracted amounts, invoices, costs")
    source_url: Optional[str] = Field(None, description="Source page URL")
    prompt_injection_flagged: bool = Field(False, description="True if content contained potential prompt injections")
