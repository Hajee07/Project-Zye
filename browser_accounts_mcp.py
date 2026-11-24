"""
Universal Multi-Account Chrome Browser Intelligence MCP Server — Day 24.
FastMCP server exposing 39 tools for persistent profile management, Playwright automation,
Gmail & Drive web intelligence, DOM content extraction, and Gemini AI synthesis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

# FastMCP Server initialization with robust fallback
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
        _MCP_AVAILABLE = True
    except ImportError:
        _MCP_AVAILABLE = False

        class FastMCP:  # type: ignore[no-redef]
            def __init__(self, name: str, **kwargs: Any) -> None:
                self.name = name
                self._tools: dict[str, Any] = {}

            def tool(self, *args: Any, **kwargs: Any) -> Any:
                def decorator(func: Any) -> Any:
                    self._tools[func.__name__] = func
                    return func
                if args and callable(args[0]):
                    return decorator(args[0])
                return decorator

            def run(self, transport: str = "stdio") -> None:
                pass

            async def list_tools(self) -> list[Any]:
                class _Stub:
                    def __init__(self, n: str):
                        self.name = n
                return [_Stub(n) for n in self._tools]


# Logging to stderr strictly so MCP stdio communication remains uncorrupted
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("zye.browser.mcp")

mcp = FastMCP("ZyeBrowserAccounts")

# Import all subsystem controllers
from zye_browser import (
    BrowserAuditLogger,
    BrowserHealthChecker,
    BrowserLifecycleController,
    BrowserNavigationController,
    BrowserSessionManager,
    BrowserStateInspector,
    BrowserTabManager,
    DOMContentExtractor,
    DOMInspector,
    GeminiWebBridge,
    GmailAdapter,
    GoogleDriveAdapter,
    ProfileManager,
    UniversalWebAdapter,
    WebAppDetector,
    WebAppRegistry,
    WebAppSearchEngine,
    WebClickEngine,
    WebInteractionEngine,
    WebElementResolver,
    format_browser_error,
)

# Instantiate singleton / primary instances
profile_mgr = ProfileManager()
session_mgr = BrowserSessionManager.get_instance(profile_mgr)
lifecycle_ctrl = BrowserLifecycleController(session_mgr, profile_mgr)
tab_mgr = BrowserTabManager(session_mgr)
nav_ctrl = BrowserNavigationController(session_mgr)
state_inspector = BrowserStateInspector(session_mgr)
app_registry = WebAppRegistry()
app_detector = WebAppDetector(app_registry)
search_engine = WebAppSearchEngine(session_mgr, app_detector)
gmail_adapter = GmailAdapter(session_mgr)
drive_adapter = GoogleDriveAdapter(session_mgr)
universal_web = UniversalWebAdapter(session_mgr)
dom_inspector = DOMInspector(session_mgr)
dom_extractor = DOMContentExtractor(session_mgr, dom_inspector)
elem_resolver = WebElementResolver(session_mgr)
interaction_engine = WebInteractionEngine(session_mgr, elem_resolver)
click_engine = WebClickEngine(session_mgr, elem_resolver)
gemini_bridge = GeminiWebBridge()


# =============================================================================
# 1. PROFILE MANAGEMENT TOOLS
# =============================================================================

@mcp.tool()
def browser_list_profiles() -> str:
    """
    List all persistent browser profiles registered in Zye with active/lock status.
    """
    try:
        profiles = profile_mgr.list_profiles()
        res = {
            "status": "SUCCESS",
            "count": len(profiles),
            "profiles": [p.model_dump() for p in profiles],
        }
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_list_profiles"), indent=2)


@mcp.tool()
def browser_discover_host_profiles() -> str:
    """
    Discover all Google Chrome profiles installed on Windows host via non-sensitive Local State.
    """
    try:
        discovered = profile_mgr.discover_host_profiles()
        res = {
            "status": "SUCCESS",
            "count": len(discovered),
            "discovered_chrome_profiles": [p.model_dump() for p in discovered],
        }
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_discover_host_profiles"), indent=2)


@mcp.tool()
def browser_sync_host_profiles() -> str:
    """
    Auto-import discovered host Google Chrome profiles into Zye's persistent registry.
    """
    try:
        synced = profile_mgr.sync_from_host()
        res = {
            "status": "SUCCESS",
            "imported_count": len(synced),
            "imported_profiles": [p.model_dump() for p in synced],
            "total_registered": len(profile_mgr.list_profiles()),
        }
        BrowserAuditLogger.log_event("SYNC_HOST_PROFILES", details={"imported_count": len(synced)})
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_sync_host_profiles"), indent=2)


@mcp.tool()
def browser_create_profile(
    profile_id: str,
    display_name: str,
    email: Optional[str] = None,
    account_type: str = "google",
    aliases: Optional[List[str]] = None,
    tamil_aliases: Optional[List[str]] = None,
) -> str:
    """
    Register a new persistent browser profile with designated aliases and storage.
    """
    try:
        p = profile_mgr.create_profile(
            profile_id=profile_id,
            display_name=display_name,
            email=email,
            account_type=account_type,
            aliases=aliases,
            tamil_aliases=tamil_aliases,
        )
        BrowserAuditLogger.log_event("CREATE_PROFILE", profile_id=profile_id)
        return json.dumps({"status": "SUCCESS", "profile": p.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_create_profile({profile_id})", profile_id), indent=2)


@mcp.tool()
def browser_get_profile(profile_id: str) -> str:
    """
    Get detailed metadata for a registered browser profile.
    """
    try:
        p = profile_mgr.get_profile(profile_id)
        if not p:
            return json.dumps({"status": "NOT_FOUND", "message": f"Profile '{profile_id}' not found."}, indent=2)
        return json.dumps({"status": "SUCCESS", "profile": p.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_get_profile({profile_id})", profile_id), indent=2)


@mcp.tool()
def browser_update_profile(
    profile_id: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    aliases: Optional[List[str]] = None,
    tamil_aliases: Optional[List[str]] = None,
) -> str:
    """
    Update metadata or aliases for an existing persistent profile.
    """
    try:
        updated = profile_mgr.update_profile(
            profile_id=profile_id,
            display_name=display_name,
            email=email,
            aliases=aliases,
            tamil_aliases=tamil_aliases,
        )
        BrowserAuditLogger.log_event("UPDATE_PROFILE", profile_id=profile_id)
        return json.dumps({"status": "SUCCESS", "profile": updated.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_update_profile({profile_id})", profile_id), indent=2)


@mcp.tool()
def browser_delete_profile(profile_id: str, delete_files: bool = False) -> str:
    """
    Remove a profile from Zye's registry, optionally deleting user data directory.
    """
    try:
        ok = profile_mgr.delete_profile(profile_id, delete_files=delete_files)
        BrowserAuditLogger.log_event("DELETE_PROFILE", profile_id=profile_id, details={"delete_files": delete_files})
        return json.dumps({"status": "SUCCESS" if ok else "NOT_FOUND", "profile_id": profile_id, "deleted": ok}, indent=2)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_delete_profile({profile_id})", profile_id), indent=2)


@mcp.tool()
def browser_resolve_account(query: Optional[str] = None) -> str:
    """
    Resolve account from voice or text input using Tamil, English, and Tanglish disambiguation.
    """
    try:
        selection = profile_mgr.resolve_account(query)
        res = {
            "status": "SUCCESS",
            "matched": selection.matched,
            "match_strategy": selection.match_strategy,
            "confidence": selection.confidence,
            "profile": selection.profile.model_dump() if selection.profile else None,
            "candidates": [c.model_dump() for c in selection.candidates],
            "selection_prompt": selection.selection_prompt,
        }
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_resolve_account({query})"), indent=2)


# =============================================================================
# 2. BROWSER LIFECYCLE & SESSION TOOLS
# =============================================================================

@mcp.tool()
async def browser_launch_session(profile_id: Optional[str] = None, headless: bool = False) -> str:
    """
    Launch Chrome persistent browser session for the specified or resolved profile.
    """
    try:
        status = await lifecycle_ctrl.start(account_query=profile_id, headless=headless)
        BrowserAuditLogger.log_event("LAUNCH_SESSION", profile_id=status.active_profile_id, details={"headless": headless})
        return json.dumps({"status": "SUCCESS", "session": status.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_launch_session", profile_id), indent=2)


@mcp.tool()
async def browser_close_session() -> str:
    """
    Cleanly close the active browser context and release profile lock.
    """
    try:
        active_id = session_mgr._active_profile_id
        res = await lifecycle_ctrl.stop()
        BrowserAuditLogger.log_event("CLOSE_SESSION", profile_id=active_id)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_close_session"), indent=2)


@mcp.tool()
async def browser_restart_session(headless: Optional[bool] = None) -> str:
    """
    Restart the currently running browser session.
    """
    try:
        status = await lifecycle_ctrl.restart(headless=headless)
        BrowserAuditLogger.log_event("RESTART_SESSION", profile_id=status.active_profile_id)
        return json.dumps({"status": "SUCCESS", "session": status.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_restart_session"), indent=2)


@mcp.tool()
async def browser_switch_profile(account_query: str, headless: bool = False) -> str:
    """
    Switch active browser context to another profile, resolving names or Tamil aliases.
    """
    try:
        status = await lifecycle_ctrl.switch_profile(new_account_query=account_query, headless=headless)
        BrowserAuditLogger.log_event("SWITCH_PROFILE", profile_id=status.active_profile_id, details={"query": account_query})
        return json.dumps({"status": "SUCCESS", "session": status.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_switch_profile({account_query})"), indent=2)


@mcp.tool()
def browser_get_session_status() -> str:
    """
    Get current runtime status, uptime, active profile, and tab counts.
    """
    try:
        status = session_mgr.get_status()
        return json.dumps({"status": "SUCCESS", "session": status.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_get_session_status"), indent=2)


@mcp.tool()
async def browser_inspect_state() -> str:
    """
    Inspect active page readyState, DOM metrics, login gate detection, and current app type.
    """
    try:
        data = await state_inspector.inspect_state()
        return json.dumps({"status": "SUCCESS", "state": data}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_inspect_state"), indent=2)


# =============================================================================
# 3. TAB MANAGEMENT TOOLS
# =============================================================================

@mcp.tool()
async def browser_list_tabs() -> str:
    """
    List all open browser tabs in the active persistent context.
    """
    try:
        tabs = await tab_mgr.list_tabs()
        res = {
            "status": "SUCCESS",
            "count": len(tabs),
            "tabs": [t.model_dump() for t in tabs],
        }
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_list_tabs"), indent=2)


@mcp.tool()
async def browser_new_tab(url: Optional[str] = None) -> str:
    """
    Open a new browser tab and optionally navigate to target URL.
    """
    try:
        tab = await tab_mgr.new_tab(url=url)
        BrowserAuditLogger.log_event("NEW_TAB", url=url, details={"tab_id": tab.tab_id})
        return json.dumps({"status": "SUCCESS", "tab": tab.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_new_tab({url})"), indent=2)


@mcp.tool()
async def browser_switch_tab(tab_id: int) -> str:
    """
    Switch active focus to the specified tab index.
    """
    try:
        tab = await tab_mgr.switch_tab(tab_id)
        return json.dumps({"status": "SUCCESS", "active_tab": tab.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_switch_tab({tab_id})"), indent=2)


@mcp.tool()
async def browser_close_tab(tab_id: Optional[int] = None) -> str:
    """
    Close the specified tab index or currently focused tab.
    """
    try:
        res = await tab_mgr.close_tab(tab_id)
        BrowserAuditLogger.log_event("CLOSE_TAB", details={"tab_id": tab_id})
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_close_tab({tab_id})"), indent=2)


# =============================================================================
# 4. NAVIGATION & WEB APPS TOOLS
# =============================================================================

@mcp.tool()
async def browser_navigate(url: str) -> str:
    """
    Navigate active tab to a sanitized URL, enforcing security and protocol validation.
    """
    try:
        res = await nav_ctrl.navigate(url)
        BrowserAuditLogger.log_event("NAVIGATE", url=url, details=res)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        BrowserAuditLogger.log_event("NAVIGATE_FAILED", url=url, status="FAILED", error=str(exc))
        return json.dumps(format_browser_error(exc, f"browser_navigate({url})"), indent=2)


@mcp.tool()
async def browser_open_app(app_name: str, query: Optional[str] = None) -> str:
    """
    Open supported Google service (gmail, drive, youtube, calendar, search) or generic app.
    """
    try:
        res = await nav_ctrl.open_app(app_name, query=query)
        BrowserAuditLogger.log_event("OPEN_APP", details={"app": app_name, "query": query})
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_open_app({app_name})"), indent=2)


@mcp.tool()
async def browser_go_back() -> str:
    """
    Navigate back one step in browser history.
    """
    try:
        res = await nav_ctrl.go_back()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_go_back"), indent=2)


@mcp.tool()
async def browser_go_forward() -> str:
    """
    Navigate forward one step in browser history.
    """
    try:
        res = await nav_ctrl.go_forward()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_go_forward"), indent=2)


@mcp.tool()
async def browser_reload() -> str:
    """
    Reload the currently active page.
    """
    try:
        res = await nav_ctrl.reload()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_reload"), indent=2)


@mcp.tool()
async def browser_search(query: str, app_override: Optional[str] = None) -> str:
    """
    Execute an in-app search on the active page (Gmail, Drive, YouTube, Google Search, or generic search input).
    """
    try:
        res = await search_engine.search(query, app_override=app_override)
        BrowserAuditLogger.log_event("WEB_APP_SEARCH", details={"query": query, "app": app_override})
        return json.dumps({"status": "SUCCESS", "search_result": res.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_search({query})"), indent=2)


# =============================================================================
# 5. GMAIL & DRIVE WEB INTELLIGENCE TOOLS
# =============================================================================

@mcp.tool()
async def browser_gmail_list_threads(max_results: int = 10, label: Optional[str] = None) -> str:
    """
    Read-only extraction of visible Gmail threads (sender, subject, snippet, unread state).
    """
    try:
        threads = await gmail_adapter.list_threads(max_results=max_results, label=label)
        BrowserAuditLogger.log_event("GMAIL_LIST_THREADS", details={"count": len(threads), "label": label})
        return json.dumps({
            "status": "SUCCESS",
            "count": len(threads),
            "threads": [t.model_dump() for t in threads],
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_gmail_list_threads"), indent=2)


@mcp.tool()
async def browser_gmail_read_thread(index: int) -> str:
    """
    Read detailed visible content of a specific Gmail thread by index.
    """
    try:
        detail = await gmail_adapter.open_thread_by_index(index=index)
        BrowserAuditLogger.log_event("GMAIL_READ_THREAD", details={"index": index, "subject": detail.subject})
        return json.dumps({"status": "SUCCESS", "thread_detail": detail.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_gmail_read_thread({index})"), indent=2)


@mcp.tool()
async def browser_gmail_search(query: str, max_results: int = 10) -> str:
    """
    Search Gmail emails and return matching thread summaries.
    """
    try:
        threads = await gmail_adapter.search_and_list(query=query, max_results=max_results)
        BrowserAuditLogger.log_event("GMAIL_SEARCH", details={"query": query, "count": len(threads)})
        return json.dumps({
            "status": "SUCCESS",
            "query": query,
            "count": len(threads),
            "threads": [t.model_dump() for t in threads],
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_gmail_search({query})"), indent=2)


@mcp.tool()
async def browser_drive_list_items(max_results: int = 15) -> str:
    """
    Read-only extraction of visible Google Drive files and folders.
    """
    try:
        items = await drive_adapter.list_items(max_results=max_results)
        BrowserAuditLogger.log_event("DRIVE_LIST_ITEMS", details={"count": len(items)})
        return json.dumps({
            "status": "SUCCESS",
            "count": len(items),
            "items": [it.model_dump() for it in items],
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_drive_list_items"), indent=2)


@mcp.tool()
async def browser_drive_search(query: str, max_results: int = 15) -> str:
    """
    Search Google Drive files and return matching items.
    """
    try:
        items = await drive_adapter.search_and_list(query=query, max_results=max_results)
        BrowserAuditLogger.log_event("DRIVE_SEARCH", details={"query": query, "count": len(items)})
        return json.dumps({
            "status": "SUCCESS",
            "query": query,
            "count": len(items),
            "items": [it.model_dump() for it in items],
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_drive_search({query})"), indent=2)


# =============================================================================
# 6. DOM EXTRACTION, INSPECTION & FILTERING TOOLS
# =============================================================================

@mcp.tool()
async def browser_extract_page_snapshot(
    max_chars: int = 12000,
    filter_criteria: Optional[str] = None,
) -> str:
    """
    Extract clean, structured visible text snapshot with prompt injection defenses (bounded to max_chars).
    """
    try:
        snapshot = await dom_extractor.extract_page_snapshot(max_chars=max_chars, filter_criteria=filter_criteria)
        return json.dumps({"status": "SUCCESS", "snapshot": snapshot.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_extract_page_snapshot"), indent=2)


@mcp.tool()
async def browser_inspect_dom() -> str:
    """
    Inspect active page headings, links, interactive buttons, inputs, and tables.
    """
    try:
        headings = await dom_inspector.get_headings()
        links = await dom_inspector.get_links(max_links=30)
        interactive = await dom_inspector.get_interactive_elements(max_elements=30)
        tables = await dom_inspector.extract_tables()

        res = {
            "status": "SUCCESS",
            "headings": headings,
            "links_sample": links,
            "interactive_elements": interactive,
            "tables_count": len(tables),
            "tables_sample": tables[:2] if tables else [],
        }
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_inspect_dom"), indent=2)


@mcp.tool()
async def browser_filter_content(criteria: str, keywords: Optional[List[str]] = None) -> str:
    """
    Filter active page text by specific criteria: 'urgent', 'action_items', 'invoices', or 'keywords'.
    """
    try:
        snapshot = await dom_extractor.extract_page_snapshot(max_chars=15000, filter_criteria=criteria, keywords=keywords)
        return json.dumps({
            "status": "SUCCESS",
            "criteria": criteria,
            "filtered_content": snapshot.content_text,
            "character_count": snapshot.character_count,
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_filter_content({criteria})"), indent=2)


# =============================================================================
# 7. INTERACTION & AI SYNTHESIS TOOLS
# =============================================================================

@mcp.tool()
async def browser_click(
    selector_or_text: str,
    role: Optional[str] = None,
    confirmed: bool = False,
) -> str:
    """
    Safely click a DOM element. Blocks destructive financial/deletion actions unless confirmed=True.
    """
    try:
        res = await click_engine.click(
            selector_or_text=selector_or_text,
            role=role,
            confirmed=confirmed,
        )
        BrowserAuditLogger.log_event("CLICK", details={"target": selector_or_text, "confirmed": confirmed, "res": res.model_dump()})
        return json.dumps(res.model_dump(), indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_click({selector_or_text})"), indent=2)


@mcp.tool()
async def browser_type(
    selector_or_text: str,
    text: str,
    press_enter: bool = False,
) -> str:
    """
    Type text into an input or textarea element on the active page.
    """
    try:
        res = await interaction_engine.type_text(
            selector_or_text=selector_or_text,
            text=text,
            press_enter=press_enter,
        )
        BrowserAuditLogger.log_event("TYPE", details={"target": selector_or_text, "length": len(text), "press_enter": press_enter})
        return json.dumps(res.model_dump(), indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_type({selector_or_text})"), indent=2)


@mcp.tool()
async def browser_scroll(direction: str = "down", amount: int = 500) -> str:
    """
    Smoothly scroll the active browser page up or down by specified pixel amount.
    """
    try:
        res = await interaction_engine.scroll(direction=direction, amount=amount)
        return json.dumps(res.model_dump(), indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_scroll({direction})"), indent=2)


@mcp.tool()
async def browser_press_key(key: str) -> str:
    """
    Send a keyboard key press (e.g. 'Enter', 'Escape', 'Tab', 'ArrowDown').
    """
    try:
        res = await interaction_engine.press_key(key=key)
        return json.dumps(res.model_dump(), indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_press_key({key})"), indent=2)


@mcp.tool()
async def browser_summarize_page(language: str = "en") -> str:
    """
    Generate an AI structured summary of the active webpage using Central Gemini Gateway.
    """
    try:
        snapshot = await dom_extractor.extract_page_snapshot(max_chars=12000)
        summary = await gemini_bridge.summarize_page(
            url=snapshot.url,
            title=snapshot.title,
            content_text=snapshot.content_text,
            language=language,
        )
        BrowserAuditLogger.log_event("SUMMARIZE_PAGE", url=snapshot.url)
        return json.dumps({"status": "SUCCESS", "summary": summary.model_dump()}, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_summarize_page"), indent=2)


@mcp.tool()
async def browser_ask_page(question: str) -> str:
    """
    Ask a natural language question about the active webpage content to Gemini AI.
    """
    try:
        snapshot = await dom_extractor.extract_page_snapshot(max_chars=12000)
        answer = await gemini_bridge.ask_about_page(
            question=question,
            url=snapshot.url,
            title=snapshot.title,
            content_text=snapshot.content_text,
        )
        return json.dumps({
            "status": "SUCCESS",
            "question": question,
            "answer": answer,
            "source_url": snapshot.url,
        }, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, f"browser_ask_page({question})"), indent=2)


@mcp.tool()
def browser_check_health() -> str:
    """
    Run complete Day 24 diagnostic health check suite (Playwright, Chrome, profiles, configs).
    """
    try:
        res = BrowserHealthChecker.check_all()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(format_browser_error(exc, "browser_check_health"), indent=2)


if __name__ == "__main__":
    logger.info("Starting Zye Browser Accounts & Intelligence MCP Server over stdio...")
    mcp.run(transport="stdio")
