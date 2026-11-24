"""
Zye Browser Intelligence & Persistent Profile Automation Package — Day 24.
Universal multi-account browser automation, Gmail & Drive extraction, DOM inspection, and Gemini AI synthesis.
"""

from __future__ import annotations

from zye_browser.browser_errors import (
    BrowserAccountAmbiguousError,
    BrowserAccountSelectionRequiredError,
    BrowserAutomationError,
    BrowserNavigationSecurityError,
    BrowserProfileError,
    BrowserProfileLockedError,
    BrowserProfileNotFoundError,
    BrowserPromptInjectionDetectedError,
    BrowserSessionError,
    DOMElementAmbiguousError,
    DOMElementNotFoundError,
    DriveLoginRequiredError,
    GmailLoginRequiredError,
    ZyeBrowserError,
    format_browser_error,
)
from zye_browser.models import (
    BrowserAccountSelection,
    BrowserProfileMetadata,
    BrowserSessionStatus,
    BrowserTabMetadata,
    DiscoveredChromeProfile,
    DOMPageSnapshot,
    GeminiWebSummary,
    GmailEmailDetail,
    GmailEmailSummary,
    GoogleDriveItemMetadata,
    WebInteractionResult,
    WebSearchResult,
)
from zye_browser.profile_path_validator import ProfilePathValidator
from zye_browser.profile_lock_manager import ProfileLockManager
from zye_browser.profile_discovery import ChromeProfileDiscovery
from zye_browser.profile_registry import ProfileRegistry
from zye_browser.profile_manager import ProfileManager
from zye_browser.account_selector import AccountSelector
from zye_browser.browser_url_validator import BrowserURLValidator
from zye_browser.browser_session_manager import BrowserSessionManager
from zye_browser.browser_lifecycle import BrowserLifecycleController
from zye_browser.browser_tab_manager import BrowserTabManager
from zye_browser.browser_navigation import BrowserNavigationController
from zye_browser.browser_state_inspector import BrowserStateInspector
from zye_browser.web_app_registry import WebAppRegistry
from zye_browser.web_app_detector import WebAppDetector
from zye_browser.web_app_search import WebAppSearchEngine
from zye_browser.gmail_adapter import GmailAdapter
from zye_browser.google_drive_adapter import GoogleDriveAdapter
from zye_browser.universal_web_adapter import UniversalWebAdapter
from zye_browser.dom_inspector import DOMInspector
from zye_browser.visible_text_cleaner import VisibleTextCleaner
from zye_browser.content_filter import ContentFilter
from zye_browser.content_chunker import ContentChunker
from zye_browser.page_snapshot import PageSnapshotFormatter
from zye_browser.dom_content_extractor import DOMContentExtractor
from zye_browser.web_element_resolver import WebElementResolver
from zye_browser.web_interaction_engine import WebInteractionEngine
from zye_browser.web_click_engine import WebClickEngine
from zye_browser.gemini_web_bridge import GeminiWebBridge
from zye_browser.browser_audit import BrowserAuditLogger
from zye_browser.browser_health import BrowserHealthChecker

__all__ = [
    # Errors
    "ZyeBrowserError",
    "BrowserProfileError",
    "BrowserProfileNotFoundError",
    "BrowserProfileLockedError",
    "BrowserAccountAmbiguousError",
    "BrowserAccountSelectionRequiredError",
    "BrowserSessionError",
    "BrowserNavigationSecurityError",
    "BrowserAutomationError",
    "GmailLoginRequiredError",
    "DriveLoginRequiredError",
    "DOMElementNotFoundError",
    "DOMElementAmbiguousError",
    "BrowserPromptInjectionDetectedError",
    "format_browser_error",
    # Models
    "BrowserProfileMetadata",
    "DiscoveredChromeProfile",
    "BrowserAccountSelection",
    "BrowserTabMetadata",
    "BrowserSessionStatus",
    "GmailEmailSummary",
    "GmailEmailDetail",
    "GoogleDriveItemMetadata",
    "DOMPageSnapshot",
    "WebSearchResult",
    "WebInteractionResult",
    "GeminiWebSummary",
    # Managers & Controllers
    "ProfilePathValidator",
    "ProfileLockManager",
    "ChromeProfileDiscovery",
    "ProfileRegistry",
    "ProfileManager",
    "AccountSelector",
    "BrowserURLValidator",
    "BrowserSessionManager",
    "BrowserLifecycleController",
    "BrowserTabManager",
    "BrowserNavigationController",
    "BrowserStateInspector",
    "WebAppRegistry",
    "WebAppDetector",
    "WebAppSearchEngine",
    "GmailAdapter",
    "GoogleDriveAdapter",
    "UniversalWebAdapter",
    "DOMInspector",
    "VisibleTextCleaner",
    "ContentFilter",
    "ContentChunker",
    "PageSnapshotFormatter",
    "DOMContentExtractor",
    "WebElementResolver",
    "WebInteractionEngine",
    "WebClickEngine",
    "GeminiWebBridge",
    "BrowserAuditLogger",
    "BrowserHealthChecker",
]
