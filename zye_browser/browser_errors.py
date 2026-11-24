"""
Structured Error Taxonomy for Zye Browser Intelligence & Profile Management — Day 24.
Unified exception classes with trace IDs, remediation guidance, and JSON serialization.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


class ZyeBrowserError(Exception):
    """Base exception for all Zye browser and profile automation errors."""

    def __init__(
        self,
        code: str,
        message: str,
        profile_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        retryable: bool = False,
        remediation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.profile_id = profile_id
        self.operation_id = operation_id
        self.retryable = retryable
        self.remediation = remediation or "Inspect browser status and retry the operation."
        self.details = details or {}
        self.trace_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to clean, JSON-serializable structured error dict."""
        res: Dict[str, Any] = {
            "status": "ERROR",
            "error_code": self.code,
            "message": self.message,
            "trace_id": self.trace_id,
            "retryable": self.retryable,
            "remediation": self.remediation,
        }
        if self.profile_id:
            res["profile_id"] = self.profile_id
        if self.operation_id:
            res["operation_id"] = self.operation_id
        if self.details:
            res["details"] = self.details
        return res


# -----------------------------------------------------------------------------
# Profile Management Errors
# -----------------------------------------------------------------------------
class BrowserProfileNotFoundError(ZyeBrowserError):
    def __init__(self, profile_id_or_name: str, remediation: Optional[str] = None) -> None:
        super().__init__(
            code="BROWSER_PROFILE_NOT_FOUND",
            message=f"Browser profile '{profile_id_or_name}' was not found.",
            profile_id=profile_id_or_name,
            remediation=remediation or "Run list_browser_accounts to check registered accounts.",
        )


class BrowserProfileAlreadyExistsError(ZyeBrowserError):
    def __init__(self, profile_id_or_name: str) -> None:
        super().__init__(
            code="BROWSER_PROFILE_ALREADY_EXISTS",
            message=f"Browser profile '{profile_id_or_name}' already exists in registry.",
            profile_id=profile_id_or_name,
            remediation="Select an alternative profile name or use the existing registered profile.",
        )


class BrowserProfileLockedError(ZyeBrowserError):
    def __init__(self, profile_id: str, lock_file: str) -> None:
        super().__init__(
            code="BROWSER_PROFILE_LOCKED",
            message=f"Browser profile '{profile_id}' is locked by another running Chrome process ({lock_file}).",
            profile_id=profile_id,
            retryable=True,
            remediation="Close existing Chrome instances using this profile or switch to another account.",
        )


class BrowserProfilePathInvalidError(ZyeBrowserError):
    def __init__(self, path: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_PROFILE_PATH_INVALID",
            message=f"Profile storage path '{path}' is invalid: {reason}",
            remediation="Ensure profile storage path is inside the authorized Zye profile directory.",
        )


class BrowserProfileMetadataInvalidError(ZyeBrowserError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="BROWSER_PROFILE_METADATA_INVALID",
            message=message,
            remediation="Verify profile metadata schema or regenerate profile configuration.",
        )


class BrowserProfileNotRegisteredError(ZyeBrowserError):
    def __init__(self, profile_name: str) -> None:
        super().__init__(
            code="BROWSER_PROFILE_NOT_REGISTERED",
            message=f"Profile '{profile_name}' is not registered with Zye.",
            remediation="Register the profile using register_browser_account before opening.",
        )


class BrowserAccountAmbiguousError(ZyeBrowserError):
    def __init__(self, query: str, matches: list[str]) -> None:
        super().__init__(
            code="BROWSER_ACCOUNT_AMBIGUOUS",
            message=f"Multiple browser accounts matched query '{query}': {', '.join(matches)}.",
            details={"matches": matches},
            remediation="Specify the exact account name (e.g., 'Work', 'Personal').",
        )


class BrowserAccountSelectionRequiredError(ZyeBrowserError):
    def __init__(self, available_accounts: list[str]) -> None:
        super().__init__(
            code="BROWSER_ACCOUNT_SELECTION_REQUIRED",
            message=f"Multiple browser accounts are available: {', '.join(available_accounts)}. Please select one.",
            details={"available_accounts": available_accounts},
            remediation="Clarify which account to open (e.g., 'Personal' or 'Work').",
        )


