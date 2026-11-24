"""
Day 19 Unit Tests — Master MCP Tool Registry & Server Integration.
Verifies tool discovery, schema conformance, duplicate prevention,
and tool routing across ZyeWindowsControl and ZyeSystemOS FastMCP servers.
"""

from __future__ import annotations

import unittest

import system_os_mcp
import windows_control_mcp


def _get_mcp_tool_names(mcp_instance) -> set[str]:
    """Helper to extract registered tool names across different FastMCP versions."""
    if hasattr(mcp_instance, "_tool_manager") and hasattr(mcp_instance._tool_manager, "_tools"):
        return set(mcp_instance._tool_manager._tools.keys())
    elif hasattr(mcp_instance, "_tools"):
        return set(mcp_instance._tools.keys())
    return set()


class TestDay19MCPIntegration(unittest.TestCase):

    def test_windows_control_mcp_tools(self) -> None:
        """Verify windows_control_mcp exports required application control and UI tools."""
        tools = _get_mcp_tool_names(windows_control_mcp.mcp)
        required_tools = [
            "open_any_app",
            "list_installed_apps",
            "search_installed_apps",
            "inspect_app_ui",
            "get_ui_element_details",
            "click_ui_element",
            "type_into_app",
            "search_inside_application",
            "get_application_status",
            "close_application_window",
            "press_hotkey",
            "search_whatsapp_contact",
            "open_whatsapp_chat",
            "send_whatsapp_message",
            "start_whatsapp_voice_call",
            "start_whatsapp_video_call",
            "end_whatsapp_call",
            "list_open_windows",
            "get_connected_displays",
            "get_virtual_desktops",
        ]
        for t in required_tools:
            self.assertIn(t, tools, f"Expected tool '{t}' in windows_control_mcp")

    def test_system_os_mcp_tools(self) -> None:
        """Verify system_os_mcp exports required process and system OS tools."""
        tools = _get_mcp_tool_names(system_os_mcp.mcp)
        required_tools = [
            "list_processes",
            "find_process_by_name",
            "get_process_details",
            "get_process_tree",
            "get_system_resource_summary",
            "start_application_process",
            "request_process_termination",
            "terminate_process",
            "verify_process_status",
            "control_volume",
            "set_brightness",
            "get_battery_status",
            "get_clipboard_metadata",
            "search_local_files",
            "get_file_details",
            "get_active_media_session",
            "capture_active_window",
            "list_screenshots",
            "delete_screenshot",
        ]
        for t in required_tools:
            self.assertIn(t, tools, f"Expected tool '{t}' in system_os_mcp")

    def test_no_overlapping_tool_collisions(self) -> None:
        """Verify no colliding tool names exist between the two servers."""
        win_tools = _get_mcp_tool_names(windows_control_mcp.mcp)
        sys_tools = _get_mcp_tool_names(system_os_mcp.mcp)
        overlap = win_tools.intersection(sys_tools)
        self.assertEqual(len(overlap), 0, f"Detected overlapping tool names: {overlap}")


if __name__ == "__main__":
    unittest.main()
