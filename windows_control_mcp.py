"""
Zye Windows Application Control MCP Server (Day 16).
Unified FastMCP server exposing 13 core tools for Windows application discovery,
launching, UI Automation tree inspection, named element interaction, text typing,
keyboard hotkeys, and full WhatsApp Desktop automation.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# FastMCP Server initialization
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


# Configure logging: write diagnostic logs strictly to stderr so MCP stdio protocol is not corrupted
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("zye.windows.mcp")

from zye_windows import (
    WindowsAppCatalog,
    WindowsAppDiscovery,
    WindowsAppLauncher,
    WindowsApplicationController,
    WindowsDisplayManager,
    WindowsInputController,
    WindowsUIAutomation,
    WindowsUIAInspector,
    WindowsUIAInteraction,
    WindowsWindowManager,
    WindowsWorkspaceManager,
    WhatsAppController,
)

# Shared singletons for efficiency
app_discovery = WindowsAppDiscovery()
window_mgr = WindowsWindowManager()
app_launcher = WindowsAppLauncher(discovery=app_discovery, window_mgr=window_mgr)
app_catalog = WindowsAppCatalog(discovery=app_discovery, launcher=app_launcher, window_mgr=window_mgr)
uia_inspector = WindowsUIAInspector()
uia_interaction = WindowsUIAInteraction()
ui_auto = WindowsUIAutomation(inspector=uia_inspector, interaction=uia_interaction)
input_ctrl = WindowsInputController(window_mgr=window_mgr, uia_interaction=uia_interaction)
display_mgr = WindowsDisplayManager()
workspace_mgr = WindowsWorkspaceManager()
whatsapp_ctrl = WhatsAppController(
    launcher=app_launcher,
    inspector=uia_inspector,
    interaction=uia_interaction,
    input_ctrl=input_ctrl,
    window_mgr=window_mgr,
)
app_ctrl = WindowsApplicationController(
    app_catalog=app_catalog,
    window_mgr=window_mgr,
    ui_auto=ui_auto,
    input_ctrl=input_ctrl,
    whatsapp_ctrl=whatsapp_ctrl,
)

mcp = FastMCP("ZyeWindowsControl")


@mcp.tool()
def open_any_app(app_name: str = "", timeout: float = 20.0, **kwargs: Any) -> str:
    """
    Open any installed Windows application (Win32, Store, UWP) by name.
    Verifies that the window appears and is responsive before returning.
    """
    if not app_name:
        app_name = (
            kwargs.get("application")
            or kwargs.get("process_path")
            or kwargs.get("target_app")
            or kwargs.get("process_name")
            or kwargs.get("target_app_name")
            or kwargs.get("application_path")
            or kwargs.get("name")
            or kwargs.get("app")
            or ""
        )
    if isinstance(app_name, str):
        if "\\" in app_name or "/" in app_name:
            app_name = Path(app_name).stem
        if app_name.lower().endswith(".exe"):
            app_name = app_name[:-4]
    if not app_name:
        return json.dumps({
            "status": "FAILED",
            "error": "No application name specified to open_any_app",
            "verified": False,
        })
    res = app_launcher.open_any_app(app_name=app_name, timeout=timeout)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def list_installed_apps(force_refresh: bool = False) -> str:
    """
    Discover all installed Windows applications (Win32, Store, UWP).
    """
    res = app_catalog.discover_installed_apps(force_refresh=force_refresh)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def search_installed_apps(query: str) -> str:
    """
    Search installed applications by name, AppID, or keyword.
    """
    res = app_catalog.search_installed_apps(query=query)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def inspect_app_ui(window_keyword: str, max_controls: int = 60) -> str:
    """
    Inspect the Windows UI Automation (UIA) tree of an active application window.
    Returns names, control types, automation IDs, states, and available patterns.
    """
    res = uia_inspector.inspect_app_ui(window_keyword=window_keyword, max_controls=max_controls)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_ui_element_details(window_keyword: str, element_name: str) -> str:
    """
    Get exhaustive details (type, automation_id, state) for a specific UI element in a window.
    """
    res = ui_auto.get_ui_element_details(window_keyword=window_keyword, element_name=element_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def search_inside_application(app_name: str, query: str) -> str:
    """
    Find search box inside a running application, focus it, and type the query.
    """
    res = app_ctrl.search_inside_application(app_name=app_name, query=query)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_application_status(app_name: str) -> str:
    """
    Check if an application is running, count active processes, and check open window state.
    """
    res = app_ctrl.get_application_status(app_name=app_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def close_application_window(app_name: str = "", **kwargs: Any) -> str:
    """
    Close an open application window gracefully.
    """
    if not app_name:
        app_name = (
            kwargs.get("application")
            or kwargs.get("target_app")
            or kwargs.get("process_name")
            or kwargs.get("name")
            or kwargs.get("app")
            or ""
        )
    if isinstance(app_name, str) and (app_name.lower().endswith(".exe") or "\\" in app_name):
        app_name = Path(app_name).stem
    res = app_ctrl.close_application_window(app_name=app_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def click_ui_element(window_keyword: str, element_name: str, control_type: str = "") -> str:
    """
    Click or invoke a named UI control (Button, Tab, MenuItem, ListItem) within an active window.
    Uses native UIA patterns with controlled fallback.
    """
    res = uia_interaction.click_ui_element(
        window_keyword=window_keyword,
        element_name=element_name,
        control_type=control_type,
    )
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def type_into_app(
    window_keyword: str = "",
    text: str = "",
    element_name: str = "",
    press_enter: bool = False,
    **kwargs: Any,
) -> str:
    """
    Focus a named application and type text or code into it using clipboard paste.
    Supports HTML, CSS, JavaScript, Python, Tamil Unicode, Tanglish, and emojis without character loss.
    window_keyword: Name or title of the target application window (e.g. 'Notepad', 'Word', 'Chrome').
    text: The full text, code, or content to type/paste into the application.
    element_name: Optional name of the specific UI control (defaults to empty for main text area).
    press_enter: Whether to press Enter after inserting the text.
    """
    if not window_keyword:
        window_keyword = (
            kwargs.get("app_name") or kwargs.get("window") or kwargs.get("application")
            or kwargs.get("target_app") or kwargs.get("name") or "Notepad"
        )
    if not text:
        text = kwargs.get("content") or kwargs.get("code") or kwargs.get("body") or kwargs.get("data") or ""
    res = input_ctrl.type_into_app(
        window_keyword=window_keyword,
        element_name=element_name,
        text=text,
        press_enter=press_enter,
    )
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def press_hotkey(keys: list[str]) -> str:
    """
    Execute a validated keyboard shortcut combination (e.g. ['ctrl', 'v'], ['win', 'left'], ['alt', 'tab']).
    """
    res = input_ctrl.press_hotkey(keys=keys)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def search_whatsapp_contact(contact_name: str) -> str:
    """
    Search for a contact in WhatsApp Desktop by name or phone.
    Returns matching candidates or signals ambiguity.
    """
    res = whatsapp_ctrl.search_whatsapp_contact(contact_name=contact_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def open_whatsapp_chat(contact_name: str) -> str:
    """
    Open the WhatsApp chat conversation for the specified contact.
    """
    res = whatsapp_ctrl.open_whatsapp_chat(contact_name=contact_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def compose_whatsapp_message(contact_name: str, message: str) -> str:
    """
    Type a draft message into the active WhatsApp chat WITHOUT sending.
    """
    res = whatsapp_ctrl.compose_whatsapp_message(contact_name=contact_name, message=message)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def send_whatsapp_message(contact_name: str, message: str, confirmed: bool = False) -> str:
    """
    Send a WhatsApp message. Requires explicit authorization (confirmed=True).
    Protected by the Day 15 Safety Execution Gateway.
    """
    res = whatsapp_ctrl.send_whatsapp_message(contact_name=contact_name, message=message, confirmed=confirmed)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def start_whatsapp_voice_call(contact_name: str) -> str:
    """
    Initiate a WhatsApp voice call with a confirmed contact.
    """
    res = whatsapp_ctrl.start_whatsapp_voice_call(contact_name=contact_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def start_whatsapp_video_call(contact_name: str) -> str:
    """
    Initiate a WhatsApp video call with a confirmed contact.
    """
    res = whatsapp_ctrl.start_whatsapp_video_call(contact_name=contact_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def end_whatsapp_call() -> str:
    """
    Terminate any active WhatsApp voice or video call.
    """
    res = whatsapp_ctrl.end_whatsapp_call()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_whatsapp_call_status() -> str:
    """
    Query the active WhatsApp call state (idle, calling, connected).
    """
    res = whatsapp_ctrl.get_whatsapp_call_status()
    return json.dumps(res, indent=2, ensure_ascii=False)


# ============================================================================
# Day 18: Advanced Window, Workspace, Shortcut & Multi-Monitor Tools
# ============================================================================

@mcp.tool()
def list_open_windows(include_empty: bool = False) -> str:
    """
    List all visible top-level desktop windows with titles, HWNDs, PIDs, and coordinates.
    """
    res = window_mgr.list_open_windows(include_empty=include_empty)
    return json.dumps([w.model_dump() for w in res], indent=2, ensure_ascii=False)


@mcp.tool()
def find_window(query: str) -> str:
    """
    Search and disambiguate windows matching a title query.
    Returns exact match or list of candidate titles if multiple windows match.
    """
    res = window_mgr.find_window(query=query)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_active_window() -> str:
    """
    Retrieve the currently active foreground desktop window and geometry.
    """
    res = window_mgr.get_active_window()
    return json.dumps(res.model_dump() if res else None, indent=2, ensure_ascii=False)


@mcp.tool()
def move_window(window_id: str, x: int, y: int) -> str:
    """
    Move a desktop window to specified desktop coordinates (x, y).
    """
    res = window_mgr.move_window(window_id=window_id, x=x, y=y)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def resize_window(window_id: str, width: int, height: int) -> str:
    """
    Resize a desktop window to positive dimensions (width, height).
    """
    res = window_mgr.resize_window(window_id=window_id, width=width, height=height)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def center_window(window_id: str) -> str:
    """
    Center a desktop window on the primary screen.
    """
    res = window_mgr.center_window(window_id=window_id)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def execute_shortcut(shortcut_name: str) -> str:
    """
    Execute a validated Windows keyboard shortcut from the named registry.
    Supported: alt_tab, win_d, win_e, ctrl_c, ctrl_v, ctrl_z, ctrl_s, ctrl_shift_esc, alt_f4, etc.
    """
    res = input_ctrl.execute_shortcut(shortcut_name=shortcut_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_connected_displays() -> str:
    """
    Enumerate all connected physical and virtual display monitors.
    """
    res = display_mgr.get_connected_displays()
    return json.dumps([d.model_dump() for d in res], indent=2, ensure_ascii=False)


@mcp.tool()
def move_window_to_monitor(window_keyword: str, display_id: int) -> str:
    """
    Move a desktop window to a specified monitor display ID.
    """
    res = display_mgr.move_window_to_monitor(window_keyword=window_keyword, display_id=display_id)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_virtual_desktops() -> str:
    """
    List all active Windows virtual desktops and active desktop index.
    """
    res = workspace_mgr.get_virtual_desktops()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def create_virtual_desktop() -> str:
    """
    Create a new Windows virtual desktop (Win+Ctrl+D).
    """
    res = workspace_mgr.create_virtual_desktop()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def switch_virtual_desktop(target: str) -> str:
    """
    Switch to a virtual desktop. Target: 'next', 'previous', or desktop number ('1', '2').
    """
    res = workspace_mgr.switch_virtual_desktop(target=target)
    return json.dumps(res, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    logger.info("Starting Zye Windows Control MCP server over stdio...")
    mcp.run(transport="stdio")