class BrowserAccountUnavailableError(ZyeBrowserError):
    def __init__(self, account_name: str) -> None:
        super().__init__(
            code="BROWSER_ACCOUNT_UNAVAILABLE",
            message=f"Browser account '{account_name}' is currently unavailable or disabled.",
            remediation="Enable the account or choose an alternative available profile.",
        )


class BrowserAccountSwitchFailedError(ZyeBrowserError):
    def __init__(self, from_account: str, to_account: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_ACCOUNT_SWITCH_FAILED",
            message=f"Failed to switch browser from '{from_account}' to '{to_account}': {reason}",
            details={"from": from_account, "to": to_account},
            remediation="Close the active session and launch the target account independently.",
        )


# -----------------------------------------------------------------------------
# Browser Runtime & Lifecycle Errors
# -----------------------------------------------------------------------------
class BrowserNotInstalledError(ZyeBrowserError):
    def __init__(self, path: Optional[str] = None) -> None:
        super().__init__(
            code="BROWSER_NOT_INSTALLED",
            message=f"Google Chrome is not installed or reachable at expected paths ({path or 'default'}).",
            remediation="Install Google Chrome Stable on this Windows system.",
        )


class BrowserLaunchFailedError(ZyeBrowserError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            code="BROWSER_LAUNCH_FAILED",
            message=f"Failed to launch Chrome persistent browser context: {reason}",
            remediation="Check permissions, ensure Chrome is not running with conflicting flags.",
        )


class BrowserSessionDisconnectedError(ZyeBrowserError):
    def __init__(self, message: str = "Playwright browser session disconnected unexpectedly.") -> None:
        super().__init__(
            code="BROWSER_SESSION_DISCONNECTED",
            message=message,
            retryable=True,
            remediation="Reconnect or restart the browser session.",
        )


class BrowserContextClosedError(ZyeBrowserError):
    def __init__(self, message: str = "Browser context has been closed.") -> None:
        super().__init__(
            code="BROWSER_CONTEXT_CLOSED",
            message=message,
            remediation="Launch a new browser session.",
        )


class BrowserPageNotFoundError(ZyeBrowserError):
    def __init__(self, message: str = "No active webpage found in the current browser context.") -> None:
        super().__init__(
            code="BROWSER_PAGE_NOT_FOUND",
            message=message,
            remediation="Open a webpage or tab first.",
        )


class BrowserTabNotFoundError(ZyeBrowserError):
    def __init__(self, tab_id_or_index: Any) -> None:
        super().__init__(
            code="BROWSER_TAB_NOT_FOUND",
            message=f"Browser tab '{tab_id_or_index}' was not found.",
            remediation="List open tabs to query valid tab indices.",
        )


class BrowserNavigationFailedError(ZyeBrowserError):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_NAVIGATION_FAILED",
            message=f"Failed to navigate to '{url}': {reason}",
            remediation="Verify network connection and target URL correctness.",
        )


class BrowserNavigationTimeoutError(ZyeBrowserError):
    def __init__(self, url: str, timeout_ms: int) -> None:
        super().__init__(
            code="BROWSER_NAVIGATION_TIMEOUT",
            message=f"Navigation to '{url}' timed out after {timeout_ms}ms.",
            retryable=True,
            remediation="Check server responsiveness or increase navigation_timeout_ms in configs.",
        )


class BrowserUnsupportedURLError(ZyeBrowserError):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_UNSUPPORTED_URL",
            message=f"URL '{url}' is unsupported or disallowed: {reason}",
            remediation="Provide a standard http:// or https:// web destination.",
        )


class BrowserRedirectBlockedError(ZyeBrowserError):
    def __init__(self, original_url: str, redirect_url: str) -> None:
        super().__init__(
            code="BROWSER_REDIRECT_BLOCKED",
            message=f"Navigation from '{original_url}' attempted redirect to blocked target '{redirect_url}'.",
            remediation="Ensure navigation target stays within authorized web domains.",
        )


