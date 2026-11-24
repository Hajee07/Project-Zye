"""
Zye Master OS & Hardware Control MCP Server (Day 16).
Unified FastMCP server exposing 14 core tools for volume control, screen brightness,
battery status, power management, window snapping/manipulation, hands-free scrolling,
universal dictation, clipboard inspection, local file search, media keys, screenshots,
and safe Recycle Bin management.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Optional

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
logger = logging.getLogger("zye.system_os.mcp")

from zye_windows import (
    WindowsAppLifecycle,
    WindowsBrightnessManager,
    WindowsClipboardManager,
    WindowsFileSearch,
    WindowsHardwareManager,
    WindowsInputController,
    WindowsMediaController,
    WindowsPowerManager,
    WindowsProcessManager,
    WindowsProcessMonitor,
    WindowsRecycleBinManager,
    WindowsScreenshotManager,
    WindowsVolumeManager,
    WindowsWindowManager,
)

# Shared singletons
volume_mgr = WindowsVolumeManager()
brightness_mgr = WindowsBrightnessManager()
power_mgr = WindowsPowerManager()
hardware_mgr = WindowsHardwareManager(volume_mgr=volume_mgr, brightness_mgr=brightness_mgr, power_mgr=power_mgr)
window_mgr = WindowsWindowManager()
input_ctrl = WindowsInputController(window_mgr=window_mgr)
clipboard_mgr = WindowsClipboardManager()
file_search = WindowsFileSearch()
media_ctrl = WindowsMediaController()
screenshot_mgr = WindowsScreenshotManager()
process_mgr = WindowsProcessManager()
recycle_bin_mgr = WindowsRecycleBinManager()
app_lifecycle = WindowsAppLifecycle(window_manager=window_mgr, process_manager=process_mgr)
process_monitor = WindowsProcessMonitor()

mcp = FastMCP("ZyeSystemOS")


@mcp.tool()
def control_volume(action: str, steps: int = 5) -> str:
    """
    Adjust system volume. Actions: 'up', 'down', 'mute', 'unmute'.
    Steps: number of volume key increments (1..20).
    """
    res = volume_mgr.control_volume(action=action, steps=steps)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def set_volume_percent(level: int) -> str:
    """
    Set master volume to an exact percentage between 0 and 100.
    """
    res = volume_mgr.set_volume_percent(level=level)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def set_brightness(level: int) -> str:
    """
    Set primary screen brightness to a percentage between 0 and 100.
    """
    res = brightness_mgr.set_brightness(level=level)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_battery_status() -> str:
    """
    Query battery percentage, AC power status, and remaining time telemetry.
    """
    res = power_mgr.get_battery_status()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def media_control(command: str = "play_pause", action: str | None = None) -> str:
    """
    Control global media playback sessions.
    Supported: 'play_pause', 'play', 'pause', 'next', 'previous', 'stop'.
    """
    effective_cmd = action or command or "play_pause"
    res = media_ctrl.media_control(command=effective_cmd)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def power_action(action: str, confirmed: bool = False) -> str:
    """
    Perform Windows power management action: 'lock', 'sleep', 'shutdown', 'restart'.
    Shutdown and restart require explicit user confirmation (confirmed=True).
    """
    res = power_mgr.power_action(action=action, confirmed=confirmed)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def manage_window(window_keyword: str = "", action: str = "focus", **kwargs: Any) -> str:
    """
    Manage an application window.
    Actions: 'focus', 'minimize', 'maximize', 'close', 'restore', 'snap_left', 'snap_right'.
    """
    if not window_keyword:
        window_keyword = kwargs.get("keyword") or kwargs.get("app_name") or kwargs.get("name") or ""
    if not action:
        action = kwargs.get("act") or "focus"
    res = window_mgr.manage_window(window_keyword=window_keyword, action=action)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def scroll_page(direction: str = "down", amount: int = 5) -> str:
    """
    Hands-free mouse wheel page scrolling. Direction: 'up' or 'down'. Amount: 1..25 clicks.
    """
    res = volume_mgr.scroll_page(direction=direction, amount=amount)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def dictate_text_anywhere(text: str = "", press_enter: bool = False, **kwargs: Any) -> str:
    """
    Type text or code into whichever window currently has active focus using clipboard paste.
    Supports Tamil Unicode, Tanglish, emojis, HTML, CSS, JS, Python, and code without corruption.
    """
    if not text:
        text = kwargs.get("content") or kwargs.get("code") or kwargs.get("body") or kwargs.get("data") or ""
    res = input_ctrl.dictate_text_anywhere(text=text, press_enter=press_enter)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_clipboard_text(max_chars: int = 2000) -> str:
    """
    Read the current text content of the clipboard safely upon explicit user command.
    """
    res = clipboard_mgr.get_clipboard_text(max_chars=max_chars)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def find_and_open_local_file(filename_query: str, open_file: bool = False) -> str:
    """
    Search for files in Desktop, Documents, Downloads, and Videos.
    Optionally open the file using default Windows association if unambiguous.
    """
    res = file_search.find_and_open_local_file(filename_query=filename_query, open_file=open_file)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def capture_screenshot(save_path: Optional[str] = None) -> str:
    """
    Capture an on-demand desktop screenshot upon explicit user request.
    Saves to local logs/screenshots/ directory.
    """
    res = screenshot_mgr.capture_screenshot(save_path=save_path)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def preview_recycle_bin() -> str:
    """
    Stage 1: Inspect number of items and total size in Windows Recycle Bin without deleting anything.
    """
    res = recycle_bin_mgr.preview_recycle_bin()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def empty_recycle_bin(confirmed: bool = False) -> str:
    """
    Stage 2: Permanently empty the Windows Recycle Bin. Requires explicit confirmation (confirmed=True).
    """
    res = recycle_bin_mgr.empty_recycle_bin(confirmed=confirmed)
    return json.dumps(res, indent=2, ensure_ascii=False)


# ============================================================================
# Day 17: Process Management, App Lifecycle, & Resource Telemetry Tools
# ============================================================================

@mcp.tool()
def list_running_processes(query: str = "", limit: int = 50, include_details: bool = False) -> str:
    """
    List currently running processes with PID, executable name, and memory footprint.
    Optionally filter by name query and include CPU/parent process details.
    """
    res = process_mgr.list_running_processes(query=query, limit=limit, include_details=include_details)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def list_processes(query: str = "", limit: int = 50, sort_by: str = "memory") -> str:
    """
    List running Windows processes with filtering by name, configurable limit, and sorting by memory or CPU.
    """
    res = process_mgr.list_processes(query=query, limit=limit, sort_by=sort_by)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def find_process_by_name(name: str) -> str:
    """
    Find all running processes matching the exact or partial executable name.
    """
    res = process_mgr.find_process_by_name(name=name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_process_details(pid: int) -> str:
    """
    Fetch comprehensive telemetry and metadata for a specific process ID,
    including parent PID, create time, memory MB, CPU percent, and thread count.
    """
    res = process_mgr.get_process_details(pid=pid)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_system_resource_summary() -> str:
    """
    Query real-time overall CPU percent, RAM metrics, active process counts,
    and top memory/CPU consumers on-demand.
    """
    res = process_mgr.get_system_resource_summary()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def start_application_process(
    application: str = "",
    args: Optional[list[str]] = None,
    **kwargs: Any,
) -> str:
    """
    Safely start an approved application process without shell=True to prevent command injection.
    Accepts application name, process_path, or target_app aliases.
    """
    if not application:
        application = (
            kwargs.get("process_path")
            or kwargs.get("target_app")
            or kwargs.get("process_name")
            or kwargs.get("target_app_name")
            or kwargs.get("application_path")
            or kwargs.get("app_name")
            or kwargs.get("name")
            or kwargs.get("app")
            or ""
        )
    if isinstance(application, str):
        if "\\" in application or "/" in application:
            application = Path(application).stem
        if application.lower().endswith(".exe"):
            application = application[:-4]
    res = process_mgr.start_application_process(application=application, args=args)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def request_process_termination(pid: int, expected_name: str = "") -> str:
    """
    Inspect target process for termination, verify protected status and PID reuse,
    and describe confirmation requirements.
    """
    res = process_mgr.request_process_termination(pid=pid, confirmed=False, expected_name=expected_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def verify_process_status(pid: int) -> str:
    """
    Verify whether a process with specified PID is active and running.
    """
    res = process_mgr.verify_process_status(pid=pid)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_top_processes(sort_by: str = "memory", limit: int = 10) -> str:
    """
    Rank running processes by 'memory' or 'cpu' utilization.
    """
    res = process_mgr.get_top_processes(sort_by=sort_by, limit=limit)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def check_process_responsiveness(pid: int) -> str:
    """
    Check if a process is alive and responding or hung/frozen.
    """
    res = process_mgr.check_process_responsiveness(pid=pid)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_process_tree(pid: int) -> str:
    """
    Inspect the process lineage (parent process and child processes) for a PID.
    """
    res = process_mgr.get_process_tree(pid=pid)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def terminate_process(
    pid: int,
    force: bool = False,
    confirmed: bool = False,
    expected_name: str = "",
) -> str:
    """
    Safely terminate a user process with validation gates.
    force=False attempts graceful termination. force=True requires explicit confirmed=True.
    Protected Windows system processes cannot be terminated.
    """
    res = process_mgr.terminate_process(
        pid=pid,
        force=force,
        confirmed=confirmed,
        expected_name=expected_name,
    )
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_system_resource_snapshot() -> str:
    """
    Query real-time overall host CPU percent, RAM usage (total, used, percent), and total active PIDs.
    """
    res = process_monitor.get_system_snapshot()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_application_health(app_name: str) -> str:
    """
    Evaluate the end-to-end runtime health, responsiveness, and resource consumption of an application.
    """
    res = app_lifecycle.get_application_health(app_name=app_name)
    return json.dumps(res, indent=2, ensure_ascii=False)


# ============================================================================
# Day 18: File Search, Media Sessions, Clipboard Metadata & Screenshots
# ============================================================================

@mcp.tool()
def get_clipboard_metadata() -> str:
    """
    Inspect clipboard metadata (character count, line count, Unicode flag) without exposing raw text.
    """
    res = clipboard_mgr.get_clipboard_metadata()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def search_local_files(query: str, directories: Optional[list[str]] = None, limit: int = 10) -> str:
    """
    Search for files in Desktop, Documents, Downloads, Videos with limit and extension filtering.
    """
    res = file_search.search_local_files(query=query, directories=directories, limit=limit)
    return json.dumps([r.model_dump() for r in res], indent=2, ensure_ascii=False)


@mcp.tool()
def get_file_details(path: str) -> str:
    """
    Inspect canonical file details, size, modified timestamp, and executable status.
    """
    res = file_search.get_file_details(path=path)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_active_media_session() -> str:
    """
    Identify active desktop media playback session (Spotify, VLC, browser YouTube).
    """
    res = media_ctrl.get_active_media_session()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def get_media_session_details() -> str:
    """
    Retrieve full metadata for the currently active media session.
    """
    res = media_ctrl.get_media_session_details()
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def capture_active_window(save_path: Optional[str] = None) -> str:
    """
    Capture a screenshot cropped specifically to the currently active foreground window.
    """
    res = screenshot_mgr.capture_active_window(save_path=save_path)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def list_screenshots(limit: int = 20) -> str:
    """
    List previously captured screenshots in the local storage directory.
    """
    res = screenshot_mgr.list_screenshots(limit=limit)
    return json.dumps(res, indent=2, ensure_ascii=False)


@mcp.tool()
def delete_screenshot(path: str, confirmed: bool = False) -> str:
    """
    Safely delete a captured screenshot file. Requires confirmation (confirmed=True).
    """
    res = screenshot_mgr.delete_screenshot(path=path, confirmed=confirmed)
    return json.dumps(res, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    logger.info("Starting Zye System OS Control MCP server over stdio...")
    mcp.run(transport="stdio")
