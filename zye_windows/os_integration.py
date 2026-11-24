"""
Master Windows OS Integration Facade — Zye Day 19.
Unified, single-entry interface binding Window, Workspace, Display, Input, Clipboard,
File Search, Media, Screenshot, Hardware, Process, and Application controllers together.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from zye_windows.app_catalog import WindowsAppCatalog
from zye_windows.application_controller import WindowsApplicationController
from zye_windows.clipboard_manager import WindowsClipboardManager
from zye_windows.display_manager import WindowsDisplayManager
from zye_windows.file_search import WindowsFileSearch
from zye_windows.hardware_manager import WindowsHardwareManager
from zye_windows.input_controller import WindowsInputController
from zye_windows.media_controller import WindowsMediaController
from zye_windows.process_manager import WindowsProcessManager
from zye_windows.recycle_bin_manager import WindowsRecycleBinManager
from zye_windows.screenshot_manager import WindowsScreenshotManager
from zye_windows.ui_automation import WindowsUIAutomation
from zye_windows.window_manager import WindowsWindowManager
from zye_windows.workspace_manager import WindowsWorkspaceManager

logger = logging.getLogger("zye.windows.os_integration")


class WindowsOSIntegration:
    """
    Master Integration Facade providing unified access across all Windows OS automation subsystems.
    """

    def __init__(self) -> None:
        self.window_mgr = WindowsWindowManager()
        self.workspace_mgr = WindowsWorkspaceManager()
        self.display_mgr = WindowsDisplayManager()
        self.input_ctrl = WindowsInputController()
        self.clipboard_mgr = WindowsClipboardManager()
        self.file_search = WindowsFileSearch()
        self.media_ctrl = WindowsMediaController()
        self.screenshot_mgr = WindowsScreenshotManager()
        self.recycle_bin_mgr = WindowsRecycleBinManager()
        self.hardware_mgr = WindowsHardwareManager()
        self.process_mgr = WindowsProcessManager()
        self.app_catalog = WindowsAppCatalog(window_mgr=self.window_mgr)
        self.ui_auto = WindowsUIAutomation(input_ctrl=self.input_ctrl)
        self.app_ctrl = WindowsApplicationController(
            app_catalog=self.app_catalog,
            process_mgr=self.process_mgr,
            window_mgr=self.window_mgr,
            ui_auto=self.ui_auto,
            input_ctrl=self.input_ctrl,
        )

    # 1. Window Management
    def list_windows(self) -> list[dict[str, Any]]:
        return [w.model_dump() for w in self.window_mgr.list_open_windows()]

    def focus_window(self, title: str) -> dict[str, Any]:
        return self.window_mgr.focus_window(title)

    def snap_window_left(self, title: str) -> dict[str, Any]:
        return self.window_mgr.snap_left(title)

    def snap_window_right(self, title: str) -> dict[str, Any]:
        return self.window_mgr.snap_right(title)

    def center_window(self, title: str) -> dict[str, Any]:
        return self.window_mgr.center_window(title)

    def close_window(self, title: str) -> dict[str, Any]:
        return self.window_mgr.manage_window(title, "close")

    # 2. Virtual Desktops
    def get_virtual_desktops(self) -> dict[str, Any]:
        return self.workspace_mgr.get_virtual_desktops()

    def create_virtual_desktop(self) -> dict[str, Any]:
        return self.workspace_mgr.create_virtual_desktop()

    def switch_virtual_desktop(self, direction: str = "right") -> dict[str, Any]:
        return self.workspace_mgr.switch_virtual_desktop(direction)

    # 3. Displays
    def get_connected_displays(self) -> list[dict[str, Any]]:
        return [d.model_dump() for d in self.display_mgr.get_connected_displays()]

    def move_window_to_monitor(self, title: str, monitor_id: int) -> dict[str, Any]:
        return self.display_mgr.move_window_to_monitor(title, monitor_id)

    # 4. Input & Dictation
    def execute_shortcut(self, shortcut_name: str) -> dict[str, Any]:
        return self.input_ctrl.execute_shortcut(shortcut_name)

    def scroll(self, direction: str = "down", steps: int = 5) -> dict[str, Any]:
        return self.input_ctrl.scroll_page(direction, steps)

    def dictate_text(self, text: str, submit: bool = False) -> dict[str, Any]:
        return self.input_ctrl.dictate_text_anywhere(text, press_enter=submit)

    # 5. Clipboard
    def get_clipboard_metadata(self) -> dict[str, Any]:
        return self.clipboard_mgr.get_clipboard_metadata().model_dump()

    def clear_clipboard(self) -> dict[str, Any]:
        return self.clipboard_mgr.clear_clipboard()

    # 6. File Search
    def search_files(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return [r.model_dump() for r in self.file_search.search_local_files(query, limit=limit)]

    def open_local_file(self, query: str) -> dict[str, Any]:
        return self.file_search.find_and_open_local_file(query, open_file=True)

    # 7. Media Controls
    def get_media_session(self) -> dict[str, Any]:
        return self.media_ctrl.get_active_media_session().model_dump()

    def control_media(self, action: str) -> dict[str, Any]:
        return self.media_ctrl.control_media(action)

    # 8. Screenshots
    def capture_screenshot(self, active_window_only: bool = False) -> dict[str, Any]:
        if active_window_only:
            return self.screenshot_mgr.capture_active_window().model_dump()
        return self.screenshot_mgr.capture_screen().model_dump()

    # 9. Hardware
    def get_hardware_status(self) -> dict[str, Any]:
        return self.hardware_mgr.get_hardware_status()

    def set_volume(self, level: int) -> dict[str, Any]:
        return self.hardware_mgr.set_volume(level)

    def set_brightness(self, level: int) -> dict[str, Any]:
        return self.hardware_mgr.set_brightness(level)

    # 10. Process Management
    def list_processes(self, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
        return self.process_mgr.list_processes(query=query, limit=limit)

    def get_system_resources(self) -> dict[str, Any]:
        return self.process_mgr.get_system_resource_summary()

    def terminate_process(self, pid: int, force: bool = False, confirmed: bool = False) -> dict[str, Any]:
        return self.process_mgr.terminate_process(pid=pid, force=force, confirmed=confirmed)

    # 11. Application Control
    def open_app(self, app_name: str) -> dict[str, Any]:
        return self.app_ctrl.open_application(app_name)

    def inspect_app(self, app_name: str) -> dict[str, Any]:
        return self.app_ctrl.inspect_application(app_name)

    def click_app_control(self, app_name: str, control_name: str) -> dict[str, Any]:
        return self.app_ctrl.click_application_control(app_name, control_name)

    def type_app_text(self, app_name: str, field_name: str, text: str) -> dict[str, Any]:
        return self.app_ctrl.type_application_text(app_name, field_name, text)