# -----------------------------------------------------------------------------
# Web Application Errors (Gmail, Google Drive, etc.)
# -----------------------------------------------------------------------------
class WebAppNotRecognizedError(ZyeBrowserError):
    def __init__(self, url: str) -> None:
        super().__init__(
            code="WEB_APP_NOT_RECOGNIZED",
            message=f"Web application at '{url}' is not recognized in web_apps registry.",
            remediation="Use universal web tools or register the web application in configs/web_apps.toml.",
        )


class WebAppNotSupportedError(ZyeBrowserError):
    def __init__(self, app_name: str) -> None:
        super().__init__(
            code="WEB_APP_NOT_SUPPORTED",
            message=f"Operation not supported for web application '{app_name}'.",
        )


class GmailLoginRequiredError(ZyeBrowserError):
    def __init__(self, message: str = "Gmail login is required or session has expired.") -> None:
        super().__init__(
            code="GMAIL_LOGIN_REQUIRED",
            message=message,
            remediation="Sign in to your Google Account manually in the visible browser window.",
        )


class GmailSearchFailedError(ZyeBrowserError):
    def __init__(self, query: str, reason: str) -> None:
        super().__init__(
            code="GMAIL_SEARCH_FAILED",
            message=f"Gmail search for '{query}' failed: {reason}",
            remediation="Verify search syntax or inspect the Gmail search box.",
        )


class GmailMessageNotFoundError(ZyeBrowserError):
    def __init__(self, identifier: str) -> None:
        super().__init__(
            code="GMAIL_MESSAGE_NOT_FOUND",
            message=f"Email message or thread '{identifier}' was not found.",
            remediation="Run search_gmail to find active email threads.",
        )


class DriveLoginRequiredError(ZyeBrowserError):
    def __init__(self, message: str = "Google Drive login is required or session has expired.") -> None:
        super().__init__(
            code="DRIVE_LOGIN_REQUIRED",
            message=message,
            remediation="Sign in to Google Drive in the visible browser window.",
        )


class DriveSearchFailedError(ZyeBrowserError):
    def __init__(self, query: str, reason: str) -> None:
        super().__init__(
            code="DRIVE_SEARCH_FAILED",
            message=f"Google Drive search for '{query}' failed: {reason}",
            remediation="Check search keywords or verify Drive accessibility.",
        )


class DriveFileNotFoundError(ZyeBrowserError):
    def __init__(self, identifier: str) -> None:
        super().__init__(
            code="DRIVE_FILE_NOT_FOUND",
            message=f"Google Drive file or folder '{identifier}' was not found.",
            remediation="Search drive using search_google_drive to locate the file.",
        )


# -----------------------------------------------------------------------------
# DOM & Content Extraction Errors
# -----------------------------------------------------------------------------
class DOMExtractionFailedError(ZyeBrowserError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            code="DOM_EXTRACTION_FAILED",
            message=f"Failed to extract visible DOM text: {reason}",
            remediation="Ensure the webpage has finished rendering and retry.",
        )


class DOMElementNotFoundError(ZyeBrowserError):
    def __init__(self, selector_or_text: str) -> None:
        super().__init__(
            code="DOM_ELEMENT_NOT_FOUND",
            message=f"DOM element matching '{selector_or_text}' was not found on the active page.",
            remediation="Inspect page elements with inspect_current_page to locate visible controls.",
        )


class DOMElementAmbiguousError(ZyeBrowserError):
    def __init__(self, text: str, count: int) -> None:
        super().__init__(
            code="DOM_ELEMENT_AMBIGUOUS",
            message=f"Found {count} interactive elements matching '{text}'. Target is ambiguous.",
            details={"match_count": count, "text": text},
            remediation="Specify a more distinct element label, heading, or role.",
        )


class DOMElementNotVisibleError(ZyeBrowserError):
    def __init__(self, selector_or_text: str) -> None:
        super().__init__(
            code="DOM_ELEMENT_NOT_VISIBLE",
            message=f"Target element '{selector_or_text}' is present in DOM but currently not visible.",
            remediation="Scroll page or trigger container expansion before interacting.",
        )


class DOMElementDisabledError(ZyeBrowserError):
    def __init__(self, selector_or_text: str) -> None:
        super().__init__(
            code="DOM_ELEMENT_DISABLED",
            message=f"Target element '{selector_or_text}' is disabled.",
            remediation="Ensure prerequisites on the web form are satisfied.",
        )


class ContentExtractionLimitReachedError(ZyeBrowserError):
    def __init__(self, length: int, limit: int) -> None:
        super().__init__(
            code="CONTENT_EXTRACTION_LIMIT_REACHED",
            message=f"Visible content length ({length} chars) exceeded maximum limit of {limit} chars.",
            details={"length": length, "limit": limit},
            remediation="Content was safely bounded and truncated; request specific sections or summaries.",
        )


class ContentNotAccessibleError(ZyeBrowserError):
    def __init__(self, target_type: str, reason: str) -> None:
        super().__init__(
            code="CONTENT_NOT_ACCESSIBLE",
            message=f"Document or content inside {target_type} is not accessible through DOM: {reason}",
            remediation="Report limitation accurately; only visible metadata or exportable text can be read.",
        )


# -----------------------------------------------------------------------------
# Security & Privacy Errors
# -----------------------------------------------------------------------------
class BrowserPermissionDeniedError(ZyeBrowserError):
    def __init__(self, action: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_PERMISSION_DENIED",
            message=f"Action '{action}' is denied by Zye browser security policy: {reason}",
            remediation="Day 24 browser actions default to read-only safe inspection.",
        )


class BrowserUnsafeURLError(ZyeBrowserError):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            code="BROWSER_UNSAFE_URL",
            message=f"Blocked unsafe navigation to '{url}': {reason}",
            remediation="javascript:, data:, and file: URLs are strictly disallowed.",
        )


class BrowserUnauthorizedProfileError(ZyeBrowserError):
    def __init__(self, profile_id: str) -> None:
        super().__init__(
            code="BROWSER_UNAUTHORIZED_PROFILE",
            message=f"Access to profile '{profile_id}' is not authorized.",
            remediation="Select an authorized Zye browser account.",
        )


class BrowserPromptInjectionDetectedError(ZyeBrowserError):
    def __init__(self, snippet: str) -> None:
        super().__init__(
            code="BROWSER_PROMPT_INJECTION_DETECTED",
            message=f"Detected prompt injection pattern in webpage content: '{snippet[:60]}...'",
            remediation="Webpage content was isolated as untrusted data and will not override user instructions.",
        )


class BrowserUnsafeInteractionBlockedError(ZyeBrowserError):
    def __init__(self, action: str, element_text: str) -> None:
        super().__init__(
            code="BROWSER_UNSAFE_INTERACTION_BLOCKED",
            message=f"Blocked potentially destructive interaction '{action}' on element '{element_text}'.",
            remediation="Financial, account deletion, and transmission buttons require separate confirmation.",
        )


# General categorized error classes
class BrowserProfileError(ZyeBrowserError):
    """General error relating to persistent browser profile operations."""
    pass


class BrowserSessionError(ZyeBrowserError):
    """General error relating to browser launch, connection, or lifecycle."""
    pass


class BrowserAutomationError(ZyeBrowserError):
    """General error relating to DOM interaction, execution, or tab control."""
    pass


class BrowserNavigationSecurityError(ZyeBrowserError):
    """Error raised when a URL or navigation target violates security policies."""
    def __init__(self, code: str, message: str, blocked_url: Optional[str] = None, remediation: Optional[str] = None) -> None:
        super().__init__(code=code, message=message, remediation=remediation, details={"blocked_url": blocked_url} if blocked_url else None)


def format_browser_error(exc: Exception, context: str = "", profile_id: Optional[str] = None) -> Dict[str, Any]:
    """Helper to convert any exception to structured JSON error response."""
    if isinstance(exc, ZyeBrowserError):
        res = exc.to_dict()
        if context:
            res["context"] = context
        return res

    return {
        "status": "ERROR",
        "error_code": "BROWSER_UNHANDLED_EXCEPTION",
        "message": f"Unexpected browser error in {context or 'operation'}: {str(exc)}",
        "trace_id": str(uuid.uuid4())[:8],
        "retryable": False,
        "remediation": "Check application logs for details.",
    }
